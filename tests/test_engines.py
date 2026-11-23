import copy
from fractions import Fraction
from itertools import combinations, product
import json
from pathlib import Path
import subprocess
import sys
import unittest

from causal import execute
from causal.core import Budget, Failure
from causal.engines import bayesian, halpern, ness, pearl

BINARY = ["0", "1"]
ROOT = Path(__file__).resolve().parents[1]


def table(parents, fn):
    return {"parents": list(parents), "rows": [
        {"when": dict(zip(parents, pair)), "then": fn(*map(int, pair))}
        for pair in product(BINARY, repeat=len(parents))
    ]}


def scm(equations, exogenous=()):
    return {"exogenous": dict.fromkeys(exogenous, BINARY),
            "endogenous": dict.fromkeys(equations, BINARY), "equations": equations}


def roots(*names):
    return {name: table((), lambda: "1") for name in names}


def hp(model, candidate, target="Y"):
    return halpern.run("responsibility", model, {
        "context": {}, "candidate": candidate, "effect": {"eq": {target: "1"}}
    }, Budget(100000))


def rule(identifier, *requirements):
    return {"id": identifier, "effect": "Y", "requires": list(requirements),
            "law": "Mecanismo sintético", "provenance": ["S"]}


def bn():
    return {"domains": dict.fromkeys(["H", "E", "D"], BINARY), "nodes": {
        "H": table((), lambda: {"0": "1/2", "1": "1/2"}),
        "E": table(("H",), lambda h: {"0": "1/4", "1": "3/4"} if h else {"0": "3/4", "1": "1/4"}),
        "D": table(("E",), lambda e: {"0": str(1-e), "1": str(e)}),
    }}


class PearlTests(unittest.TestCase):
    def test_confounder_association_and_intervention(self):
        model = scm({"X": table(("U",), str), "Y": table(("U",), str)}, ["U"])
        model["prior"] = [{"when": {"U": value}, "then": "1/2"} for value in BINARY]
        query = {"Y": "1"}
        for operation, params, expected in [
            ("associate", {"observed": {"X": "1"}}, "1"),
            ("intervene", {"do": {"X": "1"}}, "1/2"),
            ("counterfactual", {"observed": {"X": "1"}, "do": {"X": "0"}}, "1"),
            ("effect", {"do": {"X": "1"}, "baseline": {"X": "0"}}, "1/2"),
        ]:
            with self.subTest(operation=operation):
                result = pearl.run(operation, model, {"query": query} | params, Budget(100))
                self.assertEqual(result["probability"], expected)
        self.assertEqual(result["difference"], "0")

    def test_reference_backdoor_fork(self):
        # Pearl 2010 §3.2. Back-door adjustment for the fork U -> X, U -> Y.
        model = scm({"X": table(("U",), str), "Y": table(("U", "X"), lambda u, x: str(max(u, x)))}, ["U"])
        model["prior"] = [{"when": {"U": "0"}, "then": "2/3"},
                          {"when": {"U": "1"}, "then": "1/3"}]
        result = pearl.run("effect", model, {"query": {"Y": "1"}, "do": {"X": "1"},
                                            "baseline": {"X": "0"}}, Budget(100))
        self.assertEqual(result["difference"], "2/3")
        self.assertEqual(sum(Fraction(row["probability"]) for row in result["distribution"]), 1)

    def test_context_and_linear_chain(self):
        model = scm({"X": table(("U",), str), "Y": table(("X",), str)}, ["U"])
        result = pearl.run("counterfactual", model, {
            "observed": {"Y": "1"}, "query": {"Y": "0"}, "do": {"X": "0"},
        }, Budget(100))
        self.assertTrue(result["event"])
        with self.assertRaisesRegex(Failure, "varía"):
            pearl.run("observe", model, {"query": {"Y": "1"}}, Budget(100))

    def test_cycle_and_missing_row(self):
        model = scm({"X": table(("Y",), str), "Y": table(("X",), str)})
        with self.assertRaisesRegex(Failure, "ciclo"):
            pearl.SCM(model, Budget(100))
        model = scm({"X": table(("U",), str)}, ["U"])
        model["equations"]["X"]["rows"].pop()
        with self.assertRaises(Failure) as error:
            pearl.SCM(model, Budget(100))
        self.assertEqual(error.exception.status, "insufficient_data")


class HalpernTests(unittest.TestCase):
    def test_published_two_arsonists(self):
        for connective, responsibility in [(min, "1"), (max, "1/2")]:
            model = scm(roots("A", "B") | {"Y": table(("A", "B"),
                                                       lambda a, b: str(connective(a,b)))})
            for name in ["A", "B"]:
                result = hp(model, {name: "1"})
                self.assertTrue(result["ac3"])
                self.assertEqual(result["responsibility"], responsibility)
                self.assertEqual(result["witness"]["changes"], int(connective is max))
            conjunction = hp(model, {"A": "1", "B": "1"})
            self.assertFalse(conjunction["ac3"])
            self.assertEqual(conjunction["responsibility"], "0")
            absent = hp(model, {"A": "0"})
            self.assertFalse(absent["ac1"])

    def test_published_bottle_preemption(self):
        model = scm(roots("ST", "BT") | {
            "SH": table(("ST",), str),
            "BH": table(("BT", "SH"), lambda b, s: str(int(b and not s))),
            "BS": table(("SH", "BH"), lambda s, b: str(max(s,b))),
        })
        self.assertEqual(hp(model, {"ST": "1"}, "BS")["responsibility"], "1")
        loser = hp(model, {"BT": "1"}, "BS")
        self.assertTrue(loser["ac1"])
        self.assertFalse(loser["ac2"])
        self.assertEqual(loser["responsibility"], "0")

    def test_published_unanimous_vote(self):
        voters = tuple(f"V{i}" for i in range(5))
        model = scm(roots(*voters) | {"Y": table(voters, lambda *votes: str(int(sum(votes) >= 3)))})
        self.assertEqual(hp(model, {"V0": "1"})["responsibility"], "1/3")


class NessTests(unittest.TestCase):
    def test_wright_five_of_seven_pollution_units(self):
        # Wright 1985, p. 1793. Any five of seven actual units suffice.
        units = [f"U{i}" for i in range(7)]
        mechanisms = [rule(f"M{i}", *group) for i, group in enumerate(combinations(units, 5))]
        model = {"conditions": dict.fromkeys(units + ["Y"], True),
                 "mechanisms": mechanisms, "complete": True}
        for candidate in units:
            result = ness.run("evaluate", model, {"candidate": candidate, "effect": "Y"}, Budget(1000))
            self.assertTrue(result["ness_cause"])
            self.assertFalse(result["necessary_across_declared_paths"])
            self.assertEqual(len(result["witnesses"]), 15)

    def test_concurrence_and_overdetermination(self):
        model = {"conditions": dict.fromkeys(["A", "B", "C", "Y"], True),
                 "mechanisms": [rule("AB", "A", "B"), rule("C", "C")], "complete": True}
        query = {"candidate": "A", "effect": "Y"}
        result = ness.run("evaluate", model, query, Budget(20))
        self.assertTrue(result["ness_cause"])
        self.assertFalse(result["necessary_across_declared_paths"])
        self.assertEqual(result["witnesses"][0]["without_candidate"], ["B"])
        model["conditions"]["C"] = False
        result = ness.run("evaluate", model, query, Budget(20))
        self.assertTrue(result["necessary_across_declared_paths"])

    def test_preemptive_path_explicitly_disabled(self):
        model = {"conditions": {"A": True, "B": True, "B_enabled": False, "Y": True},
                 "mechanisms": [rule("early", "A"), rule("late", "B", "B_enabled")], "complete": True}
        self.assertFalse(ness.run("evaluate", model, {"candidate": "B", "effect": "Y"},
                                  Budget(20))["ness_cause"])
        result = ness.run("evaluate", model, {"candidate": "A", "effect": "Y"}, Budget(20))
        self.assertEqual([r["id"] for r in result["active_mechanisms"]], ["early"])

    def test_reduced_set_and_open_inventory(self):
        model = {"conditions": dict.fromkeys(["A", "B", "Y"], True),
                 "mechanisms": [rule("AB", "A", "B"), rule("B", "B")], "complete": True}
        query = {"candidate": "A", "effect": "Y"}
        self.assertFalse(ness.run("evaluate", model, query, Budget(20))["ness_cause"])
        model["complete"] = False
        with self.assertRaises(Failure) as error:
            ness.run("evaluate", model, query, Budget(20))
        self.assertEqual(error.exception.status, "insufficient_data")


class BayesianTests(unittest.TestCase):
    def test_likelihood_and_dependent_evidence(self):
        result = bayesian.run("infer", bn(), {
            "hypothesis": "H", "evidence": {"E": "1", "D": "1"}, "alternatives": ["1", "0"],
        }, Budget(100))
        self.assertEqual(result["posterior"], {"0": "1/4", "1": "3/4"})
        self.assertEqual(result["comparison"]["likelihood_ratio"]["value"], "3")
        self.assertEqual(result["evidence_probability"], "1/2")

    def test_conflicting_evidence_and_missing_probabilities(self):
        model = bn()
        params = {"hypothesis": "H", "evidence": {"E": "0", "D": "1"}}
        self.assertIsNone(bayesian.run("infer", model, params, Budget(100))["posterior"])
        model["nodes"]["D"]["rows"].pop()
        with self.assertRaises(Failure) as error:
            bayesian.run("infer", model, params, Budget(100))
        self.assertEqual(error.exception.status, "insufficient_data")

    def test_invalid_normalization_and_infinite_ratio(self):
        model = bn()
        params = {"hypothesis": "H", "evidence": {"D": "1"}, "alternatives": ["1", "0"]}
        row = model["nodes"]["E"]["rows"][0]
        row["then"] = {"0": "1", "1": "0"}
        result = bayesian.run("infer", model, params, Budget(100))
        self.assertEqual(result["comparison"]["likelihood_ratio"]["status"], "infinite")
        row["then"]["1"] = "1/10"
        with self.assertRaisesRegex(Failure, "sumar uno"):
            bayesian.run("infer", model, params, Budget(100))

    def test_sensitivity_and_missing_observation(self):
        scenario = [{"node": "H", "when": {}, "then": {"0": "1/4", "1": "3/4"}}]
        result = bayesian.run("sensitivity", bn(), {
            "hypothesis": "H", "evidence": {"D": "1"}, "scenarios": [scenario],
        }, Budget(100))
        self.assertEqual(result["scenarios"][0]["posterior"]["1"], "9/10")
        self.assertEqual(result["scenarios"][0]["posterior_difference"]["1"], "3/20")


class IntegrationTests(unittest.TestCase):
    def test_examples_match_api_and_cli(self):
        for path in sorted((ROOT / "examples").glob("*.json")):
            with self.subTest(path=path):
                request = json.loads(path.read_text())
                actual = execute(request)
                cli = subprocess.run([sys.executable, "-m", "causal", str(path)],
                                     cwd=ROOT, capture_output=True, check=True)
                self.assertEqual(actual["status"], "success")
                self.assertEqual(actual, json.loads(cli.stdout))
                self.assertEqual(actual, execute(request))

    def test_provenance_and_unknown_fields(self):
        request = json.loads((ROOT / "examples/ness.json").read_text())
        request["provenance"] = {"/model": ["not-in-case"]}
        self.assertEqual(execute(request)["status"], "invalid_model")
        request["provenance"] = {}
        request["parameters"]["unexpected"] = True
        self.assertEqual(execute(request)["status"], "invalid_model")

    def test_cli_rejects_duplicate_keys_and_lossy_numbers(self):
        for raw in [b'{"engine":1,"engine":2}', b'{"n":1e-999}', b'{"n":NaN}']:
            with self.subTest(raw=raw):
                cli = subprocess.run([sys.executable, "-m", "causal", "-"], input=raw,
                                     cwd=ROOT, capture_output=True)
                self.assertEqual(cli.returncode, 1)
                self.assertEqual(json.loads(cli.stdout)["status"], "invalid_model")

    def test_resource_exhaustion_and_version(self):
        request = json.loads((ROOT / "examples/halpern.json").read_text())
        request["options"] = {"max_steps": 1}
        result = execute(request)
        self.assertEqual(result["status"], "limit_exceeded")
        self.assertIsNone(result["result"])
        changed = copy.deepcopy(request)
        changed["mathematical_version"] = "hp-2015"
        self.assertEqual(execute(changed)["status"], "invalid_model")
