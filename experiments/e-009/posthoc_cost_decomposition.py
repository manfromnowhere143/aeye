#!/usr/bin/env python3
"""Exploratory post-hoc party-level timing split for the frozen E-009-R1 run.

This does not modify, rerun, or upgrade the preregistered result. It imports the frozen
provider implementation solely to decompose the combined challenge/response measurement
that R1 retained. Values are local Python microbenchmarks, not production estimates.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
ARTIFACT_DIR = EXPERIMENT_DIR / "artifacts"
DEFAULT_OUTPUT = ARTIFACT_DIR / "posthoc-cost-decomposition.json"


def load_provider() -> ModuleType:
    path = EXPERIMENT_DIR / "generate.py"
    specification = importlib.util.spec_from_file_location("e009_frozen_provider", path)
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load frozen E-009 provider")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def distribution(samples: list[int]) -> dict[str, int]:
    ordered = sorted(samples)
    return {
        "minimum_ns": ordered[0],
        "median_ns": int(statistics.median(ordered)),
        "p95_ns": ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)],
        "mean_ns": int(statistics.fmean(ordered)),
    }


def measure(operation: Callable[[], object], warmup: int, repetitions: int) -> dict[str, int]:
    for _ in range(warmup):
        operation()
    samples: list[int] = []
    for _ in range(repetitions):
        started = time.perf_counter_ns()
        operation()
        samples.append(time.perf_counter_ns() - started)
    return distribution(samples)


def canonical_size(value: object) -> int:
    return len(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    )


def generate(output_path: Path) -> dict[str, Any]:
    provider = load_provider()
    data = load_json(EXPERIMENT_DIR / "input.json")
    trace = load_json(ARTIFACT_DIR / "trace.json")
    audit = load_json(ARTIFACT_DIR / "audit.json")
    receipt = load_json(ARTIFACT_DIR / "receipt.json")
    subject = receipt["subject"]
    preprocessing = provider.build_preprocessing(data)
    challenge_map = provider.build_challenges(data, subject["subject_root"], preprocessing)
    events = {event["event_id"]: event for event in trace["events"]}
    prime = data["arithmetic_profile"]["field_prime"]

    def client_challenges() -> object:
        return provider.build_challenges(data, subject["subject_root"], preprocessing)

    def provider_responses() -> list[dict[str, object]]:
        responses: list[dict[str, object]] = []
        for event_id, prepared in preprocessing.items():
            event = events[event_id]
            for repetition, challenge in enumerate(challenge_map[event_id]):
                left, right, accepted = provider.coded_check(
                    prepared["preprocessing"],
                    prepared["generator"],
                    event["inputs"]["x"],
                    event["outputs"]["y"],
                    challenge,
                    prime,
                )
                responses.append(
                    {
                        "event_id": event_id,
                        "repetition": repetition,
                        "left": left,
                        "right": right,
                        "accepted": accepted,
                    }
                )
        return responses

    responses = provider_responses()
    audit_text = (ARTIFACT_DIR / "audit.json").read_text(encoding="utf-8")
    profile = data["measurement_profile"]
    warmup = profile["warmup"]
    repetitions = profile["provider_repetitions"]
    timings = {
        "client_challenge_derivation": measure(client_challenges, warmup, repetitions),
        "provider_coded_response_construction": measure(provider_responses, warmup, repetitions),
        "audit_json_serialization": measure(
            lambda: json.dumps(audit, sort_keys=True, separators=(",", ":"), allow_nan=False),
            warmup,
            repetitions,
        ),
        "audit_json_parsing": measure(lambda: json.loads(audit_text), warmup, repetitions),
    }
    original_json = list(ARTIFACT_DIR.glob("*.json"))
    if output_path in original_json:
        original_json.remove(output_path)
    provider_bundle_names = (
        "trace.json",
        "output.json",
        "synthetic-pearl-work.json",
        "audit.json",
        "receipt.json",
    )
    result = {
        "schema_version": "aeye.e009-cost-decomposition.v0",
        "status": "exploratory-post-hoc",
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "measured_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
        },
        "protocol": {
            "clock": profile["clock"],
            "warmup": warmup,
            "repetitions": repetitions,
            "statistics": profile["statistics"],
            "relationship_to_r1": "Post-hoc decomposition of the frozen combined challenge/response measurement; no R1 input, transcript, result, or preregistered claim changed.",
        },
        "timings": timings,
        "serialized_sizes_bytes": {
            "challenge_terms_canonical_json": canonical_size(challenge_map),
            "coded_responses_canonical_json": canonical_size(responses),
            "audit_file": (ARTIFACT_DIR / "audit.json").stat().st_size,
            "provider_bundle": sum((ARTIFACT_DIR / name).stat().st_size for name in provider_bundle_names),
            "all_original_r1_json_artifacts": sum(path.stat().st_size for path in original_json),
        },
        "coverage": {
            "client": "Challenge derivation timed separately; no private-input masking, UI, or signing cost exists in R1.",
            "provider": "All 80 coded response equations timed separately; model execution and trace/subject timing remains in provider-measurements.json.",
            "verifier": "Independent relation replay remains in verifier-measurements.json.",
            "preprocessing": "All five Q=G^T M objects remain in provider-measurements.json as a separate offline cost.",
            "network": "Serialized byte counts are retained; transport latency, bandwidth, protocol framing, retransmission, and availability are unmeasured.",
            "storage": "Original retained JSON artifact bytes are counted; filesystem, Git, replication, indexing, and long-term retention overhead are unmeasured.",
            "privacy": "No privacy mechanism is implemented; the public toy model, inputs, intermediates, and output are disclosed.",
        },
        "limitations": [
            "This measurement was designed after observing R1 and is exploratory, not preregistered confirmatory evidence.",
            "It imports the frozen provider implementation to isolate operations and is not an independent code path.",
            "Client challenge derivation is local deterministic hashing; a beacon, signed interactive challenge, network, and anti-grinding mechanism would have additional cost.",
            "Provider response construction excludes model execution, trace construction, preprocessing, serialization, network, and failure recovery, which are reported or marked separately.",
            "Tiny Python timings and byte ratios do not predict production accelerator behavior."
        ],
    }
    write_json(output_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = generate(args.output.resolve())
    print(json.dumps(result["timings"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
