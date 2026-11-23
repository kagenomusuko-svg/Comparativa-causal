"""API local v1. Cada motor conserva su propio tipo de resultado."""
from copy import deepcopy

from .adapters import adapt
from .core import Budget, Failure, label, require
from .core.audit import affected, affected_by_request, execution_trace, is_probability_input
from .engines import bayesian, halpern, ness, pearl

__version__ = "0.3.0"

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
        require(trace["mode"] != "strict" or trace["coverage"]["complete"],
                "Cobertura de procedencia incompleta", "insufficient_data")
        engine = ENGINES.get(request["engine"])
        require(engine is not None, "Motor desconocido", "undefined_operation")
        module, validity = engine
        response["domain_of_validity"] = validity
        accepted = {module.VERSION}
        if module is bayesian:
            accepted.add(module.LEGACY_VERSION)
        require(request["mathematical_version"] in accepted, "Versión matemática incompatible")
        if module is bayesian and request["mathematical_version"] == module.LEGACY_VERSION:
            require(bayesian.historical_contract(request["operation"], model, params),
                    "Las extensiones probatorias requieren bn-exact-fnl-2012-2013", "undefined_operation")
        elif module is bayesian:
            missing_parameters = [
                row["pointer"] for row in trace["coverage"]["elements"]
                if row["coverage"] == "missing" and is_probability_input(row["pointer"])
            ]
            require(not missing_parameters, "Parámetros bayesianos sin procedencia: " +
                    ", ".join(missing_parameters), "insufficient_data")
        budget = Budget(limit)
        response["effective_options"] = {"max_steps": limit}
        result = module.run(request["operation"], model, params, budget)
        response["result"] = result
        if module is bayesian and request["operation"] == "evidence_sequence" and any(
            step["posterior"] is None for step in result["sequence"]
        ):
            response["status"] = "undefined_operation"
            response["diagnostics"].append("La secuencia contiene evidencia acumulada sin soporte")
        if module is pearl and request["operation"] == "identify":
            response["status"] = result.pop("status", "success")
            response["diagnostics"].extend(result.pop("diagnostics", []))
            response["domain_of_validity"] = "DAG causal declarado con observables y latentes"
        if module is ness and request["operation"] == "reconstruct":
            response["domain_of_validity"] = "Leyes causales directas y composables en cada reconstrucción"
            if result["conclusion"] in {"undetermined", "underspecified_mechanism"}:
                response["status"] = "insufficient_data"
                response["diagnostics"].append(result["conclusion"])
        if module is bayesian and "posterior" in result and result["posterior"] is None:
            response["status"] = "undefined_operation"
            response["diagnostics"].append("La evidencia conjunta tiene probabilidad cero")
    except Failure as exc:
        response["status"] = exc.status
        response["diagnostics"].append(str(exc))
    except Exception as exc:
        response["status"] = "execution_error"
        response["diagnostics"].append(type(exc).__name__)
    if response["trace"] is not None:
        response["trace"]["execution"] = execution_trace(response, request, response["trace"], budget.reads if budget else ())
    if budget is not None:
        response["steps"] = budget.used
    return response


def audit_coverage(request: dict) -> dict:
    """Valida las referencias y devuelve un inventario de cobertura de la solicitud."""
    return adapt(request)[3]["coverage"]
