"""Inferencia exacta de una red bayesiana categórica mediante enumeración."""
from fractions import Fraction
from itertools import combinations
from math import prod

from ..core import (assignment, dag, domains, fields, labels, matches, probability,
                    require, rows, worlds)

from ..core.audit import pointer_child
from ..core.graph import ancestors, separated
from .evidence_patterns import expand, verify
from .legal_2013 import PATTERNS as PATTERNS_2013, evidence_paths, validate_tables

VERSION = "bn-exact-fnl-2012-2013"
LEGACY_VERSION = "fnl-2013-exact"


def historical_contract(operation, model, params):
    patterns = model.get("idioms", [])
    expanded = type(patterns) is list and any(
        type(item) is dict and type(item.get("kind")) is str and item["kind"] in PATTERNS_2013
        for item in patterns
    )
    return operation in {"infer", "sensitivity"} and "soft_evidence" not in params and not expanded


class Network:
    def __init__(self, model, budget, *, structural=False):
        fields(model, "domains nodes", "idioms")
        self.states = domains(model["domains"])
        require(bool(self.states), "Red vacía")
        nodes = model["nodes"]
        require(type(nodes) is dict and nodes.keys() <= self.states.keys(), "Nodos inválidos")
        require(nodes.keys() == self.states.keys(), "Faltan nodos o parámetros", "insufficient_data")
        added, self.certificates = expand(model.get("idioms", []), self.states, budget)
        self.parents = {}
        for name, node in sorted(nodes.items()):
            required = ([] if structural else ["rows"]) + ([] if name in added else ["parents"])
            fields(node, " ".join(required), "parents rows")
            declared = labels(node.get("parents", []))
            self.parents[name] = sorted(set(declared) | added.get(name, set()))
        self.order = dag(self.parents, self.states)
        verify(self.certificates, self.parents, budget)
        self.tables = {}
        self.row_locations = {}
        for name in self.order:
            if "rows" in nodes[name]:
                self.tables[name] = rows(nodes[name]["rows"], self.parents[name], self.states,
                                         budget, lambda values: self.decode(name, values))
                prefix = pointer_child("/model/nodes", name)
                self.row_locations[name] = {
                    key: f"{prefix}/rows/{index}/then" for index, key in enumerate(self.tables[name])
                }

        validate_tables(self.certificates, self, {}, budget)

    def decode(self, node, values):
        require(type(values) is dict and values.keys() <= set(self.states[node]), "Categorías inválidas")
        require(values.keys() == set(self.states[node]), "Faltan probabilidades", "insufficient_data")
        weights = {key: probability(value) for key, value in values.items()}
        require(sum(weights.values()) == 1, "La fila condicional debe sumar uno")
        return weights

    def altered(self, updates, budget):
        require(type(updates) is list and bool(updates), "Se requieren filas de sensibilidad")
        changes = {}
        for update in updates:
            budget.tick()
            fields(update, "node when then")
            name = update["node"]
            require(type(name) is str and name in self.states, "Nodo desconocido")
            parents = self.parents[name]
            given = assignment(update["when"], self.states, parents)
            key = tuple(given[parent] for parent in parents)
            require((name, key) not in changes, "Fila de sensibilidad duplicada")
            changes[name, key] = self.decode(name, update["then"])
        return changes

    def soft_weights(self, targets, evidence, changes, budget):
        selectors = [c for c in self.certificates if c["kind"] == "exclusive_explanations"]
        require(type(targets) is dict and len(targets) <= 1, "Se admite una distribución blanda por consulta")
        require(len(selectors) <= 1, "Se admite un selector de exclusión por consulta")
        conditioning = {}
        if selectors:
            cert = selectors[0]
            roles, settings = cert["roles"], cert["settings"]
            node = roles["selector"]
            if targets:
                require(node in targets, "La distribución blanda debe aplicarse al selector")
                distribution = self.decode(node, targets[node])
                require(distribution[settings["impossible"]] == 0, "La distribución blanda admite un estado imposible")
            else:
                causes = roles["causes"]
                upstream = ancestors(causes, self.parents, budget) - set(causes)
                conditioning = {key: value for key, value in evidence.items() if key in upstream}
                require(all(separated(a, b, conditioning, self.parents, budget) for a, b in combinations(causes, 2)),
                        "La calibración de exclusión requiere trayectorias separadas")
                distribution = {}
                for cause in causes:
                    posterior = self.infer(cause, conditioning, [], changes, budget)["posterior"]
                    require(posterior is not None, "Calibración sin soporte", "undefined_operation")
                    distribution[settings["pathways"][cause]] = Fraction(posterior[settings["active_states"][cause]])
                total = sum(distribution.values())
                require(bool(total), "Ninguna causa admite calibración", "undefined_operation")
                distribution = {state: mass / total for state, mass in distribution.items()}
                distribution[settings["impossible"]] = Fraction()

        elif targets:
            node, values = next(iter(targets.items()))
            require(node in self.states, "Nodo de evidencia blanda desconocido")
            distribution = self.decode(node, values)
        else:
            return {}, {}
        prior = self.infer(node, conditioning, [], changes, budget)["posterior"]
        require(prior is not None, "Evidencia blanda sin soporte de calibración", "undefined_operation")
        weights = {}
        for state, mass in distribution.items():
            base = Fraction(prior[state])
            require(not mass or base, "Evidencia blanda sin soporte", "undefined_operation")
            weights[state] = mass / base if base else Fraction()
        certificate = {"node": node, "method": "explicit_target" if targets else "exclusive_calibration",
                       "conditioning": conditioning,
                       "target": {state: str(mass) for state, mass in distribution.items()},
                       "weights": {state: str(weight) for state, weight in weights.items()}}
        return {node: weights}, certificate

    def update(self, hypothesis, evidence, alternatives, changes, budget, targets):
        soft, certificate = self.soft_weights(targets, evidence, changes, budget)
        require(not set(soft) & evidence.keys(), "El nodo con evidencia blanda no admite observación simultánea")
        result = self.infer(hypothesis, evidence, alternatives, changes, budget, soft)
        if soft:
            result["soft_evidence_certificate"] = certificate
        return result

    def infer(self, hypothesis, evidence, alternatives, changes, budget, soft=None):
        prior = dict.fromkeys(self.states[hypothesis], Fraction())
        joint = prior.copy()
        for values in worlds(self.order, self.states):
            budget.tick()
            state = dict(zip(self.order, values))
            factors = []
            for name in self.order:
                key = tuple(state[parent] for parent in self.parents[name])
                row = changes.get((name, key))
                if row is None:
                    row = self.tables[name][key]
                    budget.reads.add(pointer_child(self.row_locations[name][key], state[name]))
                factors.append(row[state[name]])
            weight = prod(factors, start=Fraction(1))
            if soft:
                node, weights = next(iter(soft.items()))
                weight *= weights[state[node]]
            prior[state[hypothesis]] += weight
            if matches(state, evidence):
                joint[state[hypothesis]] += weight
        normalizer = sum(prior.values(), Fraction())
        if soft and normalizer:
            prior = {state: value / normalizer for state, value in prior.items()}
            joint = {state: value / normalizer for state, value in joint.items()}
        observed_mass = sum(joint.values(), Fraction())
        result = {"evidence_probability": str(observed_mass),
                  "prior": {name: str(value) for name, value in prior.items()},
                  "posterior": None, "joint_masses": {name: str(value) for name, value in joint.items()}}
        if observed_mass:
            result["posterior"] = {name: str(value / observed_mass) for name, value in joint.items()}
        if alternatives:
            left, right = alternatives
            likelihood = {name: joint[name] / prior[name] if prior[name] else None
                          for name in alternatives}
            a, b = likelihood[left], likelihood[right]
            ratio = {"status": "undefined_operation", "value": None}
            if a is not None and b:
                ratio = {"status": "success", "value": str(a / b)}
            elif a and b == 0:
                ratio = {"status": "infinite", "value": None}
            result["comparison"] = {
                "numerator": left, "denominator": right,
                "likelihoods": {name: str(value) if value is not None else None
                                for name, value in likelihood.items()},
                "likelihood_ratio": ratio,
            }
        return result


def run(operation: str, model: dict, params: dict, budget) -> dict:
    if operation == "structure":
        fields(params, "hypothesis reports")
        network = Network(model, budget, structural=True)
        hypothesis = params["hypothesis"]
        reports = labels(params["reports"])
        require(type(hypothesis) is str and hypothesis in network.states, "Hipótesis desconocida")
        require(set(reports) <= network.states.keys() - {hypothesis}, "Informe desconocido")
        return {"structure_certificate": {"effective_parents": network.parents,
                    "pattern_certificates": network.certificates,
                    "nodes_without_tables": sorted(network.states.keys() - network.tables.keys()),
                    "evidence_paths": evidence_paths(hypothesis, reports, network.parents, network.order, budget)}}
    extras = {"infer": "", "sensitivity": "scenarios", "evidence_sequence": "sequence",
              "evidence_sensitivity": "reports"}
    require(operation in extras, "Operación bayesiana desconocida", "undefined_operation")
    fields(params, "hypothesis evidence " + extras[operation], "alternatives soft_evidence")
    network = Network(model, budget)
    hypothesis = params["hypothesis"]
    require(type(hypothesis) is str and hypothesis in network.states, "Hipótesis desconocida")
    evidence = assignment(params["evidence"], network.states)
    require(hypothesis not in evidence, "La variable de hipótesis está reservada para consulta")
    alternatives = labels(params["alternatives"]) if "alternatives" in params else []
    if "alternatives" in params:
        require(len(alternatives) == 2 and all(a in network.states[hypothesis] for a in alternatives),
                "Se requieren dos estados distintos de la hipótesis")
    targets = params.get("soft_evidence", {})
    baseline = network.update(hypothesis, evidence, alternatives, {}, budget, targets)
    soft_nodes = set(targets) | {cert["roles"]["selector"] for cert in network.certificates
                                 if cert["kind"] == "exclusive_explanations"}
    if network.certificates:
        baseline["pattern_certificates"] = network.certificates
        baseline["effective_parents"] = network.parents
    if operation == "infer":
        return baseline
    if operation == "evidence_sequence":
        require(type(params["sequence"]) is list and bool(params["sequence"]), "Secuencia vacía o inválida")
        cumulative = evidence.copy()
        sequence = []
        for step in params["sequence"]:
            observed = assignment(step, network.states)
            require(observed and not observed.keys() & ({hypothesis} | soft_nodes | cumulative.keys()),
                    "La secuencia requiere observaciones nuevas, sin reemplazos")
            cumulative.update(observed)
            updated = network.update(hypothesis, cumulative, alternatives, {}, budget, targets)
            sequence.append({"evidence": cumulative.copy(), **updated})
        return baseline | {"sequence": sequence}
    if operation == "evidence_sensitivity":
        reports = labels(params["reports"], nonempty=True)
        require(set(reports) <= network.states.keys() - ({hypothesis} | evidence.keys() | soft_nodes),
                "Informe de sensibilidad inválido o ya observado")
        variants = {}
        for report in reports:
            variants[report] = {state: network.update(hypothesis, evidence | {report: state},
                                                     alternatives, {}, budget, targets)
                                for state in network.states[report]}
        ranges = {}
        for report, distribution in variants.items():
            supported = [row["posterior"] for row in distribution.values() if row["posterior"] is not None]
            ranges[report] = {}
            for state in network.states[hypothesis]:
                values = [Fraction(posterior[state]) for posterior in supported]
                ranges[report][state] = {"min": str(min(values)), "max": str(max(values))} if values else None
        return baseline | {"evidence_sensitivity": variants, "evidence_sensitivity_ranges": ranges}
    scenarios = params["scenarios"]
    require(type(scenarios) is list and bool(scenarios), "Se requieren escenarios de sensibilidad")
    results = []
    for updates in scenarios:
        changes = network.altered(updates, budget)
        validate_tables(network.certificates, network, changes, budget)
        altered = network.update(hypothesis, evidence, alternatives, changes, budget, targets)
        delta = None
        if baseline["posterior"] is not None and altered["posterior"] is not None:
            delta = {name: str(Fraction(value) - Fraction(baseline["posterior"][name]))
                     for name, value in altered["posterior"].items()}
        results.append(altered | {"posterior_difference": delta,
                                  "status": "success" if altered["posterior"] else "undefined_operation"})
    return baseline | {"scenarios": results}
