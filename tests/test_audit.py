import copy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from jsonschema import Draft202012Validator

from causal import affected, affected_by_request, audit_coverage, execute
from causal.external import bundle
from test_engines import ROOT
from test_completion import chain, request
from test_fnl_2013 import covered, fig1, legal
from test_schemas import SCHEMAS


def example(engine):
    return json.loads((ROOT / f"examples/{engine}.json").read_text())


def output_trace(response, pointer):
    return next(item for item in response["trace"]["execution"]["outputs"] if item["pointer"] == pointer)


class ProvenanceTests(unittest.TestCase):
    def test_individually_missing_probabilities_and_aggregate_noninheritance(self):
        req = example("bayesian")
        first = "/model/nodes/H/rows/0/then/0"
        second = "/model/nodes/H/rows/0/then/1"
        req["lineage"] = {first: {"basis": [{"kind": "document", "ref": "S"}]},
                          "/model": {"basis": [{"kind": "document", "ref": "S"}]}}
        req["options"] = {"provenance_mode": "strict"}
        out = execute(req)
        index = {row["pointer"]: row for row in out["trace"]["coverage"]["elements"]}
        self.assertEqual(out["status"], "insufficient_data")
        self.assertEqual(index[first]["coverage"], "individual")
        self.assertEqual(index[second]["coverage"], "missing")
        self.assertIsNone(out["result"])
        self.assertEqual(out["trace"]["execution"]["status"], "unknown")
        self.assertIsNone(affected(out, [second])["requires_recalculation"])

    def test_explicit_assumptions_and_verified_group_members(self):
        req = covered(example("bayesian"))
        key = "/model/nodes/H/rows/0/then/1"
        req["lineage"][key] = {"basis": [{"kind": "assumption", "ref": req["assumptions"][0]}]}
        row = next(row for row in audit_coverage(req)["elements"] if row["pointer"] == key)
        self.assertEqual(row["coverage"], "individual")
        self.assertEqual(row["basis_kinds"], ["assumption"])
        out = execute(req)
        self.assertEqual(out["result"]["posterior"]["1"], "3/4")
        self.assertEqual(out["trace"]["provenance_status"], "declared_unverified")
        req["lineage_groups"][0]["members"].append("/model/nodes/H")
        self.assertEqual(execute(req)["status"], "invalid_model")

    def test_derived_input_is_referential_and_acyclic(self):
        req = covered(example("bayesian"))
        keys = ["/model/nodes/H/rows/0/then/0", "/model/nodes/H/rows/0/then/1"]
        req["lineage"][keys[0]] = {"basis": [{"kind": "document", "ref": "S"}]}
        req["lineage"][keys[1]] = {"basis": [{"kind": "derived", "ref": keys[0]}],
                                   "derivation": "Complemento unitario"}
        out = execute(req)
        derived = next(row for row in out["trace"]["coverage"]["elements"] if row["pointer"] == keys[1])
        self.assertEqual(derived["basis_kinds"], ["derived", "document"])
        row = output_trace(out, "/result/posterior")
        self.assertIn("/case/entries/1", row["inputs"])
        self.assertEqual([entry["pointer"] for entry in row["intermediates"]],
                         ["/result/joint_masses", "/result/evidence_probability"])
        self.assertTrue(all(entry["dependency"] == "exact" for entry in row["intermediates"]))
        req["lineage"][keys[0]] = {"basis": [{"kind": "derived", "ref": keys[1]}], "derivation": "Circular"}
        self.assertEqual(execute(req)["status"], "invalid_model")

    def test_document_assertion_and_hypothesis_changes_propagate(self):
        req = covered(example("pearl"))
        req["case"]["entries"].append({"id": "P", "kind": "proposition", "text": "Dato sintético",
                                      "links": [{"relation": "asserted_by", "target": "S"}]})
        req["lineage"]["/parameters/do/A"] = {"basis": [{"kind": "assertion", "ref": "P"},
            {"kind": "hypothesis", "ref": req["modeling_hypotheses"][0]}]}
        out = execute(req)
        for location in ("/case/entries/1/text", "/case/entries/2/text", "/modeling_hypotheses/0"):
            self.assertIn("/result/event", affected(out, [location])["affected"])
        revised = copy.deepcopy(req)
        revised["case"]["entries"][0]["text"] = "Texto no utilizado por la consulta"
        self.assertFalse(affected_by_request(out, revised)["requires_recalculation"])

    def test_changed_cpt_invalidates_and_recomputes_posterior(self):
        req = legal("infer", fig1(), {"hypothesis": "H", "evidence": {"R": "1"}})
        out = execute(req)
        revised = copy.deepcopy(req)
        revised["model"]["nodes"]["R"]["rows"][0]["then"] = {"0": "9/10", "1": "1/10"}
        report = affected_by_request(out, revised)
        self.assertEqual(report["status"], "conservative")
        self.assertIn("/result/posterior", report["affected"])
        self.assertIn("/model/nodes/R/rows/0/then/1", report["changes"])
        self.assertEqual(execute(revised)["result"]["posterior"]["1"], "10/109")
        self.assertFalse(affected_by_request(out, req)["requires_recalculation"])

    def test_necessity_certificates_scoped_to_reconstruction(self):
        model = {"reconstructions": [
            {"id": "first", "model": chain()}, {"id": "second", "model": chain()}]}
        req = covered(request("ness", "reconstruct", model, {"candidate": "A", "effect": "Y"}))
        out = execute(req)
        self.assertEqual(out["result"]["conclusion"], "cause")
        revised = copy.deepcopy(req)
        revised["model"]["reconstructions"][0]["model"]["mechanisms"][1]["requires"][0] = "A"
        report = affected_by_request(out, revised)
        self.assertIn("/result/reconstructions/0", report["affected"])
        self.assertNotIn("/result/reconstructions/1", report["affected"])
        new = execute(revised)
        self.assertEqual(new["result"]["reconstructions"][0]["witnesses"][0]["mechanisms"][0]["id"], "second")
        self.assertEqual(new["result"]["reconstructions"][1], out["result"]["reconstructions"][1])

    def test_counterfactual_and_responsibility_use_distinct_certificates(self):
        req = covered(example("pearl"))
        out = execute(req)
        row = output_trace(out, "/result/event")
        self.assertIn("/parameters/context", row["inputs"])
        self.assertIn("/parameters/do/A", row["inputs"])
        self.assertIn("/model/equations/Y/rows/1/then", out["trace"]["execution"]["observed_reads"]["inputs"])
        self.assertNotIn("/model/equations/Y/rows/0/then", out["trace"]["execution"]["observed_reads"]["inputs"])
        self.assertIn("replace_equations", row["operations"])
        req = covered(example("halpern"))
        out = execute(req)
        row = output_trace(out, "/result/responsibility")
        self.assertEqual(out["result"]["responsibility"], "1/2")
        self.assertIn("/parameters/candidate/A", row["inputs"])
        self.assertIn({"pointer": "/result/witness", "dependency": "exact"}, row["intermediates"])
        self.assertGreater(out["result"]["witness"]["stability_subsets_verified"], 0)

    def test_two_hypotheses_keep_disjoint_bases_and_outcomes(self):
        req = example("pearl")
        first = covered(req | {"reconstruction_id": "A"})
        second = copy.deepcopy(first)
        second["reconstruction_id"] = "B"
        second["parameters"]["do"] = {"A": "0", "B": "0"}
        second["assumptions"] = ["Segunda reconstrucción sintética"]
        second["lineage"] = {"/model": {"basis": [{"kind": "assumption", "ref": second["assumptions"][0]}]}}
        second.pop("lineage_groups")
        second = covered(second)
        results = [execute(first), execute(second)]
        packet = bundle(first["case"]["id"], results)
        Draft202012Validator(SCHEMAS["external-engines-v1"]).validate(packet)
        self.assertEqual([r["result"]["event"] for r in packet["runs"]], [True, False])
        self.assertNotEqual(results[0]["trace"]["elements"], results[1]["trace"]["elements"])

    def test_historical_result_and_invalid_extended_certificate(self):
        historical = execute(example("bayesian-testimony"))
        for field in ("coverage", "mode", "execution", "provenance_status"):
            historical["trace"].pop(field)
        for item in historical["result"]["pattern_certificates"]:
            item.pop("settings")
        Draft202012Validator(SCHEMAS["result-v1"]).validate(historical)
        self.assertEqual(affected(historical, ["/model"])["status"], "unknown")
        request = example("bayesian-structure")
        result = execute(request)
        result["result"]["structure_certificate"]["pattern_certificates"][0]["edges"] = [["H"]]
        self.assertFalse(Draft202012Validator(SCHEMAS["result-v1"]).is_valid(result))

    def test_cli_reports_agree_with_api_and_schemas(self):
        req = covered(example("bayesian"))
        out = execute(req)
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            inputs, result, changes = (directory / name for name in ("input.json", "result.json", "changes.json"))
            inputs.write_text(json.dumps(req))
            result.write_text(json.dumps(out))
            paths = ["/model/nodes/H/rows/0/then/0"]
            changes.write_text(json.dumps(paths))
            for switches, expected, schema in [
                (["--coverage", str(inputs)], audit_coverage(req), "coverage-v1"),
                (["--changes", str(changes), str(result)], affected(out, paths), "affected-v1"),
                (["--revised", str(inputs), str(result)], affected_by_request(out, req), "affected-v1"),
            ]:
                command = [sys.executable, "-m", "causal", *switches]
                observed = json.loads(subprocess.check_output(command, cwd=ROOT))
                Draft202012Validator(SCHEMAS[schema]).validate(observed)
                self.assertEqual(observed, expected)
