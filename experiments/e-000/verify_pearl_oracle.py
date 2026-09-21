#!/usr/bin/env python3
"""Compare E-000's two BLAKE3 lanes with Pearl's pinned Rust implementation."""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PEARL = ROOT / "evidence" / "external" / "pearl"
ORACLE = HERE / "pearl-oracle" / "Cargo.toml"
RUST_TOOLCHAIN = "1.98.1"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from conformance import (  # noqa: E402
    PEARL_COMMIT,
    IncompleteBlockHeader,
    MiningConfiguration,
    matrix_commitment_transcript,
    sha256_hex,
)


def run(arguments: list[str], cwd: Path | None = None) -> str:
    environment = os.environ.copy()
    environment.update(
        {
            "CARGO_NET_GIT_FETCH_WITH_CLI": "true",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    completed = subprocess.run(
        arguments,
        cwd=cwd,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        diagnostic = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"{' '.join(arguments)} failed: {diagnostic}")
    return completed.stdout.strip()


def run_failure(arguments: list[str], expected_code: str, cwd: Path | None = None) -> str:
    environment = os.environ.copy()
    environment.update(
        {
            "CARGO_NET_GIT_FETCH_WITH_CLI": "true",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    completed = subprocess.run(
        arguments,
        cwd=cwd,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode == 0:
        raise RuntimeError(f"{' '.join(arguments)} unexpectedly succeeded")
    diagnostic = completed.stderr.strip() or completed.stdout.strip()
    if expected_code not in diagnostic:
        raise RuntimeError(
            f"{' '.join(arguments)} did not emit {expected_code}: {diagnostic}"
        )
    return diagnostic


def deterministic_inputs() -> tuple[bytes, bytes, bytes]:
    rows_pattern = bytes.fromhex("070103010000")
    cols_pattern = bytes.fromhex("000103010101")
    config = struct.pack("<IHH", 1024, 64, 0) + rows_pattern + cols_pattern + bytes(32)
    header = b"".join(
        (
            struct.pack("<I", 0x20000000),
            bytes(range(32)),
            bytes(range(32, 64)),
            struct.pack("<II", 1_800_000_000, 0x1D00FFFF),
        )
    )
    slab = bytes((index * 73 + 19) % 256 for index in range(64 * 1024 + 17))
    return header, config, slab


def verify_oracle_dependency_identities() -> dict[str, object]:
    oracle_lock_path = ORACLE.parent / "Cargo.lock"
    pearl_lock_path = PEARL / "zk-pow" / "Cargo.lock"
    oracle_lock = tomllib.loads(oracle_lock_path.read_text(encoding="utf-8"))
    pearl_lock = tomllib.loads(pearl_lock_path.read_text(encoding="utf-8"))

    def identity(package: dict[str, object]) -> tuple[object, ...]:
        return (
            package.get("name"),
            package.get("version"),
            package.get("source"),
            package.get("checksum"),
        )

    pearl_identities = {identity(package) for package in pearl_lock["package"]}
    oracle_packages = [
        package
        for package in oracle_lock["package"]
        if package["name"] != "aeye-e000-pearl-oracle"
    ]
    drift = sorted(
        f"{package['name']}@{package['version']}"
        for package in oracle_packages
        if identity(package) not in pearl_identities
    )
    if drift:
        raise RuntimeError(f"Pearl-oracle dependency identities drift from the pin: {drift}")
    return {
        "active_oracle_packages": len(oracle_packages),
        "all_active_identities_present_in_pinned_pearl_lock": True,
        "pearl_zk_pow_lock_sha256": sha256_hex(pearl_lock_path.read_bytes()),
        "oracle_lock_sha256": sha256_hex(oracle_lock_path.read_bytes()),
        "difference_scope": "Aeye binary root added; inactive pyo3 and zk-pow dev dependencies pruned",
    }


def main() -> int:
    try:
        dependency_lock = verify_oracle_dependency_identities()
        observed_commit = run(["git", "rev-parse", "HEAD"], cwd=PEARL)
        if observed_commit != PEARL_COMMIT:
            raise RuntimeError(f"Pearl checkout is {observed_commit}, expected {PEARL_COMMIT}")
        if run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=PEARL):
            raise RuntimeError("Pearl checkout is dirty")

        header, config, slab = deterministic_inputs()
        parsed_header = IncompleteBlockHeader.parse(header)
        parsed_config = MiningConfiguration.parse(config)
        if parsed_header.to_bytes() != header or parsed_config.to_bytes() != config:
            raise RuntimeError("Aeye parser round-trip changed deterministic input bytes")

        with tempfile.TemporaryDirectory(prefix="aeye-e000-oracle-") as temporary:
            temporary_path = Path(temporary)
            header_path = temporary_path / "header.bin"
            config_path = temporary_path / "config.bin"
            slab_path = temporary_path / "slab.bin"
            header_path.write_bytes(header)
            config_path.write_bytes(config)
            slab_path.write_bytes(slab)

            build_command = [
                "cargo",
                f"+{RUST_TOOLCHAIN}",
                "build",
                "--quiet",
                "--locked",
                "--manifest-path",
                str(ORACLE),
            ]
            run(build_command)
            oracle_binary = ORACLE.parent / "target" / "debug" / "aeye-e000-pearl-oracle"
            if not oracle_binary.is_file():
                raise RuntimeError(f"Pearl oracle binary was not built at {oracle_binary}")
            command = [str(oracle_binary)]
            pearl_job_key = run([*command, "job-key", str(header_path), str(config_path)])
            structured_output = run(
                [
                    *command,
                    "job-key-fields",
                    str(parsed_header.version),
                    parsed_header.prev_block_display_order.hex(),
                    parsed_header.merkle_root_display_order.hex(),
                    str(parsed_header.timestamp),
                    str(parsed_header.nbits),
                    str(config_path),
                ]
            )
            pearl_header_hex, pearl_config_hex, pearl_structured_job_key = structured_output.split(":")
            if bytes.fromhex(pearl_header_hex) != header:
                raise RuntimeError("Pearl structured header serialization differs from the wire bytes")
            if bytes.fromhex(pearl_config_hex) != config:
                raise RuntimeError("Pearl structured mining-config serialization differs from the wire bytes")
            if pearl_structured_job_key != pearl_job_key:
                raise RuntimeError("Pearl raw-byte and structured job_key paths disagree")

            reversed_once_output = run(
                [
                    *command,
                    "job-key-fields",
                    str(parsed_header.version),
                    header[4:36].hex(),
                    parsed_header.merkle_root_display_order.hex(),
                    str(parsed_header.timestamp),
                    str(parsed_header.nbits),
                    str(config_path),
                ]
            )
            reversed_once_header, _, reversed_once_job_key = reversed_once_output.split(":")
            if bytes.fromhex(reversed_once_header) == header or reversed_once_job_key == pearl_job_key:
                raise RuntimeError("Pearl structured path did not detect one extra header-hash reversal")

            swapped_scalars_output = run(
                [
                    *command,
                    "job-key-fields",
                    str(parsed_header.version),
                    parsed_header.prev_block_display_order.hex(),
                    parsed_header.merkle_root_display_order.hex(),
                    str(parsed_header.nbits),
                    str(parsed_header.timestamp),
                    str(config_path),
                ]
            )
            swapped_scalars_header, _, swapped_scalars_job_key = swapped_scalars_output.split(":")
            if bytes.fromhex(swapped_scalars_header) == header or swapped_scalars_job_key == pearl_job_key:
                raise RuntimeError("Pearl structured path did not detect swapped timestamp and nbits")

            config_mutations = {
                "nonzero_reserved": config[:51] + b"\x01",
                "dense_top_k_nonzero": config[:22] + b"\x01\x00" + config[24:],
                "unsupported_mma_type": config[:6] + b"\x01\x00" + config[8:],
                "wrong_length": config[:-1],
            }
            config_controls = []
            for mutation, mutated_config in config_mutations.items():
                mutated_path = temporary_path / f"config-{mutation}.bin"
                mutated_path.write_bytes(mutated_config)
                diagnostic = run_failure(
                    [
                        *command,
                        "job-key-fields",
                        str(parsed_header.version),
                        parsed_header.prev_block_display_order.hex(),
                        parsed_header.merkle_root_display_order.hex(),
                        str(parsed_header.timestamp),
                        str(parsed_header.nbits),
                        str(mutated_path),
                    ],
                    "E000-REJ-MINING-CONFIG",
                )
                config_controls.append(
                    {
                        "control_id": "E000-KB-22",
                        "mutation": mutation,
                        "expected_diagnostic": "E000-REJ-MINING-CONFIG",
                        "pearl_rejected": True,
                        "pearl_diagnostic": diagnostic,
                    }
                )
            aeye_job_key = parsed_config
            del aeye_job_key  # parsing is checked above; job_key is over the canonical bytes directly
            from blake3 import blake3

            primary_job_key = blake3(header + config).hexdigest()
            from blake3_reference import digest as reference_blake3

            reference_job_key = reference_blake3(header + config).hex()
            if len({pearl_job_key, primary_job_key, reference_job_key}) != 1:
                raise RuntimeError("Pearl, optimized, and reference job_key lanes disagree")

            transcript = matrix_commitment_transcript(slab, bytes.fromhex(primary_job_key))
            pearl_root = run([*command, "matrix-root", str(slab_path), primary_job_key])
            if pearl_root != transcript["primary_root_hex"]:
                raise RuntimeError("Pearl and Aeye matrix-root lanes disagree")

            seed_arguments = ["aa" * 32, "bb" * 32, "192", "320", "11" * 32]
            salted_seed_output = run([*command, "noise-seeds", "salted", *seed_arguments])
            salted_b_seed, salted_a_seed = salted_seed_output.split(":")
            expected_salted_b = "60ed9b73c5a9599b200b6cd563e7f0d5d9a67d2402d85fd4ef966c580080d0e5"
            expected_salted_a = "301784168005ec833ab0aa60006f7fe7faaa95307d8c1fc6819b2ffdd717eccf"
            if (salted_b_seed, salted_a_seed) != (expected_salted_b, expected_salted_a):
                raise RuntimeError("Pearl Salted seed derivation differs from its pinned V3 vector")
            legacy_seed_output = run([*command, "noise-seeds", "legacy", *seed_arguments])
            legacy_b_seed, legacy_a_seed = legacy_seed_output.split(":")
            if (legacy_b_seed, legacy_a_seed) == (salted_b_seed, salted_a_seed):
                raise RuntimeError("Pearl Legacy and Salted seed derivations did not diverge")

        result = {
            "schema_version": "aeye.e000-pearl-parity.v0",
            "status": "synthetic_conformance_only",
            "protocol": {
                "pearl_commit": PEARL_COMMIT,
                "certificate_version": 3,
                "pearl_oracle": "zk_pow::api serialization plus pearl-blake3 hashing and MerkleTree",
                "rust_toolchain": RUST_TOOLCHAIN,
                "dependency_lock": dependency_lock,
            },
            "inputs": {
                "incomplete_header_sha256": sha256_hex(header),
                "mining_config_sha256": sha256_hex(config),
                "slab_sha256": sha256_hex(slab),
                "slab_bytes": len(slab),
            },
            "job_key": {
                "pearl_hex": pearl_job_key,
                "pearl_structured_hex": pearl_structured_job_key,
                "aeye_optimized_hex": primary_job_key,
                "aeye_reference_hex": reference_job_key,
                "all_agree": True,
            },
            "structured_serialization": {
                "header_76_hex": pearl_header_hex,
                "mining_config_52_hex": pearl_config_hex,
                "pearl_types": [
                    "zk_pow::api::proof::IncompleteBlockHeader",
                    "zk_pow::api::proof::MiningConfiguration",
                ],
                "all_agree": True,
            },
            "structured_negative_controls": [
                {
                    "control_id": "E000-KB-20",
                    "mutation": "one extra prev_block reversal before Pearl field serialization",
                    "expected_diagnostic": "E000-DIV-JOB-KEY",
                    "mutated_header_76_hex": reversed_once_header,
                    "mutated_job_key_hex": reversed_once_job_key,
                    "rejected_as_equal": True,
                },
                {
                    "control_id": "E000-KB-21",
                    "mutation": "timestamp and nbits field values swapped before Pearl field serialization",
                    "expected_diagnostic": "E000-DIV-JOB-KEY",
                    "mutated_header_76_hex": swapped_scalars_header,
                    "mutated_job_key_hex": swapped_scalars_job_key,
                    "rejected_as_equal": True,
                },
            ],
            "mining_config_negative_controls": config_controls,
            "seed_derivation": {
                "pinned_source_vector": {
                    "hash_a_hex": "aa" * 32,
                    "hash_b_hex": "bb" * 32,
                    "m": 192,
                    "n": 320,
                    "job_key_hex": "11" * 32,
                    "salted_b_noise_seed_hex": salted_b_seed,
                    "salted_a_noise_seed_hex": salted_a_seed,
                    "matches_pinned_vector": True,
                },
                "negative_control": {
                    "control_id": "E000-KB-23",
                    "mutation": "Legacy derivation substituted for certificate-v3 Salted derivation",
                    "expected_diagnostic": "E000-REJ-SEED-DERIVATION",
                    "legacy_b_noise_seed_hex": legacy_b_seed,
                    "legacy_a_noise_seed_hex": legacy_a_seed,
                    "rejected_as_equal": True,
                },
                "claim_ceiling": "noise-seed parity only; hash_b wire commitment remains unsalted",
            },
            "matrix_root": {
                "pearl_hex": pearl_root,
                "aeye_optimized_hex": transcript["primary_root_hex"],
                "aeye_reference_hex": transcript["reference_root_hex"],
                "all_agree": True,
            },
            "candidate_inspected": False,
            "claim_ceiling": "synthetic byte-path parity; not an E-000 result, Pearl proof verification, or independent review",
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
