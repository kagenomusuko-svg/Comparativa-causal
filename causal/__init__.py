"""API local v1. Cada motor conserva su propio tipo de resultado."""
from copy import deepcopy

from .adapters import adapt
from .core import Budget, Failure, label, require
from .engines import bayesian, halpern, ness, pearl

__version__ = "0.2.0"

ENGINES = {
    "pearl": (pearl, "SCM recursivo finito con ecuaciones totales"),
    "halpern": (halpern, "Causalidad efectiva HP 2001 y responsabilidad CH 2004"),
    "ness": (ness, "Vías directas con suficiencia y esencialidad declaradas"),
    "bayesian": (bayesian, "DAG discreto con parámetros declarados y racionales"),
}


def execute(request: dict) -> dict:
    """Valida y ejecuta una solicitud JSON v1, devolviendo un resultado v1."""
    source = request if type(request) is dict else {}
    case = source.get("case")
    case_id = case.get("id") if type(case) is dict else None
    identity = {key: source[key] if label(source.get(key)) else None
                for key in ("engine", "mathematical_version", "operation", "reconstruction_id")}
    response = {
        "schema_version": "1", "software_version": __version__,
        "case_id": case_id if label(case_id) else None, **identity,
        "status": "success", "result": None,
        "domain_of_validity": None, "effective_input": deepcopy(request),
        "effective_options": None, "steps": 0, "diagnostics": [], "trace": None,
    }
    budget = None
    try:
        model, params, limit, trace = adapt(request)
        response["trace"] = trace
        engine = ENGINES.get(request["engine"])
        require(engine is not None, "Motor desconocido", "undefined_operation")
        module, validity = engine
        response["domain_of_validity"] = validity
        require(request["mathematical_version"] == module.VERSION, "Versión matemática incompatible")
        budget = Budget(limit)
        response["effective_options"] = {"max_steps": limit}
        result = module.run(request["operation"], model, params, budget)
        response["result"] = result
        if module is pearl and request["operation"] == "identify":
            response["status"] = result.pop("status", "success")
            response["diagnostics"].extend(result.pop("diagnostics", []))
            response["domain_of_validity"] = "DAG causal declarado con observables y latentes"
        if module is ness and request["operation"] == "reconstruct":
            response["domain_of_validity"] = "Leyes causales directas y composables en cada reconstrucción"
            if result["conclusion"] in {"undetermined", "underspecified_mechanism"}:
                response["status"] = "insufficient_data"
                response["diagnostics"].append(result["conclusion"])
        if module is bayesian and result["posterior"] is None:
            response["status"] = "undefined_operation"
            response["diagnostics"].append("La evidencia conjunta tiene probabilidad cero")
    except Failure as exc:
        response["status"] = exc.status
        response["diagnostics"].append(str(exc))
    except Exception as exc:
        response["status"] = "execution_error"
        response["diagnostics"].append(type(exc).__name__)
    if budget is not None:
        response["steps"] = budget.used
    return response
