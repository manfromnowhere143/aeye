#!/usr/bin/env python3
"""Generate the frozen E-009-R1 provider transcript and receipt.

This program is the provider/issuer implementation. The independent verifier does not
import it. The experiment is a finite-field transformer-shaped causal block, not a
language model, production proof system, Pearl verifier, or hardware benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
DEFAULT_INPUT = EXPERIMENT_DIR / "input.json"
DEFAULT_OUTPUT = EXPERIMENT_DIR / "artifacts"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def canonical_digest(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_bytes(value)).hexdigest()}"


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def digest_bytes(value: str) -> bytes:
    prefix, encoded = value.split(":", 1)
    if prefix != "sha256" or len(encoded) != 64:
        raise ValueError(f"invalid digest {value!r}")
    return bytes.fromhex(encoded)


def framed_digest(domain: str, parts: Iterable[bytes]) -> str:
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(b"\x00")
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return f"sha256:{digest.hexdigest()}"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def encode_scalar(value: int, field: int) -> int:
    return value % field


def encode_vector(values: Sequence[int], field: int) -> list[int]:
    return [encode_scalar(value, field) for value in values]


def encode_matrix(values: Sequence[Sequence[int]], field: int) -> list[list[int]]:
    return [encode_vector(row, field) for row in values]


def signed_decode(value: int, field: int) -> int:
    residue = value % field
    return residue if residue <= (field - 1) // 2 else residue - field


def dot(left: Sequence[int], right: Sequence[int], field: int) -> int:
    if len(left) != len(right):
        raise ValueError("dot-product dimensions differ")
    return sum((a % field) * (b % field) for a, b in zip(left, right)) % field


def matrix_vector(matrix: Sequence[Sequence[int]], vector: Sequence[int], field: int) -> list[int]:
    if not matrix or not matrix[0] or any(len(row) != len(vector) for row in matrix):
        raise ValueError("matrix/vector dimensions differ")
    return [dot(row, vector, field) for row in matrix]


def vector_add(left: Sequence[int], right: Sequence[int], field: int) -> list[int]:
    if len(left) != len(right):
        raise ValueError("vector dimensions differ")
    return [(a + b) % field for a, b in zip(left, right)]


def centered_argmax(values: Sequence[int], field: int) -> int:
    if not values:
        raise ValueError("cannot select from an empty vector")
    return max(range(len(values)), key=lambda index: (signed_decode(values[index], field), -index))


def operand_root(event_id: str, role: str, values: object) -> str:
    if role not in {"A", "B"}:
        raise ValueError("operand role must be A or B")
    shape: list[int]
    if isinstance(values, list) and values and isinstance(values[0], list):
        matrix = values
        shape = [len(matrix), len(matrix[0])]
    elif isinstance(values, list):
        shape = [len(values)]
    else:
        raise ValueError("operand must be a vector or matrix")
    return canonical_digest(
        {
            "domain": "aeye/e009/clean-operand/v0",
            "event_id": event_id,
            "role": role,
            "shape": shape,
            "values": values,
        }
    )


def reed_solomon_generator(message_length: int, block_length: int, field: int) -> list[list[int]]:
    if not 1 <= message_length <= block_length < field:
        raise ValueError("invalid Reed-Solomon dimensions")
    return [
        [pow(point, degree, field) for point in range(1, block_length + 1)]
        for degree in range(message_length)
    ]


def preprocess(
    matrix: Sequence[Sequence[int]], generator: Sequence[Sequence[int]], field: int
) -> list[list[int]]:
    if not matrix or not matrix[0] or len(generator) != len(matrix):
        raise ValueError("preprocessing dimensions differ")
    columns = len(matrix[0])
    block_length = len(generator[0])
    if any(len(row) != columns for row in matrix) or any(
        len(row) != block_length for row in generator
    ):
        raise ValueError("ragged preprocessing input")
    return [
        [
            sum(generator[row][position] * matrix[row][column] for row in range(len(matrix)))
            % field
            for column in range(columns)
        ]
        for position in range(block_length)
    ]


def encode_message(message: Sequence[int], generator: Sequence[Sequence[int]], field: int) -> list[int]:
    if len(message) != len(generator):
        raise ValueError("message/generator dimensions differ")
    return [
        sum(generator[row][position] * message[row] for row in range(len(message))) % field
        for position in range(len(generator[0]))
    ]


class HashStream:
    def __init__(self, domain: str, subject_root: str, event_id: str, repetition: int) -> None:
        event = event_id.encode("utf-8")
        self.seed = (
            domain.encode("ascii")
            + b"\x00"
            + digest_bytes(subject_root)
            + len(event).to_bytes(4, "big")
            + event
            + repetition.to_bytes(8, "big")
        )
        self.counter = 0

    def uniform_below(self, limit: int) -> int:
        if limit <= 0:
            raise ValueError("limit must be positive")
        modulus = 1 << 256
        cutoff = modulus - modulus % limit
        while True:
            block = hashlib.sha256(self.seed + self.counter.to_bytes(8, "big")).digest()
            self.counter += 1
            candidate = int.from_bytes(block, "big")
            if candidate < cutoff:
                return candidate % limit


def sparse_challenge(
    domain: str,
    subject_root: str,
    event_id: str,
    repetition: int,
    block_length: int,
    sparsity: int,
    field: int,
) -> list[dict[str, int]]:
    if not 1 <= sparsity <= block_length:
        raise ValueError("invalid sparsity")
    stream = HashStream(domain, subject_root, event_id, repetition)
    positions: set[int] = set()
    while len(positions) < sparsity:
        positions.add(stream.uniform_below(block_length))
    return [
        {"position": position, "coefficient": 1 + stream.uniform_below(field - 1)}
        for position in sorted(positions)
    ]


def coded_check(
    prepared: Sequence[Sequence[int]],
    generator: Sequence[Sequence[int]],
    vector: Sequence[int],
    output: Sequence[int],
    challenge: Sequence[dict[str, int]],
    field: int,
) -> tuple[int, int, bool]:
    projected = [0] * len(vector)
    encoded_output = encode_message(output, generator, field)
    right = 0
    for item in challenge:
        position = item["position"]
        coefficient = item["coefficient"]
        for column in range(len(vector)):
            projected[column] = (
                projected[column] + coefficient * prepared[position][column]
            ) % field
        right = (right + coefficient * encoded_output[position]) % field
    left = dot(projected, vector, field)
    return left, right, left == right


def roots_from_input(data: dict[str, Any]) -> dict[str, str]:
    request_root = canonical_digest(data["request"])
    model_root = canonical_digest(data["model"])
    execution_root = canonical_digest(
        {
            "arithmetic_profile": data["arithmetic_profile"],
            "event_universe": data["event_universe"],
            "audit_profile": data["audit_profile"],
        }
    )
    demand_root = canonical_digest(data["demand"])
    intent_id = framed_digest(
        data["commitment_profile"]["intent_domain"],
        (
            digest_bytes(request_root),
            digest_bytes(model_root),
            digest_bytes(execution_root),
            bytes.fromhex(data["request"]["client_nonce"]),
            data["request"]["freshness_domain"].encode("utf-8"),
        ),
    )
    job_id = framed_digest(
        data["commitment_profile"]["job_domain"],
        (digest_bytes(intent_id), digest_bytes(demand_root)),
    )
    return {
        "request_root": request_root,
        "model_root": model_root,
        "execution_root": execution_root,
        "demand_root": demand_root,
        "intent_id": intent_id,
        "job_id": job_id,
    }


def compute_values(data: dict[str, Any]) -> dict[str, Any]:
    field = data["arithmetic_profile"]["field_prime"]
    matrices = {
        name: encode_matrix(matrix, field) for name, matrix in data["model"]["matrices"].items()
    }
    x = encode_vector(data["request"]["input_vector"], field)
    q = matrix_vector(matrices["Wq"], x, field)
    k = matrix_vector(matrices["Wk"], x, field)
    v = matrix_vector(matrices["Wv"], x, field)
    cache_keys = [
        encode_vector(row, field) for row in data["model"]["initial_cache"]["keys"]
    ] + [k]
    cache_values = [
        encode_vector(row, field) for row in data["model"]["initial_cache"]["values"]
    ] + [v]
    scores = [dot(q, key, field) for key in cache_keys]
    selected_index = centered_argmax(scores, field)
    selected_value = cache_values[selected_index]
    residual = vector_add(selected_value, x, field)
    mlp = matrix_vector(matrices["W1"], residual, field)
    relu = [encode_scalar(max(0, signed_decode(value, field)), field) for value in mlp]
    logits = matrix_vector(matrices["W2"], relu, field)
    token_id = centered_argmax(logits, field)
    return {
        "x": x,
        "q": q,
        "k": k,
        "v": v,
        "cache_keys": cache_keys,
        "cache_values": cache_values,
        "scores": scores,
        "selected_index": selected_index,
        "selected_value": selected_value,
        "residual": residual,
        "mlp": mlp,
        "relu": relu,
        "logits": logits,
        "token_id": token_id,
        "token": data["model"]["vocabulary"][token_id],
        "matrices": matrices,
    }


def linear_event(
    sequence: int,
    event_id: str,
    job_id: str,
    matrix_name: str,
    matrix: list[list[int]],
    vector: list[int],
    output: list[int],
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "event_id": event_id,
        "job_id": job_id,
        "verification": "coded_linear",
        "inputs": {
            "matrix_name": matrix_name,
            "x": vector,
            "operand_root_a": operand_root(event_id, "A", vector),
            "operand_root_b": operand_root(event_id, "B", matrix),
        },
        "outputs": {"y": output},
    }


def build_trace(data: dict[str, Any], roots: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    values = compute_values(data)
    job_id = roots["job_id"]
    events: list[dict[str, Any]] = [
        {
            "sequence": 0,
            "event_id": "request_input",
            "job_id": job_id,
            "verification": "exact",
            "inputs": {"request_root": roots["request_root"]},
            "outputs": {"x": values["x"]},
        },
        linear_event(1, "q_linear", job_id, "Wq", values["matrices"]["Wq"], values["x"], values["q"]),
        linear_event(2, "k_linear", job_id, "Wk", values["matrices"]["Wk"], values["x"], values["k"]),
        linear_event(3, "v_linear", job_id, "Wv", values["matrices"]["Wv"], values["x"], values["v"]),
        {
            "sequence": 4,
            "event_id": "cache_append",
            "job_id": job_id,
            "verification": "exact",
            "inputs": {
                "initial_keys": values["cache_keys"][:-1],
                "initial_values": values["cache_values"][:-1],
                "k": values["k"],
                "v": values["v"],
            },
            "outputs": {"keys": values["cache_keys"], "values": values["cache_values"]},
        },
        {
            "sequence": 5,
            "event_id": "attention_scores",
            "job_id": job_id,
            "verification": "exact",
            "inputs": {"q": values["q"], "keys": values["cache_keys"]},
            "outputs": {"scores": values["scores"]},
        },
        {
            "sequence": 6,
            "event_id": "hard_attention_select",
            "job_id": job_id,
            "verification": "exact",
            "inputs": {"scores": values["scores"], "values": values["cache_values"]},
            "outputs": {"selected_index": values["selected_index"], "selected_value": values["selected_value"]},
        },
        {
            "sequence": 7,
            "event_id": "residual",
            "job_id": job_id,
            "verification": "exact",
            "inputs": {"selected_value": values["selected_value"], "x": values["x"]},
            "outputs": {"residual": values["residual"]},
        },
        linear_event(8, "mlp_linear", job_id, "W1", values["matrices"]["W1"], values["residual"], values["mlp"]),
        {
            "sequence": 9,
            "event_id": "relu",
            "job_id": job_id,
            "verification": "exact",
            "inputs": {"mlp": values["mlp"]},
            "outputs": {"relu": values["relu"]},
        },
        linear_event(10, "logits_linear", job_id, "W2", values["matrices"]["W2"], values["relu"], values["logits"]),
        {
            "sequence": 11,
            "event_id": "argmax",
            "job_id": job_id,
            "verification": "exact",
            "inputs": {"logits": values["logits"]},
            "outputs": {"token_id": values["token_id"]},
        },
        {
            "sequence": 12,
            "event_id": "output_emit",
            "job_id": job_id,
            "verification": "exact",
            "inputs": {"token_id": values["token_id"]},
            "outputs": {"token_id": values["token_id"], "token": values["token"]},
        },
    ]
    trace = {
        "schema_version": "aeye.e009-trace.v0",
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "job_id": job_id,
        "event_count": len(events),
        "events": events,
    }
    output = {
        "schema_version": "aeye.e009-output.v0",
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "job_id": job_id,
        "source_event_id": "argmax",
        "token_id": values["token_id"],
        "token": values["token"],
    }
    return trace, output


def complete_subject(
    data: dict[str, Any], roots: dict[str, str], trace: dict[str, Any], output: dict[str, Any]
) -> dict[str, str]:
    trace_root = canonical_digest(trace)
    output_root = canonical_digest(output)
    subject_root = framed_digest(
        data["commitment_profile"]["subject_domain"],
        (digest_bytes(roots["job_id"]), digest_bytes(trace_root), digest_bytes(output_root)),
    )
    return {
        "intent_id": roots["intent_id"],
        "job_id": roots["job_id"],
        "request_root": roots["request_root"],
        "model_root": roots["model_root"],
        "execution_root": roots["execution_root"],
        "demand_root": roots["demand_root"],
        "trace_root": trace_root,
        "output_root": output_root,
        "subject_root": subject_root,
        "freshness_domain": data["request"]["freshness_domain"],
        "client_nonce": data["request"]["client_nonce"],
    }


def build_preprocessing(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    field = data["arithmetic_profile"]["field_prime"]
    linear_definitions = [
        item for item in data["event_universe"] if item["verification"] == "coded_linear"
    ]
    result: dict[str, dict[str, Any]] = {}
    for definition in linear_definitions:
        matrix_name = definition["matrix"]
        matrix = encode_matrix(data["model"]["matrices"][matrix_name], field)
        message_length = len(matrix)
        block_length = 2 * message_length
        generator = reed_solomon_generator(message_length, block_length, field)
        prepared = preprocess(matrix, generator, field)
        result[definition["event_id"]] = {
            "matrix_name": matrix_name,
            "message_length": message_length,
            "block_length": block_length,
            "minimum_distance": block_length - message_length + 1,
            "generator": generator,
            "generator_digest": canonical_digest(generator),
            "preprocessing": prepared,
            "preprocessing_digest": canonical_digest(prepared),
            "matrix_digest": canonical_digest(matrix),
        }
    return result


def build_challenges(
    data: dict[str, Any], subject_root: str, preprocessing: dict[str, dict[str, Any]]
) -> dict[str, list[list[dict[str, int]]]]:
    profile = data["audit_profile"]["challenge"]
    return {
        event_id: [
            sparse_challenge(
                profile["domain"],
                subject_root,
                event_id,
                repetition,
                prepared["block_length"],
                profile["sparsity"],
                data["arithmetic_profile"]["field_prime"],
            )
            for repetition in range(profile["repetitions"])
        ]
        for event_id, prepared in preprocessing.items()
    }


def build_audit(
    data: dict[str, Any],
    subject: dict[str, str],
    trace: dict[str, Any],
    preprocessing: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    field = data["arithmetic_profile"]["field_prime"]
    profile = data["audit_profile"]["challenge"]
    events = {event["event_id"]: event for event in trace["events"]}
    challenges = build_challenges(data, subject["subject_root"], preprocessing)
    relations: list[dict[str, Any]] = []
    union_bound = Fraction(0, 1)
    for definition in data["event_universe"]:
        if definition["verification"] != "coded_linear":
            continue
        event_id = definition["event_id"]
        event = events[event_id]
        prepared = preprocessing[event_id]
        checks: list[dict[str, Any]] = []
        for repetition, challenge in enumerate(challenges[event_id]):
            left, right, accepted = coded_check(
                prepared["preprocessing"],
                prepared["generator"],
                event["inputs"]["x"],
                event["outputs"]["y"],
                challenge,
                field,
            )
            checks.append(
                {
                    "repetition": repetition,
                    "challenge": challenge,
                    "left": left,
                    "right": right,
                    "accepted": accepted,
                }
            )
        delta = Fraction(prepared["minimum_distance"], prepared["block_length"])
        one_round = (1 - delta) ** profile["sparsity"] + Fraction(1, field - 1)
        bound = one_round ** profile["repetitions"]
        union_bound += bound
        relations.append(
            {
                "event_id": event_id,
                "matrix_name": prepared["matrix_name"],
                "operand_root_a": event["inputs"]["operand_root_a"],
                "operand_root_b": event["inputs"]["operand_root_b"],
                "matrix_digest": prepared["matrix_digest"],
                "message_length": prepared["message_length"],
                "block_length": prepared["block_length"],
                "minimum_distance": prepared["minimum_distance"],
                "relative_distance": {
                    "numerator": delta.numerator,
                    "denominator": delta.denominator,
                },
                "generator": prepared["generator"],
                "generator_digest": prepared["generator_digest"],
                "preprocessing": prepared["preprocessing"],
                "preprocessing_digest": prepared["preprocessing_digest"],
                "input": event["inputs"]["x"],
                "output": event["outputs"]["y"],
                "checks": checks,
                "accepted": all(check["accepted"] for check in checks),
                "conditional_soundness_bound": {
                    "numerator": bound.numerator,
                    "denominator": bound.denominator,
                },
            }
        )
    return {
        "schema_version": "aeye.e009-audit.v0",
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "subject_root": subject["subject_root"],
        "challenge_sequence": 4,
        "challenge_source": profile["source"],
        "challenge_domain": profile["domain"],
        "field_prime": field,
        "sparsity": profile["sparsity"],
        "repetitions": profile["repetitions"],
        "relations": relations,
        "all_relations_accept": all(relation["accepted"] for relation in relations),
        "conditional_union_bound": {
            "numerator": union_bound.numerator,
            "denominator": union_bound.denominator,
        },
        "assumptions": [
            "fixed Reed-Solomon/Vandermonde generator is MDS over the declared field",
            "SHA-256 Fiat-Shamir transform is modeled as a random oracle",
            "the final subject is binding and grinding is bounded",
            "preprocessing Q is authenticated against the frozen model matrix",
        ],
    }


def build_synthetic_work(
    data: dict[str, Any], subject: dict[str, str], trace: dict[str, Any]
) -> dict[str, Any]:
    q_event = next(event for event in trace["events"] if event["event_id"] == "q_linear")
    context = {
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "kind": "synthetic-clean-operand-context",
        "pearl_version": None,
        "certificate": None,
    }
    return {
        "schema_version": "aeye.e009-synthetic-pearl-work.v0",
        "status": "synthetic_only",
        "statement_id": "aeye:synthetic-pearl-clean-operands:v0",
        "job_id": subject["job_id"],
        "work_context": context,
        "work_context_root": canonical_digest(context),
        "operand_event_id": "q_linear",
        "operand_root_a": q_event["inputs"]["operand_root_a"],
        "operand_root_b": q_event["inputs"]["operand_root_b"],
        "native_pearl_relation_present": False,
        "native_pearl_certificate_present": False,
        "diagnostic": "Only clean operand roots are represented. No Pearl relation or certificate was generated or verified.",
    }


def assumption(identifier: str, version: str, kind: str, status: str) -> dict[str, str]:
    return {
        "assumption_id": identifier,
        "version": version,
        "kind": kind,
        "status": status,
    }


def native_inputs(
    *,
    intent: str | None = None,
    job: str | None = None,
    subject: str | None = None,
    work_context: str | None = None,
    operand_a: str | None = None,
    operand_b: str | None = None,
) -> dict[str, str | None]:
    return {
        "aeye_intent_id": intent,
        "aeye_job_id": job,
        "aeye_subject_root": subject,
        "work_context_root": work_context,
        "operand_root_a": operand_a,
        "operand_root_b": operand_b,
    }


def unknown_coverage(scope: str) -> dict[str, Any]:
    return {
        "known": False,
        "scope": scope,
        "unit": "unknown",
        "numerator": None,
        "denominator": None,
    }


def event_coverage(scope: str, count: int) -> dict[str, Any]:
    return {
        "known": True,
        "scope": scope,
        "unit": "event",
        "numerator": count,
        "denominator": count,
    }


def build_receipt(
    data: dict[str, Any],
    subject: dict[str, str],
    work: dict[str, Any],
    work_digest: str,
    audit_digest: str,
    trace_digest: str,
) -> dict[str, Any]:
    event_count = len(data["event_universe"])
    work_assumptions = [
        assumption("synthetic.pearl.no-certificate", "E-009-R1", "availability", "unsupported"),
        assumption("sha256.collision-resistance", "FIPS-180-4", "standard", "reviewed"),
    ]
    execution_assumptions = [
        assumption("e009.coded-mvm-mds-soundness", "v0", "computational", "declared"),
        assumption("e009.fiat-shamir-random-oracle-and-bounded-grinding", "v0", "computational", "declared"),
        assumption("e009.verifier-code-correctness", "independent-code-path-v0", "trust", "declared"),
        assumption("sha256.collision-resistance", "FIPS-180-4", "standard", "reviewed"),
    ]
    semantics_assumptions = [
        assumption("e009.finite-field-profile-fidelity", "aeye:finite-field-hard-attention:v0", "trust", "declared"),
        assumption("e009.verifier-code-correctness", "independent-code-path-v0", "trust", "declared"),
        assumption("sha256.collision-resistance", "FIPS-180-4", "standard", "reviewed"),
    ]
    work_evidence_id = "e009:r1:synthetic-pearl-operands"
    execution_evidence_id = "e009:r1:coded-execution-audit"
    semantics_evidence_id = "e009:r1:declared-semantics-conformance"
    evidence = [
        {
            "evidence_id": work_evidence_id,
            "evidence_type": "pearl_pouw",
            "statement_id": work["statement_id"],
            "producer_id": "e009:provider-generator",
            "receipt_job_id": subject["job_id"],
            "native_public_inputs": native_inputs(
                work_context=work["work_context_root"],
                operand_a=work["operand_root_a"],
                operand_b=work["operand_root_b"],
            ),
            "coordinates": ["WORK"],
            "assurance": "commitment_only",
            "scope": {"kind": "job", "scope_id": data["run_id"], "membership_proof_ref": None},
            "coverage": unknown_coverage("No native Pearl statement or certificate exists in E-009."),
            "artifact_digest": work_digest,
            "assumptions": work_assumptions,
        },
        {
            "evidence_id": execution_evidence_id,
            "evidence_type": "sampled_audit",
            "statement_id": "aeye:e009-complete-causal-block:v0",
            "producer_id": "e009:provider-generator",
            "receipt_job_id": subject["job_id"],
            "native_public_inputs": native_inputs(
                job=subject["job_id"],
                subject=subject["subject_root"],
                operand_a=work["operand_root_a"],
                operand_b=work["operand_root_b"],
            ),
            "coordinates": ["EXECUTION"],
            "assurance": "sampled",
            "scope": {"kind": "job", "scope_id": data["run_id"], "membership_proof_ref": None},
            "coverage": event_coverage("Frozen E-009 event universe: five sampled coded-linear and eight exact relations.", event_count),
            "artifact_digest": audit_digest,
            "assumptions": execution_assumptions,
        },
        {
            "evidence_id": semantics_evidence_id,
            "evidence_type": "arithmetic_conformance",
            "statement_id": data["arithmetic_profile"]["profile_id"],
            "producer_id": "e009:provider-generator",
            "receipt_job_id": subject["job_id"],
            "native_public_inputs": native_inputs(subject=subject["subject_root"]),
            "coordinates": ["SEMANTICS"],
            "assurance": "hybrid",
            "scope": {"kind": "job", "scope_id": data["run_id"], "membership_proof_ref": None},
            "coverage": event_coverage("Exact declared finite-field/hard-attention profile; no hardware mapping.", event_count),
            "artifact_digest": trace_digest,
            "assumptions": semantics_assumptions,
        },
    ]
    return {
        "schema_version": "aeye.receipt.v0",
        "receipt_profile": "aeye.research-json.v0",
        "issued_at": data["artifact_times"]["receipt_issued_at"],
        "issuer": {"principal_id": "e009:provider-generator"},
        "subject": subject,
        "timeline": {
            "intent_fixed_sequence": 0,
            "authorization_fixed_sequence": 1,
            "job_fixed_sequence": 2,
            "subject_fixed_sequence": 3,
            "challenge_sampled_sequence": 4,
            "receipt_sealed_sequence": 5,
        },
        "evidence": evidence,
        "cross_evidence_bindings": [
            {
                "binding_id": "e009:r1:synthetic-pearl-to-q-linear",
                "binding_type": "pearl_work_to_execution",
                "work_evidence_ref": work_evidence_id,
                "execution_evidence_ref": execution_evidence_id,
                "equal_fields": ["operand_root_a", "operand_root_b"],
                "diagnostics": [
                    "Equality is real for the frozen clean q_linear operands; the WORK-side relation is synthetic and does not establish Pearl WORK."
                ],
            }
        ],
        "claimed_results": {
            "WORK": {
                "status": "unknown",
                "assurance": "commitment_only",
                "coverage": unknown_coverage("No native Pearl statement or certificate exists in E-009."),
                "assumptions": [item["assumption_id"] for item in work_assumptions],
                "evidence_refs": [work_evidence_id],
                "diagnostics": ["Synthetic clean-operand roots do not establish Pearl WORK."],
            },
            "EXECUTION": {
                "status": "satisfied",
                "assurance": "sampled",
                "coverage": event_coverage("Frozen E-009 event universe: five sampled coded-linear and eight exact relations.", event_count),
                "assumptions": [item["assumption_id"] for item in execution_assumptions],
                "evidence_refs": [execution_evidence_id],
                "diagnostics": [
                    "Limited to E-009-R1 and conditional on the reported coded-audit bound and Fiat-Shamir assumptions."
                ],
            },
            "SEMANTICS": {
                "status": "satisfied",
                "assurance": "hybrid",
                "coverage": event_coverage("Exact declared finite-field/hard-attention profile; no hardware mapping.", event_count),
                "assumptions": [item["assumption_id"] for item in semantics_assumptions],
                "evidence_refs": [semantics_evidence_id],
                "diagnostics": [
                    "Only the declared prime-field, centered-decode, hard-attention semantics are in scope; this is not GPU or ordinary transformer semantics."
                ],
            },
            "DEMAND": {
                "status": "unsupported",
                "assurance": "none",
                "coverage": unknown_coverage("No qualifying signed independent authorization or economic event is represented."),
                "assumptions": [],
                "evidence_refs": [],
                "diagnostics": ["The operator's experiment instruction is provenance, not DEMAND evidence."],
            },
        },
        "conflicts": [],
    }


def distribution(values: list[int]) -> dict[str, int]:
    ordered = sorted(values)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "minimum_ns": ordered[0],
        "median_ns": int(statistics.median(ordered)),
        "p95_ns": ordered[p95_index],
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


def environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
    }


def provider_measurements(
    data: dict[str, Any],
    roots: dict[str, str],
    trace: dict[str, Any],
    output: dict[str, Any],
    subject: dict[str, str],
    preprocessing_data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    profile = data["measurement_profile"]
    warmup = profile["warmup"]
    repetitions = profile["provider_repetitions"]

    def build_trace_and_subject() -> object:
        candidate_trace, candidate_output = build_trace(data, roots)
        return complete_subject(data, roots, candidate_trace, candidate_output)

    def build_complete_audit() -> object:
        return build_audit(data, subject, trace, preprocessing_data)

    baseline = measure(lambda: compute_values(data), warmup, repetitions)
    offline = measure(lambda: build_preprocessing(data), warmup, repetitions)
    commitment = measure(build_trace_and_subject, warmup, repetitions)
    challenge_and_response = measure(build_complete_audit, warmup, repetitions)
    return {
        "schema_version": "aeye.e009-provider-measurements.v0",
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "environment": environment(),
        "protocol": {
            "clock": profile["clock"],
            "warmup": warmup,
            "repetitions": repetitions,
            "statistics": profile["statistics"],
            "baseline": profile["baseline"],
        },
        "timings": {
            "identical_no_aeye_execution": baseline,
            "offline_coded_preprocessing_all_five_matrices": offline,
            "online_execution_trace_and_subject": commitment,
            "post_subject_challenge_and_all_coded_responses": challenge_and_response,
        },
        "serialized_sizes_bytes": {},
        "diagnostics": [
            "These are local Python toy measurements, not production serving or Pearl overhead.",
            "Offline preprocessing is reported separately and is not hidden from the total cost surface.",
            "The baseline and protected path execute the identical frozen toy causal block.",
        ],
    }


def ensure_empty_output(output_dir: Path, force: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise FileExistsError(
            f"refusing to overwrite non-empty {output_dir}; use a new run or explicit --force"
        )
    output_dir.mkdir(parents=True, exist_ok=True)


def generate(input_path: Path, output_dir: Path, force: bool = False) -> dict[str, Any]:
    ensure_empty_output(output_dir, force)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    roots = roots_from_input(data)
    trace, output = build_trace(data, roots)
    subject = complete_subject(data, roots, trace, output)
    preprocessing_data = build_preprocessing(data)
    audit = build_audit(data, subject, trace, preprocessing_data)
    work = build_synthetic_work(data, subject, trace)

    paths = {
        "trace": output_dir / "trace.json",
        "output": output_dir / "output.json",
        "synthetic_pearl_work": output_dir / "synthetic-pearl-work.json",
        "audit": output_dir / "audit.json",
        "provider_measurements": output_dir / "provider-measurements.json",
        "receipt": output_dir / "receipt.json",
        "run_index": output_dir / "run.json",
    }
    write_json(paths["trace"], trace)
    write_json(paths["output"], output)
    write_json(paths["synthetic_pearl_work"], work)
    write_json(paths["audit"], audit)

    measurements = provider_measurements(
        data, roots, trace, output, subject, preprocessing_data
    )
    write_json(paths["provider_measurements"], measurements)
    receipt = build_receipt(
        data,
        subject,
        work,
        file_digest(paths["synthetic_pearl_work"]),
        file_digest(paths["audit"]),
        file_digest(paths["trace"]),
    )
    write_json(paths["receipt"], receipt)

    baseline_output_bytes = len(canonical_bytes(output))
    protected_names = ("trace", "output", "synthetic_pearl_work", "audit", "receipt")
    measurements["serialized_sizes_bytes"] = {
        "identical_no_aeye_output_canonical_json": baseline_output_bytes,
        **{name: paths[name].stat().st_size for name in protected_names},
        "protected_transfer_bundle": sum(paths[name].stat().st_size for name in protected_names),
        "offline_input_model_and_profiles": input_path.stat().st_size,
    }
    write_json(paths["provider_measurements"], measurements)

    artifacts = {
        name: {
            "path": str(path.relative_to(REPOSITORY_ROOT)),
            "sha256": file_digest(path),
            "bytes": path.stat().st_size,
        }
        for name, path in paths.items()
        if name != "run_index"
    }
    run_index = {
        "schema_version": "aeye.e009-run.v0",
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "input": {
            "path": str(input_path.relative_to(REPOSITORY_ROOT)),
            "sha256": file_digest(input_path),
        },
        "subject": subject,
        "observations": {
            "event_count": len(trace["events"]),
            "coded_linear_event_count": len(audit["relations"]),
            "exact_event_count": len(trace["events"]) - len(audit["relations"]),
            "all_provider_coded_checks_accept": audit["all_relations_accept"],
            "output_token_id": output["token_id"],
            "output_token": output["token"],
            "conditional_union_bound": audit["conditional_union_bound"],
        },
        "artifacts": artifacts,
        "non_claims": data["non_claims"],
    }
    write_json(paths["run_index"], run_index)
    return run_index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true", help="explicitly overwrite an existing run directory")
    arguments = parser.parse_args()
    run = generate(arguments.input.resolve(), arguments.output.resolve(), arguments.force)
    print(json.dumps(run["observations"], indent=2, sort_keys=True))
    return 0 if run["observations"]["all_provider_coded_checks_accept"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
