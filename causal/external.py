"""Ensamblado de resultados heterogéneos conforme al contrato externo v1."""
from copy import deepcopy

from .core import fields, label, require

STATUSES = {"success", "insufficient_data", "invalid_model", "not_identifiable",
            "undefined_operation", "limit_exceeded", "execution_error"}


def bundle(case_id: str, runs: list[dict]) -> dict:
    """Valida identidad y sobre de cada salida sin interpretar su resultado."""
    require(label(case_id) and type(runs) is list and bool(runs), "Lote externo inválido")
    for run in runs:
        fields(run, "schema_version case_id engine mathematical_version software_version operation "
                    "domain_of_validity status effective_input effective_options diagnostics steps result",
               "trace reconstruction_id")
        require(run["schema_version"] == "1" and run["case_id"] == case_id, "Identidad de lote incompatible")
        require(all(label(run[key]) for key in ("engine", "mathematical_version", "software_version", "operation")),
                "Identidad de motor inválida")
        require(type(run["status"]) is str and run["status"] in STATUSES, "Estado externo inválido")
        require(type(run["steps"]) is int and run["steps"] >= 0, "Pasos de ejecución inválidos")
        require(type(run["diagnostics"]) is list and all(map(label, run["diagnostics"])), "Diagnósticos inválidos")
        require(type(run["effective_input"]) is dict, "Entrada efectiva inválida")
        for name, check in {
            "effective_options": lambda value: type(value) is dict,
            "domain_of_validity": label,
            "result": lambda value: type(value) is dict,
            "trace": lambda value: type(value) is dict,
            "reconstruction_id": label,
        }.items():
            value = run.get(name)
            require(value is None or check(value), f"Campo externo inválido: {name}")
        if run["status"] == "success":
            require(run["result"] is not None and run["domain_of_validity"] is not None,
                    "Una ejecución exitosa requiere resultado y dominio")
    return {"schema_version": "1", "case_id": case_id, "runs": deepcopy(runs)}
