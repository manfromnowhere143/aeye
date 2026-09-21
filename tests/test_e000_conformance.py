from __future__ import annotations

import hashlib
import json
import struct
import sys
import unittest
from pathlib import Path

from blake3 import blake3


ROOT = Path(__file__).resolve().parents[1]
E000 = ROOT / "experiments" / "e-000"
if str(E000) not in sys.path:
    sys.path.insert(0, str(E000))

import blake3_reference  # noqa: E402
import audit_reviewer_freeze  # noqa: E402
import conformance  # noqa: E402
import slab_recipe  # noqa: E402
import verify_pearl_oracle  # noqa: E402


def digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def assert_code(test: unittest.TestCase, code: str, callback) -> None:
    with test.assertRaises(conformance.ConformanceError) as context:
        callback()
    test.assertEqual(code, context.exception.code)


def dense_vector() -> dict[str, bytes | conformance.PublicProofDataV3]:
    rows_pattern = bytes.fromhex("070103010000")  # [0, 8, 64, 72]
    cols_pattern = bytes.fromhex("000103010101")  # [0, 1, 8, 9, 32, 33, 40, 41]
    mining_config = struct.pack("<IHH", 1024, 64, 0) + rows_pattern + cols_pattern + bytes(32)

    incomplete_header = b"".join(
        (
            struct.pack("<I", 0x20000000),
            bytes(range(32)),
            bytes(range(32, 64)),
            struct.pack("<II", 1_800_000_000, 0x1D00FFFF),
        )
    )
    slab = bytes((index * 73 + 19) % 256 for index in range(64 * 1024))
    parsed_config = conformance.MiningConfiguration.parse(mining_config)
    header = conformance.IncompleteBlockHeader.parse(incomplete_header)
    job_key = blake3(incomplete_header + mining_config).digest()
    hash_b = blake3(slab, key=job_key).digest()
    public_data = b"".join(
        (
            mining_config,
            bytes([0xA5]) * 32,
            hash_b,
            bytes([0x5A]) * 32,
            struct.pack("<IIII", 128, 64, 0, 0),
        )
    )
    parsed_public = conformance.PublicProofDataV3.parse(public_data)
    proof_commitment = conformance.double_sha256(struct.pack("<I", 3) + public_data)
    full_header = incomplete_header + proof_commitment
    header_hash = conformance.double_sha256(full_header)
    proof_data = bytes.fromhex("0011223344556677")
    certificate = b"".join(
        (
            struct.pack("<I", 3),
            header_hash,
            struct.pack("<I", len(public_data)),
            public_data,
            struct.pack("<I", len(proof_data)),
            proof_data,
        )
    )
    return {
        "mining_config": mining_config,
        "incomplete_header": incomplete_header,
        "full_header": full_header,
        "public_data": public_data,
        "certificate": certificate,
        "slab": slab,
        "job_key": job_key,
        "hash_b": hash_b,
        "parsed_public": parsed_public,
        "parsed_config": parsed_config,
        "parsed_header": header,
    }


def moe_public_data() -> bytes:
    rows_pattern = bytes.fromhex("070103010000")
    cols_pattern = bytes.fromhex("000103010101")
    trailer = struct.pack("<HH", 4, 2) + bytes(28)
    mining_config = struct.pack("<IHH", 1024, 64, 0) + rows_pattern + cols_pattern + trailer
    core = b"".join(
        (
            mining_config,
            bytes([0x11]) * 32,
            bytes([0x22]) * 32,
            bytes([0x33]) * 32,
            struct.pack("<IIII", 128, 64, 0, 0),
        )
    )
    return b"".join(
        (
            core,
            struct.pack("<H", 0),
            struct.pack("<4I", 100, 150, 200, 256),
            bytes([0x44]) * 32,
            bytes([4]),
            struct.pack("<4I", 1, 2, 3, 4),
        )
    )


class Blake3ReferenceTests(unittest.TestCase):
    def test_reference_matches_optimized_across_tree_boundaries(self) -> None:
        lengths = (0, 1, 63, 64, 65, 1023, 1024, 1025, 2048, 3072, 4097, 8199)
        key = bytes(range(32))
        for length in lengths:
            with self.subTest(length=length, mode="unkeyed"):
                data = bytes((index * 131 + 7) % 256 for index in range(length))
                self.assertEqual(blake3(data).digest(), blake3_reference.digest(data))
            with self.subTest(length=length, mode="keyed"):
                data = bytes((index * 17 + 211) % 256 for index in range(length))
                self.assertEqual(
                    blake3(data, key=key).digest(),
                    blake3_reference.digest(data, key=key),
                )

    def test_reference_rejects_wrong_key_length(self) -> None:
        with self.assertRaises(ValueError):
            blake3_reference.digest(b"value", key=b"short")


class ReviewerFreezeAuditTests(unittest.TestCase):
    def test_all_owner_amendment_checks_pass_without_creating_acceptance(self) -> None:
        report = audit_reviewer_freeze.build_report()
        self.assertEqual(
            "historical_amendments_confirmed_binding_corrected_review_pending",
            report["status"],
        )
        self.assertEqual([], report["failed"])
        self.assertFalse(report["protocol_sequence_blocked"])
        self.assertTrue(report["sequence_correction_implemented"])
        self.assertTrue(report["binding_correction_implemented"])
        self.assertTrue(report["fresh_reviewer_readback_blocked"])
        self.assertEqual(
            [
                "A1",
                "A2",
                "A3",
                "A4",
                "A5",
                "A6",
                "A7",
                "A8",
                "A9",
                "A10",
                "A11",
                "A12",
                "D1",
                "D2",
                "D3",
                "D4",
                "OWNER-CHECKLIST-DIGEST",
                "OWNER-SEQUENCE-CORRECTION",
            ],
            [item["amendment_id"] for item in report["checks"]],
        )
        self.assertFalse(report["candidate_input_read_by_this_program"])
        self.assertFalse(report["operator_acceptance_created"])

    def test_missing_control_is_detected_on_a_copy(self) -> None:
        manifest = json.loads(audit_reviewer_freeze.MANIFEST_PATH.read_text())
        freeze = json.loads(audit_reviewer_freeze.FREEZE_PATH.read_text())
        manifest["known_bad_controls"] = manifest["known_bad_controls"][:-1]
        checks = audit_reviewer_freeze.audit(
            manifest,
            freeze,
            freeze_digest=audit_reviewer_freeze.sha256(audit_reviewer_freeze.FREEZE_PATH),
            checklist_digest=audit_reviewer_freeze.sha256(
                audit_reviewer_freeze.CHECKLIST_PATH
            ),
            pab_text=audit_reviewer_freeze.PAB_PATH.read_text(),
        )
        control_check = next(item for item in checks if item.amendment_id == "A7")
        self.assertFalse(control_check.passed)
        self.assertIn("E000-KB-30", control_check.detail)

    def test_operator_acceptance_before_freezes_is_detected_on_a_copy(self) -> None:
        manifest = json.loads(audit_reviewer_freeze.MANIFEST_PATH.read_text())
        manifest["procedure"][1], manifest["procedure"][5] = (
            manifest["procedure"][5],
            manifest["procedure"][1],
        )
        corrected, reviewer_pending, _detail = (
            audit_reviewer_freeze._sequence_correction_state(manifest)
        )
        self.assertFalse(corrected)
        self.assertTrue(reviewer_pending)

    def test_self_referential_reviewer_field_is_detected_on_a_copy(self) -> None:
        manifest = json.loads(audit_reviewer_freeze.MANIFEST_PATH.read_text())
        manifest["frozen_inputs"].append(
            {
                "input_id": "reviewer_freeze_sha256",
                "value": "sha256:" + "00" * 32,
                "status": "blocked",
            }
        )
        freeze = json.loads(audit_reviewer_freeze.FREEZE_PATH.read_text())
        checks = audit_reviewer_freeze.audit(
            manifest,
            freeze,
            freeze_digest=audit_reviewer_freeze.sha256(audit_reviewer_freeze.FREEZE_PATH),
            checklist_digest=audit_reviewer_freeze.sha256(
                audit_reviewer_freeze.CHECKLIST_PATH
            ),
            pab_text=audit_reviewer_freeze.PAB_PATH.read_text(),
        )
        self.assertFalse(next(item for item in checks if item.amendment_id == "D1").passed)

    def test_predecessor_acceptance_pointer_is_detected_on_a_copy(self) -> None:
        manifest = json.loads(audit_reviewer_freeze.MANIFEST_PATH.read_text())
        inputs = {item["input_id"]: item for item in manifest["frozen_inputs"]}
        selection = inputs["candidate_selection_rule"]["value"]
        selection["inputs"][0] = (
            "T_accept: UTC time of the operator acceptance record that cites this "
            "file's SHA-256"
        )
        freeze = json.loads(audit_reviewer_freeze.FREEZE_PATH.read_text())
        checks = audit_reviewer_freeze.audit(
            manifest,
            freeze,
            freeze_digest=audit_reviewer_freeze.sha256(audit_reviewer_freeze.FREEZE_PATH),
            checklist_digest=audit_reviewer_freeze.sha256(
                audit_reviewer_freeze.CHECKLIST_PATH
            ),
            pab_text=audit_reviewer_freeze.PAB_PATH.read_text(),
        )
        self.assertFalse(next(item for item in checks if item.amendment_id == "D2").passed)

    def test_historical_predecessor_cannot_regain_active_status(self) -> None:
        manifest = json.loads(audit_reviewer_freeze.MANIFEST_PATH.read_text())
        inputs = {item["input_id"]: item for item in manifest["frozen_inputs"]}
        inputs["predecessor_reviewer_freeze"]["status"] = "fixed"
        freeze = json.loads(audit_reviewer_freeze.FREEZE_PATH.read_text())
        checks = audit_reviewer_freeze.audit(
            manifest,
            freeze,
            freeze_digest=audit_reviewer_freeze.sha256(audit_reviewer_freeze.FREEZE_PATH),
            checklist_digest=audit_reviewer_freeze.sha256(
                audit_reviewer_freeze.CHECKLIST_PATH
            ),
            pab_text=audit_reviewer_freeze.PAB_PATH.read_text(),
        )
        self.assertFalse(next(item for item in checks if item.amendment_id == "D3").passed)


class PearlOracleContractTests(unittest.TestCase):
    def test_active_dependency_identities_match_pinned_pearl_lock(self) -> None:
        pearl_lock = verify_pearl_oracle.PEARL / "zk-pow" / "Cargo.lock"
        if not pearl_lock.is_file():
            self.skipTest("pinned Pearl checkout is not hydrated in this source-only checkout")
        result = verify_pearl_oracle.verify_oracle_dependency_identities()
        self.assertTrue(result["all_active_identities_present_in_pinned_pearl_lock"])
        self.assertGreater(result["active_oracle_packages"], 0)


class CertificateV3ConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vector = dense_vector()

    def test_dense_v3_envelope_roundtrips_and_binds_header(self) -> None:
        header = conformance.BlockHeader.parse(self.vector["full_header"])  # type: ignore[arg-type]
        certificate = conformance.CertificateV3.parse(self.vector["certificate"])  # type: ignore[arg-type]
        conformance.verify_header_certificate_binding(header, certificate)
        self.assertEqual(self.vector["hash_b"], certificate.public_data.hash_b)
        self.assertEqual(
            self.vector["job_key"],
            certificate.public_data.job_key(header.incomplete),
        )

    def test_matrix_commitment_matches_public_hash_b_in_both_lanes(self) -> None:
        transcript = conformance.matrix_commitment_transcript(
            self.vector["slab"], self.vector["job_key"]  # type: ignore[arg-type]
        )
        self.assertTrue(transcript["engines_agree"])
        self.assertEqual(self.vector["hash_b"].hex(), transcript["primary_root_hex"])  # type: ignore[union-attr]

    def test_v1_v2_and_unknown_versions_fail_closed(self) -> None:
        certificate = bytearray(self.vector["certificate"])  # type: ignore[arg-type]
        for version in (1, 2, 4, 0xFFFFFFFF):
            with self.subTest(version=version):
                mutated = bytearray(certificate)
                struct.pack_into("<I", mutated, 0, version)
                assert_code(
                    self,
                    "E000_CERTIFICATE_VERSION",
                    lambda mutated=mutated: conformance.CertificateV3.parse(bytes(mutated)),
                )

    def test_moe_v3_public_data_roundtrips_and_uses_stacked_b_shape(self) -> None:
        public = conformance.PublicProofDataV3.parse(moe_public_data())
        self.assertIsNotNone(public.moe)
        self.assertEqual(4, public.mining_config.experts)
        self.assertEqual(2, public.mining_config.top_k)
        self.assertEqual(moe_public_data(), public.to_bytes())
        matrix = slab_recipe.Int8Matrix(4 * 64, 1024, bytes(4 * 64 * 1024))
        slab_recipe.validate_slab_against_public_data(matrix, public)

    def test_dense_moe_presence_mismatch_and_outer_count_fail_closed(self) -> None:
        dense = bytearray(self.vector["public_data"])  # type: ignore[arg-type]
        struct.pack_into("<HH", dense, 20, 4, 2)
        assert_code(
            self,
            "E000_MOE_TAIL_MISSING",
            lambda: conformance.PublicProofDataV3.parse(bytes(dense)),
        )

        moe = bytearray(moe_public_data())
        outer_count_offset = 164 + 2 + 4 * 4 + 32
        moe[outer_count_offset] = 3
        del moe[-4:]
        assert_code(
            self,
            "E000_MOE_OUTER_COUNT",
            lambda: conformance.PublicProofDataV3.parse(bytes(moe)),
        )

    def test_certificate_length_and_public_data_mutations_fail_closed(self) -> None:
        certificate = self.vector["certificate"]  # type: ignore[assignment]
        assert_code(
            self,
            "E000_CERTIFICATE_TRUNCATED",
            lambda: conformance.CertificateV3.parse(certificate[:39]),
        )
        assert_code(
            self,
            "E000_CERTIFICATE_LENGTH",
            lambda: conformance.CertificateV3.parse(certificate + b"\x00"),
        )
        public_data = self.vector["public_data"]  # type: ignore[assignment]
        proof_data = bytes.fromhex("0011223344556677")
        mutated = b"".join(
            (
                certificate[:36],
                struct.pack("<I", 163),
                public_data[:163],
                struct.pack("<I", len(proof_data)),
                proof_data,
            )
        )
        assert_code(
            self,
            "E000_PUBLIC_DATA_LENGTH",
            lambda: conformance.CertificateV3.parse(mutated),
        )

    def test_noncanonical_mining_config_is_rejected(self) -> None:
        config = bytearray(self.vector["mining_config"])  # type: ignore[arg-type]
        config[-1] = 1
        assert_code(
            self,
            "E000_MINING_CONFIG_RESERVED",
            lambda: conformance.MiningConfiguration.parse(bytes(config)),
        )

    def test_header_hash_and_proof_commitment_are_separate_checks(self) -> None:
        certificate = conformance.CertificateV3.parse(self.vector["certificate"])  # type: ignore[arg-type]
        header_bytes = bytearray(self.vector["full_header"])  # type: ignore[arg-type]
        header_bytes[0] ^= 1
        changed_header = conformance.BlockHeader.parse(bytes(header_bytes))
        assert_code(
            self,
            "E000_CERTIFICATE_BLOCK_HASH",
            lambda: conformance.verify_header_certificate_binding(changed_header, certificate),
        )

        header_bytes = bytearray(self.vector["full_header"])  # type: ignore[arg-type]
        header_bytes[-1] ^= 1
        certificate_bytes = bytearray(self.vector["certificate"])  # type: ignore[arg-type]
        certificate_bytes[4:36] = conformance.double_sha256(bytes(header_bytes))
        changed_certificate = conformance.CertificateV3.parse(bytes(certificate_bytes))
        changed_header = conformance.BlockHeader.parse(bytes(header_bytes))
        assert_code(
            self,
            "E000_CERTIFICATE_PROOF_COMMITMENT",
            lambda: conformance.verify_header_certificate_binding(changed_header, changed_certificate),
        )

    def test_padding_key_orientation_and_layout_controls_diverge(self) -> None:
        raw = bytes((index * 5 + 1) % 256 for index in range(1025))
        key = self.vector["job_key"]  # type: ignore[assignment]
        correct = conformance.matrix_commitment_transcript(raw, key)["primary_root_hex"]
        self.assertNotEqual(correct, blake3(raw, key=key).hexdigest())
        wrong_key = bytes([key[0] ^ 1]) + key[1:]
        self.assertNotEqual(correct, conformance.matrix_commitment_transcript(raw, wrong_key)["primary_root_hex"])
        self.assertNotEqual(correct, blake3(conformance.pad_to_chunk_boundary(raw)).hexdigest())

        matrix = slab_recipe.Int8Matrix(5, 205, raw[: 5 * 205])
        transposed = matrix.transpose()
        self.assertNotEqual(
            conformance.matrix_commitment_transcript(matrix.data, key)["primary_root_hex"],
            conformance.matrix_commitment_transcript(transposed.data, key)["primary_root_hex"],
        )


class SlabRecipeTests(unittest.TestCase):
    def _recipe(self, data: bytes) -> dict:
        return {
            "schema_version": "aeye.e000-slab-recipe.v0",
            "protocol": {
                "pearl_commit": conformance.PEARL_COMMIT,
                "vllm_version": "0.20.2",
                "certificate_version": 3,
            },
            "sources": [
                {
                    "source_id": "fused_qkv",
                    "path": "unused.bin",
                    "sha256": digest(data),
                    "rows": 8,
                    "cols": 4,
                    "dtype": "int8_twos_complement",
                    "layout": "c_row_major_contiguous",
                    "checkpoint_tensor": "layer.qkv_proj.weight",
                }
            ],
            "steps": [
                {
                    "step_id": "tp_rank_1",
                    "op": "select_row_ranges",
                    "input": "fused_qkv",
                    "ranges": [
                        {"label": "q.rank1", "start": 2, "stop": 4},
                        {"label": "k.rank1", "start": 5, "stop": 6},
                        {"label": "v.rank1", "start": 7, "stop": 8},
                    ],
                }
            ],
            "output": {
                "matrix_id": "tp_rank_1",
                "expected_rows": 4,
                "expected_cols": 4,
                "semantic_layout": "pearl_B_transpose_n_by_k_c_row_major",
            },
        }

    def test_fused_partition_is_explicit_and_not_naive_equal_slice(self) -> None:
        data = bytes(range(32))
        recipe = self._recipe(data)
        source = slab_recipe.Int8Matrix(8, 4, data)
        output, transcript = slab_recipe.evaluate_recipe(recipe, {"fused_qkv": source})
        expected = source.row_slice(2, 4).data + source.row_slice(5, 6).data + source.row_slice(7, 8).data
        self.assertEqual(expected, output.data)
        self.assertNotEqual(source.row_slice(4, 8).data, output.data)
        self.assertEqual(["q.rank1", "k.rank1", "v.rank1"], transcript["steps"][0]["labels"])

    def test_fusion_order_changes_output_digest(self) -> None:
        data = bytes(range(32))
        correct = self._recipe(data)
        wrong = json.loads(json.dumps(correct))
        wrong["steps"][0]["ranges"][0], wrong["steps"][0]["ranges"][2] = (
            wrong["steps"][0]["ranges"][2],
            wrong["steps"][0]["ranges"][0],
        )
        source = slab_recipe.Int8Matrix(8, 4, data)
        correct_output, _ = slab_recipe.evaluate_recipe(correct, {"fused_qkv": source})
        wrong_output, _ = slab_recipe.evaluate_recipe(wrong, {"fused_qkv": source})
        self.assertNotEqual(digest(correct_output.data), digest(wrong_output.data))

    def test_expert_order_must_be_canonical(self) -> None:
        expert0 = bytes(range(8))
        expert1 = bytes(range(8, 16))
        recipe = {
            "schema_version": "aeye.e000-slab-recipe.v0",
            "protocol": {
                "pearl_commit": conformance.PEARL_COMMIT,
                "vllm_version": "0.20.2",
                "certificate_version": 3,
            },
            "sources": [
                {
                    "source_id": "e0",
                    "path": "e0.bin",
                    "sha256": digest(expert0),
                    "rows": 2,
                    "cols": 4,
                    "dtype": "int8_twos_complement",
                    "layout": "c_row_major_contiguous",
                },
                {
                    "source_id": "e1",
                    "path": "e1.bin",
                    "sha256": digest(expert1),
                    "rows": 2,
                    "cols": 4,
                    "dtype": "int8_twos_complement",
                    "layout": "c_row_major_contiguous",
                },
            ],
            "steps": [
                {
                    "step_id": "stacked",
                    "op": "stack_experts",
                    "inputs": ["e1", "e0"],
                    "expert_ids": [1, 0],
                }
            ],
            "output": {
                "matrix_id": "stacked",
                "expected_rows": 4,
                "expected_cols": 4,
                "semantic_layout": "pearl_B_transpose_n_by_k_c_row_major",
            },
        }
        sources = {
            "e0": slab_recipe.Int8Matrix(2, 4, expert0),
            "e1": slab_recipe.Int8Matrix(2, 4, expert1),
        }
        assert_code(
            self,
            "E000_EXPERT_ORDER",
            lambda: slab_recipe.evaluate_recipe(recipe, sources),
        )

    def test_source_digest_and_final_shape_fail_closed(self) -> None:
        data = bytes(range(32))
        recipe = self._recipe(data)
        wrong_source = slab_recipe.Int8Matrix(8, 4, bytes(reversed(data)))
        assert_code(
            self,
            "E000_SOURCE_DIGEST",
            lambda: slab_recipe.evaluate_recipe(recipe, {"fused_qkv": wrong_source}),
        )
        recipe["output"]["expected_rows"] = 5
        source = slab_recipe.Int8Matrix(8, 4, data)
        assert_code(
            self,
            "E000_OUTPUT_SHAPE",
            lambda: slab_recipe.evaluate_recipe(recipe, {"fused_qkv": source}),
        )

    def test_native_dense_shape_is_checked_separately(self) -> None:
        vector = dense_vector()
        public = vector["parsed_public"]
        correct = slab_recipe.Int8Matrix(64, 1024, vector["slab"])  # type: ignore[arg-type]
        slab_recipe.validate_slab_against_public_data(correct, public)  # type: ignore[arg-type]
        wrong = slab_recipe.Int8Matrix(32, 2048, vector["slab"])  # type: ignore[arg-type]
        assert_code(
            self,
            "E000_NATIVE_SLAB_SHAPE",
            lambda: slab_recipe.validate_slab_against_public_data(wrong, public),  # type: ignore[arg-type]
        )


if __name__ == "__main__":
    unittest.main()
