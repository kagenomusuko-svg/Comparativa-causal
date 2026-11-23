"""Academic fixtures contain only abstract variables and published hypothetical numbers."""
from fractions import Fraction
import unittest

from causal import audit_coverage, execute
from causal.engines import bayesian
from test_completion import request
from test_engines import BINARY, table
from test_patterns import bit_row, fragment, root


def covered(req, scope="/model"):
    req["lineage"] = {scope: {"basis": [{"kind": "assumption", "ref": req["assumptions"][0]}]}}
    req["lineage_groups"] = [{"record": scope, "members": [
        item["pointer"] for item in audit_coverage(req)["elements"]
    ]}]
    req["options"] = {"provenance_mode": "strict"}
    return req


def legal(operation, model, params):
    req = request("bayesian", operation, model, params) | {"mathematical_version": bayesian.VERSION}
    return covered(req)


def pattern(kind, settings=None, **roles):
    result = fragment(kind, **roles)
    return result if settings is None else result | {"settings": settings}


def network(nodes, *fragments, extra_states=None):
    return {"domains": dict.fromkeys(nodes, BINARY) | (extra_states or {}),
            "nodes": nodes, "idioms": list(fragments)}


def fig1():
    return network({"H": root(Fraction(1, 100)), "R": {"rows":
        table(("H",), lambda h: bit_row(Fraction(1) if h else Fraction(1, 1_000_000)))["rows"]}},
        fragment("evidence", target="H", report="R"))


class Published2013Tests(unittest.TestCase):
    def test_figure_1_exact_match_probability(self):
        req = legal("infer", fig1(), {"hypothesis": "H", "evidence": {"R": "1"}, "alternatives": ["1", "0"]})
        out = execute(req)
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["result"]["posterior"]["1"], "1000000/1000099")
        self.assertEqual(out["result"]["comparison"]["likelihood_ratio"]["value"], "1000000")

    def test_figure_5_accurate_and_inaccurate_match(self):
        model = network({"H": root(Fraction(1, 100)), "A": root(Fraction(9, 10)),
                         "R": {"rows": table(("H", "A"), lambda h, a: bit_row(
                             (Fraction(1) if h else Fraction(1, 1_000_000)) if a else Fraction(1, 2)))["rows"]}},
                        fragment("evidence_accuracy", target="H", accuracy="A", report="R"))
        for constraints, expected in [({"A": "1"}, "1000000/1000099"), ({"A": "0"}, "1/100")]:
            result = execute(legal("infer", model, {"hypothesis": "H", "evidence": {"R": "1"} | constraints}))
            self.assertEqual(result["result"]["posterior"]["1"], expected)
        result = execute(legal("infer", model, {"hypothesis": "H", "evidence": {"R": "1"}}))["result"]
        self.assertEqual(result["posterior"]["1"], "9500000/59000891")

    def test_figures_8_9_13_16_structure_without_cpts(self):
        model = network(
            {name: ({"parents": []} if name in {"O", "M1", "M2", "C", "B", "V"} else {}) for name in
             ("O", "M1", "M2", "M", "H", "C", "B", "V", "A", "R", "AA", "AR")},
            fragment("accuracy_components", target="H", report="R", accuracy="A",
                     competence="C", objectivity="B", veracity="V"),
            pattern("necessary_opportunity", {"opportunity_absent": "0", "hypothesis_true": "1"},
                    opportunity="O", hypothesis="H"),
            fragment("aggregate_motive", motives=["M1", "M2"], aggregate="M", hypothesis="H"),
            fragment("alibi_accuracy", opportunity="O", hypothesis="H", accuracy="AA", report="AR"))
        out = execute(legal("structure", model, {"hypothesis": "H", "reports": ["R", "AR"]}))
        cert = out["result"]["structure_certificate"]
        self.assertEqual(cert["effective_parents"]["A"], ["B", "C", "V"])
        self.assertEqual(cert["effective_parents"]["H"], ["M", "O"])
        self.assertEqual(cert["effective_parents"]["M"], ["M1", "M2"])
        self.assertEqual(cert["effective_parents"]["AA"], ["H"])
        self.assertEqual(cert["effective_parents"]["AR"], ["AA", "O"])
        self.assertEqual(cert["evidence_paths"], {"R": "direct", "AR": "circumstantial"})
        self.assertEqual(set(cert["nodes_without_tables"]), set(model["nodes"]))
        model["nodes"]["H"]["parents"] = ["M1"]
        out = execute(legal("structure", model, {"hypothesis": "H", "reports": ["R"]}))
        self.assertEqual(out["status"], "invalid_model")

    def test_figures_7_and_22_reusable_subgraphs(self):
        model = network(
            {name: {} for name in ("M1", "M2", "M3", "M", "H", "O", "OR", "OA", "H1", "H2",
                                   "C", "C1", "C2", "ER", "A1", "A2", "R1", "R2")},
            fragment("aggregate_motive", motives=["M1", "M2", "M3"], aggregate="M", hypothesis="H"),
            fragment("alibi_accuracy", opportunity="O", hypothesis="H", accuracy="OA", report="OR"),
            fragment("evidence_accuracy", target="H1", report="R1", accuracy="A1"),
            pattern("evidence_accuracy", target="H2", report="R2", accuracy="A2") | {"id": "second_accuracy"},
            pattern("exclusive_explanations", {"active_states": {"C1": "1", "C2": "1"},
                    "pathways": {"C1": "first", "C2": "second"}, "impossible": "invalid"},
                    causes=["C1", "C2"], effect="ER", selector="C"),
            extra_states={"C": ["first", "second", "invalid"]})
        declared = {"O": [], "M1": [], "M2": [], "M3": [], "H1": ["H"], "H2": ["H1"],
                    "C1": ["H"], "C2": [], "A1": [], "A2": []}
        for node, parents in declared.items():
            model["nodes"][node]["parents"] = parents
        out = execute(legal("structure", model, {"hypothesis": "H", "reports": ["OR", "R1", "R2", "ER"]}))
        cert = out["result"]["structure_certificate"]
        self.assertEqual(cert["effective_parents"]["M"], ["M1", "M2", "M3"])
        self.assertEqual(cert["effective_parents"]["C"], ["C1", "C2"])
        self.assertEqual(cert["effective_parents"]["R2"], ["A2", "H2"])
        self.assertEqual(set(cert["evidence_paths"].values()), {"circumstantial"})

    def test_false_claim_of_necessary_opportunity(self):
        model = network({"O": root(Fraction(1, 2)), "H": table(("O",), lambda _: bit_row(Fraction(1, 2)))},
            pattern("necessary_opportunity", {"opportunity_absent": "0", "hypothesis_true": "1"},
                    opportunity="O", hypothesis="H"))
        req = legal("infer", model, {"hypothesis": "H", "evidence": {}})
        self.assertEqual(execute(req)["status"], "invalid_model")

    def test_figure_14_dependence_and_section_4_sequence(self):
        model = network({"H": root(Fraction(1, 10)), "D": root(Fraction(1, 2)),
                         "E1": table(("H",), lambda h: bit_row(Fraction(1 + 7*h, 10))),
                         "E2": table(("D", "E1", "H"), lambda d, e, h:
                                     bit_row(Fraction(e) if d else Fraction(1 + 7*h, 10)))},
                        fragment("dependent_evidence", target="H", first_report="E1",
                                 second_report="E2", dependency="D"))
        req = legal("evidence_sequence", model, {"hypothesis": "H", "evidence": {"D": "1"},
                    "sequence": [{"E1": "1"}, {"E2": "1"}]})
        out = execute(req)["result"]
        self.assertEqual(out["effective_parents"]["E2"], ["D", "E1", "H"])
        self.assertEqual([item["posterior"]["1"] for item in out["sequence"]], ["8/17", "8/17"])
        req["parameters"]["sequence"][1]["E2"] = "0"
        self.assertEqual(execute(req)["status"], "undefined_operation")
        terms = execute(legal("evidence_sensitivity", model, {
            "hypothesis": "H", "evidence": {"D": "1"}, "reports": ["E2"]}))["result"]
        self.assertEqual(terms["evidence_sensitivity"]["E2"]["0"]["posterior"]["1"], "2/83")
        self.assertEqual(terms["evidence_sensitivity_ranges"]["E2"]["1"], {"min": "2/83", "max": "8/17"})
        req["parameters"]["sequence"][1]["E2"] = "1"
        req["parameters"]["evidence"]["D"] = "0"
        self.assertEqual(execute(req)["result"]["sequence"][-1]["posterior"]["1"], "64/73")

    def test_explaining_away_and_exclusive_calibration(self):
        model = network({"A": root(Fraction(7, 10)), "B": root(Fraction(3, 10)),
                         "E": table(("A", "B"), lambda a, b: bit_row(Fraction(1) if a else
                                                                  Fraction(1, 2) if b else Fraction()))},
                        fragment("explaining_away", cause_a="A", cause_b="B", effect="E"))
        base = execute(legal("infer", model, {"hypothesis": "A", "evidence": {"E": "1"}}))["result"]
        self.assertEqual(base["posterior"]["1"], "140/149")
        model["domains"]["C"] = ["A", "B", "invalid"]
        model["nodes"]["C"] = table(("A", "B"), lambda a, b: {
            "A": str(int(a > b)), "B": str(int(b > a)), "invalid": str(int(a == b))})
        model["idioms"] = [pattern("exclusive_explanations",
            {"active_states": {"A": "1", "B": "1"}, "pathways": {"A": "A", "B": "B"}, "impossible": "invalid"},
            causes=["A", "B"], effect="E", selector="C")]
        out = execute(legal("infer", model, {"hypothesis": "A", "evidence": {"E": "1"}}))["result"]
        self.assertEqual(out["prior"]["1"], "7/10")
        self.assertEqual(out["posterior"]["1"], "14/17")
        self.assertEqual(out["soft_evidence_certificate"]["weights"],
                         {"A": "10/7", "B": "10/3", "invalid": "0"})
        req = legal("infer", model, {"hypothesis": "A", "evidence": {}, "soft_evidence": {
            "C": {"A": "1/2", "B": "1/2", "invalid": "0"}}})
        self.assertEqual(execute(req)["result"]["prior"]["1"], "1/2")
        model["nodes"]["C"]["rows"][0]["then"] = {"A": "1", "B": "0", "invalid": "0"}
        self.assertEqual(execute(req)["status"], "invalid_model")

    def test_figure_18_selector_and_likelihood(self):
        selector = pattern("exclusive_explanations", {"active_states": {"A": "1", "B": "1"},
                           "pathways": {"A": "a", "B": "b"}, "impossible": "invalid"},
                           causes=["A", "B"], effect="E", selector="S")
        model = network({"A": root(Fraction(1, 2)), "B": root(Fraction(1, 2)),
                         "E": table(("A", "B"), lambda a, b: bit_row(Fraction(1) if a else Fraction(b, 100))),
                         "S": table(("A", "B"), lambda a, b: {
                             "a": str(int(a>b)), "b": str(int(b>a)), "invalid": str(int(a==b))})},
                        selector, extra_states={"S": ["a", "b", "invalid"]})
        out = execute(legal("infer", model, {"hypothesis": "A", "evidence": {"E": "1"}}))["result"]
        self.assertEqual(out["posterior"]["1"], "100/101")
        self.assertEqual(out["soft_evidence_certificate"]["target"], {"a": "1/2", "b": "1/2", "invalid": "0"})

    def test_three_exclusive_paths_preserve_marginals(self):
        # Fenton, Neil and Lagnado technical report, general solution, Fig. 20.
        p = {"A": Fraction(7, 10), "B": Fraction(1, 5), "C": Fraction(1, 10)}
        paths = {cause: cause.lower() for cause in p}
        states = list(paths.values()) + ["invalid"]

        def selector(*values):
            active = [paths[cause] for cause, is_active in zip(p, values) if is_active]
            chosen = active[0] if len(active) == 1 else "invalid"
            return {state: str(int(state == chosen)) for state in states}

        model = network({key: root(mass) for key, mass in p.items()} | {
            "E": table(tuple(p), lambda *v: bit_row(Fraction(int(any(v))))),
            "S": table(tuple(p), selector),
        }, pattern("exclusive_explanations", {"active_states": dict.fromkeys(p, "1"),
                  "pathways": paths, "impossible": "invalid"},
                  causes=list(p), selector="S", effect="E"), extra_states={"S": states})
        result = execute(legal("infer", model, {"hypothesis": "S", "evidence": {}}))["result"]
        self.assertEqual(result["posterior"], {"a": "7/10", "b": "1/5", "c": "1/10", "invalid": "0"})
        self.assertEqual(result["soft_evidence_certificate"]["weights"],
                         {"a":"25/18","b":"100/27","c":"25/6","invalid":"0"})

    def test_provenance_of_cpts_required_for_new_profile_and_old_alias_compatible(self):
        req = legal("infer", fig1(), {"hypothesis": "H", "evidence": {"R": "1"}})
        req.pop("lineage_groups")
        req.pop("options")
        self.assertEqual(execute(req)["status"], "insufficient_data")
        req["mathematical_version"] = bayesian.LEGACY_VERSION
        self.assertEqual(execute(req)["result"]["posterior"]["1"], "1000000/1000099")
