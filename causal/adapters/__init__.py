"""Adaptador v1 de modelos explícitos vinculados a un registro documental."""
from ..core import fields, label, labels, require
from ..core.case import validate_case


def adapt(request: dict) -> tuple[dict, dict, int]:
    fields(request, "schema_version case engine mathematical_version operation model parameters",
           "modeling_hypotheses assumptions provenance options")
    require(request["schema_version"] == "1", "Versión de solicitud incompatible")
    require(all(label(request[key]) for key in ("engine", "mathematical_version", "operation")),
            "Identificación de operación inválida")
    known = validate_case(request["case"])
    for key in ("modeling_hypotheses", "assumptions"):
        labels(request.get(key, []))
    provenance = request.get("provenance", {})
    require(type(provenance) is dict and all(map(label, provenance)), "Procedencia inválida")
    for refs in provenance.values():
        require(set(labels(refs, nonempty=True)) <= known, "Referencia de procedencia inexistente")
    model = request["model"]
    params = request["parameters"]
    require(type(model) is dict and type(params) is dict, "Se requieren objetos para modelo y parámetros")
    if request["engine"] == "ness" and type(model.get("mechanisms")) is list:
        for mechanism in model["mechanisms"]:
            if type(mechanism) is dict and "provenance" in mechanism:
                require(set(labels(mechanism["provenance"], nonempty=True)) <= known,
                        "Referencia de mecanismo inexistente")
    options = fields(request.get("options", {}), "", "max_steps")
    limit = options.get("max_steps", 100_000)
    require(type(limit) is int and limit > 0, "max_steps debe ser entero positivo")
    return model, params, limit
