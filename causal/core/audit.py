"""Cobertura por elemento e invalidación conservadora de resultados."""
from . import fields, label, labels, require


def pointer_child(pointer, component):
    return pointer + "/" + str(component).replace("~", "~0").replace("/", "~1")


def is_probability_input(pointer):
    parts = pointer.split("/")
    if parts[1:3] == ["model", "nodes"]:
        return len(parts) == 8 and parts[4] == "rows" and parts[6] == "then"
    if parts[1:3] == ["parameters", "scenarios"]:
        return len(parts) == 7 and parts[5] == "then"
    return parts[1:3] == ["parameters", "soft_evidence"] and len(parts) == 5


def leaves(value, pointer):
    pending = [(value, pointer)]
    while pending:
        current, path = pending.pop()
        if isinstance(current, dict) and current:
            children = current.items()
        elif isinstance(current, list) and current:
            children = enumerate(current)
        else:
            yield path
            continue
        pending.extend((child, pointer_child(path, key)) for key, child in children)


def coverage(request, records, dependency_order):
    targets = set(leaves(request["model"], "/model")) | set(leaves(request["parameters"], "/parameters"))
    declared = {record["pointer"]: record for record in records}
    effective_kinds = {}
    for pointer in dependency_order:
        record = declared[pointer]
        effective_kinds[pointer] = {base["kind"] for base in record["basis"]}
        for source in record["depends_on"]:
            effective_kinds[pointer].update(effective_kinds[source])
    grouped = {}
    groups = request.get("lineage_groups", [])
    require(type(groups) is list, "lineage_groups debe ser una lista")
    for group in groups:
        fields(group, "record members")
        source = group["record"]
        require(label(source) and source in declared, "Registro de agrupación inexistente")
        for member in labels(group["members"], nonempty=True):
            require(member in targets and member not in grouped, "Miembro de agrupación inválido o duplicado")
            grouped[member] = source
    report = []
    for target in sorted(targets):
        source = target if target in declared else grouped.get(target)
        report.append({"pointer": target, "coverage": "individual" if source == target else
                       "grouped" if source is not None else "missing",
                       "record": source, "basis_kinds": sorted(effective_kinds.get(source, ()))})
    return {"complete": all(row["record"] is not None for row in report), "elements": report}


def input_dependencies(request, trace):
    """Resuelve bases declaradas y dependencias documentales transitivas."""
    declared = {record["pointer"]: record for record in trace["elements"]}
    entries = {entry["id"]: (index, entry) for index, entry in enumerate(request["case"]["entries"])}
    referenced_paths = {}
    for pointer in trace["dependency_order"]:
        record = declared[pointer]
        paths = {pointer, pointer_child("/lineage", pointer)}
        for dependency in record["depends_on"]:
            paths.update(referenced_paths[dependency])
        pending = [base["ref"] for base in record["basis"] if base["kind"] != "derived"]
        visited = set()
        while pending:
            ref = pending.pop()
            if ref in visited:
                continue
            visited.add(ref)
            if ref in entries:
                index, entry = entries[ref]
                paths.add(f"/case/entries/{index}")
                pending.extend(entry.get("refs", []))
                pending.extend(link["target"] for link in entry.get("links", []))
            for key in ("assumptions", "modeling_hypotheses"):
                paths.update(f"/{key}/{i}" for i, value in enumerate(request.get(key, [])) if value == ref)
        referenced_paths[pointer] = paths
    return {row["pointer"]: {row["pointer"]} | (referenced_paths.get(row["record"], set()) - {row["record"]})
            for row in trace["coverage"]["elements"]}


STAGES = {
    "observe": ("solve_structural_equations", "condition_on_observation"),
    "associate": ("condition_on_observation", "normalize"),
    "intervene": ("replace_equations", "solve_structural_equations"),
    "counterfactual": ("abduce_context", "replace_equations", "predict"),
    "effect": ("evaluate_intervention_regimes", "subtract_probabilities"),
    "identify": ("verify_graphical_criterion", "standardize_observational_terms"),
    "responsibility": ("verify_ac1", "search_ac2", "test_ac3", "score_responsibility"),
    "evaluate": ("verify_actual_conditions", "test_sufficiency_and_necessity"),
    "reconstruct": ("compose_active_mechanisms", "test_reduced_sets", "aggregate_reconstructions"),
    "infer": ("factor_joint_mass", "marginalize", "condition"),
    "sensitivity": ("factor_joint_mass", "condition", "replace_rows", "compare_scenarios"),
    "structure": ("instantiate_fragments", "verify_graph_and_constraints"),
    "evidence_sequence": ("factor_joint_mass", "accumulate_evidence", "condition"),
    "evidence_sensitivity": ("factor_joint_mass", "vary_one_observation", "condition"),
}


ARTIFACTS = {
    "event": ("outcome",),
    "difference": ("probability", "baseline_probability"),
    "responsibility": ("ac1", "ac2", "ac3", "witness"),
    "ac2": ("witness",),
    "ac3": ("minimality_counterexample",),
    "ness_cause": ("witnesses",),
    "evidence_probability": ("joint_masses",),
    "posterior": ("joint_masses", "evidence_probability"),
    "comparison": ("joint_masses", "prior"),
    "conclusion": ("reconstructions",),
}


def execution_trace(response, request, trace, reads=()):
    result = response["result"]
    if result is None:
        return {"status": "unknown", "outputs": []}
    dependencies = input_dependencies(request, trace)
    inputs = sorted(set().union(*dependencies.values()))
    stages = STAGES.get(request["operation"], ())
    if request["operation"] == "responsibility":
        stages = ("verify_ac1",)
        if result["ac2"] is not None:
            stages += ("search_ac2",)
        if result["ac3"] is not None:
            stages += ("test_ac3",)
        stages += ("score_responsibility",)
    elif request["operation"] == "identify" and "terms" not in result:
        stages = ("verify_graphical_criterion",)
    outputs = []
    for key in sorted(result):
        artifacts = ARTIFACTS.get(key, ())
        if key == "probability" and result[key] is not None:
            artifacts = ("terms",) if request["operation"] == "identify" else ("distribution",)
        if key == "responsibility" and not result["actual_cause"]:
            artifacts = ("ac1", "ac2", "ac3")
        outputs.append({"pointer": pointer_child("/result", key), "dependency": "conservative",
                        "inputs": inputs, "operations": list(stages),
                        "intermediates": [
                            {"pointer": pointer_child("/result", name), "dependency": "exact"}
                            for name in artifacts if result.get(name) is not None
                        ]})
    if request["operation"] == "reconstruct":
        for index, _ in enumerate(result["reconstructions"]):
            scope = f"/model/reconstructions/{index}"
            local = set().union(*(terms for path, terms in dependencies.items()
                                  if path.startswith(scope + "/") or path.startswith("/parameters/")))
            outputs.append({"pointer": f"/result/reconstructions/{index}", "dependency": "conservative",
                            "inputs": sorted(local), "operations": list(stages[:2]), "intermediates": [],
                            "input_scope": scope})
    return {"status": "conservative", "outputs": outputs,
            "observed_reads": {"dependency": "exact", "scope": "instrumented_value_lookups", "inputs": sorted(reads)}}


def affected(response, changes):
    """Devuelve resultados que requieren recálculo ante rutas modificadas en la solicitud."""
    require(type(response) is dict, "Resultado inválido")
    changed = labels(changes, nonempty=True)
    require(all(path.startswith("/") for path in changed), "Se requieren punteros JSON de entrada")
    trace = response.get("trace") or {}
    execution = trace.get("execution") or {"status": "unknown", "outputs": []}
    pointers = []
    if execution["status"] == "unknown":
        return {"status": "unknown", "changes": changed, "affected": [], "requires_recalculation": None}
    for output in execution["outputs"]:
        for path in changed:
            # Structural additions can introduce a previously absent dependency.
            structural = output["dependency"] == "conservative" and (
                path.split("/")[1] in {"model", "parameters", "lineage", "lineage_groups", "provenance",
                                        "assumptions", "modeling_hypotheses", "engine",
                                        "mathematical_version", "operation", "options"}
                or (not trace.get("coverage", {}).get("complete") and path.startswith("/case"))
            )
            scope = output.get("input_scope")
            if scope and path.startswith("/model/reconstructions/") and not (
                path == scope or path.startswith(scope + "/")
            ):
                structural = False
            if structural or any(path == item or path.startswith(item + "/") or item.startswith(path + "/")
                                 for item in output["inputs"]):
                pointers.append(output["pointer"])
                break
    return {"status": execution["status"], "changes": changed, "affected": pointers,
            "requires_recalculation": bool(pointers)}


def affected_by_request(response, revised):
    """Compara la solicitud efectiva original con una revisión JSON."""
    original = response.get("effective_input") if type(response) is dict else None
    require(type(original) is dict and type(revised) is dict, "Se requieren solicitudes como objetos")
    changes = []
    pending = [(original, revised, "")]
    while pending:
        old, new, path = pending.pop()
        if type(old) is dict and type(new) is dict:
            for key in old.keys() | new.keys():
                child = pointer_child(path, key)
                if key in old and key in new:
                    pending.append((old[key], new[key], child))
                else:
                    changes.append(child)
        elif type(old) is list and type(new) is list and len(old) == len(new):
            pending.extend((a, b, pointer_child(path, index)) for index, (a, b) in enumerate(zip(old, new)))
        elif type(old) is not type(new) or old != new:
            changes.append(path)
    if not changes:
        return {"status": "exact", "changes": [], "affected": [], "requires_recalculation": False}
    return affected(response, sorted(changes))
