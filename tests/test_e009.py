from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import unittest
from fractions import Fraction
from scripts import validate


class E009ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.experiment = validate.ROOT / "experiments" / "e-009"
        cls.artifacts = cls.experiment / "artifacts"

    def load(self, name: str) -> dict[str, object]:
        return json.loads((self.artifacts / name).read_text(encoding="utf-8"))

    def test_frozen_independent_replay_accepts(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(self.experiment / "independent_verify.py"), "--json"],
            cwd=validate.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual([], payload["findings"])

    def test_coordinate_vector_and_complete_event_denominator(self) -> None:
        result = self.load("result.json")
        self.assertEqual(
            {
                "WORK": "unknown",
                "EXECUTION": "satisfied",
                "SEMANTICS": "satisfied",
                "DEMAND": "unsupported",
            },
            result["coordinate_results"],
        )
        self.assertEqual(
            {"numerator": 13, "denominator": 13, "coded_linear": 5, "exact": 8},
            result["event_coverage"],
        )

    def test_all_preregistered_mutations_reject(self) -> None:
        mutations = self.load("mutation-results.json")
        self.assertEqual(8, mutations["case_count"])
        self.assertTrue(mutations["all_rejected"])
        self.assertTrue(mutations["all_expected_failures_observed"])
        for outcome in mutations["outcomes"]:
            self.assertIn(outcome["expected_code"], outcome["observed_codes"])

    def test_union_bound_is_below_two_to_minus_80(self) -> None:
        result = self.load("result.json")
        bound = result["conditional_union_bound"]
        observed = Fraction(bound["numerator"], bound["denominator"])
        self.assertLess(observed, Fraction(1, 2**80))

    def test_verifier_has_no_provider_or_demo_import(self) -> None:
        source = (self.experiment / "independent_verify.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertFalse(any("generate" in name or "coded_mvm_demo" in name for name in imported))

    def test_structural_receipt_and_report_are_valid(self) -> None:
        receipt_path = self.artifacts / "receipt.json"
        report_path = self.artifacts / "verification-report.json"
        self.assertEqual([], validate.validate_receipt(validate.load_json(receipt_path), receipt_path))
        self.assertEqual([], validate.validate_report(validate.load_json(report_path), report_path))

    def test_posthoc_cost_split_is_explicitly_exploratory(self) -> None:
        path = self.artifacts / "posthoc-cost-decomposition.json"
        decomposition = validate.load_json(path)
        self.assertEqual("exploratory-post-hoc", decomposition["status"])
        self.assertIn("Post-hoc", decomposition["protocol"]["relationship_to_r1"])
        self.assertEqual(
            {
                "client",
                "provider",
                "verifier",
                "preprocessing",
                "network",
                "storage",
                "privacy",
            },
            set(decomposition["coverage"]),
        )
        self.assertEqual(
            [],
            validate.schema_findings(
                decomposition,
                validate.SCHEMA_DIR / "e009-cost-decomposition-v0.schema.json",
                path,
            ),
        )

    def test_posthoc_self_consistent_forgery_is_reproduced_and_rejected(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(self.experiment / "posthoc_adversarial_probe.py"),
                "--json",
            ],
            cwd=validate.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        observed = json.loads(completed.stdout)
        retained_path = self.artifacts / "posthoc-adversarial-probe.json"
        retained = validate.load_json(retained_path)
        self.assertEqual(retained, observed)
        self.assertEqual(
            [
                "AUDIT_ACCEPTANCE_MISMATCH",
                "CODED_CHECK_TRANSCRIPT_MISMATCH",
                "CODED_LINEAR_REJECT",
                "RELATION_ACCEPTANCE_MISMATCH",
            ],
            observed["observation"]["finding_codes"],
        )
        self.assertTrue(observed["observation"]["only_coded_relation_findings"])
        self.assertEqual([], observed["observation"]["honest_regeneration_finding_codes"])
        self.assertEqual(
            [],
            validate.schema_findings(
                observed,
                validate.SCHEMA_DIR / "e009-posthoc-adversarial-probe-v0.schema.json",
                retained_path,
            ),
        )

    def test_posthoc_claim_appraisal_reproduces_and_closes_metadata_gap(self) -> None:
        verifier_path = self.experiment / "independent_verify.py"
        self.assertEqual(
            "9c4f6f4eed0c490b8261214a694db133ba33575f0fbe34c318cb6a853de7cf31",
            hashlib.sha256(verifier_path.read_bytes()).hexdigest(),
            "the preregistered R1 verifier must remain byte-for-byte frozen",
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(self.experiment / "posthoc_claim_appraisal.py"),
                "--json",
            ],
            cwd=validate.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        observed = json.loads(completed.stdout)
        retained_path = self.artifacts / "posthoc-claim-appraisal.json"
        retained = validate.load_json(retained_path)
        self.assertEqual(retained, observed)
        self.assertEqual(
            [],
            validate.schema_findings(
                observed,
                validate.SCHEMA_DIR
                / "e009-posthoc-claim-appraisal-v0.schema.json",
                retained_path,
            ),
        )

        probes = {item["case_id"]: item for item in observed["probes"]}
        self.assertTrue(probes["unchanged"]["frozen_accepted"])
        self.assertTrue(probes["unchanged"]["corrected_accepted"])
        self.assertEqual(
            ["CLAIM_COVERAGE_MISMATCH"],
            probes["inflated_coverage"]["corrected_finding_codes"],
        )
        self.assertEqual(
            ["CLAIM_ASSUMPTION_MISMATCH", "EVIDENCE_ASSUMPTION_MISMATCH"],
            probes["removed_assumptions"]["corrected_finding_codes"],
        )
        self.assertEqual(
            ["EVIDENCE_STATEMENT_MISMATCH"],
            probes["unknown_statement_id"]["corrected_finding_codes"],
        )
        for case_id in (
            "inflated_coverage",
            "removed_assumptions",
            "unknown_statement_id",
        ):
            self.assertTrue(probes[case_id]["frozen_accepted"])
            self.assertFalse(probes[case_id]["corrected_accepted"])
        self.assertFalse(probes["wrong_output_control"]["frozen_accepted"])
        self.assertFalse(probes["wrong_output_control"]["corrected_accepted"])


if __name__ == "__main__":
    unittest.main()
