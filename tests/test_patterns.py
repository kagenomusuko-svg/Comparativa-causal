from fractions import Fraction
import unittest

from causal import execute
from test_completion import request
from test_engines import BINARY, table


def bit_row(chance):
    return {"0": str(1 - chance), "1": str(chance)}


def root(p):
    return table((), lambda: bit_row(p))


def fragment(name, **roles):
    return {"id": name, "kind": name, "roles": roles, "provenance": ["S"]}


def reliable_report():
    # Lagnado, Fenton and Neil (2012), §3.2, Figure 6.
    return {
        "domains": dict.fromkeys(["H", "R", "E"], BINARY),
        "nodes": {
            "H": root(Fraction(1, 100)),
            "R": root(Fraction(4, 5)),
            "E": {"rows": table(("H", "R"), lambda h, r: bit_row(Fraction(h) if r else Fraction(1, 2)))["rows"]},
        },
        "idioms": [fragment("evidence_reliability", target="H", reliability="R", report="E")],
    }


def infer(model, evidence, hypothesis="H", **extra):
    return execute(request("bayesian", "infer", model, {"hypothesis": hypothesis, "evidence": evidence} | extra))


class EvidencePatternsTests(unittest.TestCase):
    def test_published_evidence_pattern(self):
        model = {
            "domains": dict.fromkeys(["H", "E"], BINARY),
            "nodes": {"H": root(Fraction(1, 100)),
                      "E": {"rows": table(("H",), lambda h: bit_row(Fraction(1 + 8*h, 10)))["rows"]}},
            "idioms": [fragment("evidence", target="H", report="E")],
        }
        out = infer(model, {"E": "1"}, alternatives=["1", "0"])
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["result"]["posterior"]["1"], "1/12")
        self.assertEqual(out["result"]["comparison"]["likelihood_ratio"]["value"], "9")
        self.assertEqual(out["result"]["pattern_certificates"][0]["section"], "3.1")

    def test_reliability_and_explaining_away(self):
        model = reliable_report()
        out = infer(model, {"E": "1"})
        self.assertEqual(out["result"]["posterior"]["1"], "1/12")
        out = infer(model, {"E": "1", "R": "0"})
        self.assertEqual(out["result"]["posterior"]["1"], "1/100")
        out = infer(model, {"E": "1", "H": "0"}, hypothesis="R")
        self.assertEqual(out["result"]["posterior"]["1"], "0")
        model["nodes"]["R"] = table(("H",), lambda _: bit_row(Fraction(4, 5)))
        self.assertEqual(infer(model, {"E": "1"})["status"], "invalid_model")

    def test_composed_opportunity_alibi_and_veracity(self):
        variables = ["O", "M", "H", "V", "E", "SEN", "OBJ"]
        model = {"domains": dict.fromkeys(variables, BINARY), "nodes": {
            "O": root(Fraction(1, 2)), "M": root(Fraction(1, 2)),
            "H": {"rows": table(("O", "M"), lambda o, m: bit_row(Fraction(o*(1+m), 4)))["rows"]},
            "V": {"rows": table(("H",), lambda h: bit_row(Fraction(3-2*h, 4)))["rows"]},
            "E": {"rows": table(("O", "V", "SEN", "OBJ"),
                                lambda o, v, s, b: bit_row(Fraction(int(bool(v and s and b and not o)))))["rows"]},
            "SEN": root(Fraction(1, 2)), "OBJ": root(Fraction(1, 2)),
        }, "idioms": [
            fragment("opportunity_motive", opportunity="O", motive="M", hypothesis="H"),
            fragment("alibi", opportunity="O", hypothesis="H", veracity="V", report="E"),
            fragment("testimony_components", target="O", report="E", sensitivity="SEN", objectivity="OBJ", veracity="V"),
        ]}
        out = infer(model, {"E": "1"})
        self.assertEqual(out["result"]["effective_parents"]["E"], ["O", "OBJ", "SEN", "V"])
        self.assertEqual(out["result"]["posterior"]["1"], "0")
        self.assertEqual(out["result"]["evidence_probability"], "3/32")
        self.assertEqual(infer(model, {"E": "1", "O": "1"})["status"], "undefined_operation")

    def test_missing_parameter_conflicting_structure_and_limit(self):
        model = reliable_report()
        model["nodes"]["E"]["rows"].pop()
        self.assertEqual(infer(model, {"E": "1"})["status"], "insufficient_data")
        model = reliable_report()
        model["nodes"]["H"]["parents"] = ["E"]
        self.assertEqual(infer(model, {"E": "1"})["status"], "invalid_model")
        req = request("bayesian", "infer", reliable_report(), {"hypothesis": "H", "evidence": {"E": "1"}})
        self.assertEqual(execute(req | {"options": {"max_steps": 1}})["status"], "limit_exceeded")
