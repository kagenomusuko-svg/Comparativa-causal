"""Certificados de suficiencia causal mediante mecanismos declarados."""
from ..core import fields, label, labels, require

from .ness_composition import reconstruct

VERSION = "wright-1985-declared"


def run(operation: str, model: dict, params: dict, budget) -> dict:
    if operation == "reconstruct":
        return reconstruct(model, params, budget)
    require(operation == "evaluate", "Operación NESS desconocida", "undefined_operation")
    fields(model, "conditions mechanisms complete")
    fields(params, "candidate effect")
    conditions = model["conditions"]
    require(type(conditions) is dict and all(label(k) and (v is None or type(v) is bool)
                                             for k, v in conditions.items()), "Condiciones inválidas")
    candidate, effect = params["candidate"], params["effect"]
    require(label(candidate) and label(effect) and candidate != effect, "Consulta inválida")
    require(candidate in conditions and effect in conditions, "Condición efectiva ausente", "insufficient_data")
    require(type(model["complete"]) is bool and type(model["mechanisms"]) is list, "Inventario inválido")
    present, unresolved = [], []
    seen = set()
    for mechanism in model["mechanisms"]:
        budget.tick()
        fields(mechanism, "id effect requires law provenance")
        require(all(label(mechanism[k]) for k in ("id", "effect", "law")), "Mecanismo inválido")
        labels(mechanism["provenance"], nonempty=True)
        antecedents = labels(mechanism["requires"], nonempty=True)
        require(mechanism["id"] not in seen, "Mecanismo duplicado")
        seen.add(mechanism["id"])
        target = mechanism["effect"]
        require(target in conditions and target not in antecedents and
                set(antecedents) <= conditions.keys(), "Antecedentes o consecuente inválidos")
        values = [conditions[name] for name in antecedents]
        if False in values:
            continue
        if None not in values:
            require(conditions[target] is not False, "Una ley activa contradice el efecto declarado")
        if target == effect:
            (unresolved if None in values else present).append(mechanism)
    require(conditions[effect] is not None, "Efecto efectivo desconocido", "insufficient_data")
    require(not (model["complete"] and conditions[effect] and not present and not unresolved),
            "El inventario exhaustivo no explica el efecto efectivo")
    if conditions[effect] is False or conditions[candidate] is False:
        return {"ness_cause": False, "necessary_across_declared_paths": None, "witnesses": []}
    alternatives = [rule for rule in present if candidate not in rule["requires"]]
    witnesses = []
    for rule in present:
        if candidate not in rule["requires"]:
            continue
        reduced = [name for name in rule["requires"] if name != candidate]
        for alternative in alternatives:
            budget.tick()
            if set(alternative["requires"]) <= set(reduced):
                break
        else:
            witnesses.append(rule | {"without_candidate": reduced})
    pending = [rule for rule in unresolved if candidate in rule["requires"]]
    require(bool(witnesses) or (conditions[candidate] is True and model["complete"] and not pending),
            "Información insuficiente para descartar un conjunto causal suficiente", "insufficient_data")
    uncovered = any(candidate not in rule["requires"] for rule in unresolved)
    necessary = None
    if alternatives:
        necessary = False
    elif witnesses and model["complete"] and not uncovered:
        necessary = True
    return {"ness_cause": bool(witnesses), "necessary_across_declared_paths": necessary,
            "witnesses": witnesses, "active_mechanisms": present, "alternative_mechanisms": alternatives,
            "unresolved_mechanisms": unresolved}
