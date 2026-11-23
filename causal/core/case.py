"""Registro documental v1, validado sin convertir estados en observaciones."""
from . import fields, label, labels, require

KINDS = {"act", "event", "participant", "condition", "relation", "sequence",
         "source", "proposition", "hypothesis", "support", "contradiction"}
STATES = {"accredited", "refuted", "disputed", "unknown", "pending"}


def validate_case(case: dict) -> set[str]:
    fields(case, "schema_version id reference_event entries")
    require(case["schema_version"] == "1", "Versión del caso incompatible")
    require(label(case["id"]) and label(case["reference_event"]), "Identificación inválida")
    require(type(case["entries"]) is list, "entries debe ser una lista")
    entries = {}
    for entry in case["entries"]:
        fields(entry, "id kind text", "state refs")
        require(all(label(entry[key]) for key in ("id", "kind", "text")), "Registro inválido")
        require(entry["kind"] in KINDS, "Tipo de registro desconocido")
        require(entry["id"] not in entries, "Registro duplicado")
        if "state" in entry:
            require(label(entry["state"]) and entry["state"] in STATES, "Estado documental inválido")
        labels(entry.get("refs", []))
        entries[entry["id"]] = entry
    event = entries.get(case["reference_event"])
    require(event is not None and event["kind"] == "event", "Acontecimiento de referencia inexistente")
    for entry in entries.values():
        require(set(entry.get("refs", [])) <= entries.keys(), "Referencia documental inexistente")
    return set(entries)
