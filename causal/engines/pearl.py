"""SCM recursivo finito con ecuaciones tabuladas."""
from collections import defaultdict
from fractions import Fraction

from ..core import (assignment, dag, domains, fields, labels, matches, probability,
                    require, rows, worlds)

from .identification import identify

VERSION = "pearl-2010"


class SCM:
    def __init__(self, model: dict, budget):
        fields(model, "exogenous endogenous equations", "prior")
        self.u = domains(model["exogenous"])
        self.v = domains(model["endogenous"])
        require(self.v and not self.u.keys() & self.v.keys(), "Firma SCM inválida")
        self.states = self.u | self.v
        equations = model["equations"]
        require(type(equations) is dict and equations.keys() <= self.v.keys(),
                "Ecuaciones inválidas o variable desconocida")
        require(equations.keys() == self.v.keys(),
                "Se requiere una ecuación por variable endógena", "insufficient_data")
        self.parents = {}
        for name, equation in sorted(equations.items()):
            fields(equation, "parents rows")
            self.parents[name] = labels(equation["parents"])
        self.order = tuple(n for n in dag(self.parents, self.states) if n in self.v)
        self.tables = {}
        for name in self.order:
            def decode(value):
                require(value in self.v[name], "Salida estructural fuera del dominio")
                return value

            self.tables[name] = rows(equations[name]["rows"], self.parents[name],
                                     self.states, budget, decode)
        self.budget = budget
        self.prior = None
        if "prior" in model:
            self.prior = rows(model["prior"], tuple(self.u), self.u, budget, probability)
            require(sum(self.prior.values()) == 1, "La masa exógena debe sumar uno")

    def solve(self, context: dict, interventions: dict) -> dict:
        self.budget.tick()
        state = context.copy()
        for name in self.order:
            if name in interventions:
                state[name] = interventions[name]
            else:
                key = tuple(state[parent] for parent in self.parents[name])
                state[name] = self.tables[name][key]
        return {name: state[name] for name in self.v}

    def contexts(self, partial: dict):
        for values in worlds(self.u, self.u):
            self.budget.tick()
            context = dict(zip(self.u, values))
            if matches(context, partial):
                yield context, self.prior[values] if self.prior is not None else None


def run(operation: str, model: dict, params: dict, budget) -> dict:
    if operation == "identify":
        return identify(model, params, budget)
    allowed = {
        "observe": ("query", "context observed"),
        "associate": ("query observed", "context"),
        "intervene": ("query do", "context"),
        "counterfactual": ("query do", "context observed"),
        "effect": ("query do baseline", ""),
    }
    require(operation in allowed, "Operación SCM desconocida", "undefined_operation")
    fields(params, *allowed[operation])
    scm = SCM(model, budget)
    query = assignment(params["query"], scm.v)
    require(bool(query), "Evento vacío")
    context = assignment(params.get("context", {}), scm.u)
    observed = assignment(params.get("observed", {}), scm.v)
    action = assignment(params.get("do", {}), scm.v)
    baseline = assignment(params.get("baseline", {}), scm.v)

    explicit_context = "context" in params or scm.prior is None
    if explicit_context and context.keys() == scm.u.keys() and operation not in {"associate", "effect"}:
        factual = scm.solve(context, {})
        require(matches(factual, observed), "Contexto incompatible con la observación", "undefined_operation")
        outcome = scm.solve(context, action) if action else factual
        return {"event": matches(outcome, query), "outcome": outcome, "factual": factual}

    require(scm.prior is not None or operation not in {"associate", "effect"},
            "Falta la masa conjunta exógena", "insufficient_data")
    outcomes = set()
    mass = defaultdict(Fraction)
    denominator = Fraction()
    effect_baseline = Fraction()
    for candidate, weight in scm.contexts(context):
        if weight == 0 or (observed and not matches(scm.solve(candidate, {}), observed)):
            continue
        outcome = scm.solve(candidate, action)
        key = tuple(outcome.items())
        outcomes.add(key)
        if weight is not None:
            mass[key] += weight
            denominator += weight
            if operation == "effect" and matches(scm.solve(candidate, baseline), query):
                effect_baseline += weight

    require(bool(outcomes), "Condicionamiento sin soporte", "undefined_operation")
    truth = {matches(dict(outcome), query) for outcome in outcomes}
    if scm.prior is None:
        require(len(truth) == 1, "El evento varía entre contextos compatibles", "not_identifiable")
        return {"event": truth.pop(), "compatible_outcomes": [dict(key) for key in sorted(outcomes)]}

    chance = sum((weight for key, weight in mass.items() if matches(dict(key), query)), Fraction())
    result = {
        "probability": str(chance / denominator),
        "conditioning_mass": str(denominator),
        "distribution": [{"assignment": dict(key), "probability": str(mass[key] / denominator)}
                         for key in sorted(mass)],
    }
    if operation == "effect":
        result["baseline_probability"] = str(effect_baseline / denominator)
        result["difference"] = str((chance - effect_baseline) / denominator)
    return result
