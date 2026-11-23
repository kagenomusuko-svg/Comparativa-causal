"""Registro documental con referencias, afirmaciones y secuencias tipadas."""
from . import fields, label, labels, require

KINDS = {"act", "event", "participant", "condition", "relation", "sequence",
         "source", "proposition", "hypothesis", "support", "contradiction",
         "mechanism", "evidence", "absence", "assumption"}
STATES = {"accredited", "refuted", "disputed", "unknown", "pending"}
LINK_TARGETS = {
    "asserted_by": {"source"},
    "supports": {"hypothesis", "proposition", "evidence", "relation", "mechanism", "condition"},
    "contradicts": {"hypothesis", "proposition", "evidence", "relation", "mechanism", "condition"},
    "about": KINDS,
    "participates_in": {"act", "event", "mechanism"},
}
TEMPORAL = {"event", "act", "condition", "mechanism"}


def validate_case(case: dict) -> set[str]:
    fields(case, "schema_version id reference_event entries")
    require(case["schema_version"] == "1", "Versión del caso incompatible")
    require(label(case["id"]) and label(case["reference_event"]), "Identificación inválida")
    require(type(case["entries"]) is list, "entries debe ser una lista")
    entries = {}
    for entry in case["entries"]:
        fields(entry, "id kind text", "state refs links locator")
        require(all(label(entry[key]) for key in ("id", "kind", "text")), "Registro inválido")
        require(entry["kind"] in KINDS, "Tipo de registro desconocido")
        require(entry["id"] not in entries, "Registro duplicado")
        if "state" in entry:
            require(label(entry["state"]) and entry["state"] in STATES, "Estado documental inválido")
        if "locator" in entry:
            require(label(entry["locator"]), "Localizador documental inválido")
        labels(entry.get("refs", []))
        entries[entry["id"]] = entry
    event = entries.get(case["reference_event"])
    require(event is not None and event["kind"] == "event", "Acontecimiento de referencia inexistente")
    for entry in entries.values():
        refs = entry.get("refs", [])
        require(set(refs) <= entries.keys(), "Referencia documental inexistente")
        if entry["kind"] == "sequence":
            require(all(entries[ref]["kind"] in TEMPORAL for ref in refs), "Referencia temporal incompatible")
        links = entry.get("links", [])
        require(type(links) is list, "Se esperaba una lista de vínculos documentales")
        seen = set()
        for link in links:
            fields(link, "relation target")
            relation, target = link["relation"], link["target"]
            require(label(relation) and relation in LINK_TARGETS and label(target) and target in entries,
                    "Vínculo documental inválido")
            require(entries[target]["kind"] in LINK_TARGETS[relation] and target != entry["id"],
                    "Destino incompatible en vínculo documental")
            require((relation, target) not in seen, "Vínculo documental duplicado")
            seen.add((relation, target))
    return set(entries)
