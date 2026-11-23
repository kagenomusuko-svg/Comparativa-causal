"""Trazabilidad por punteros JSON, con dependencias acíclicas y bases tipadas."""
from copy import deepcopy
import re

from . import dag, fields, label, labels, require


def resolve_pointer(document, pointer):
    require(type(pointer) is str and pointer.startswith("/"), "Puntero JSON inválido")
    value = document
    for component in pointer[1:].split("/"):
        require(not re.search(r"~(?![01])", component), "Escape de puntero inválido")
        key = component.replace("~1", "/").replace("~0", "~")
        if type(value) is list and re.fullmatch(r"0|[1-9][0-9]*", key):
            require(len(key) <= len(str(len(value))) and int(key) < len(value),
                    f"Índice de puntero inexistente: {pointer}")
            value = value[int(key)]
        else:
            require(type(value) is dict and key in value, f"Puntero inexistente: {pointer}")
            value = value[key]
    return value


def lineage(request):
    case = request["case"]
    entries = {entry["id"]: entry for entry in case["entries"]}
    raw = request.get("lineage", {})
    require(type(raw) is dict, "lineage debe ser un objeto")
    graph = {}
    records = []
    for pointer, record in sorted(raw.items()):
        require(type(pointer) is str and pointer.startswith(("/model", "/parameters")) and
                pointer.split("/")[1] in {"model", "parameters"}, "Puntero fuera del modelo o parámetros")
        resolve_pointer(request, pointer)
        fields(record, "basis", "depends_on")
        graph[pointer] = labels(record.get("depends_on", []))
        bases = record["basis"]
        require(type(bases) is list and bool(bases), "El elemento debe tener una base declarada")
        seen = set()
        for base in bases:
            fields(base, "kind ref")
            kind, ref = base["kind"], base["ref"]
            require(label(kind) and label(ref), "Base de procedencia inválida")
            expected = {
                "document": {"source"},
                "assertion": {"proposition", "evidence", "contradiction", "support", "absence"},
                "hypothesis": {"hypothesis"},
                "assumption": {"assumption"},
            }
            require(kind in expected, "Tipo de base desconocido")
            declared_field = {"assumption": "assumptions", "hypothesis": "modeling_hypotheses"}.get(kind)
            valid_entry = ref in entries and entries[ref]["kind"] in expected[kind]
            valid_declaration = declared_field is not None and ref in request.get(declared_field, [])
            require(valid_entry or valid_declaration, f"Base incompatible o inexistente: {ref}")
            require((kind, ref) not in seen, "Base duplicada")
            seen.add((kind, ref))
        records.append({"pointer": pointer, "basis": deepcopy(bases), "depends_on": graph[pointer]})
    order = dag(graph, raw)
    return {"scope": "declared_inputs", "elements": records, "dependency_order": list(order)}
