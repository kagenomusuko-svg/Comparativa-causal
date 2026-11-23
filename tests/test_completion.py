from fractions import Fraction
from itertools import combinations, product
import copy
import json
import unittest

from causal import execute
from causal.core import Budget, Failure
from causal.engines import pearl
from causal.external import bundle
from test_engines import ROOT, BINARY, hp, roots, rule, scm, table


def request(engine, operation, model, parameters):
    original = json.loads((ROOT / f"examples/{engine}.json").read_text())
    return original | {"operation": operation, "model": model, "parameters": parameters}


def joint(names, mass):
    return [{"when": dict(zip(names, values)), "then": str(mass(tuple(map(int, values))))}
            for values in product(BINARY, repeat=len(names))]


def frontdoor():
    def mass(states):
        x, m, y = states
        weights = {
            "x": (Fraction(1, 4), Fraction(3, 4)),
            "m": (Fraction(1, 4), Fraction(3, 4)),
        }
        total = Fraction()
        for u in (0, 1):
            px, pm = weights["x"][u], weights["m"][x]
            py = Fraction(1 + 2 * m + u, 5)
            total += (px if x else 1-px) * (pm if m else 1-pm) * (py if y else 1-py) / 2
        return total

    return {"observed": dict.fromkeys(("X", "M", "Y"), BINARY), "latent": ["U"],
            "parents": {"X": ["U"], "U": [], "M": ["X"], "Y": ["M", "U"]},
            "observational_distribution": joint(("X", "M", "Y"), mass)}


def backdoor():
    def mass(states):
        u, x, y = states
        px = Fraction(1 + 2*u, 4)
        py = Fraction(1 + u + 2*x, 5)
        return (px if x else 1-px) * (py if y else 1-py) / 2

    return {"observed": dict.fromkeys(("U", "X", "Y"), BINARY), "latent": [],
            "parents": {"U": [], "X": ["U"], "Y": ["X", "U"]},
            "observational_distribution": joint(("U", "X", "Y"), mass)}


def identification(model, criterion, **extra):
    return execute(request("pearl", "identify", model,
                   {"treatment": {"X": "1"}, "outcome": {"Y": "1"}, "criterion": criterion} | extra))


class IdentificationTests(unittest.TestCase):
    def test_frontdoor_matches_latent_truncated_factorization(self):
        result = identification(frontdoor(), "frontdoor", mediator="M")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["probability"], "3/5")
        self.assertTrue(all(result["result"]["checks"].values()))
        self.assertEqual(sum(Fraction(row["term"]) for row in result["result"]["terms"]), Fraction(3, 5))

    def test_frontdoor_rejects_each_invalid_graph(self):
        base = frontdoor()
        for target, source, check in [
            ("Y", "X", "intercepts_all_directed_paths"),
            ("M", "U", "no_treatment_mediator_backdoor"),
            ("M", "V", "treatment_blocks_mediator_outcome_backdoors"),
        ]:
            model = copy.deepcopy(base)
            if source == "V":
                model["latent"].append("V")
                model["parents"]["V"] = []
                model["parents"]["Y"].append("V")
            model["parents"][target].append(source)
            out = identification(model, "frontdoor", mediator="M")
            self.assertEqual(out["status"], "not_identifiable")
            self.assertFalse(out["result"]["checks"][check])
            self.assertIsNone(out["result"]["probability"])

    def test_backdoor_matches_manual_stratum_standardization(self):
        out = identification(backdoor(), "backdoor", adjustment=["U"])
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["result"]["probability"], "7/10")
        self.assertEqual([row["term"] for row in out["result"]["terms"]], ["3/10", "2/5"])

    def test_backdoor_and_positivity(self):
        model = frontdoor()
        model["observed"]["U"] = BINARY
        model["latent"] = []
        model["observational_distribution"] = joint(("U", "X", "M", "Y"),
            lambda values: Fraction(1, 16))
        output = identification(model, "backdoor", adjustment=["U"])
        self.assertEqual(output["result"]["probability"], "1/2")
        self.assertGreater(output["result"]["observed_independences_verified"], 0)
        self.assertEqual(identification(model, "backdoor", adjustment=["M"])["status"], "not_identifiable")
        self.assertEqual(identification(model, "backdoor", adjustment=[])["status"], "not_identifiable")
        model["observational_distribution"] = joint(("U", "X", "M", "Y"),
            lambda values: Fraction(1, 8) if values[0] == values[1] else 0)
        self.assertEqual(identification(model, "backdoor", adjustment=["U"])["status"], "not_identifiable")

    def test_invalid_independence_missing_data_and_limits(self):
        model = {"observed": {"X": BINARY, "Y": BINARY}, "latent": [],
                 "parents": {"X": [], "Y": []}}
        out = identification(model, "backdoor", adjustment=[])
        self.assertEqual(out["status"], "insufficient_data")
        self.assertTrue(all(out["result"]["checks"].values()))
        model["observational_distribution"] = joint(("X", "Y"), lambda v: Fraction(1, 2) if v[0] == v[1] else 0)
        self.assertEqual(identification(model, "backdoor", adjustment=[])["status"], "invalid_model")
        req = request("pearl", "identify", model,
                      {"criterion": "backdoor", "treatment": {"X": "1"}, "outcome": {"Y": "1"}, "adjustment": []})
        self.assertEqual(execute(req | {"options": {"max_steps": 1}})["status"], "limit_exceeded")


class ResponsibilityTests(unittest.TestCase):
    def test_conjunctive_candidate_fails_minimality(self):
        model = scm({"X": table((), lambda: "0"), "B": table((), lambda: "0"),
                     "Y": table(("X", "B"), lambda x, b: str(int(not (x and b))))})
        output = hp(model, {"X": "0", "B": "0"})
        self.assertEqual(output["responsibility"], "0")  # each is causal under a contingency
        self.assertFalse(output["ac3"])

        # With equality, a singleton is already a but-for cause.
        model["equations"]["Y"] = table(("X", "B"), lambda x, b: str(int(x == b)))
        self.assertEqual(hp(model, {"X": "0", "B": "0"})["responsibility"], "0")

    def test_witness_replay_and_minimal_change(self):
        model = scm(roots("A", "B", "C") | {"Y": table(("A", "B", "C"), lambda *v: str(max(v)))})
        result = hp(model, {"A": "1"})
        witness = result["witness"]
        self.assertEqual(result["responsibility"], "1/3")
        self.assertEqual(witness["stability_subsets_verified"], 2 ** len(witness["z"]))
        structural = pearl.SCM(model, Budget(100))
        self.assertEqual(structural.solve({}, witness["alternative"] | witness["w"])["Y"], "0")
        for size in range(len(witness["z"])+1):
            for subset in combinations(witness["z"], size):
                restore = {k: witness["actual_z"][k] for k in subset}
                self.assertEqual(structural.solve({}, {"A": "1"} | witness["w"] | restore)["Y"], "1")

    def test_published_refined_vote_with_intermediate_tally(self):
        # Halpern and Pearl (2001), Figure 4.
        model = scm(roots("V1", "V2") | {
            "M": table(("V1", "V2"), lambda a, b: str(a + b)),
            "Y": {"parents": ["M"], "rows": [
                {"when": {"M": str(count)}, "then": str(int(count > 0))} for count in range(3)]},
        })
        model["endogenous"]["M"] = ["0", "1", "2"]
        result = hp(model, {"V1": "1"})
        self.assertEqual(result["responsibility"], "1/2")
        self.assertEqual(result["actual"]["M"], "2")
        witness = result["witness"]
        self.assertEqual(pearl.SCM(model, Budget(100)).solve({}, witness["w"] | {"V1": "1"})["M"], "1")
        req = request("halpern", "responsibility", model,
                      {"context": {}, "candidate": {"V1": "1"}, "effect": {"eq": {"Y": "1"}}})
        limit = execute(req)["steps"] - 1
        interrupted = execute(req | {"options": {"max_steps": limit}})
        self.assertEqual(interrupted["status"], "limit_exceeded")
        self.assertIsNone(interrupted["result"])

    def test_actual_context_missing_and_formula(self):
        model = scm({"X": table(("U",), str)}, ["U"])
        req = request("halpern", "responsibility", model,
                      {"context": {}, "candidate": {"X": "1"}, "effect": {"not": {"eq": {"X": "0"}}}})
        self.assertEqual(execute(req)["status"], "insufficient_data")
        req["parameters"]["context"] = {"U": "1"}
        self.assertEqual(execute(req)["result"]["responsibility"], "1")


def path_rule(name, target, *requirements, composable=True):
    return rule(name, *requirements) | {"effect": target, "composable": composable}


def chain():
    return {"conditions": dict.fromkeys(("A", "B", "MID", "Y"), True),
            "roots": ["A", "B"], "complete": True,
            "mechanisms": [path_rule("first", "MID", "A"), path_rule("second", "Y", "MID", "B")]}


def reconstruct(*models, candidate="A"):
    return execute(request("ness", "reconstruct", {"reconstructions": [
        {"id": str(index), "model": model} for index, model in enumerate(models)
    ]}, {"candidate": candidate, "effect": "Y"}))


class CompositionTests(unittest.TestCase):
    def test_chain_and_certificate(self):
        result = reconstruct(chain())["result"]["reconstructions"][0]
        self.assertEqual(result["status"], "cause")
        self.assertTrue(result["necessary_across_declared_paths"])
        self.assertEqual(result["witnesses"][0]["set"], ["A", "B"])
        self.assertEqual([r["id"] for r in result["witnesses"][0]["mechanisms"]], ["first", "second"])
        self.assertEqual(reconstruct(chain(), candidate="MID")["result"]["conclusion"], "cause")

    def test_reduced_set_and_disagreement(self):
        base = chain()
        alternative = copy.deepcopy(base)
        alternative["mechanisms"].append(path_rule("short", "Y", "B"))
        self.assertEqual(reconstruct(alternative)["result"]["conclusion"], "not_causal")
        out = reconstruct(base, alternative)
        self.assertEqual(out["status"], "insufficient_data")
        self.assertEqual(out["result"]["conclusion"], "undetermined")

    def test_open_inventory_and_missing_composition_assertion(self):
        base = chain()
        base["complete"] = False
        self.assertIsNone(reconstruct(base)["result"]["reconstructions"][0]["necessary_across_declared_paths"])
        base["mechanisms"][0]["composable"] = False
        out = reconstruct(base)
        self.assertEqual(out["result"]["conclusion"], "underspecified_mechanism")
        self.assertEqual(out["status"], "insufficient_data")

    def test_declared_effect_with_missing_active_law(self):
        base = chain()
        base["complete"] = False
        base["conditions"]["A"] = False
        out = reconstruct(base, candidate="B")
        self.assertEqual(out["result"]["conclusion"], "underspecified_mechanism")
        self.assertIn({"condition": "MID", "reason": "missing_mechanism"},
                      out["result"]["reconstructions"][0]["gaps"])

    def test_cycle_and_limits(self):
        base = chain()
        base["mechanisms"].append(path_rule("cyclic", "MID", "Y"))
        self.assertEqual(reconstruct(base)["status"], "invalid_model")
        req = request("ness", "reconstruct", {"reconstructions": [{"id": "one", "model": chain()}]},
                      {"candidate": "A", "effect": "Y"})
        self.assertEqual(execute(req | {"options": {"max_steps": 2}})["status"], "limit_exceeded")


class TraceTests(unittest.TestCase):
    def test_valid_and_invalid_lineage(self):
        original = json.loads((ROOT / "examples/pearl.json").read_text())
        original["reconstruction_id"] = "R1"
        original["case"]["entries"].append({"id": "P", "kind": "proposition", "text": "Afirmación",
            "links": [{"relation": "asserted_by", "target": "S"}]})
        original["lineage"] = {
            "/model/equations/A/rows/0/then": {"basis": [{"kind": "assertion", "ref": "P"}]},
            "/parameters/query/Y": {"basis": [{"kind": "document", "ref": "S"}],
                "depends_on": ["/model/equations/A/rows/0/then"]},
        }
        out = execute(original)
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["trace"]["dependency_order"], list(original["lineage"]))
        self.assertEqual(bundle(original["case"]["id"], [out])["runs"], [out])
        with self.assertRaises(Failure):
            bundle("different", [out])
        original["lineage"]["/model/equations/A/rows/0/then"]["depends_on"] = ["/parameters/query/Y"]
        self.assertEqual(execute(original)["status"], "invalid_model")
        original["lineage"] = {"/model/missing": {"basis": [{"kind": "document", "ref": "S"}]}}
        self.assertEqual(execute(original)["status"], "invalid_model")

    def test_mistyped_relation_and_assumption_base(self):
        original = json.loads((ROOT / "examples/bayesian.json").read_text())
        original["case"]["entries"].append({"id": "P", "kind": "proposition", "text": "Posible",
            "links": [{"relation": "asserted_by", "target": "E"}]})
        self.assertEqual(execute(original)["status"], "invalid_model")
        original["case"]["entries"][-1]["links"][0]["target"] = "S"
        original["lineage"] = {"/model/nodes/H": {"basis": [
            {"kind": "assumption", "ref": original["assumptions"][0]}]}}
        self.assertEqual(execute(original)["status"], "success")
