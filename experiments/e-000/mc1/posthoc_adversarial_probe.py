#!/usr/bin/env python3
"""Post-hoc adversarial probes over the retained MC1 three-lane transcript."""

from __future__ import annotations

import copy
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("mc1_compare_probe", ROOT / "compare_mc1.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load MC1 comparator")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mutate_root(_prereg: dict[str, Any], _python: dict[str, Any], rust: dict[str, Any]) -> None:
    rust["records"][0]["rust_root"] = "00" * 32


def mutate_byte_identity(
    _prereg: dict[str, Any], python: dict[str, Any], _rust: dict[str, Any]
) -> None:
    python["records"][1]["slab_sha256"] = "11" * 32


def remove_shape(_prereg: dict[str, Any], _python: dict[str, Any], rust: dict[str, Any]) -> None:
    rust["records"].pop()


def mark_candidate(_prereg: dict[str, Any], python: dict[str, Any], _rust: dict[str, Any]) -> None:
    python["candidate_inspected"] = True


def mutate_source_binding(
    _prereg: dict[str, Any], _python: dict[str, Any], rust: dict[str, Any]
) -> None:
    rust["records"][2]["source_tensors"] = ["substituted.tensor"]


def mutate_key(_prereg: dict[str, Any], _python: dict[str, Any], rust: dict[str, Any]) -> None:
    rust["synthetic_key_hex"] = "22" * 32


def remove_assumption_boundary(
    _prereg: dict[str, Any], python: dict[str, Any], _rust: dict[str, Any]
) -> None:
    python["synthetic_key_is_candidate_job_key"] = True


def launder_mutation(
    _prereg: dict[str, Any], python: dict[str, Any], _rust: dict[str, Any]
) -> None:
    python["controls"]["MC1-BYTE-MUTATION"]["status"] = "PASS"


def alter_wrap(_prereg: dict[str, Any], _python: dict[str, Any], rust: dict[str, Any]) -> None:
    rust["controls"]["MC1-I8-U8-BIT-PRESERVATION"]["unsigned_bytes_hex"] = "800100017f"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, default=ROOT / "mc1-preregistration.json")
    parser.add_argument("--python-result", type=Path, default=ROOT / "python-oracle-result.json")
    parser.add_argument("--rust-result", type=Path, default=ROOT / "rust-result.json")
    parser.add_argument("--output", type=Path, default=ROOT / "posthoc-adversarial-probe.json")
    args = parser.parse_args()
    prereg = load(args.preregistration)
    python = load(args.python_result)
    rust = load(args.rust_result)
    baseline = MODULE.compare(prereg, python, rust)
    cases = [
        ("ROOT_MUTATION", mutate_root, "keyed root differs"),
        ("BYTE_IDENTITY_MUTATION", mutate_byte_identity, "slab_sha256 differs"),
        ("MISSING_SHAPE_CLASS", remove_shape, "identity sets differ"),
        ("CANDIDATE_LABEL", mark_candidate, "candidate-labelled"),
        ("SOURCE_BINDING_MUTATION", mutate_source_binding, "source_tensors differs"),
        ("SYNTHETIC_KEY_MUTATION", mutate_key, "synthetic key differs"),
        ("CANDIDATE_KEY_LAUNDERING", remove_assumption_boundary, "mislabelled"),
        ("MUTATION_RESULT_LAUNDERING", launder_mutation, "not rejected"),
        ("I8_U8_CONTROL_MUTATION", alter_wrap, "int8/uint8 control differs"),
    ]
    results = []
    for case_id, mutator, expected in cases:
        left = copy.deepcopy(prereg)
        middle = copy.deepcopy(python)
        right = copy.deepcopy(rust)
        mutator(left, middle, right)
        try:
            MODULE.compare(left, middle, right)
        except MODULE.ComparisonError as exc:
            message = str(exc)
            if expected not in message:
                raise AssertionError(f"{case_id}: expected {expected!r}, got {message!r}") from exc
            results.append({"case_id": case_id, "diagnostic": message, "rejected": True})
        else:
            raise AssertionError(f"{case_id}: mutated transcript accepted")
    result = {
        "baseline_accepted": baseline["status"] == "supported_pre_candidate_calibration",
        "candidate_inspected": False,
        "cases": results,
        "inputs": {
            "comparator_sha256": sha256(ROOT / "compare_mc1.py"),
            "preregistration_sha256": sha256(args.preregistration),
            "python_result_sha256": sha256(args.python_result),
            "rust_result_sha256": sha256(args.rust_result),
        },
        "mutations_rejected": len(results),
        "schema_version": "aeye.private.e000-mc1-posthoc-adversarial-probe.v0",
        "status": "exploratory_posthoc",
        "total_mutations": len(cases),
    }
    output = args.output
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "mutations_rejected": len(results), "output_sha256": sha256(output)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
