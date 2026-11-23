"""AC1–AC3 originales y responsabilidad de Chockler–Halpern."""
from fractions import Fraction
from itertools import combinations

from ..core import assignment, fields, matches, require, worlds
from .pearl import SCM

VERSION = "hp-2001-ch-2004"


def subsets(names, start=0, stop=None):
    for size in range(start, len(names) + 1 if stop is None else stop):
        yield from combinations(names, size)


def event(formula, states, budget, depth=0):
    require(depth < 128, "El efecto excede 128 niveles", "limit_exceeded")
    budget.tick()
    fields(formula, "", "eq not all any")
    require(len(formula) == 1, "El efecto debe tener un operador")
    operator, argument = next(iter(formula.items()))
    if operator == "eq":
        condition = assignment(argument, states)
        require(len(condition) == 1, "eq requiere un evento primitivo")
        return lambda state: matches(state, condition)
    if operator == "not":
        operand = event(argument, states, budget, depth + 1)
        return lambda state: not operand(state)
    require(type(argument) is list and bool(argument), "Operador booleano vacío o inválido")
    operands = [event(item, states, budget, depth + 1) for item in argument]
    combine = all if operator == "all" else any
    return lambda state: combine(operand(state) for operand in operands)


def witness(scm, context, actual, cause, effect, *, first=False):
    remaining = [name for name in scm.v if name not in cause]
    best = None
    for w in subsets(remaining):
        z = [name for name in scm.v if name not in w]
        for values in worlds(w, scm.v):
            budget = scm.budget
            budget.tick()
            contingency = dict(zip(w, values))
            changes = sum(actual[name] != contingency[name] for name in w)
            if best is not None and changes >= best["changes"]:
                continue
            for alternative in worlds(cause, scm.v):
                budget.tick()
                alternate = dict(zip(cause, alternative))
                if alternate == cause or effect(scm.solve(context, alternate | contingency)):
                    continue
                if all(effect(scm.solve(context, cause | contingency |
                                        {name: actual[name] for name in restored}))
                       for restored in subsets(z)):
                    best = {
                        "z": z, "w": contingency, "alternative": alternate, "changes": changes,
                        "actual_z": {name: actual[name] for name in z},
                        "stability_subsets_verified": 2 ** len(z),
                    }
                    if first or changes == 0:
                        return best
                    break
    return best


def run(operation: str, model: dict, params: dict, budget) -> dict:
    require(operation == "responsibility", "Operación HP desconocida", "undefined_operation")
    fields(params, "context candidate effect")
    scm = SCM(model, budget)
    context = assignment(params["context"], scm.u)
    require(context.keys() == scm.u.keys(), "Contexto efectivo incompleto", "insufficient_data")
    cause = assignment(params["candidate"], scm.v)
    require(bool(cause), "Candidato vacío")
    effect = event(params["effect"], scm.v, budget)
    actual = scm.solve(context, {})
    result = {"actual": actual, "ac1": matches(actual, cause) and effect(actual),
              "ac2": None, "ac3": None, "actual_cause": False, "responsibility": "0"}
    if not result["ac1"]:
        return result
    contingency = witness(scm, context, actual, cause, effect)
    result["ac2"] = contingency is not None
    if contingency is None:
        return result
    result["witness"] = contingency
    for subset in subsets(tuple(cause), start=1, stop=len(cause)):
        minimality_candidate = {name: cause[name] for name in subset}
        certificate = witness(scm, context, actual, minimality_candidate, effect, first=True)
        if certificate is not None:
            return result | {"ac3": False, "smaller_candidate": minimality_candidate,
                             "minimality_counterexample": certificate}
    return result | {"ac3": True, "actual_cause": True,
                     "responsibility": str(Fraction(1, 1 + contingency["changes"]))}
