"""NESS con composición declarada de vías estables en un DAG de condiciones."""
from itertools import product

from ..core import Failure, dag, fields, label, labels, require


def validate(model, candidate, effect, budget):
    fields(model, "conditions mechanisms complete roots")
    conditions = model["conditions"]
    require(type(conditions) is dict and all(label(k) and (v is None or type(v) is bool)
                                             for k, v in conditions.items()), "Condiciones inválidas")
    require({candidate, effect} <= conditions.keys(), "Faltan condiciones de la consulta", "insufficient_data")
    roots = set(labels(model["roots"]))
    require(roots <= conditions.keys(), "Raíz desconocida")
    require(type(model["complete"]) is bool and type(model["mechanisms"]) is list, "Inventario inválido")
    rules = {name: [] for name in conditions}
    parents = {name: set() for name in conditions}
    seen = set()
    for rule in model["mechanisms"]:
        budget.tick()
        fields(rule, "id effect requires law provenance composable")
        require(all(label(rule[k]) for k in ("id", "effect", "law")), "Mecanismo inválido")
        require(type(rule["composable"]) is bool, "La estabilidad para composición debe declararse")
        labels(rule["provenance"], nonempty=True)
        required = set(labels(rule["requires"], nonempty=True))
        target = rule["effect"]
        require(target in conditions and target not in roots and required <= conditions.keys(),
                "Dominio de mecanismo inválido")
        require(rule["id"] not in seen, "Mecanismo duplicado")
        seen.add(rule["id"])
        parents[target].update(required)
        rules[target].append(rule)
        if all(conditions[name] is True for name in required):
            require(conditions[target] is not False, "Mecanismo efectivo contradice su efecto")
    order = dag({key: sorted(value) for key, value in parents.items()}, conditions)
    return conditions, roots, rules, order


def closure(seeds, active, order, budget):
    present = set(seeds)
    for node in order:
        for rule in active[node]:
            budget.tick()
            if set(rule["requires"]) <= present:
                present.add(node)
                break
    return present


def evaluate(model, candidate, effect, budget):
    conditions, roots, rules, order = validate(model, candidate, effect, budget)
    if conditions[effect] is False or conditions[candidate] is False:
        return {"status": "not_causal", "witnesses": [], "necessary_across_declared_paths": None}
    if conditions[effect] is None or conditions[candidate] is None:
        return {"status": "undetermined", "witnesses": [], "necessary_across_declared_paths": None}
    active = {node: [] for node in conditions}
    gaps = []
    for node in order:
        if conditions[node] is False:
            continue
        specified = False
        for rule in rules[node]:
            if any(conditions[name] is False for name in rule["requires"]):
                continue
            specified = True
            if not rule["composable"] or conditions[node] is None or any(
                conditions[name] is None for name in rule["requires"]
            ):
                gaps.append({"mechanism": rule["id"], "condition": node, "reason": "unverified_composition"})
            else:
                active[node].append(rule)
        if conditions[node] is True and node not in roots and not specified:
            gaps.append({"condition": node, "reason": "missing_mechanism"})

    # Each certificate may take the candidate itself as an actual antecedent.
    # Every other leaf must be a declared root.
    proofs = {node: {} for node in conditions}
    by_id = {rule["id"]: rule for alternatives in active.values() for rule in alternatives}
    for node in order:
        if conditions[node] is True and (node in roots or node == candidate):
            proofs[node][(frozenset({node}), frozenset())] = None
        for rule in active[node]:
            for premises in product(*(proofs[name] for name in rule["requires"])):
                budget.tick()
                leaves = frozenset().union(*(pair[0] for pair in premises))
                steps = frozenset({rule["id"]}).union(*(pair[1] for pair in premises))
                proofs[node][leaves, steps] = None

    witnesses = []
    for leaves, steps in proofs[effect]:
        budget.tick()
        if candidate not in leaves:
            continue
        reduced = leaves - {candidate}
        if effect not in closure(reduced, active, order, budget):
            witnesses.append({"set": sorted(leaves), "without_candidate": sorted(reduced),
                              "mechanisms": [by_id[name] for name in sorted(steps)]})

    # Restrict incompleteness diagnostics to ancestors of the queried effect.
    relevant = {effect}
    for node in reversed(order):
        if node in relevant:
            for rule in rules[node]:
                if not any(conditions[name] is False for name in rule["requires"]):
                    relevant.update(rule["requires"])
    gaps = [gap for gap in gaps if gap["condition"] in relevant]
    actual_roots = {name for name in roots if conditions[name] is True}
    without = actual_roots - {candidate}
    alternative = effect in closure(without, active, order, budget)
    source_set = actual_roots | {candidate}
    covered = effect in closure(source_set, active, order, budget)
    if not covered and model["complete"] and not gaps:
        raise Failure("invalid_model", "El inventario exhaustivo no deriva el efecto efectivo")
    if witnesses:
        status = "cause"
    elif gaps:
        status = "underspecified_mechanism"
    elif model["complete"]:
        status = "not_causal"
    else:
        status = "undetermined"
    necessary = False if alternative else None
    if witnesses and model["complete"] and not gaps and candidate in roots and not alternative:
        necessary = True
    return {"status": status, "witnesses": witnesses, "gaps": gaps,
            "necessary_across_declared_paths": necessary}


def reconstruct(model, params, budget):
    fields(model, "reconstructions")
    fields(params, "candidate effect")
    candidate, effect = params["candidate"], params["effect"]
    require(label(candidate) and label(effect) and candidate != effect, "Consulta inválida")
    alternatives = model["reconstructions"]
    require(type(alternatives) is list and bool(alternatives), "Se requieren reconstrucciones")
    results = []
    seen = set()
    for item in alternatives:
        budget.tick()
        fields(item, "id model")
        require(label(item["id"]) and item["id"] not in seen, "Identificador de reconstrucción inválido")
        seen.add(item["id"])
        results.append({"id": item["id"]} | evaluate(item["model"], candidate, effect, budget))
    verdicts = {result["status"] for result in results}
    status = verdicts.pop() if len(verdicts) == 1 else "undetermined"
    return {"conclusion": status, "reconstructions": results}
