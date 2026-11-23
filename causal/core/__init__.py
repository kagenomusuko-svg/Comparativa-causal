"""Validación y primitivas de cálculo finito."""
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from graphlib import CycleError, TopologicalSorter
from typing import Any


class Failure(ValueError):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


def require(condition: bool, message: str, status: str = "invalid_model") -> None:
    if not condition:
        raise Failure(status, message)


def fields(value: Any, required: str = "", optional: str = "") -> dict:
    needed = set(required.split())
    require(type(value) is dict, "Se esperaba un objeto JSON")
    require(set(value) <= needed | set(optional.split()), "Campos no reconocidos")
    missing = needed - value.keys()
    require(not missing, f"Campos ausentes: {sorted(missing)}", "insufficient_data")
    return value


def label(value: Any) -> bool:
    return type(value) is str and bool(value.strip())


def labels(value: Any, *, nonempty: bool = False) -> list[str]:
    require(type(value) is list and all(map(label, value)), "Se esperaba una lista de etiquetas")
    require(len(value) == len(set(value)), "Etiquetas repetidas")
    require(not nonempty or bool(value), "Lista vacía")
    return value


def domains(value: Any) -> dict[str, list[str]]:
    require(type(value) is dict and all(map(label, value)), "Dominios inválidos")
    return {name: labels(states, nonempty=True) for name, states in sorted(value.items())}


def assignment(value: Any, states: dict, exact=None) -> dict[str, str]:
    require(type(value) is dict, "Asignación inválida")
    require(all(k in states and v in states[k] for k, v in value.items()), "Valor fuera del dominio")
    if exact is not None:
        require(value.keys() == set(exact), "Asignación incompleta o de alcance incorrecto")
    return dict(sorted(value.items()))


def worlds(names, states):
    return product(*(states[name] for name in names))


def dag(parents: dict, states: dict) -> tuple[str, ...]:
    require(all(set(items) <= states.keys() for items in parents.values()), "Padre desconocido")
    sorter = TopologicalSorter({name: parents[name] for name in sorted(parents)})
    try:
        return tuple(sorter.static_order())
    except CycleError as exc:
        raise Failure("invalid_model", "El grafo contiene un ciclo") from exc


def probability(value: Any) -> Fraction:
    require(type(value) in (int, float, str), "Probabilidad inválida")
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise Failure("invalid_model", "Probabilidad inválida") from exc
    require(0 <= result <= 1, "Probabilidad fuera de [0,1]")
    return result


def rows(raw, parents, states, budget, decode):
    require(type(raw) is list, "Las filas deben ser una lista")
    table = {}
    for row in raw:
        budget.tick()
        fields(row, "when then")
        given = assignment(row["when"], states, parents)
        key = tuple(given[name] for name in parents)
        require(key not in table, "Fila duplicada")
        table[key] = decode(row["then"])
    for key in worlds(parents, states):
        budget.tick()
        require(key in table, "Falta una fila de la tabla", "insufficient_data")
    return table


def matches(world: dict, condition: dict) -> bool:
    return all(world.get(k) == v for k, v in condition.items())


@dataclass
class Budget:
    limit: int
    used: int = 0

    def tick(self) -> None:
        if self.used >= self.limit:
            raise Failure("limit_exceeded", f"Presupuesto agotado tras {self.used} pasos")
        self.used += 1
