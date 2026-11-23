"""Identificación por los criterios gráficos de Pearl, para efectos puntuales."""
from itertools import combinations
from fractions import Fraction

from ..core import assignment, dag, domains, fields, labels, matches, probability, require, rows, worlds
from ..core.graph import ancestors, separated


def cut_outgoing(parents, node):
    return {child: [parent for parent in values if parent != node]
            for child, values in parents.items()}


class Observational:
    def __init__(self, raw, states, budget):
        self.states = states
        self.names = tuple(states)
        self.table = rows(raw, self.names, states, budget, probability)
        require(sum(self.table.values()) == 1, "La distribución observacional debe sumar uno")
        self.budget = budget
        self.cache = {}

    def marginal(self, event):
        key = tuple(sorted(event.items()))
        if key not in self.cache:
            mass = Fraction()
            for values, weight in self.table.items():
                self.budget.tick()
                if weight and matches(dict(zip(self.names, values)), event):
                    mass += weight
            self.cache[key] = mass
        return self.cache[key]

    def conditional(self, event, given):
        denominator = self.marginal(given)
        require(bool(denominator), f"Falta soporte observacional en {given}", "not_identifiable")
        return self.marginal(given | event) / denominator


    def check_implied_independences(self, parents):
        tested = 0
        for left, right in combinations(self.names, 2):
            rest = [name for name in self.names if name not in {left, right}]
            for length in range(len(rest) + 1):
                for given in combinations(rest, length):
                    self.budget.tick()
                    if not separated(left, right, given, parents, self.budget):
                        continue
                    tested += 1
                    for values in worlds(given, self.states):
                        stratum = dict(zip(given, values))
                        marginal = self.marginal(stratum)
                        if not marginal:
                            continue
                        for a, b in worlds((left, right), self.states):
                            self.budget.tick()
                            left_event = stratum | {left: a}
                            right_event = stratum | {right: b}
                            joint = self.marginal(left_event | right_event)
                            require(joint * marginal == self.marginal(left_event) * self.marginal(right_event),
                                    f"La masa contradice la independencia gráfica {left}, {right} | {given}")
        return tested


def identify(model, params, budget):
    fields(model, "observed latent parents", "observational_distribution")
    fields(params, "treatment outcome criterion", "adjustment mediator")
    observed = domains(model["observed"])
    latent = labels(model["latent"])
    require(not observed.keys() & set(latent), "Nodos observados y latentes se solapan")
    names = set(observed) | set(latent)
    raw_parents = model["parents"]
    require(type(raw_parents) is dict and raw_parents.keys() == names, "Se requiere la lista de padres de cada nodo")
    parents = {node: labels(raw_parents[node]) for node in sorted(names)}
    dag(parents, raw_parents)
    treatment = assignment(params["treatment"], observed)
    outcome = assignment(params["outcome"], observed)
    require(len(treatment) == len(outcome) == 1 and not treatment.keys() & outcome.keys(),
            "Tratamiento y desenlace deben ser nodos observados distintos")
    x, y = next(iter(treatment)), next(iter(outcome))
    criterion = params["criterion"]
    require(criterion in ("backdoor", "frontdoor"), "Criterio no implementado", "undefined_operation")
    x_cut = cut_outgoing(parents, x)

    if criterion == "backdoor":
        fields(params, "treatment outcome criterion adjustment")
        adjustment = sorted(labels(params["adjustment"]))
        require(set(adjustment) <= observed.keys() - {x, y}, "Ajuste debe usar nodos observados distintos")
        checks = {
            "no_treatment_descendants": all(x not in ancestors({z}, parents, budget) for z in adjustment),
            "blocks_backdoor_paths": separated(x, y, adjustment, x_cut, budget),
        }
        formula = "sum_z P(y|x,z) P(z)"
    else:
        fields(params, "treatment outcome criterion mediator")
        mediator = params["mediator"]
        require(type(mediator) is str and mediator in observed.keys() - {x, y}, "Mediador observado inválido")
        z_cut = {node: [p for p in values if p != mediator]
                 for node, values in parents.items() if node != mediator}
        checks = {
            "intercepts_all_directed_paths": x not in ancestors({y}, z_cut, budget),
            "no_treatment_mediator_backdoor": separated(x, mediator, (), x_cut, budget),
            "treatment_blocks_mediator_outcome_backdoors":
                separated(mediator, y, (x,), cut_outgoing(parents, mediator), budget),
        }
        formula = "sum_z P(z|x) sum_x' P(y|z,x') P(x')"

    result = {"criterion": criterion, "checks": checks, "functional": formula, "probability": None}
    if not all(checks.values()):
        return result | {"status": "not_identifiable",
                         "diagnostics": ["El criterio solicitado no identifica el efecto en este grafo"]}
    if "observational_distribution" not in model:
        return result | {"status": "insufficient_data",
                         "diagnostics": ["El criterio identifica la fórmula, falta la distribución observacional"]}
    data = Observational(model["observational_distribution"], observed, budget)
    result["observed_independences_verified"] = data.check_implied_independences(parents)
    terms = []
    if criterion == "backdoor":
        for values in worlds(adjustment, observed):
            budget.tick()
            stratum = dict(zip(adjustment, values))
            weight = data.marginal(stratum)
            if weight:
                term = weight * data.conditional(outcome, treatment | stratum)
                terms.append({"stratum": stratum, "term": str(term)})
    else:
        for value in observed[mediator]:
            budget.tick()
            stratum = {mediator: value}
            weight = data.conditional(stratum, treatment)
            if not weight:
                continue
            inner = Fraction()
            for alternative in observed[x]:
                budget.tick()
                arm = {x: alternative}
                marginal = data.marginal(arm)
                if marginal:
                    inner += marginal * data.conditional(outcome, arm | stratum)
            terms.append({"stratum": stratum, "term": str(weight * inner)})
    return result | {"probability": str(sum((Fraction(row["term"]) for row in terms), Fraction())),
                     "terms": terms}
