"""Adaptador v1 de modelos explícitos vinculados a un registro documental."""
from ..core import fields, label, labels, require
from ..core.case import validate_case
from ..core.lineage import lineage, resolve_pointer


def adapt(request: dict) -> tuple[dict, dict, int, dict]:
    fields(request, "schema_version case engine mathematical_version operation model parameters",
           "modeling_hypotheses assumptions provenance options lineage lineage_groups reconstruction_id")
    require(request["schema_version"] == "1", "Versión de solicitud incompatible")
    require(all(label(request[key]) for key in ("engine", "mathematical_version", "operation")),
            "Identificación de operación inválida")
    known = validate_case(request["case"])
    for key in ("modeling_hypotheses", "assumptions"):
        labels(request.get(key, []))
    provenance = request.get("provenance", {})
    require(type(provenance) is dict and all(map(label, provenance)), "Procedencia inválida")
    for pointer, refs in provenance.items():
        if pointer.startswith("/"):
            resolve_pointer(request, pointer)
        require(set(labels(refs, nonempty=True)) <= known, "Referencia de procedencia inexistente")
    model = request["model"]
    params = request["parameters"]
    require(type(model) is dict and type(params) is dict, "Se requieren objetos para modelo y parámetros")
    if request["engine"] == "ness":
        validate_mechanism_sources(model, known)
    if request["engine"] == "bayesian" and type(model.get("idioms")) is list:
        for pattern in model["idioms"]:
            if type(pattern) is dict and "provenance" in pattern:
                require(set(labels(pattern["provenance"], nonempty=True)) <= known,
                        "Referencia de patrón inexistente")
    if "reconstruction_id" in request:
        require(label(request["reconstruction_id"]), "Identificación de reconstrucción inválida")
    options = fields(request.get("options", {}), "", "max_steps provenance_mode")
    limit = options.get("max_steps", 100_000)
    require(type(limit) is int and limit > 0, "max_steps debe ser entero positivo")
    mode = options.get("provenance_mode", "compatible")
    require(mode in ("compatible", "strict"), "Modo de procedencia inválido")
    return model, params, limit, lineage(request) | {"mode": mode}


def validate_mechanism_sources(model, known):
    models = [model]
    alternatives = model.get("reconstructions")
    if type(alternatives) is list:
        models.extend(item["model"] for item in alternatives if type(item) is dict
                      and type(item.get("model")) is dict)
    for item in models:
        mechanisms = item.get("mechanisms")
        if type(mechanisms) is list:
            for mechanism in mechanisms:
                if type(mechanism) is dict and "provenance" in mechanism:
                    require(set(labels(mechanism["provenance"], nonempty=True)) <= known,
                            "Referencia de mecanismo inexistente")
