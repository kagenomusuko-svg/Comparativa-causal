import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from causal import execute
from causal.external import bundle

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {p.name.split(".")[0]: json.loads(p.read_text(encoding="utf-8"))
           for p in (ROOT / "schemas").glob("*.json")}


class SchemaTests(unittest.TestCase):
    def test_schemas_and_examples(self):
        for schema in SCHEMAS.values():
            Draft202012Validator.check_schema(schema)
        results = []
        for path in sorted((ROOT / "examples").glob("*.json")):
            with self.subTest(path=path):
                request = json.loads(path.read_text(encoding="utf-8"))
                Draft202012Validator(SCHEMAS["case-v1"]).validate(request["case"])
                Draft202012Validator(SCHEMAS["request-v1"]).validate(request)
                result = execute(request)
                Draft202012Validator(SCHEMAS["result-v1"]).validate(result)
                self.assertEqual(result["status"], "success")
                results.append(result)
        report = bundle(results[0]["case_id"], results)
        Draft202012Validator(SCHEMAS["external-engines-v1"]).validate(report)

    def test_failure_outputs_are_valid(self):
        sample = json.loads((ROOT / "examples/halpern.json").read_text(encoding="utf-8"))
        samples = [None, sample | {"engine":[]}, sample | {"case":{"id":7}},
                   sample | {"options":{"max_steps":1}}, sample | {"mathematical_version":"other"}]
        for payload in samples:
            result = execute(payload)
            self.assertNotEqual(result["status"], "success")
            Draft202012Validator(SCHEMAS["result-v1"]).validate(result)

    def test_success_schema_rejects_sham_result(self):
        sample = json.loads((ROOT / "examples/halpern.json").read_text(encoding="utf-8"))
        result = execute(sample)
        result["result"] = {"responsibility": "0"}
        self.assertFalse(Draft202012Validator(SCHEMAS["result-v1"]).is_valid(result))
