"""Fragmentos y restricciones estructurales de Fenton, Neil y Lagnado 2013."""
from ..core import assignment, fields, label, labels, require, worlds

DOI = "10.1111/cogs.12004"
PATTERNS = {
    "evidence_accuracy": ("target report accuracy", "", "3.3", [("target", "report"), ("accuracy", "report")]),
    "accuracy_components": ("target report accuracy competence objectivity veracity", "", "3.3",
                            [(key, "accuracy") for key in ("competence", "objectivity", "veracity")] +
                            [("target", "report"), ("accuracy", "report")]),
    "necessary_opportunity": ("opportunity hypothesis", "", "3.4.1", [("opportunity", "hypothesis")]),
    "aggregate_motive": ("motives aggregate hypothesis", "", "3.4.2", [("aggregate", "hypothesis")]),
    "dependent_evidence": ("target first_report second_report", "dependency", "3.5",
                           [("target", "first_report"), ("target", "second_report"),
                            ("first_report", "second_report")]),
    "alibi_accuracy": ("opportunity hypothesis accuracy report", "", "3.6",
                       [("opportunity", "hypothesis"), ("opportunity", "report"), ("hypothesis", "accuracy"),
                        ("accuracy", "report")]),
    "explaining_away": ("cause_a cause_b effect", "", "3.7", [("cause_a", "effect"), ("cause_b", "effect")]),
    "exclusive_explanations": ("causes effect selector", "", "3.7", []),
}


def settings_for(kind, value, roles, states):
    if kind == "necessary_opportunity":
        fields(value, "opportunity_absent hypothesis_true")
        assignment({roles["opportunity"]: value["opportunity_absent"],
                    roles["hypothesis"]: value["hypothesis_true"]}, states)
    elif kind == "exclusive_explanations":
        fields(value, "active_states pathways impossible")
        assignment(value["active_states"], states, roles["causes"])
        paths = value["pathways"]
        require(type(paths) is dict and set(paths) == set(roles["causes"]) and all(map(label, paths.values())),
                "Se requiere una etiqueta de selector por causa")
        impossible = value["impossible"]
        require(label(impossible) and set(states[roles["selector"]]) == set(paths.values()) | {impossible}
                and len(states[roles["selector"]]) == len(roles["causes"]) + 1,
                "El selector requiere un estado distinto por trayectoria y uno imposible")
    else:
        fields(value)
    return value


def role_nodes(roles):
    """Valida las listas de roles de cardinalidad variable y las aplana."""
    names = []
    for key, value in roles.items():
        if key in {"motives", "causes"}:
            group = labels(value)
            require(len(group) >= 2, "El fragmento requiere al menos dos nodos del rol")
            names.extend(group)
        else:
            names.append(value)
    return names


def links_for(kind, roles, edges):
    links = [[roles[parent], roles[child]] for parent, child in edges]
    if kind == "aggregate_motive":
        links.extend([motive, roles["aggregate"]] for motive in roles["motives"])
    if kind == "exclusive_explanations":
        links.extend([cause, roles[target]] for cause in roles["causes"] for target in ("effect", "selector"))
    return links


def validate_graph(certificates, parents, budget):
    for cert in certificates:
        roles = cert["roles"]
        if cert["kind"] == "aggregate_motive":
            require(not set(roles["motives"]) & set(parents[roles["hypothesis"]]),
                    "Los motivos individuales deben pasar por el motivo agregado")
        if cert["kind"] == "exclusive_explanations":
            selector = roles["selector"]
            require(set(parents[selector]) == set(roles["causes"]) and
                    all(selector not in values for values in parents.values()),
                    "El selector debe ser una hoja con las causas como únicos padres")


def validate_tables(certificates, network, updates, budget):
    for cert in certificates:
        kind, roles = cert["kind"], cert["roles"]
        if kind not in {"necessary_opportunity", "exclusive_explanations", "accuracy_components"}:
            continue
        settings = cert["settings"]
        target = roles[{"necessary_opportunity": "hypothesis", "exclusive_explanations": "selector",
                        "accuracy_components": "accuracy"}[kind]]
        if target not in network.tables:
            continue
        parents = network.parents[target]
        for key in worlds(parents, network.states):
            budget.tick()
            row = updates.get((target, key), network.tables[target][key])
            given = dict(zip(parents, key))
            if kind == "necessary_opportunity":
                if given[roles["opportunity"]] == settings["opportunity_absent"]:
                    require(row[settings["hypothesis_true"]] == 0, "La oportunidad declarada necesaria exige masa cero")
            elif kind == "accuracy_components":
                require(1 in row.values(), "La definición de exactitud debe ser determinista")
            else:
                active = [cause for cause in roles["causes"] if given[cause] == settings["active_states"][cause]]
                expected = settings["pathways"][active[0]] if len(active) == 1 else settings["impossible"]
                require(row[expected] == 1, "La CPT del selector contradice la exclusión declarada")


def evidence_paths(hypothesis, reports, parents, order, budget):
    """Clasifica caminos directos y caminos causales sin colisionadores (§3.8)."""
    lengths = {hypothesis: 0}
    for node in reversed(order):
        if node in lengths:
            for parent in parents[node]:
                budget.tick()
                lengths[parent] = min(lengths.get(parent, float("inf")), lengths[node] + 1)
    for node in order:
        for parent in parents[node]:
            budget.tick()
            if parent in lengths:
                lengths[node] = min(lengths.get(node, float("inf")), lengths[parent] + 1)
    return {report: "direct" if hypothesis in parents[report] else
            "circumstantial" if lengths.get(report, 0) >= 2 else "unclassified"
            for report in sorted(reports)}
