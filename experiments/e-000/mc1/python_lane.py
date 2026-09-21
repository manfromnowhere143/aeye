#!/usr/bin/env python3
"""Pre-candidate MC1 Python reconstruction plus pinned-Pearl oracle lane.

This program reconstructs one real checkpoint-derived slab from every frozen
family/shape class, hashes the exact raw int8 bytes as unsigned byte strings,
and compares Python's keyed BLAKE3 root with Pearl's pinned implementation.
It never reads a chain candidate and never retains a weight-bearing slab.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from blake3 import blake3


CHUNK = 1024
COPY_BLOCK = 8 * 1024 * 1024
SLAB_ID = re.compile(
    r"^layer-(?P<layer>[0-9]{2}):(?P<family>gate_up_proj|o_proj|qkv_proj):"
    r"tp-(?P<degree>[0-9]{2}):rank-(?P<rank>[0-9]{2})$"
)


class MC1Error(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MC1Error(message)


def digest_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"regular non-symlink file required: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(COPY_BLOCK), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"regular JSON file required: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def atomic_create(path: Path, value: dict[str, Any]) -> None:
    require(not path.exists(), f"refusing to overwrite {path}")
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        temporary.unlink()
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def unprefix(value: str) -> str:
    require(value.startswith("sha256:"), f"sha256 prefix absent: {value}")
    digest = value.removeprefix("sha256:")
    require(len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "invalid SHA-256")
    return digest


@dataclass(frozen=True)
class Tensor:
    name: str
    path: Path
    sha256: str
    rows: int
    cols: int
    bytes: int


class HashingSink:
    def __init__(self, handle: BinaryIO, key: bytes):
        self.handle = handle
        self.sha256 = hashlib.sha256()
        self.blake3 = blake3(key=key)
        self.count = 0

    def write(self, payload: bytes) -> None:
        self.handle.write(payload)
        self.sha256.update(payload)
        self.blake3.update(payload)
        self.count += len(payload)

    def padded_root(self) -> str:
        padding = (-self.count) % CHUNK
        if padding:
            self.blake3.update(bytes(padding))
        return self.blake3.hexdigest()


def load_tensor_inventory(bundle_roots: list[Path]) -> tuple[dict[str, Tensor], list[str]]:
    tensors: dict[str, Tensor] = {}
    receipt_digests: list[str] = []
    for root in bundle_roots:
        receipt_path = root / "extraction" / "receipt.json"
        receipt = load_json(receipt_path)
        require(
            receipt.get("candidate_inspected") is False, "candidate-labelled extraction forbidden"
        )
        stream = receipt.get("stream", {})
        require(stream.get("full_digest_verified") is True, "unverified source stream")
        require(
            stream.get("sha256") == stream.get("expected_sha256"), "source stream digest mismatch"
        )
        require(receipt.get("trust", {}).get("tier") == "T0", "extraction must remain labelled T0")
        receipt_digests.append(digest_file(receipt_path))
        for item in receipt.get("same_stream_extractions", []):
            name = item.get("name")
            relative = item.get("path")
            shape = item.get("shape")
            require(
                isinstance(name, str) and name not in tensors,
                f"invalid or duplicate tensor: {name}",
            )
            require(
                isinstance(relative, str)
                and relative == f"{name}.i8"
                and "/" not in relative
                and "\\" not in relative,
                f"unsafe tensor path: {relative}",
            )
            require(item.get("dtype") == "I8", f"non-I8 tensor: {name}")
            require(
                isinstance(shape, list)
                and len(shape) == 2
                and all(isinstance(v, int) and v > 0 for v in shape),
                f"invalid tensor shape: {name}",
            )
            path = root / "extraction" / relative
            require(path.is_file() and not path.is_symlink(), f"unsafe tensor file: {name}")
            size = shape[0] * shape[1]
            require(
                item.get("bytes") == size == path.stat().st_size, f"tensor length mismatch: {name}"
            )
            tensors[name] = Tensor(name, path, item["sha256"], shape[0], shape[1], size)
    return tensors, sorted(receipt_digests)


def selected_slabs(
    registry: dict[str, Any], preregistration: dict[str, Any]
) -> list[dict[str, Any]]:
    require(registry.get("candidate_inspected") is False, "candidate-labelled registry forbidden")
    require(
        registry.get("candidate_keyed_roots_computed") is False,
        "candidate roots present in source registry",
    )
    groups: dict[tuple[str, tuple[int, int]], dict[str, Any]] = {}
    for record in sorted(registry.get("slabs", []), key=lambda value: value.get("slab_id", "")):
        family = record.get("family")
        shape = record.get("shape_n_k")
        require(
            isinstance(family, str)
            and isinstance(shape, list)
            and len(shape) == 2
            and all(isinstance(v, int) for v in shape),
            "malformed registry slab",
        )
        groups.setdefault((family, tuple(shape)), record)
    observed = [{"family": family, "shape_n_k": list(shape)} for family, shape in sorted(groups)]
    expected = sorted(
        preregistration["expected_shape_classes"],
        key=lambda value: (value["family"], value["shape_n_k"]),
    )
    require(observed == expected, "shape-class universe differs from preregistration")
    selected = [groups[key] for key in sorted(groups)]
    require(
        len(selected) == preregistration["required_selected_slabs"] == 15, "selected count differs"
    )
    return selected


def parse_slab(record: dict[str, Any]) -> tuple[int, str, int, int]:
    match = SLAB_ID.fullmatch(record["slab_id"])
    require(match is not None, f"invalid slab identity: {record.get('slab_id')}")
    layer = int(match.group("layer"))
    family = match.group("family")
    degree = int(match.group("degree"))
    rank = int(match.group("rank"))
    require(family == record["family"], "slab family identity mismatch")
    return layer, family, degree, rank


def verify_tensor(tensor: Tensor, cache: set[str]) -> None:
    if tensor.name not in cache:
        require(digest_file(tensor.path) == tensor.sha256, f"tensor digest mismatch: {tensor.name}")
        cache.add(tensor.name)


def copy_region(tensor: Tensor, offset: int, length: int, sink: HashingSink) -> None:
    require(
        0 <= offset <= tensor.bytes and 0 <= length <= tensor.bytes - offset,
        "tensor region out of range",
    )
    with tensor.path.open("rb") as source:
        source.seek(offset)
        remaining = length
        while remaining:
            block = source.read(min(COPY_BLOCK, remaining))
            require(bool(block), "unexpected EOF in tensor region")
            sink.write(block)
            remaining -= len(block)


def reconstruct(record: dict[str, Any], tensors: dict[str, Tensor], sink: HashingSink) -> list[str]:
    layer, family, degree, rank = parse_slab(record)
    base = f"model.layers.{layer}"
    used: list[str] = []
    if family == "gate_up_proj":
        local = 14336 // degree
        for suffix in ("mlp.gate_proj.weight", "mlp.up_proj.weight"):
            name = f"{base}.{suffix}"
            tensor = tensors[name]
            require((tensor.rows, tensor.cols) == (14336, 4096), f"unexpected shape: {name}")
            copy_region(tensor, rank * local * 4096, local * 4096, sink)
            used.append(name)
    elif family == "o_proj":
        name = f"{base}.self_attn.o_proj.weight"
        tensor = tensors[name]
        require((tensor.rows, tensor.cols) == (4096, 4096), f"unexpected shape: {name}")
        local = 4096 // degree
        start = rank * local
        with tensor.path.open("rb") as source:
            for row in range(4096):
                source.seek(row * 4096 + start)
                payload = source.read(local)
                require(len(payload) == local, "unexpected EOF in o_proj column slice")
                sink.write(payload)
        used.append(name)
    else:
        q_rows = 4096 // degree
        if degree >= 8:
            kv_rows = 128
            replicas = degree // 8
        else:
            kv_rows = 1024 // degree
            replicas = 1
        specs = (
            ("q_proj", rank * q_rows, q_rows, 4096),
            ("k_proj", (rank // replicas) * kv_rows, kv_rows, 1024),
            ("v_proj", (rank // replicas) * kv_rows, kv_rows, 1024),
        )
        for projection, start, rows, total_rows in specs:
            name = f"{base}.self_attn.{projection}.weight"
            tensor = tensors[name]
            require((tensor.rows, tensor.cols) == (total_rows, 4096), f"unexpected shape: {name}")
            copy_region(tensor, start * 4096, rows * 4096, sink)
            used.append(name)
    require(sink.count == record["bytes"], f"reconstructed length mismatch: {record['slab_id']}")
    return used


def pearl_root(oracle: Path, slab: Path, key: bytes) -> str:
    completed = subprocess.run(
        [str(oracle), "matrix-root", str(slab), key.hex()],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    require(completed.returncode == 0, f"Pearl oracle failed: {completed.stderr.strip()}")
    root = completed.stdout.strip()
    require(len(root) == 64 and all(c in "0123456789abcdef" for c in root), "invalid oracle root")
    return root


def validate_recaptures(paths: list[Path], preregistration: dict[str, Any]) -> list[str]:
    digests = sorted(f"sha256:{digest_file(path)}" for path in paths)
    expected = sorted(preregistration["inputs"]["hardened_t0_retrieval_receipts"])
    require(digests == expected, "hardened T0 receipt digest set differs")
    for path in paths:
        receipt = load_json(path)
        require(receipt.get("candidate_inspected") is False, "candidate-labelled recapture")
        require(
            receipt.get("contains_model_weight_bytes") is False, "recapture retained weight bytes"
        )
        require(receipt.get("status") == "observed_t0_transport", "recapture status differs")
        require(receipt.get("trust", {}).get("observed_tier") == "T0", "recapture tier differs")
        transport = receipt.get("transport", {})
        require(transport.get("complete_get") is True, "recapture is not a complete GET")
        require(
            transport.get("bytes_received") == receipt.get("source", {}).get("expected_bytes")
            and transport.get("sha256") == receipt.get("source", {}).get("expected_sha256"),
            "recapture length or digest differs",
        )
    return digests


def run(args: argparse.Namespace) -> dict[str, Any]:
    prereg_path = args.preregistration.resolve()
    registry_path = args.registry.resolve()
    preregistration = load_json(prereg_path)
    registry = load_json(registry_path)
    require(
        preregistration.get("status") == "preregistered_pre_candidate",
        "preregistration state differs",
    )
    require(
        preregistration.get("candidate_inspected") is False, "candidate-labelled preregistration"
    )
    require(
        digest_file(registry_path) == unprefix(preregistration["inputs"]["reviewed_rust_registry"]),
        "reviewed Rust registry digest differs",
    )
    manifest_digest = unprefix(preregistration["inputs"]["reviewed_real_byte_packet_manifest"])
    domain = bytes.fromhex(preregistration["inputs"]["synthetic_key_derivation"]["domain_hex"])
    key = hashlib.sha256(domain + bytes.fromhex(manifest_digest)).digest()
    require(
        key.hex() == preregistration["inputs"]["synthetic_key_derivation"]["result_hex"],
        "synthetic key derivation differs",
    )
    recapture_digests = validate_recaptures(args.recaptures, preregistration)
    tensors, extraction_receipt_digests = load_tensor_inventory(args.bundles)
    selected = selected_slabs(registry, preregistration)
    verified: set[str] = set()
    records: list[dict[str, Any]] = []
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    first_materialized: bytes | None = None
    first_record: dict[str, Any] | None = None
    for index, record in enumerate(selected):
        descriptor, temporary_name = tempfile.mkstemp(prefix="mc1-slab-", suffix=".bin", dir=work)
        slab_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                sink = HashingSink(handle, key)
                used = reconstruct(record, tensors, sink)
                for name in used:
                    verify_tensor(tensors[name], verified)
                handle.flush()
                os.fsync(handle.fileno())
                python_root = sink.padded_root()
                slab_sha256 = sink.sha256.hexdigest()
            require(
                slab_sha256 == record["slab_sha256"],
                f"registry digest mismatch: {record['slab_id']}",
            )
            oracle_root = pearl_root(args.oracle.resolve(), slab_path, key)
            require(python_root == oracle_root, f"Python/Pearl root mismatch: {record['slab_id']}")
            if index == 0:
                first_materialized = slab_path.read_bytes()
                first_record = record
            records.append(
                {
                    "bytes": record["bytes"],
                    "family": record["family"],
                    "oracle_root": oracle_root,
                    "python_root": python_root,
                    "shape_n_k": record["shape_n_k"],
                    "slab_id": record["slab_id"],
                    "slab_sha256": slab_sha256,
                    "source_tensors": used,
                }
            )
        finally:
            slab_path.unlink(missing_ok=True)
    require(first_materialized is not None and first_record is not None, "mutation source absent")
    mutated = bytearray(first_materialized)
    mutated[0] ^= 1
    descriptor, mutation_name = tempfile.mkstemp(prefix="mc1-mutated-", suffix=".bin", dir=work)
    mutation_path = Path(mutation_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(mutated)
            handle.flush()
            os.fsync(handle.fileno())
        mutated_sha = hashlib.sha256(mutated).hexdigest()
        mutated_hasher = blake3(key=key)
        mutated_hasher.update(mutated)
        padding = (-len(mutated)) % CHUNK
        if padding:
            mutated_hasher.update(bytes(padding))
        mutated_root = mutated_hasher.hexdigest()
        mutation_oracle_root = pearl_root(args.oracle.resolve(), mutation_path, key)
        require(mutated_root == mutation_oracle_root, "mutation Python/Pearl root mismatch")
        require(mutated_sha != records[0]["slab_sha256"], "mutation left SHA-256 unchanged")
        require(mutated_root != records[0]["python_root"], "mutation left keyed root unchanged")
    finally:
        mutation_path.unlink(missing_ok=True)
    signed = [-128, -1, 0, 1, 127]
    signed_bytes = struct.pack("5b", *signed)
    unsigned = bytes([128, 255, 0, 1, 127])
    require(signed_bytes == unsigned, "Python int8-to-uint8 bit preservation failed")
    return {
        "candidate_inspected": False,
        "claim_ceiling": preregistration["claim_ceiling"],
        "controls": {
            "MC1-BYTE-MUTATION": {
                "mutated_oracle_root": mutation_oracle_root,
                "mutated_python_root": mutated_root,
                "mutated_sha256": mutated_sha,
                "source_slab_id": first_record["slab_id"],
                "status": "REJECT_MUTATION",
            },
            "MC1-I8-U8-BIT-PRESERVATION": {
                "signed_values": signed,
                "status": "PASS",
                "unsigned_bytes_hex": unsigned.hex(),
            },
            "MC1-REAL-SLAB-KEYED-ROOT-PARITY": {
                "selected_shape_classes": len(records),
                "status": "PASS",
            },
        },
        "inputs": {
            "extraction_receipt_sha256": extraction_receipt_digests,
            "hardened_t0_receipt_sha256": recapture_digests,
            "preregistration_sha256": f"sha256:{digest_file(prereg_path)}",
            "reviewed_registry_sha256": f"sha256:{digest_file(registry_path)}",
        },
        "implementation": {
            "blake3_python_version": __import__("blake3").__version__,
            "language": "Python",
            "oracle_executable_sha256": digest_file(args.oracle.resolve()),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "python_executable_sha256": digest_file(Path(sys.executable).resolve()),
            "reconstruction_and_hashing_code_path": "owner-python-mc1-v0",
            "source_sha256": digest_file(Path(__file__).resolve()),
        },
        "records": records,
        "schema_version": "aeye.private.e000-mc1-python-and-oracle-result.v0",
        "status": "supported_pre_candidate_calibration",
        "synthetic_key_hex": key.hex(),
        "synthetic_key_is_candidate_job_key": False,
        "weight_bearing_temporary_files_retained": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--bundle", dest="bundles", type=Path, action="append", required=True)
    parser.add_argument("--recapture", dest="recaptures", type=Path, action="append", required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    require(len(arguments.bundles) == 2, "exactly two extraction bundles required")
    require(len(arguments.recaptures) == 2, "exactly two hardened T0 receipts required")
    return arguments


def main() -> int:
    try:
        args = parse_args()
        result = run(args)
        atomic_create(args.output, result)
        print(
            json.dumps(
                {
                    "candidate_inspected": False,
                    "ok": True,
                    "output_sha256": digest_file(args.output),
                    "selected_shape_classes": len(result["records"]),
                },
                sort_keys=True,
            )
        )
        return 0
    except (MC1Error, OSError, KeyError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
