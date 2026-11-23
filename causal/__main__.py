"""Invocación local por archivo JSON o entrada estándar."""
import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import sys

from . import affected, affected_by_request, audit_coverage, execute
from .core import Failure


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Clave JSON duplicada")
        obj[key] = value
    return obj


def reject_constant(value):
    raise ValueError(f"Constante JSON inválida: {value}")


def finite_float(value):
    number = float(value)
    if not math.isfinite(number) or Decimal(value) != Decimal(str(number)):
        raise ValueError("Número JSON sin representación decimal fiel. Use una cadena racional.")
    return number


def read_json(path):
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant,
                      parse_float=finite_float)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", help="Archivo UTF-8 o - para entrada estándar")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--coverage", action="store_true", help="Audita la procedencia de una solicitud")
    mode.add_argument("--changes", metavar="JSON", help="Evalúa cambios sobre un resultado previo")
    mode.add_argument("--revised", metavar="JSON", help="Compara un resultado con una solicitud revisada")
    args = parser.parse_args()
    try:
        request = read_json(args.request)
        if args.coverage:
            response = audit_coverage(request)
        elif args.changes:
            response = affected(request, read_json(args.changes))
        elif args.revised:
            response = affected_by_request(request, read_json(args.revised))
        else:
            response = execute(request)
    except (OSError, ValueError, RecursionError) as exc:
        response = execute(None)
        response["status"] = exc.status if isinstance(exc, Failure) else (
            "execution_error" if isinstance(exc, OSError) else "invalid_model")
        response["diagnostics"] = [str(exc)]
    print(json.dumps(response, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2))
    return 0 if response.get("status", "success") in {"success", "conservative", "exact"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
