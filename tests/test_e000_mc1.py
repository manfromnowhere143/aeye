from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
MC1 = ROOT / "experiments" / "e-000" / "mc1"
ARTIFACTS = MC1 / "artifacts"
SPEC = importlib.util.spec_from_file_location("e000_mc1_compare", MC1 / "compare_mc1.py")
assert SPEC is not None and SPEC.loader is not None
COMPARE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COMPARE
SPEC.loader.exec_module(COMPARE)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"object required: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MC1PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load(MC1 / "publication-manifest-v0.json")
        cls.preregistration = load(MC1 / "mc1-preregistration.json")
        cls.python = load(ARTIFACTS / "python-oracle-result-v1.json")
        cls.rust = load(ARTIFACTS / "rust-result-v1.json")
        cls.agreement = load(ARTIFACTS / "mc1-agreement-v1.json")
        cls.provenance = load(MC1 / "input-provenance-v0.json")
        cls.ledger = load(ROOT / "evidence" / "ledger" / "sources.json")

    def test_publication_manifest_is_content_addressed(self) -> None:
        seen: set[str] = set()
        for entry in self.manifest["artifacts"]:
            relative = entry["path"]
            self.assertNotIn(relative, seen)
            seen.add(relative)
            target = (MC1 / relative).resolve(strict=True)
            target.relative_to(MC1.resolve())
            self.assertTrue(target.is_file())
            self.assertFalse(target.is_symlink())
            self.assertEqual(entry["bytes"], target.stat().st_size)
            self.assertEqual(entry["sha256"], sha256(target))

        expected = {
            path.relative_to(MC1).as_posix()
            for path in MC1.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.name not in {"README.md", "publication-manifest-v0.json"}
        }
        self.assertEqual(expected, seen)

    def test_three_lane_result_rederives_from_retained_outputs(self) -> None:
        observed = COMPARE.compare(self.preregistration, self.python, self.rust)
        observed["inputs"] = {
            "preregistration_sha256": f"sha256:{sha256(MC1 / 'mc1-preregistration.json')}",
            "python_result_sha256": (
                f"sha256:{sha256(ARTIFACTS / 'python-oracle-result-v1.json')}"
            ),
            "rust_result_sha256": (f"sha256:{sha256(ARTIFACTS / 'rust-result-v1.json')}"),
        }
        self.assertEqual(self.agreement, observed)
        self.assertEqual(self.manifest["result"], observed["agreement"])

    def test_posthoc_mutation_probe_replays_byte_identically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "probe.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(MC1 / "posthoc_adversarial_probe.py"),
                    "--preregistration",
                    str(MC1 / "mc1-preregistration.json"),
                    "--python-result",
                    str(ARTIFACTS / "python-oracle-result-v1.json"),
                    "--rust-result",
                    str(ARTIFACTS / "rust-result-v1.json"),
                    "--output",
                    str(output),
                ],
                cwd=MC1,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
            self.assertEqual(
                (ARTIFACTS / "posthoc-adversarial-probe-v1.json").read_bytes(),
                output.read_bytes(),
            )

    def test_result_sources_and_locks_are_bound(self) -> None:
        python_implementation = self.python["implementation"]
        rust_implementation = self.rust["implementation"]
        self.assertEqual(python_implementation["source_sha256"], sha256(MC1 / "python_lane.py"))
        self.assertEqual(rust_implementation["source_sha256"], sha256(MC1 / "src" / "main.rs"))
        self.assertEqual(rust_implementation["cargo_toml_sha256"], sha256(MC1 / "Cargo.toml"))
        self.assertEqual(rust_implementation["cargo_lock_sha256"], sha256(MC1 / "Cargo.lock"))
        self.assertEqual(
            rust_implementation["rust_toolchain_sha256"],
            sha256(MC1 / "rust-toolchain.toml"),
        )

    def test_replay_receipt_binds_exact_result_bytes(self) -> None:
        receipt = load(ARTIFACTS / "replay-receipt-v1.json")
        self.assertEqual(
            receipt["outputs"],
            {
                "agreement_sha256": sha256(ARTIFACTS / "mc1-agreement-v1.json"),
                "python_result_sha256": sha256(ARTIFACTS / "python-oracle-result-v1.json"),
                "rust_result_sha256": sha256(ARTIFACTS / "rust-result-v1.json"),
            },
        )
        self.assertFalse(receipt["candidate_inspected"])
        self.assertFalse(receipt["weight_bearing_temporary_files_retained"])

    def test_public_packet_contains_no_local_or_persuasion_material(self) -> None:
        forbidden = (
            b"/Users/",
            b"/private/tmp/",
            b"/tmp/",
            b"Claude",
            b"Codex",
            b"Omri",
            b"Columbia",
        )
        for path in MC1.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                payload = path.read_bytes()
                for marker in forbidden:
                    self.assertNotIn(marker, payload, f"{marker!r} leaked in {path}")

    def test_result_cannot_be_laundered_into_a_candidate_claim(self) -> None:
        self.assertFalse(self.manifest["candidate_inspected"])
        self.assertFalse(self.manifest["contains_model_weight_bytes"])
        self.assertFalse(self.agreement["synthetic_key_is_candidate_job_key"])
        self.assertEqual("owner_result_awaiting_adversarial_readback", self.manifest["status"])

    def test_external_inputs_are_unique_content_addresses(self) -> None:
        entries = self.manifest["external_inputs"]
        identifiers = [entry["artifact_id"] for entry in entries]
        digests = [entry["sha256"] for entry in entries]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(len(digests), len(set(digests)))
        for digest in digests:
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_input_provenance_is_closed_and_matches_retained_results(self) -> None:
        schema = load(ROOT / "schemas" / "e000-mc1-input-provenance-v0.schema.json")
        Draft202012Validator.check_schema(schema)
        errors = list(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
                self.provenance
            )
        )
        self.assertEqual([], errors)

        registry = self.provenance["reviewed_registry"]
        self.assertEqual(
            registry["sha256"],
            self.python["inputs"]["reviewed_registry_sha256"].removeprefix("sha256:"),
        )
        self.assertEqual(
            registry["sha256"],
            self.rust["inputs"]["reviewed_registry_sha256"].removeprefix("sha256:"),
        )
        self.assertEqual(
            sorted(shard["extraction_receipt_sha256"] for shard in self.provenance["shards"]),
            sorted(self.python["inputs"]["extraction_receipt_sha256"]),
        )
        self.assertFalse(self.provenance["public_replay"]["full_replay_from_repository_alone"])

        ledger_by_url = {
            entry["url"]: entry for entry in self.ledger["entries"] if entry.get("url") is not None
        }
        for shard in self.provenance["shards"]:
            entry = ledger_by_url[shard["source_url"]]
            self.assertEqual(entry["evidence_status"], "metadata_only")
            self.assertEqual(entry["artifact"]["sha256"], f"sha256:{shard['stream_sha256']}")
            self.assertIn(self.provenance["checkpoint"]["revision"], entry["version"])


if __name__ == "__main__":
    unittest.main()
