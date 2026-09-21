from __future__ import annotations

import unittest

from scripts import validate


class RepositoryValidationTests(unittest.TestCase):
    def test_repository_packet_passes(self) -> None:
        findings, outcomes = validate.validate_repository()
        self.assertEqual([], findings)
        manifest = validate.load_json(validate.FIXTURE_MANIFEST)
        self.assertEqual(len(manifest["valid"]) + len(manifest["invalid"]), len(outcomes))

    def test_every_negative_fixture_is_rejected(self) -> None:
        manifest = validate.load_json(validate.FIXTURE_MANIFEST)
        findings, outcomes = validate.validate_fixture_manifest()
        self.assertEqual([], findings)
        for fixture in manifest["invalid"]:
            observed = {item.code for item in outcomes[fixture["path"]]}
            self.assertTrue(observed, fixture["path"])
            self.assertTrue(set(fixture["expected_codes"]).issubset(observed), fixture["path"])

    def test_fixture_subject_binding_is_reproducible(self) -> None:
        receipt = validate.load_json(validate.ROOT / "fixtures/valid/minimal-receipt.json")
        subject = receipt["subject"]
        self.assertEqual(subject["intent_id"], validate.expected_intent_id(subject))
        self.assertEqual(subject["job_id"], validate.expected_job_id(subject))
        self.assertEqual(subject["subject_root"], validate.expected_subject_root(subject))

    def test_no_retained_source_is_unledgered(self) -> None:
        ledger = validate.load_json(validate.LEDGER)
        codes = {item.code for item in validate.validate_ledger(ledger)}
        self.assertNotIn("UNLEDGERED_RETAINED_FILE", codes)
        self.assertNotIn("UNLEDGERED_RETAINED_GIT", codes)

    def test_experiment_payload_is_not_misparsed_as_a_manifest(self) -> None:
        payload = validate.ROOT / "experiments" / "e-009" / "input.json"
        self.assertTrue(payload.is_file())
        manifests = {
            *validate.ROOT.joinpath("experiments").rglob("manifest.json"),
            *validate.ROOT.joinpath("experiments").rglob("preregistration.json"),
        }
        self.assertNotIn(payload, manifests)


if __name__ == "__main__":
    unittest.main()
