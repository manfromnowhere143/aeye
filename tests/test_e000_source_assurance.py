from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "experiments" / "e-000" / "source_assurance.py"
SPEC = importlib.util.spec_from_file_location("e000_source_assurance", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SourceAssuranceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s0 = MODULE.SourceFacts(
            publisher_revision_frozen=True,
            metadata_digests_retained=True,
            all_shards_complete=True,
            all_lengths_match=True,
            all_sha256_match=True,
            same_stream_transcripts_retained=True,
            independent_parser_replay_passed=True,
            single_publisher_trust_disclosed=True,
        )

    def test_default_facts_fail_closed(self) -> None:
        decision = MODULE.classify(MODULE.SourceFacts())
        self.assertEqual(decision.source_class, MODULE.SourceClass.BLOCKED)
        self.assertEqual(decision.code, "S-BLK-PUBLISHER-ASSOCIATION")

    def test_one_complete_content_addressed_source_is_s0(self) -> None:
        decision = MODULE.classify(self.s0)
        self.assertEqual(decision.source_class, MODULE.SourceClass.S0_PUBLISHER_ASSOCIATED)
        self.assertEqual(decision.transport_observation, "NO_SECOND_PATH_OBSERVATION")

    def test_second_transport_does_not_upgrade_source_class(self) -> None:
        decision = MODULE.classify(
            replace(
                self.s0,
                second_transport_complete=True,
                second_transport_path_distinct=True,
            )
        )
        self.assertEqual(decision.source_class, MODULE.SourceClass.S0_PUBLISHER_ASSOCIATED)
        self.assertEqual(decision.transport_observation, "SECOND_PATH_OBSERVED")

    def test_independent_exact_derivation_upgrades_to_s1(self) -> None:
        decision = MODULE.classify(
            replace(
                self.s0,
                independent_derivation_complete=True,
                independent_derivation_exact=True,
                derivation_recipe_frozen=True,
                derivation_implementation_independent=True,
                upstream_source_trust_disclosed=True,
            )
        )
        self.assertEqual(decision.source_class, MODULE.SourceClass.S1_INDEPENDENTLY_DERIVED)

    def test_partial_derivation_does_not_upgrade(self) -> None:
        decision = MODULE.classify(replace(self.s0, independent_derivation_complete=True))
        self.assertEqual(decision.source_class, MODULE.SourceClass.S0_PUBLISHER_ASSOCIATED)

    def test_undisclosed_upstream_trust_does_not_upgrade(self) -> None:
        decision = MODULE.classify(
            replace(
                self.s0,
                independent_derivation_complete=True,
                independent_derivation_exact=True,
                derivation_recipe_frozen=True,
                derivation_implementation_independent=True,
            )
        )
        self.assertEqual(decision.source_class, MODULE.SourceClass.S0_PUBLISHER_ASSOCIATED)

    def test_missing_digest_match_blocks(self) -> None:
        decision = MODULE.classify(replace(self.s0, all_sha256_match=False))
        self.assertEqual(decision.source_class, MODULE.SourceClass.BLOCKED)

    def test_every_s0_prerequisite_fails_closed(self) -> None:
        prerequisites = (
            "publisher_revision_frozen",
            "metadata_digests_retained",
            "all_shards_complete",
            "all_lengths_match",
            "all_sha256_match",
            "same_stream_transcripts_retained",
            "independent_parser_replay_passed",
            "single_publisher_trust_disclosed",
        )
        for field in prerequisites:
            with self.subTest(field=field):
                decision = MODULE.classify(replace(self.s0, **{field: False}))
                self.assertEqual(decision.source_class, MODULE.SourceClass.BLOCKED)

    def test_missing_single_publisher_disclosure_blocks(self) -> None:
        decision = MODULE.classify(replace(self.s0, single_publisher_trust_disclosed=False))
        self.assertEqual(decision.source_class, MODULE.SourceClass.BLOCKED)

    def test_candidate_leakage_blocks(self) -> None:
        decision = MODULE.classify(replace(self.s0, candidate_inspected=True))
        self.assertEqual(decision.source_class, MODULE.SourceClass.BLOCKED)
        self.assertEqual(decision.code, "S-INV-CANDIDATE-LEAKAGE")


if __name__ == "__main__":
    unittest.main()
