"""Inferencia exacta de una red bayesiana categórica mediante enumeración."""
from fractions import Fraction
from math import prod

from ..core import (assignment, dag, domains, fields, labels, matches, probability,
                    require, rows, worlds)

VERSION = "fnl-2013-exact"


class Network:
    def __init__(self, model, budget):
        fields(model, "domains nodes")
        self.states = domains(model["domains"])
        require(bool(self.states), "Red vacía")
        nodes = model["nodes"]
        require(type(nodes) is dict and nodes.keys() <= self.states.keys(), "Nodos inválidos")
        require(nodes.keys() == self.states.keys(), "Faltan nodos o parámetros", "insufficient_data")
        self.parents = {}
        for name, node in sorted(nodes.items()):
            fields(node, "parents rows")
            self.parents[name] = labels(node["parents"])
        self.order = dag(self.parents, self.states)
        self.tables = {}
        for name in self.order:
            self.tables[name] = rows(nodes[name]["rows"], self.parents[name], self.states,
                                     budget, lambda values: self.decode(name, values))

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

    def infer(self, hypothesis, evidence, alternatives, changes, budget):
        prior = dict.fromkeys(self.states[hypothesis], Fraction())
        joint = prior.copy()
        for values in worlds(self.order, self.states):
            budget.tick()
            state = dict(zip(self.order, values))
            factors = []
            for name in self.order:
                key = tuple(state[parent] for parent in self.parents[name])
                row = changes.get((name, key), self.tables[name][key])
                factors.append(row[state[name]])
            weight = prod(factors, start=Fraction(1))
            prior[state[hypothesis]] += weight
            if matches(state, evidence):
                joint[state[hypothesis]] += weight
        observed_mass = sum(joint.values(), Fraction())
        result = {"evidence_probability": str(observed_mass),
                  "prior": {name: str(value) for name, value in prior.items()},
                  "posterior": None}
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
    require(operation in {"infer", "sensitivity"}, "Operación bayesiana desconocida", "undefined_operation")
    required = "hypothesis evidence scenarios" if operation == "sensitivity" else "hypothesis evidence"
    fields(params, required, "alternatives")
    network = Network(model, budget)
    hypothesis = params["hypothesis"]
    require(type(hypothesis) is str and hypothesis in network.states, "Hipótesis desconocida")
    evidence = assignment(params["evidence"], network.states)
    require(hypothesis not in evidence, "La variable de hipótesis está reservada para consulta")
    alternatives = labels(params["alternatives"]) if "alternatives" in params else []
    if "alternatives" in params:
        require(len(alternatives) == 2 and all(a in network.states[hypothesis] for a in alternatives),
                "Se requieren dos estados distintos de la hipótesis")
    baseline = network.infer(hypothesis, evidence, alternatives, {}, budget)
    if operation == "infer":
        return baseline
    scenarios = params["scenarios"]
    require(type(scenarios) is list and bool(scenarios), "Se requieren escenarios de sensibilidad")
    results = []
    for updates in scenarios:
        altered = network.infer(hypothesis, evidence, alternatives, network.altered(updates, budget), budget)
        delta = None
        if baseline["posterior"] is not None and altered["posterior"] is not None:
            delta = {name: str(Fraction(value) - Fraction(baseline["posterior"][name]))
                     for name, value in altered["posterior"].items()}
        results.append(altered | {"posterior_difference": delta,
                                  "status": "success" if altered["posterior"] else "undefined_operation"})
    return baseline | {"scenarios": results}
