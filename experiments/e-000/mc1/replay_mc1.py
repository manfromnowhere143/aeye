#!/usr/bin/env python3
"""One-command replay driver for the pre-candidate MC1 calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


class ReplayError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_create(path: Path, value: dict[str, Any]) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
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


def execute(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, capture_output=True, text=True, timeout=600)
    require(
        completed.returncode == 0,
        f"command failed: {command[0]}: {completed.stderr or completed.stdout}",
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    require(lines, f"command returned no completion record: {command[0]}")
    completion = json.loads(lines[-1])
    require(
        isinstance(completion, dict) and completion.get("ok") is True,
        f"invalid completion: {command[0]}",
    )
    return completion


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--bundle", dest="bundles", type=Path, action="append", required=True)
    parser.add_argument("--recapture", dest="recaptures", type=Path, action="append", required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--rust-lane", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    require(len(arguments.bundles) == 2, "exactly two bundles required")
    require(len(arguments.recaptures) == 2, "exactly two recapture receipts required")
    return arguments


def main() -> int:
    try:
        args = parse_args()
        output = args.output_dir.resolve()
        require(not output.exists(), f"refusing to reuse output directory: {output}")
        output.mkdir(parents=True)
        work = output / "ephemeral-weight-bearing-work"
        work.mkdir()
        rust_result = output / "rust-result.json"
        python_result = output / "python-oracle-result.json"
        agreement = output / "mc1-agreement.json"
        rust_completion = execute(
            [
                str(args.rust_lane.resolve()),
                str(args.preregistration.resolve()),
                str(args.registry.resolve()),
                *(str(path.resolve()) for path in args.bundles),
                str(rust_result),
            ]
        )
        python_command = [
            sys.executable,
            str(ROOT / "python_lane.py"),
            "--preregistration",
            str(args.preregistration.resolve()),
            "--registry",
            str(args.registry.resolve()),
        ]
        for bundle in args.bundles:
            python_command.extend(("--bundle", str(bundle.resolve())))
        for recapture in args.recaptures:
            python_command.extend(("--recapture", str(recapture.resolve())))
        python_command.extend(
            (
                "--oracle",
                str(args.oracle.resolve()),
                "--work-dir",
                str(work),
                "--output",
                str(python_result),
            )
        )
        python_completion = execute(python_command)
        comparison_completion = execute(
            [
                sys.executable,
                str(ROOT / "compare_mc1.py"),
                "--preregistration",
                str(args.preregistration.resolve()),
                "--python-result",
                str(python_result),
                "--rust-result",
                str(rust_result),
                "--output",
                str(agreement),
            ]
        )
        require(not any(work.iterdir()), "weight-bearing temporary file survived replay")
        receipt = {
            "candidate_inspected": False,
            "commands_succeeded": 3,
            "outputs": {
                "agreement_sha256": digest_file(agreement),
                "python_result_sha256": digest_file(python_result),
                "rust_result_sha256": digest_file(rust_result),
            },
            "schema_version": "aeye.private.e000-mc1-replay-receipt.v0",
            "status": "replayed",
            "subprocess_completions": {
                "comparison": comparison_completion,
                "python": python_completion,
                "rust": rust_completion,
            },
            "weight_bearing_temporary_files_retained": False,
        }
        atomic_create(output / "replay-receipt.json", receipt)
        print(
            json.dumps(
                {
                    "agreement_sha256": receipt["outputs"]["agreement_sha256"],
                    "ok": True,
                    "replay_receipt_sha256": digest_file(output / "replay-receipt.json"),
                },
                sort_keys=True,
            )
        )
        return 0
    except (ReplayError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
