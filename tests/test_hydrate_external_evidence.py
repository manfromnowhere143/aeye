from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from scripts import hydrate_external_evidence


class ExternalEvidenceHydrationTests(unittest.TestCase):
    def require_all_or_no_external_paths(self, paths: list[Path], kind: str) -> None:
        present = [path.exists() for path in paths]
        if not any(present):
            self.skipTest(f"{kind} evidence is not hydrated in this source-only checkout")
        self.assertTrue(all(present), f"{kind} evidence is only partially hydrated")

    def test_ledger_file_sources_are_digest_pinned_and_publicly_retrievable(self) -> None:
        specs = hydrate_external_evidence.load_file_specs()
        self.assertEqual(33, len(specs))
        self.assertEqual(len(specs), len({spec.path for spec in specs}))
        for spec in specs:
            self.assertRegex(spec.sha256, re.compile(r"^sha256:[0-9a-f]{64}$"))
            hydrate_external_evidence.require_file_path(spec)
            hydrate_external_evidence.require_public_https(
                spec.source_id, spec.retrieval_url
            )

    def test_current_file_evidence_matches_the_ledger(self) -> None:
        specs = hydrate_external_evidence.load_file_specs()
        self.require_all_or_no_external_paths(
            [spec.absolute_path for spec in specs], "file"
        )
        for spec in specs:
            observed = hydrate_external_evidence.verify_file(spec)
            self.assertEqual(spec.sha256, observed["sha256"])
            self.assertGreater(observed["bytes"], 0)

    def test_file_evidence_rejects_unsafe_locator_and_corrupt_bytes(self) -> None:
        spec = hydrate_external_evidence.FileSpec(
            source_id="test:unsafe",
            path="evidence/papers/test.pdf",
            sha256="sha256:" + "00" * 32,
            retrieval_url="http://arxiv.org/pdf/test",
        )
        with self.assertRaises(ValueError):
            hydrate_external_evidence.require_public_https(
                spec.source_id, spec.retrieval_url
            )
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "test.pdf"
            artifact.write_bytes(b"not the expected source")
            with self.assertRaises(RuntimeError):
                hydrate_external_evidence.verify_file(spec, artifact)

    def test_file_evidence_rejects_path_escape(self) -> None:
        spec = hydrate_external_evidence.FileSpec(
            source_id="test:escape",
            path="../outside.pdf",
            sha256="sha256:" + "00" * 32,
            retrieval_url="https://arxiv.org/pdf/test",
        )
        with self.assertRaises(ValueError):
            hydrate_external_evidence.require_file_path(spec)

    def test_ledger_git_sources_are_closed_and_safe(self) -> None:
        specs = hydrate_external_evidence.load_specs()
        self.assertEqual(
            {
                "git:hawkeye:30703fcb",
                "git:immaculate:2e45382f",
                "git:mma-sim:5efd4b7a",
                "git:pearl:4a0c24bc",
                "git:pearl-pips:9dacf7fb",
                "git:vllm:bc150f50",
            },
            {spec.source_id for spec in specs},
        )
        self.assertEqual(len(specs), len({spec.path for spec in specs}))
        for spec in specs:
            self.assertRegex(spec.commit, re.compile(r"^[0-9a-f]{40}$"))
            self.assertTrue(spec.path.startswith("evidence/external/"))
            parsed = urlparse(spec.remote)
            self.assertEqual("https", parsed.scheme)
            self.assertEqual("github.com", parsed.hostname)
            self.assertIsNone(parsed.username)

    def test_current_external_checkouts_match_the_ledger(self) -> None:
        specs = hydrate_external_evidence.load_specs()
        self.require_all_or_no_external_paths(
            [spec.absolute_path for spec in specs], "Git"
        )
        for spec in specs:
            observed = hydrate_external_evidence.verify_checkout(spec)
            self.assertEqual(spec.commit, observed["commit"])
            self.assertEqual(spec.remote, observed["remote"])
            self.assertEqual("", observed["status"])


if __name__ == "__main__":
    unittest.main()
