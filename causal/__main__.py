"""Invocación local por archivo JSON o entrada estándar."""
import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import sys

from . import execute


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", help="Archivo UTF-8 o - para entrada estándar")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.request == "-" else Path(args.request).read_text(encoding="utf-8")
        request = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant,
                             parse_float=finite_float)
    except (OSError, ValueError, RecursionError) as exc:
        response = execute(None)
        response["status"] = "execution_error" if isinstance(exc, OSError) else "invalid_model"
        response["diagnostics"] = [str(exc)]
    else:
        response = execute(request)
    print(json.dumps(response, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2))
    return 0 if response["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
