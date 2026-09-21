from __future__ import annotations

import copy
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
MODULE_PATH = ROOT / "experiments" / "e-000" / "registry.py"
SPEC = importlib.util.spec_from_file_location("e000_registry", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
registry = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = registry
SPEC.loader.exec_module(registry)

ZERO = "sha256:" + "00" * 32
ONE = "sha256:" + "11" * 32
TWO = "sha256:" + "22" * 32
THREE = "sha256:" + "33" * 32


def receipt(role: str, shard_digest: str, size: int, suffix: int) -> dict:
    primary = role == "primary"
    host = "cdn.publisher.example" if primary else "proxy.example"
    source = "publisher.example" if primary else "proxy.example"
    return {
        "retrieval_id": f"{role}-{suffix}",
        "route_role": role,
        "route_evidence_kind": "observed_transport",
        "network_path_label": f"observed-{role}",
        "raw_receipt_sha256": ZERO,
        "source_url": f"https://{source}/weights/shard-{suffix}",
        "effective_url_without_query": f"https://{host}/objects/shard-{suffix}",
        "final_delivery_host": host,
        "resolved_ip": "192.0.2.10" if primary else "198.51.100.20",
        "dns_names": [host],
        "asn": "AS64500" if primary else "AS64501",
        "operator_organization": "Publisher CDN" if primary else "Independent Transit",
        "tls_session_sha256": (ONE if primary else TWO),
        "started_at_utc": (
            f"2026-09-21T08:0{suffix}:00Z" if primary else f"2026-09-21T09:0{suffix}:00Z"
        ),
        "completed_at_utc": (
            f"2026-09-21T08:0{suffix}:10Z" if primary else f"2026-09-21T09:0{suffix}:12Z"
        ),
        "http_status": 200,
        "complete_get": True,
        "range_requested": False,
        "resumed": False,
        "derived_from_local_bytes": False,
        "redirect_chain": (
            [f"https://{host}/objects/shard-{suffix}"] if primary else []
        ),
        "redirect_chain_raw_sha256": THREE,
        "server_declared_upstream_urls": [],
        "server_declared_upstream_raw_sha256": THREE,
        "response_headers": {
            "etag": f"object-{suffix}",
            "x_linked_etag": shard_digest.removeprefix("sha256:"),
            "x_repo_commit": "a" * 40,
            "content_length": str(size),
            "content_range": None,
            "server": "test-server",
            "via": None,
            "location_chain": (
                [f"https://{host}/objects/shard-{suffix}"] if primary else []
            ),
            "location_chain_raw_sha256": THREE,
        },
        "bytes_received": size,
        "sha256": shard_digest,
        "elapsed_seconds": 10.0 if primary else 12.0,
        "wrapper_source_sha256": THREE,
        "extractor_source_sha256": TWO,
        "toolchain": {
            "runtime": "synthetic-runtime-1",
            "downloader": "synthetic-downloader-1",
            "extractor": "synthetic-extractor-1",
        },
        "same_stream_manifest_sha256": ONE,
        "tensor_transcript_sha256": TWO,
    }


def valid_registry() -> dict:
    names = ["model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors"]
    digests = [ONE, TWO]
    sizes = [101, 202]
    shards = []
    for index, (name, digest, size) in enumerate(zip(names, digests, sizes, strict=True), 1):
        shards.append(
            {
                "path": name,
                "bytes": size,
                "lfs_sha256": digest,
                "retrievals": [
                    receipt("primary", digest, size, index),
                    receipt("secondary", digest, size, index),
                ],
            }
        )
    return {
        "schema_version": "aeye.e000-checkpoint-registry.v0",
        "experiment_id": "E-000",
        "manifest_sha256": registry.EXPECTED_MANIFEST_SHA256,
        "created_at_utc": "2026-09-21T10:00:00Z",
        "candidate_inspected": False,
        "contains_model_weight_bytes": False,
        "entries": [
            {
                "entry_id": "synthetic-checkpoint-v0",
                "repository": "https://publisher.example/models/synthetic",
                "revision": "a" * 40,
                "publisher_commit_timestamp_utc": "2026-09-20T00:00:00Z",
                "publisher_timestamp_load_bearing": False,
                "metadata_retrieved_at_utc": "2026-09-21T07:00:00Z",
                "metadata_receipt_sha256": ZERO,
                "config": {"path": "config.json", "bytes": 10, "sha256": ZERO},
                "weight_index": {
                    "path": "model.safetensors.index.json",
                    "bytes": 20,
                    "sha256": THREE,
                    "declared_weight_shards": names,
                },
                "tensor_inventory_sha256": ZERO,
                "transform_recipe": {
                    "recipe_id": "synthetic-recipe-v0",
                    "artifact_sha256": THREE,
                    "status": "frozen",
                    "unresolved_parameters": [],
                    "source_verification_sha256": TWO,
                    "semantic_entailment_review": "accepted",
                    "semantic_entailment_review_sha256": ONE,
                },
                "tensor_parallel_degrees": [1, 2, 4],
                "transport_disclosure": {
                    "same_workstation": True,
                    "same_client_implementation": True,
                    "effective_origin_shared": True,
                    "effective_origin_evidence": "object identifier equality",
                    "independent_publication": False,
                    "proxy_revision_header_status": "unresolved and non-authoritative",
                },
                "claims": [],
                "weight_shards": shards,
            }
        ],
    }


def codes(report: dict) -> set[str]:
    output = {item["code"] for item in report["findings"]}
    for entry in report["entry_results"]:
        output.update(item["code"] for item in entry["findings"])
    return output


class RegistrySchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema_path = ROOT / "schemas" / "e000-checkpoint-registry-v0.schema.json"
        cls.schema = json.loads(schema_path.read_text())
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())
        report_schema_path = (
            ROOT / "schemas" / "e000-registry-prequalification-v0.schema.json"
        )
        cls.report_schema = json.loads(report_schema_path.read_text())
        Draft202012Validator.check_schema(cls.report_schema)
        cls.report_validator = Draft202012Validator(
            cls.report_schema, format_checker=FormatChecker()
        )

    def test_valid_synthetic_registry_satisfies_schema(self) -> None:
        self.assertEqual([], list(self.validator.iter_errors(valid_registry())))

    def test_derived_report_satisfies_schema(self) -> None:
        report = registry.prequalify_registry(valid_registry())
        self.assertEqual([], list(self.report_validator.iter_errors(report)))

    def test_report_can_bind_exact_registry_artifact_bytes(self) -> None:
        document = valid_registry()
        encoded = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
        artifact_sha256 = "sha256:" + hashlib.sha256(encoded).hexdigest()
        report = registry.prequalify_registry(
            document, registry_artifact_sha256=artifact_sha256
        )
        self.assertEqual(artifact_sha256, report["registry_artifact_sha256"])
        self.assertEqual([], list(self.report_validator.iter_errors(report)))

    def test_cli_computes_exact_registry_artifact_digest(self) -> None:
        encoded = (json.dumps(valid_registry(), indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "registry.json"
            registry_path.write_bytes(encoded)
            completed = subprocess.run(
                [sys.executable, str(MODULE_PATH), str(registry_path)],
                cwd=ROOT,
                capture_output=True,
                check=False,
                text=True,
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(
            "sha256:" + hashlib.sha256(encoded).hexdigest(),
            report["registry_artifact_sha256"],
        )

    def test_cli_rejects_duplicate_members_and_nonfinite_numbers(self) -> None:
        documents = (
            b'{"schema_version":"a","schema_version":"b"}\n',
            b'{"elapsed_seconds":NaN}\n',
        )
        for encoded in documents:
            with self.subTest(encoded=encoded), tempfile.TemporaryDirectory() as directory:
                registry_path = Path(directory) / "registry.json"
                registry_path.write_bytes(encoded)
                completed = subprocess.run(
                    [sys.executable, str(MODULE_PATH), str(registry_path)],
                    cwd=ROOT,
                    capture_output=True,
                    check=False,
                    text=True,
                )
            self.assertEqual(2, completed.returncode)
            self.assertEqual("E000-REG-REJ-JSON-PARSE", json.loads(completed.stderr)["code"])

    def test_nonfinite_programmatic_input_fails_without_throwing(self) -> None:
        document = valid_registry()
        document["entries"][0]["weight_shards"][0]["retrievals"][0][
            "elapsed_seconds"
        ] = float("nan")
        report = registry.prequalify_registry(document)
        self.assertEqual("invalid_input", report["prequalification_status"])
        self.assertIsNone(report["registry_canonical_sha256"])
        self.assertIn("E000-REG-REJ-NONCANONICAL-JSON", codes(report))

    def test_schema_rejects_embedded_weight_bytes(self) -> None:
        document = valid_registry()
        document["entries"][0]["weight_shards"][0]["weight_bytes"] = "00"
        self.assertTrue(list(self.validator.iter_errors(document)))

    def test_schema_rejects_query_bearing_effective_url(self) -> None:
        document = valid_registry()
        document["entries"][0]["weight_shards"][0]["retrievals"][0][
            "effective_url_without_query"
        ] += "?secret=forbidden"
        self.assertTrue(list(self.validator.iter_errors(document)))


class RegistryPrequalificationTests(unittest.TestCase):
    def mutation(self, callback) -> dict:
        document = copy.deepcopy(valid_registry())
        callback(document)
        return registry.prequalify_registry(document)

    def test_facts_prequalify_for_t1_review_with_scoped_statement(self) -> None:
        report = registry.prequalify_registry(valid_registry())
        self.assertEqual("eligible_for_review", report["prequalification_status"])
        self.assertEqual("T0", report["entry_results"][0]["observed_tier"])
        self.assertEqual("T1", report["entry_results"][0]["candidate_tier"])
        self.assertEqual(
            "T1 (transport corroboration via a shared-effective-origin proxy); "
            "single-publisher trust; same-workstation retrieval",
            report["entry_results"][0]["candidate_tier_statement"],
        )
        self.assertTrue(report["reviewer_adjudication_required"])
        self.assertFalse(report["t2_evaluated"])
        self.assertIn("not assign T1", report["claim_ceiling"])

    def test_report_is_deterministic_and_does_not_mutate_input(self) -> None:
        document = valid_registry()
        frozen = copy.deepcopy(document)
        self.assertEqual(
            registry.prequalify_registry(document), registry.prequalify_registry(document)
        )
        self.assertEqual(frozen, document)

    def test_missing_shard_prevents_t1(self) -> None:
        report = self.mutation(lambda d: d["entries"][0]["weight_shards"].pop())
        self.assertEqual("below_minimum", report["prequalification_status"])
        self.assertIsNone(report["entry_results"][0]["observed_tier"])
        self.assertIn("T1-REJ-SHARD-COVERAGE", codes(report))

    def test_one_complete_route_is_valid_t0_but_below_t1_minimum(self) -> None:
        document = valid_registry()
        for shard in document["entries"][0]["weight_shards"]:
            shard["retrievals"] = [shard["retrievals"][0]]
        schema_path = ROOT / "schemas" / "e000-checkpoint-registry-v0.schema.json"
        schema = json.loads(schema_path.read_text())
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.assertEqual([], list(validator.iter_errors(document)))
        report = registry.prequalify_registry(document)
        self.assertEqual("below_minimum", report["prequalification_status"])
        self.assertTrue(
            all(item["observed_tier"] == "T0" for item in report["entry_results"])
        )
        self.assertTrue(
            all(item["candidate_tier"] is None for item in report["entry_results"])
        )

    def test_t0_preserves_unretained_transport_metadata_as_unknown(self) -> None:
        document = valid_registry()
        nullable = (
            "resolved_ip",
            "asn",
            "operator_organization",
            "tls_session_sha256",
            "redirect_chain_raw_sha256",
            "server_declared_upstream_raw_sha256",
            "wrapper_source_sha256",
            "extractor_source_sha256",
            "toolchain",
            "same_stream_manifest_sha256",
            "tensor_transcript_sha256",
        )
        for shard in document["entries"][0]["weight_shards"]:
            primary = shard["retrievals"][0]
            shard["retrievals"] = [primary]
            for field in nullable:
                primary[field] = None
            primary["dns_names"] = []
            primary["response_headers"]["location_chain_raw_sha256"] = None
        schema_path = ROOT / "schemas" / "e000-checkpoint-registry-v0.schema.json"
        schema = json.loads(schema_path.read_text())
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.assertEqual([], list(validator.iter_errors(document)))
        report = registry.prequalify_registry(document)
        self.assertEqual("below_minimum", report["prequalification_status"])
        self.assertEqual("T0", report["entry_results"][0]["observed_tier"])

    def test_same_host_rejects_relabel(self) -> None:
        def mutate(document: dict) -> None:
            secondary = document["entries"][0]["weight_shards"][0]["retrievals"][1]
            secondary["final_delivery_host"] = "cdn.publisher.example"

        self.assertIn("T1-REJ-RELABEL", codes(self.mutation(mutate)))

    def test_redirect_to_primary_payload_host_is_rejected(self) -> None:
        def mutate(document: dict) -> None:
            secondary = document["entries"][0]["weight_shards"][0]["retrievals"][1]
            secondary["redirect_chain"] = ["https://cdn.publisher.example/objects/shard-1"]

        self.assertIn(
            "T1-REJ-REDIRECT-SAME-PAYLOAD-HOST", codes(self.mutation(mutate))
        )

    def test_shared_tls_session_rejects_single_stream(self) -> None:
        def mutate(document: dict) -> None:
            pair = document["entries"][0]["weight_shards"][0]["retrievals"]
            pair[1]["tls_session_sha256"] = pair[0]["tls_session_sha256"]

        self.assertIn("T1-REJ-SINGLE-STREAM", codes(self.mutation(mutate)))

    def test_absent_tls_sessions_are_missing_evidence_not_a_shared_stream(self) -> None:
        def mutate(document: dict) -> None:
            pair = document["entries"][0]["weight_shards"][0]["retrievals"]
            pair[0]["tls_session_sha256"] = None
            pair[1]["tls_session_sha256"] = None

        result_codes = codes(self.mutation(mutate))
        self.assertIn("T1-REJ-MISSING-RETAINED-ARTIFACT", result_codes)
        self.assertNotIn("T1-REJ-SINGLE-STREAM", result_codes)

    def test_final_delivery_host_must_match_effective_url(self) -> None:
        def mutate(document: dict) -> None:
            document["entries"][0]["weight_shards"][0]["retrievals"][0][
                "final_delivery_host"
            ] = "unrelated.example"

        report = self.mutation(mutate)
        self.assertEqual("invalid_input", report["prequalification_status"])
        self.assertIn("E000-REG-REJ-FINAL-HOST", codes(report))

    def test_truncation_is_typed_before_digest_mismatch(self) -> None:
        def mutate(document: dict) -> None:
            secondary = document["entries"][0]["weight_shards"][0]["retrievals"][1]
            secondary["complete_get"] = False
            secondary["bytes_received"] -= 1
            secondary["sha256"] = ZERO

        result_codes = codes(self.mutation(mutate))
        self.assertIn("T1-REJ-INCOMPLETE-GET", result_codes)
        self.assertNotIn("T1-REJ-DIGEST-OR-LENGTH", result_codes)

    def test_complete_digest_mismatch_is_rejected(self) -> None:
        def mutate(document: dict) -> None:
            document["entries"][0]["weight_shards"][0]["retrievals"][1]["sha256"] = ZERO

        self.assertIn("T1-REJ-DIGEST-OR-LENGTH", codes(self.mutation(mutate)))

    def test_missing_transcript_is_rejected(self) -> None:
        def mutate(document: dict) -> None:
            del document["entries"][0]["weight_shards"][0]["retrievals"][1][
                "tensor_transcript_sha256"
            ]

        self.assertIn("T1-REJ-MISSING-RETAINED-ARTIFACT", codes(self.mutation(mutate)))

    def test_label_only_route_is_rejected(self) -> None:
        def mutate(document: dict) -> None:
            document["entries"][0]["weight_shards"][0]["retrievals"][1][
                "route_evidence_kind"
            ] = "label_only"

        self.assertIn("T1-REJ-LABEL-ONLY", codes(self.mutation(mutate)))

    def test_same_operator_is_rejected_even_with_different_host(self) -> None:
        def mutate(document: dict) -> None:
            secondary = document["entries"][0]["weight_shards"][0]["retrievals"][1]
            secondary["asn"] = "AS64500"

        self.assertIn("T1-REJ-OPERATOR-IDENTITY", codes(self.mutation(mutate)))

    def test_source_authentication_language_is_rejected(self) -> None:
        def mutate(document: dict) -> None:
            document["entries"][0]["claims"] = ["These are verified weights"]

        self.assertIn("T1-REJ-TIER-LANGUAGE", codes(self.mutation(mutate)))

    def test_independent_publication_boolean_cannot_upgrade_proxy_evidence(self) -> None:
        def mutate(document: dict) -> None:
            document["entries"][0]["transport_disclosure"]["independent_publication"] = True

        self.assertIn("T1-REJ-TIER-LANGUAGE", codes(self.mutation(mutate)))

    def test_candidate_and_model_payload_fields_fail_closed(self) -> None:
        candidate = self.mutation(lambda d: d.update({"hash_b": "00" * 32}))
        weights = self.mutation(lambda d: d.update({"model_weight_bytes": "00"}))
        self.assertEqual("invalid_input", candidate["prequalification_status"])
        self.assertEqual("invalid_input", weights["prequalification_status"])
        self.assertIn("E000-REG-REJ-CANDIDATE-MATERIAL", codes(candidate))
        self.assertIn("E000-REG-REJ-MODEL-BYTES", codes(weights))

    def test_manifest_revision_and_tp_bindings_fail_closed(self) -> None:
        manifest = self.mutation(lambda d: d.update({"manifest_sha256": ZERO}))
        revision = self.mutation(lambda d: d["entries"][0].update({"revision": "main"}))
        degrees = self.mutation(
            lambda d: d["entries"][0].update({"tensor_parallel_degrees": [4, 2, 2]})
        )
        self.assertIn("E000-REG-REJ-MANIFEST-BINDING", codes(manifest))
        self.assertIn("E000-REG-REJ-REVISION", codes(revision))
        self.assertIn("E000-REG-REJ-TP-DEGREES", codes(degrees))

    def test_owner_supplied_tier_is_not_part_of_the_input_contract(self) -> None:
        report = self.mutation(lambda d: d["entries"][0].update({"trust_tier": "T1"}))
        self.assertEqual("invalid_input", report["prequalification_status"])
        self.assertIsNone(report["entry_results"][0]["observed_tier"])
        self.assertIsNone(report["entry_results"][0]["candidate_tier"])
        self.assertIn("E000-REG-REJ-SCHEMA", codes(report))

    def test_global_binding_error_erases_entry_level_positive_results(self) -> None:
        report = self.mutation(lambda d: d.update({"manifest_sha256": ZERO}))
        entry = report["entry_results"][0]
        self.assertEqual("invalid_input", report["prequalification_status"])
        self.assertEqual("invalid_input", entry["prequalification_status"])
        self.assertIsNone(entry["observed_tier"])
        self.assertIsNone(entry["candidate_tier"])
        self.assertIsNone(entry["candidate_tier_statement"])

    def test_one_invalid_entry_erases_sibling_positive_results(self) -> None:
        document = valid_registry()
        sibling = copy.deepcopy(document["entries"][0])
        sibling["entry_id"] = "synthetic-checkpoint-invalid"
        sibling["weight_shards"][0]["retrievals"][0][
            "final_delivery_host"
        ] = "unrelated.example"
        document["entries"].append(sibling)
        report = registry.prequalify_registry(document)
        self.assertEqual("invalid_input", report["prequalification_status"])
        self.assertTrue(
            all(item["prequalification_status"] == "invalid_input" for item in report["entry_results"])
        )
        self.assertTrue(all(item["candidate_tier"] is None for item in report["entry_results"]))
        self.assertIn("E000-REG-REJ-ENTRY-SET", codes(report))

    def test_unreviewed_recipe_blocks_t1_candidacy_without_erasing_t0(self) -> None:
        def mutate(document: dict) -> None:
            recipe = document["entries"][0]["transform_recipe"]
            recipe["status"] = "proposed"
            recipe["unresolved_parameters"] = ["semantic_entailment_review"]
            recipe["semantic_entailment_review"] = "pending"
            recipe["semantic_entailment_review_sha256"] = None

        report = self.mutation(mutate)
        entry = report["entry_results"][0]
        self.assertEqual("below_minimum", report["prequalification_status"])
        self.assertEqual("T0", entry["observed_tier"])
        self.assertIsNone(entry["candidate_tier"])
        self.assertIn("E000-BLK-UNRESOLVED-TRANSFORM", codes(report))

    def test_unbound_accepted_recipe_review_is_invalid(self) -> None:
        def mutate(document: dict) -> None:
            document["entries"][0]["transform_recipe"][
                "semantic_entailment_review_sha256"
            ] = None

        report = self.mutation(mutate)
        self.assertEqual("invalid_input", report["prequalification_status"])
        self.assertIsNone(report["entry_results"][0]["candidate_tier"])
        self.assertIn("E000-REG-REJ-SCHEMA", codes(report))

    def test_recipe_review_cannot_reuse_source_verification_digest(self) -> None:
        def mutate(document: dict) -> None:
            recipe = document["entries"][0]["transform_recipe"]
            recipe["semantic_entailment_review_sha256"] = recipe[
                "source_verification_sha256"
            ]

        report = self.mutation(mutate)
        self.assertEqual("below_minimum", report["prequalification_status"])
        self.assertEqual("T0", report["entry_results"][0]["observed_tier"])
        self.assertIsNone(report["entry_results"][0]["candidate_tier"])
        self.assertIn("E000-BLK-UNRESOLVED-TRANSFORM", codes(report))

    def test_malformed_json_shapes_fail_without_throwing(self) -> None:
        documents = [
            None,
            [],
            {"schema_version": "wrong"},
            {**valid_registry(), "entries": [None]},
            {**valid_registry(), "entries": [{"entry_id": "broken", "weight_index": "x"}]},
            self._nested_malformed("tensor_parallel_degrees", [[1]]),
            self._nested_malformed("declared_weight_shards", [{}]),
            self._nested_malformed("artifact_sha256", {}),
            self._nested_malformed("route_role", {}),
        ]
        for document in documents:
            with self.subTest(document=document):
                report = registry.prequalify_registry(document)
                self.assertEqual("invalid_input", report["prequalification_status"])

    @staticmethod
    def _nested_malformed(field: str, value: object) -> dict:
        document = valid_registry()
        if field == "tensor_parallel_degrees":
            document["entries"][0][field] = value
        elif field == "declared_weight_shards":
            document["entries"][0]["weight_index"][field] = value
        elif field == "artifact_sha256":
            document["entries"][0]["transform_recipe"][field] = value
        elif field == "route_role":
            document["entries"][0]["weight_shards"][0]["retrievals"][0][field] = value
        return document

    def test_t2_is_never_inferred_by_this_contract(self) -> None:
        document = valid_registry()
        document["entries"][0]["transport_disclosure"]["effective_origin_shared"] = False
        report = registry.prequalify_registry(document)
        self.assertEqual("T1", report["entry_results"][0]["candidate_tier"])
        self.assertEqual("T0", report["entry_results"][0]["observed_tier"])
        self.assertFalse(report["entry_results"][0]["t2_evaluated"])


if __name__ == "__main__":
    unittest.main()
