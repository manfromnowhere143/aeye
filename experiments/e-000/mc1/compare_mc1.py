#!/usr/bin/env python3
"""Fail-closed comparison for the three MC1 keyed-root lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


class ComparisonError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ComparisonError(message)


def digest_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"regular non-symlink file required: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
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


def index(records: Any, lane: str) -> dict[str, dict[str, Any]]:
    require(isinstance(records, list), f"{lane} records are not a list")
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        require(isinstance(record, dict), f"{lane} record is not an object")
        identity = record.get("slab_id")
        require(isinstance(identity, str) and identity, f"{lane} slab identity is invalid")
        require(identity not in result, f"{lane} duplicate slab identity: {identity}")
        result[identity] = record
    return result


def compare(
    preregistration: dict[str, Any],
    python: dict[str, Any],
    rust: dict[str, Any],
) -> dict[str, Any]:
    require(
        preregistration.get("candidate_inspected") is False, "candidate-labelled preregistration"
    )
    require(python.get("candidate_inspected") is False, "candidate-labelled Python result")
    require(rust.get("candidate_inspected") is False, "candidate-labelled Rust result")
    require(
        python.get("synthetic_key_is_candidate_job_key") is False
        and rust.get("synthetic_key_is_candidate_job_key") is False,
        "synthetic key mislabelled as a candidate key",
    )
    expected_key = preregistration["inputs"]["synthetic_key_derivation"]["result_hex"]
    require(
        python.get("synthetic_key_hex") == rust.get("synthetic_key_hex") == expected_key,
        "synthetic key differs across lanes",
    )
    prereg_digest = python.get("inputs", {}).get("preregistration_sha256")
    require(
        prereg_digest == rust.get("inputs", {}).get("preregistration_sha256"),
        "preregistration binding differs across lanes",
    )
    registry_digest = python.get("inputs", {}).get("reviewed_registry_sha256")
    require(
        registry_digest == rust.get("inputs", {}).get("reviewed_registry_sha256"),
        "registry binding differs across lanes",
    )
    require(
        python.get("inputs", {}).get("extraction_receipt_sha256")
        == rust.get("inputs", {}).get("extraction_receipt_sha256"),
        "extraction-receipt bindings differ across lanes",
    )
    py_records = index(python.get("records"), "Python")
    rs_records = index(rust.get("records"), "Rust")
    require(set(py_records) == set(rs_records), "selected slab identity sets differ")
    require(
        len(py_records) == preregistration.get("required_selected_slabs") == 15,
        "selected count differs",
    )
    agreements: list[dict[str, Any]] = []
    for identity in sorted(py_records):
        left = py_records[identity]
        right = rs_records[identity]
        for field in ("family", "shape_n_k", "bytes", "slab_sha256", "source_tensors"):
            require(left.get(field) == right.get(field), f"{field} differs: {identity}")
        roots = {left.get("python_root"), left.get("oracle_root"), right.get("rust_root")}
        require(None not in roots and len(roots) == 1, f"keyed root differs: {identity}")
        agreements.append(
            {
                "bytes": left["bytes"],
                "family": left["family"],
                "keyed_root": left["python_root"],
                "shape_n_k": left["shape_n_k"],
                "slab_id": identity,
                "slab_sha256": left["slab_sha256"],
            }
        )
    py_wrap = python["controls"]["MC1-I8-U8-BIT-PRESERVATION"]
    rs_wrap = rust["controls"]["MC1-I8-U8-BIT-PRESERVATION"]
    require(py_wrap == rs_wrap and py_wrap.get("status") == "PASS", "int8/uint8 control differs")
    mutation = python["controls"]["MC1-BYTE-MUTATION"]
    source = py_records[mutation["source_slab_id"]]
    require(mutation.get("status") == "REJECT_MUTATION", "byte mutation was not rejected")
    require(
        mutation.get("mutated_python_root") == mutation.get("mutated_oracle_root"),
        "mutated Python/Pearl roots differ",
    )
    require(
        mutation.get("mutated_python_root") != source.get("python_root")
        and mutation.get("mutated_sha256") != source.get("slab_sha256"),
        "byte mutation did not change both identities",
    )
    family_counts = Counter(record["family"] for record in agreements)
    require(
        dict(sorted(family_counts.items())) == {"gate_up_proj": 6, "o_proj": 3, "qkv_proj": 6},
        "family counts differ",
    )
    return {
        "agreement": {
            "by_family": dict(sorted(family_counts.items())),
            "byte_identities_equal": True,
            "keyed_roots_equal_python_rust_pearl": True,
            "selected_shape_classes": len(agreements),
            "total_raw_slab_bytes_processed_per_lane": sum(
                record["bytes"] for record in agreements
            ),
        },
        "candidate_inspected": False,
        "claim_ceiling": preregistration["claim_ceiling"],
        "controls": {
            "MC1-BYTE-MUTATION": mutation,
            "MC1-I8-U8-BIT-PRESERVATION": py_wrap,
            "MC1-REAL-SLAB-KEYED-ROOT-PARITY": "PASS",
        },
        "records": agreements,
        "schema_version": "aeye.private.e000-mc1-three-lane-agreement.v0",
        "status": "supported_pre_candidate_calibration",
        "synthetic_key_hex": expected_key,
        "synthetic_key_is_candidate_job_key": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--python-result", type=Path, required=True)
    parser.add_argument("--rust-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare(
            load_json(args.preregistration),
            load_json(args.python_result),
            load_json(args.rust_result),
        )
        result["inputs"] = {
            "preregistration_sha256": f"sha256:{digest_file(args.preregistration)}",
            "python_result_sha256": f"sha256:{digest_file(args.python_result)}",
            "rust_result_sha256": f"sha256:{digest_file(args.rust_result)}",
        }
        atomic_create(args.output, result)
        print(json.dumps({"ok": True, "output_sha256": digest_file(args.output)}, sort_keys=True))
        return 0
    except (ComparisonError, OSError, KeyError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
