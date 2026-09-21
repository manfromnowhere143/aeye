#!/usr/bin/env python3
"""Independently replay and falsify the frozen E-009-R1 artifact bundle.

This implementation intentionally does not import generate.py, coded_mvm_demo.py, or
their arithmetic helpers. Its independence is code-path separation only; it is not an
independent person, institution, security audit, or peer review.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import statistics
import sys
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from jsonschema import Draft202012Validator, FormatChecker


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
ARTIFACT_DIR = EXPERIMENT_DIR / "artifacts"
SCHEMA_DIR = REPOSITORY_ROOT / "schemas"
PREREGISTRATION = EXPERIMENT_DIR / "preregistration.json"

EXPECTED_EVENTS = (
    "request_input",
    "q_linear",
    "k_linear",
    "v_linear",
    "cache_append",
    "attention_scores",
    "hard_attention_select",
    "residual",
    "mlp_linear",
    "relu",
    "logits_linear",
    "argmax",
    "output_emit",
)
LINEAR_EVENTS = {
    "q_linear": "Wq",
    "k_linear": "Wk",
    "v_linear": "Wv",
    "mlp_linear": "W1",
    "logits_linear": "W2",
}


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    location: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "location": self.location, "message": self.message}


def add(findings: list[Finding], condition: bool, code: str, location: str, message: str) -> None:
    if not condition:
        findings.append(Finding(code, location, message))


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def canonical_digest(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_bytes(value)).hexdigest()}"


def file_digest(path: Path) -> str:
    accumulator = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            block = source.read(1024 * 1024)
            if not block:
                break
            accumulator.update(block)
    return f"sha256:{accumulator.hexdigest()}"


def digest_bytes(value: str) -> bytes:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError("malformed SHA-256 identifier")
    return bytes.fromhex(value[7:])


def framed_digest(domain: str, parts: Iterable[bytes]) -> str:
    state = hashlib.sha256()
    state.update(domain.encode("ascii"))
    state.update(b"\x00")
    for part in parts:
        state.update(len(part).to_bytes(8, byteorder="big", signed=False))
        state.update(part)
    return f"sha256:{state.hexdigest()}"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def encode_vector(vector: Sequence[int], prime: int) -> list[int]:
    return [entry % prime for entry in vector]


def encode_matrix(matrix: Sequence[Sequence[int]], prime: int) -> list[list[int]]:
    return [encode_vector(row, prime) for row in matrix]


def centered(value: int, prime: int) -> int:
    residue = value % prime
    return residue if residue <= (prime - 1) // 2 else residue - prime


def field_dot(left: Sequence[int], right: Sequence[int], prime: int) -> int:
    if len(left) != len(right):
        raise ValueError("dot dimensions disagree")
    total = 0
    for first, second in zip(left, right):
        total = (total + (first % prime) * (second % prime)) % prime
    return total


def field_add(left: Sequence[int], right: Sequence[int], prime: int) -> list[int]:
    if len(left) != len(right):
        raise ValueError("addition dimensions disagree")
    return [(first + second) % prime for first, second in zip(left, right)]


def stable_argmax(values: Sequence[int], prime: int) -> int:
    if not values:
        raise ValueError("empty argmax")
    best = 0
    for index in range(1, len(values)):
        if centered(values[index], prime) > centered(values[best], prime):
            best = index
    return best


def clean_operand_root(event_id: str, role: str, values: object) -> str:
    if not isinstance(values, list) or not values:
        raise ValueError("empty operand")
    shape = [len(values), len(values[0])] if isinstance(values[0], list) else [len(values)]
    return canonical_digest(
        {
            "domain": "aeye/e009/clean-operand/v0",
            "event_id": event_id,
            "role": role,
            "shape": shape,
            "values": values,
        }
    )


def make_generator(rows: int, columns: int, prime: int) -> list[list[int]]:
    if rows < 1 or columns < rows or columns >= prime:
        raise ValueError("invalid code dimensions")
    table: list[list[int]] = []
    for degree in range(rows):
        table.append([pow(point, degree, prime) for point in range(1, columns + 1)])
    return table


def make_preprocessing(
    matrix: Sequence[Sequence[int]], generator: Sequence[Sequence[int]], prime: int
) -> list[list[int]]:
    row_count = len(matrix)
    if not row_count or len(generator) != row_count:
        raise ValueError("preprocessing row mismatch")
    input_width = len(matrix[0])
    code_width = len(generator[0])
    if any(len(row) != input_width for row in matrix):
        raise ValueError("ragged matrix")
    if any(len(row) != code_width for row in generator):
        raise ValueError("ragged generator")
    answer: list[list[int]] = []
    for code_position in range(code_width):
        prepared_row: list[int] = []
        for input_position in range(input_width):
            value = 0
            for row in range(row_count):
                value += generator[row][code_position] * matrix[row][input_position]
            prepared_row.append(value % prime)
        answer.append(prepared_row)
    return answer


def encode_codeword(message: Sequence[int], generator: Sequence[Sequence[int]], prime: int) -> list[int]:
    if len(message) != len(generator):
        raise ValueError("message dimension mismatch")
    result: list[int] = []
    for position in range(len(generator[0])):
        accumulator = 0
        for row, value in enumerate(message):
            accumulator += generator[row][position] * value
        result.append(accumulator % prime)
    return result


class IndependentHashStream:
    def __init__(self, domain: str, subject_root: str, event_id: str, repetition: int) -> None:
        encoded_event = event_id.encode("utf-8")
        self.material = b"".join(
            (
                domain.encode("ascii"),
                b"\x00",
                digest_bytes(subject_root),
                len(encoded_event).to_bytes(4, "big"),
                encoded_event,
                repetition.to_bytes(8, "big"),
            )
        )
        self.index = 0

    def sample(self, ceiling: int) -> int:
        if ceiling <= 0:
            raise ValueError("non-positive sample ceiling")
        full = 2**256
        acceptable = full - full % ceiling
        while True:
            digest = hashlib.sha256(self.material + self.index.to_bytes(8, "big")).digest()
            self.index += 1
            integer = int.from_bytes(digest, "big")
            if integer < acceptable:
                return integer % ceiling


def derive_challenge(
    domain: str,
    subject_root: str,
    event_id: str,
    repetition: int,
    width: int,
    sparsity: int,
    prime: int,
) -> list[dict[str, int]]:
    stream = IndependentHashStream(domain, subject_root, event_id, repetition)
    selected: set[int] = set()
    while len(selected) < sparsity:
        selected.add(stream.sample(width))
    answer: list[dict[str, int]] = []
    for position in sorted(selected):
        answer.append({"position": position, "coefficient": stream.sample(prime - 1) + 1})
    return answer


def verify_coded_equation(
    prepared: Sequence[Sequence[int]],
    generator: Sequence[Sequence[int]],
    vector: Sequence[int],
    claimed: Sequence[int],
    challenge: Sequence[dict[str, int]],
    prime: int,
) -> tuple[int, int]:
    compressed_row = [0] * len(vector)
    encoded_claim = encode_codeword(claimed, generator, prime)
    compressed_claim = 0
    for coefficient_record in challenge:
        position = coefficient_record["position"]
        coefficient = coefficient_record["coefficient"]
        if position < 0 or position >= len(prepared):
            raise ValueError("challenge position outside preprocessing")
        for column in range(len(vector)):
            compressed_row[column] = (
                compressed_row[column] + coefficient * prepared[position][column]
            ) % prime
        compressed_claim = (
            compressed_claim + coefficient * encoded_claim[position]
        ) % prime
    return field_dot(compressed_row, vector, prime), compressed_claim


def initial_roots(data: dict[str, Any]) -> dict[str, str]:
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
    intent = framed_digest(
        data["commitment_profile"]["intent_domain"],
        (
            digest_bytes(request_root),
            digest_bytes(model_root),
            digest_bytes(execution_root),
            bytes.fromhex(data["request"]["client_nonce"]),
            data["request"]["freshness_domain"].encode("utf-8"),
        ),
    )
    job = framed_digest(
        data["commitment_profile"]["job_domain"],
        (digest_bytes(intent), digest_bytes(demand_root)),
    )
    return {
        "request_root": request_root,
        "model_root": model_root,
        "execution_root": execution_root,
        "demand_root": demand_root,
        "intent_id": intent,
        "job_id": job,
    }


def completed_subject(
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


def schema_findings(instance: object, schema_name: str, location: str) -> list[Finding]:
    schema = load_json(SCHEMA_DIR / schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        Finding(
            "SCHEMA_VIOLATION",
            f"{location}#/{'/'.join(str(part) for part in error.absolute_path)}",
            error.message,
        )
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    ]


def validate_input_contract(data: dict[str, Any], findings: list[Finding]) -> None:
    add(findings, data.get("run_id") == "E-009-R1", "FROZEN_RUN_ID_MISMATCH", "input/run_id", "run id is not the frozen R1 identifier")
    prime = data.get("arithmetic_profile", {}).get("field_prime")
    add(findings, prime == 2**61 - 1, "FIELD_MISMATCH", "input/arithmetic_profile/field_prime", "field differs from the preregistered Mersenne prime")
    definitions = data.get("event_universe", [])
    observed_ids = tuple(item.get("event_id") for item in definitions if isinstance(item, dict))
    add(findings, observed_ids == EXPECTED_EVENTS, "EVENT_UNIVERSE_MISMATCH", "input/event_universe", "event identifiers or order differ from the frozen universe")
    if isinstance(definitions, list):
        sequences = [item.get("sequence") for item in definitions if isinstance(item, dict)]
        add(findings, sequences == list(range(len(EXPECTED_EVENTS))), "EVENT_SEQUENCE_MISMATCH", "input/event_universe", "event sequence is not contiguous")
        mapping = {
            item.get("event_id"): item.get("matrix")
            for item in definitions
            if isinstance(item, dict) and item.get("verification") == "coded_linear"
        }
        add(findings, mapping == LINEAR_EVENTS, "LINEAR_UNIVERSE_MISMATCH", "input/event_universe", "coded-linear event/matrix mapping changed")
    challenge = data.get("audit_profile", {}).get("challenge", {})
    add(findings, challenge.get("sparsity") == 4 and challenge.get("repetitions") == 16, "AUDIT_PARAMETER_MISMATCH", "input/audit_profile/challenge", "challenge parameters differ from t=4, ell=16")
    model = data.get("model", {})
    dimensions = model.get("dimensions", {})
    expected_shapes = {
        "Wq": (dimensions.get("key"), dimensions.get("model")),
        "Wk": (dimensions.get("key"), dimensions.get("model")),
        "Wv": (dimensions.get("value"), dimensions.get("model")),
        "W1": (dimensions.get("hidden"), dimensions.get("model")),
        "W2": (dimensions.get("vocabulary"), dimensions.get("hidden")),
    }
    for name, expected in expected_shapes.items():
        matrix = model.get("matrices", {}).get(name, [])
        observed = (len(matrix), len(matrix[0]) if matrix and isinstance(matrix[0], list) else 0)
        add(findings, observed == expected and all(len(row) == observed[1] for row in matrix), "MODEL_SHAPE_MISMATCH", f"input/model/matrices/{name}", f"matrix shape {observed} differs from {expected}")
    add(findings, len(data.get("request", {}).get("input_vector", [])) == dimensions.get("model"), "REQUEST_SHAPE_MISMATCH", "input/request/input_vector", "request vector has the wrong width")
    cache = model.get("initial_cache", {})
    add(findings, len(cache.get("keys", [])) == len(cache.get("values", [])) == 1, "CACHE_SHAPE_MISMATCH", "input/model/initial_cache", "R1 requires exactly one initial key/value row")
    add(findings, len(cache.get("keys", [[]])[0]) == dimensions.get("key"), "CACHE_SHAPE_MISMATCH", "input/model/initial_cache/keys", "cache key width differs")
    add(findings, len(cache.get("values", [[]])[0]) == dimensions.get("value"), "CACHE_SHAPE_MISMATCH", "input/model/initial_cache/values", "cache value width differs")
    add(findings, dimensions.get("model") == dimensions.get("value"), "RESIDUAL_SHAPE_MISMATCH", "input/model/dimensions", "residual requires value width equal to model width")
    add(findings, len(model.get("vocabulary", [])) == dimensions.get("vocabulary"), "VOCABULARY_SHAPE_MISMATCH", "input/model/vocabulary", "vocabulary length differs")
    add(findings, data.get("demand", {}).get("status") == "unsupported", "DEMAND_UPGRADE", "input/demand/status", "frozen experiment cannot upgrade demand")


def event_map(trace: dict[str, Any], findings: list[Finding]) -> dict[str, dict[str, Any]]:
    events = trace.get("events", [])
    if not isinstance(events, list):
        findings.append(Finding("EVENT_UNIVERSE_MISMATCH", "trace/events", "events is not an array"))
        return {}
    ids = [event.get("event_id") for event in events if isinstance(event, dict)]
    add(findings, tuple(ids) == EXPECTED_EVENTS, "EVENT_UNIVERSE_MISMATCH", "trace/events", "trace omits, duplicates, adds, or reorders an event")
    mapping: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events):
        if not isinstance(event, dict) or not isinstance(event.get("event_id"), str):
            findings.append(Finding("EVENT_MALFORMED", f"trace/events/{index}", "event is malformed"))
            continue
        if event["event_id"] in mapping:
            findings.append(Finding("EVENT_UNIVERSE_MISMATCH", f"trace/events/{index}", "duplicate event id"))
        mapping[event["event_id"]] = event
        add(findings, event.get("sequence") == index, "EVENT_SEQUENCE_MISMATCH", f"trace/events/{index}", "event sequence differs from array position")
    add(findings, trace.get("event_count") == len(events) == len(EXPECTED_EVENTS), "EVENT_COUNT_MISMATCH", "trace/event_count", "event denominator is not the frozen universe")
    return mapping


def exact_event_checks(
    data: dict[str, Any],
    roots: dict[str, str],
    events: dict[str, dict[str, Any]],
    output: dict[str, Any],
    findings: list[Finding],
) -> None:
    if any(event_id not in events for event_id in EXPECTED_EVENTS):
        return
    prime = data["arithmetic_profile"]["field_prime"]
    model = data["model"]
    expected_x = encode_vector(data["request"]["input_vector"], prime)
    request = events["request_input"]
    add(findings, request.get("inputs", {}).get("request_root") == roots["request_root"], "REQUEST_ROOT_MISMATCH", "trace/request_input", "request event does not bind the frozen request")
    add(findings, request.get("outputs", {}).get("x") == expected_x, "REQUEST_ROW_GRAFT", "trace/request_input/outputs/x", "request row differs from the frozen request")

    q = events["q_linear"].get("outputs", {}).get("y")
    k = events["k_linear"].get("outputs", {}).get("y")
    v = events["v_linear"].get("outputs", {}).get("y")
    initial_keys = [encode_vector(row, prime) for row in model["initial_cache"]["keys"]]
    initial_values = [encode_vector(row, prime) for row in model["initial_cache"]["values"]]
    cache = events["cache_append"]
    expected_cache_inputs = {"initial_keys": initial_keys, "initial_values": initial_values, "k": k, "v": v}
    expected_cache_outputs = {"keys": initial_keys + [k], "values": initial_values + [v]}
    add(findings, cache.get("inputs") == expected_cache_inputs, "CACHE_INPUT_MISMATCH", "trace/cache_append/inputs", "cache append inputs break causal continuity")
    add(findings, cache.get("outputs") == expected_cache_outputs, "CACHE_APPEND_MISMATCH", "trace/cache_append/outputs", "cache append output is not exact")

    score_event = events["attention_scores"]
    cache_keys = expected_cache_outputs["keys"]
    expected_scores = [field_dot(q, key, prime) for key in cache_keys]
    add(findings, score_event.get("inputs") == {"q": q, "keys": cache_keys}, "ATTENTION_INPUT_MISMATCH", "trace/attention_scores/inputs", "attention inputs break causal continuity")
    add(findings, score_event.get("outputs", {}).get("scores") == expected_scores, "ATTENTION_SCORE_MISMATCH", "trace/attention_scores/outputs", "attention score relation failed")

    selection = events["hard_attention_select"]
    selected_index = stable_argmax(expected_scores, prime)
    expected_values = expected_cache_outputs["values"]
    add(findings, selection.get("inputs") == {"scores": expected_scores, "values": expected_values}, "ATTENTION_SELECTION_INPUT_MISMATCH", "trace/hard_attention_select/inputs", "selection inputs break causal continuity")
    add(findings, selection.get("outputs") == {"selected_index": selected_index, "selected_value": expected_values[selected_index]}, "ATTENTION_SELECTION_MISMATCH", "trace/hard_attention_select/outputs", "hard-attention selection failed")

    residual_event = events["residual"]
    expected_residual = field_add(expected_values[selected_index], expected_x, prime)
    add(findings, residual_event.get("inputs") == {"selected_value": expected_values[selected_index], "x": expected_x}, "RESIDUAL_INPUT_MISMATCH", "trace/residual/inputs", "residual inputs break causal continuity")
    add(findings, residual_event.get("outputs", {}).get("residual") == expected_residual, "RESIDUAL_MISMATCH", "trace/residual/outputs", "residual relation failed")

    mlp = events["mlp_linear"].get("outputs", {}).get("y")
    relu_event = events["relu"]
    expected_relu = [max(0, centered(value, prime)) % prime for value in mlp]
    add(findings, relu_event.get("inputs") == {"mlp": mlp}, "RELU_INPUT_MISMATCH", "trace/relu/inputs", "ReLU input breaks causal continuity")
    add(findings, relu_event.get("outputs", {}).get("relu") == expected_relu, "RELU_MISMATCH", "trace/relu/outputs", "centered ReLU relation failed")

    logits = events["logits_linear"].get("outputs", {}).get("y")
    argmax_event = events["argmax"]
    expected_token_id = stable_argmax(logits, prime)
    add(findings, argmax_event.get("inputs") == {"logits": logits}, "ARGMAX_INPUT_MISMATCH", "trace/argmax/inputs", "argmax input breaks causal continuity")
    add(findings, argmax_event.get("outputs") == {"token_id": expected_token_id}, "ARGMAX_MISMATCH", "trace/argmax/outputs", "centered-logit argmax failed")

    emit = events["output_emit"]
    expected_token = model["vocabulary"][expected_token_id]
    add(findings, emit.get("inputs") == {"token_id": expected_token_id}, "OUTPUT_INPUT_MISMATCH", "trace/output_emit/inputs", "output event input breaks causal continuity")
    add(findings, emit.get("outputs") == {"token_id": expected_token_id, "token": expected_token}, "OUTPUT_EMIT_MISMATCH", "trace/output_emit/outputs", "output event differs from vocabulary decoding")
    expected_output = {
        "schema_version": "aeye.e009-output.v0",
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "job_id": roots["job_id"],
        "source_event_id": "argmax",
        "token_id": expected_token_id,
        "token": expected_token,
    }
    add(findings, output == expected_output, "OUTPUT_TRACE_MISMATCH", "output", "output artifact is not the exact terminal trace value")


def linear_and_audit_checks(
    data: dict[str, Any],
    subject: dict[str, str],
    events: dict[str, dict[str, Any]],
    audit: dict[str, Any],
    findings: list[Finding],
) -> None:
    if any(event_id not in events for event_id in LINEAR_EVENTS):
        return
    prime = data["arithmetic_profile"]["field_prime"]
    profile = data["audit_profile"]["challenge"]
    expected_x = encode_vector(data["request"]["input_vector"], prime)
    residual = events.get("residual", {}).get("outputs", {}).get("residual")
    relu = events.get("relu", {}).get("outputs", {}).get("relu")
    expected_inputs = {
        "q_linear": expected_x,
        "k_linear": expected_x,
        "v_linear": expected_x,
        "mlp_linear": residual,
        "logits_linear": relu,
    }
    relations_raw = audit.get("relations", [])
    relations = {
        relation.get("event_id"): relation
        for relation in relations_raw
        if isinstance(relation, dict) and isinstance(relation.get("event_id"), str)
    }
    add(findings, set(relations) == set(LINEAR_EVENTS), "AUDIT_RELATION_UNIVERSE_MISMATCH", "audit/relations", "audit does not cover exactly five frozen linear events")
    computed_union = Fraction(0, 1)
    for event_id, matrix_name in LINEAR_EVENTS.items():
        event = events[event_id]
        location = f"trace/{event_id}"
        matrix = encode_matrix(data["model"]["matrices"][matrix_name], prime)
        vector = expected_inputs[event_id]
        claimed = event.get("outputs", {}).get("y")
        add(findings, event.get("verification") == "coded_linear", "LINEAR_VERIFICATION_MODE_MISMATCH", location, "linear event is not marked coded_linear")
        add(findings, event.get("inputs", {}).get("matrix_name") == matrix_name, "LINEAR_MATRIX_MISMATCH", f"{location}/inputs", "linear event names the wrong matrix")
        add(findings, event.get("inputs", {}).get("x") == vector, "REQUEST_ROW_GRAFT" if event_id in {"q_linear", "k_linear", "v_linear"} else "LINEAR_INPUT_EDGE_MISMATCH", f"{location}/inputs/x", "linear input is not the causal predecessor")
        if not isinstance(vector, list) or not isinstance(claimed, list):
            findings.append(Finding("LINEAR_EVENT_MALFORMED", location, "linear vector or output is missing"))
            continue
        add(findings, len(claimed) == len(matrix), "LINEAR_OUTPUT_SHAPE_MISMATCH", f"{location}/outputs/y", "linear output has the wrong row count")
        expected_a = clean_operand_root(event_id, "A", vector)
        expected_b = clean_operand_root(event_id, "B", matrix)
        add(findings, event.get("inputs", {}).get("operand_root_a") == expected_a, "OPERAND_ROOT_A_MISMATCH", f"{location}/inputs/operand_root_a", "input operand root is wrong")
        add(findings, event.get("inputs", {}).get("operand_root_b") == expected_b, "OPERAND_ROOT_B_MISMATCH", f"{location}/inputs/operand_root_b", "matrix operand root is wrong")
        relation = relations.get(event_id)
        if relation is None:
            continue
        rows = len(matrix)
        width = 2 * rows
        generator = make_generator(rows, width, prime)
        prepared = make_preprocessing(matrix, generator, prime)
        add(findings, relation.get("matrix_name") == matrix_name, "AUDIT_MATRIX_MISMATCH", f"audit/{event_id}", "audit names the wrong matrix")
        add(findings, relation.get("input") == vector, "AUDIT_TRACE_INPUT_MISMATCH", f"audit/{event_id}/input", "audit input differs from trace")
        add(findings, relation.get("output") == claimed, "AUDIT_TRACE_OUTPUT_MISMATCH", f"audit/{event_id}/output", "audit output differs from trace")
        add(findings, relation.get("operand_root_a") == expected_a and relation.get("operand_root_b") == expected_b, "AUDIT_OPERAND_BINDING_MISMATCH", f"audit/{event_id}", "audit clean operands differ from trace")
        add(findings, relation.get("generator") == generator and relation.get("generator_digest") == canonical_digest(generator), "GENERATOR_AUTHENTICATION_FAILED", f"audit/{event_id}/generator", "generator bytes or digest differ from frozen construction")
        add(findings, relation.get("preprocessing") == prepared and relation.get("preprocessing_digest") == canonical_digest(prepared), "PREPROCESSING_AUTHENTICATION_FAILED", f"audit/{event_id}/preprocessing", "Q is not G^T M for the frozen model")
        add(findings, relation.get("matrix_digest") == canonical_digest(matrix), "MODEL_PREPROCESSING_BINDING_FAILED", f"audit/{event_id}/matrix_digest", "preprocessing matrix digest differs")
        checks = relation.get("checks", [])
        add(findings, len(checks) == profile["repetitions"], "CHALLENGE_COUNT_MISMATCH", f"audit/{event_id}/checks", "wrong repetition count")
        relation_accepts = True
        for repetition in range(profile["repetitions"]):
            if repetition >= len(checks) or not isinstance(checks[repetition], dict):
                relation_accepts = False
                continue
            check = checks[repetition]
            expected_challenge = derive_challenge(
                profile["domain"],
                subject["subject_root"],
                event_id,
                repetition,
                width,
                profile["sparsity"],
                prime,
            )
            add(findings, check.get("repetition") == repetition, "CHALLENGE_SEQUENCE_MISMATCH", f"audit/{event_id}/checks/{repetition}", "challenge repetition is misnumbered")
            add(findings, check.get("challenge") == expected_challenge, "CHALLENGE_DERIVATION_MISMATCH", f"audit/{event_id}/checks/{repetition}/challenge", "challenge is not derived from the final subject")
            try:
                left, right = verify_coded_equation(prepared, generator, vector, claimed, expected_challenge, prime)
            except (ValueError, TypeError, IndexError) as exc:
                findings.append(Finding("CODED_LINEAR_MALFORMED", f"audit/{event_id}/checks/{repetition}", str(exc)))
                relation_accepts = False
                continue
            accepted = left == right
            relation_accepts &= accepted
            add(findings, accepted, "CODED_LINEAR_REJECT", f"audit/{event_id}/checks/{repetition}", "coded MVM equation rejected")
            add(findings, check.get("left") == left and check.get("right") == right and check.get("accepted") == accepted, "CODED_CHECK_TRANSCRIPT_MISMATCH", f"audit/{event_id}/checks/{repetition}", "retained coded equation values differ from replay")
        distance = width - rows + 1
        delta = Fraction(distance, width)
        bound = ((1 - delta) ** profile["sparsity"] + Fraction(1, prime - 1)) ** profile["repetitions"]
        computed_union += bound
        add(findings, relation.get("message_length") == rows and relation.get("block_length") == width and relation.get("minimum_distance") == distance, "CODE_PARAMETER_MISMATCH", f"audit/{event_id}", "code dimensions or distance differ")
        add(findings, relation.get("relative_distance") == {"numerator": delta.numerator, "denominator": delta.denominator}, "CODE_DISTANCE_MISMATCH", f"audit/{event_id}/relative_distance", "relative distance differs")
        add(findings, relation.get("conditional_soundness_bound") == {"numerator": bound.numerator, "denominator": bound.denominator}, "SOUNDNESS_BOUND_MISMATCH", f"audit/{event_id}/conditional_soundness_bound", "conditional bound differs from frozen formula")
        add(findings, relation.get("accepted") is relation_accepts, "RELATION_ACCEPTANCE_MISMATCH", f"audit/{event_id}/accepted", "retained relation acceptance differs from replay")
    add(findings, audit.get("conditional_union_bound") == {"numerator": computed_union.numerator, "denominator": computed_union.denominator}, "UNION_BOUND_MISMATCH", "audit/conditional_union_bound", "five-relation union bound differs")
    add(findings, audit.get("all_relations_accept") is True and not any(item.code == "CODED_LINEAR_REJECT" for item in findings), "AUDIT_ACCEPTANCE_MISMATCH", "audit/all_relations_accept", "aggregate coded acceptance is false or inconsistent")


def subject_and_policy_checks(
    data: dict[str, Any],
    roots: dict[str, str],
    subject: dict[str, str],
    trace: dict[str, Any],
    output: dict[str, Any],
    work: dict[str, Any],
    audit: dict[str, Any],
    receipt: dict[str, Any],
    events: dict[str, dict[str, Any]],
    findings: list[Finding],
) -> None:
    add(findings, trace.get("job_id") == roots["job_id"], "TRACE_JOB_MISMATCH", "trace/job_id", "trace belongs to a different job")
    for event_id, event in events.items():
        add(findings, event.get("job_id") == roots["job_id"], "CROSS_REQUEST_ROW_GRAFT", f"trace/{event_id}/job_id", "event row belongs to a different job")
    add(findings, receipt.get("subject") == subject, "SUBJECT_BINDING_MISMATCH", "receipt/subject", "receipt subject does not recompute from retained input, trace, and output")
    add(findings, audit.get("subject_root") == subject["subject_root"], "AUDIT_SUBJECT_MISMATCH", "audit/subject_root", "audit challenge subject differs")
    timeline = receipt.get("timeline", {})
    order = [timeline.get(name) for name in ("intent_fixed_sequence", "authorization_fixed_sequence", "job_fixed_sequence", "subject_fixed_sequence", "challenge_sampled_sequence", "receipt_sealed_sequence")]
    add(findings, all(isinstance(value, int) for value in order) and order == sorted(order) and len(set(order)) == len(order), "CHALLENGE_ORDER", "receipt/timeline", "intent, authorization, job, subject, challenge, and seal are not strictly ordered")
    if len(order) == 6 and all(isinstance(value, int) for value in order):
        add(findings, order[3] < order[4], "CHALLENGE_ORDER", "receipt/timeline/challenge_sampled_sequence", "challenge was not sampled after the final subject")

    q_event = events.get("q_linear", {})
    q_a = q_event.get("inputs", {}).get("operand_root_a")
    q_b = q_event.get("inputs", {}).get("operand_root_b")
    add(findings, work.get("status") == "synthetic_only" and work.get("native_pearl_relation_present") is False and work.get("native_pearl_certificate_present") is False, "SYNTHETIC_WORK_MISCLASSIFIED", "synthetic-pearl-work", "synthetic WORK artifact claims a native Pearl relation")
    add(findings, work.get("job_id") == roots["job_id"], "WORK_JOB_MISMATCH", "synthetic-pearl-work/job_id", "synthetic work object belongs to another job")
    add(findings, work.get("operand_event_id") == "q_linear" and work.get("operand_root_a") == q_a and work.get("operand_root_b") == q_b, "WORK_EXECUTION_OPERAND_MISMATCH", "synthetic-pearl-work", "synthetic work roots do not equal q_linear roots")
    expected_context = {
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "kind": "synthetic-clean-operand-context",
        "pearl_version": None,
        "certificate": None,
    }
    add(findings, work.get("work_context") == expected_context and work.get("work_context_root") == canonical_digest(expected_context), "WORK_CONTEXT_MISMATCH", "synthetic-pearl-work/work_context", "synthetic context commitment differs")

    evidence = receipt.get("evidence", [])
    by_id = {
        item.get("evidence_id"): item
        for item in evidence
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    work_ev = by_id.get("e009:r1:synthetic-pearl-operands", {})
    execution_ev = by_id.get("e009:r1:coded-execution-audit", {})
    semantics_ev = by_id.get("e009:r1:declared-semantics-conformance", {})
    work_inputs = work_ev.get("native_public_inputs", {})
    execution_inputs = execution_ev.get("native_public_inputs", {})
    add(findings, work_inputs.get("operand_root_a") == execution_inputs.get("operand_root_a") == q_a and work_inputs.get("operand_root_b") == execution_inputs.get("operand_root_b") == q_b, "CROSS_EVIDENCE_BINDING_MISMATCH", "receipt/cross_evidence_bindings", "WORK and EXECUTION native operand roots differ")
    add(findings, execution_inputs.get("aeye_job_id") == subject["job_id"] and execution_inputs.get("aeye_subject_root") == subject["subject_root"], "EXECUTION_SUBJECT_BINDING_MISSING", "receipt/evidence/execution", "execution relation does not bind job and final subject")
    add(findings, semantics_ev.get("native_public_inputs", {}).get("aeye_subject_root") == subject["subject_root"], "SEMANTICS_SUBJECT_BINDING_MISSING", "receipt/evidence/semantics", "semantics relation does not bind final subject")
    results = receipt.get("claimed_results", {})
    expected_statuses = {"WORK": "unknown", "EXECUTION": "satisfied", "SEMANTICS": "satisfied", "DEMAND": "unsupported"}
    for coordinate, expected in expected_statuses.items():
        add(findings, results.get(coordinate, {}).get("status") == expected, "SYNTHETIC_WORK_UPGRADE" if coordinate == "WORK" else "COORDINATE_POLICY_MISMATCH", f"receipt/claimed_results/{coordinate}/status", f"{coordinate} must remain {expected!r} in E-009")
    add(findings, results.get("EXECUTION", {}).get("assurance") == "sampled", "EXECUTION_ASSURANCE_MISMATCH", "receipt/claimed_results/EXECUTION", "execution assurance must remain sampled")
    add(findings, results.get("SEMANTICS", {}).get("assurance") == "hybrid", "SEMANTICS_ASSURANCE_MISMATCH", "receipt/claimed_results/SEMANTICS", "semantics assurance must remain hybrid")
    add(findings, results.get("DEMAND", {}).get("evidence_refs") == [], "DEMAND_UPGRADE", "receipt/claimed_results/DEMAND", "no DEMAND evidence is permitted in R1")
    add(findings, work_ev.get("statement_id") == "aeye:synthetic-pearl-clean-operands:v0" and work_ev.get("assurance") == "commitment_only", "SYNTHETIC_WORK_MISCLASSIFIED", "receipt/evidence/work", "synthetic roots were relabelled as native Pearl verification")


def artifact_digest_checks(paths: dict[str, Path], work: dict[str, Any], audit: dict[str, Any], receipt: dict[str, Any], findings: list[Finding]) -> None:
    by_id = {
        item.get("evidence_id"): item
        for item in receipt.get("evidence", [])
        if isinstance(item, dict)
    }
    expected = {
        "e009:r1:synthetic-pearl-operands": paths["synthetic_pearl_work"],
        "e009:r1:coded-execution-audit": paths["audit"],
        "e009:r1:declared-semantics-conformance": paths["trace"],
    }
    for evidence_id, path in expected.items():
        observed = by_id.get(evidence_id, {}).get("artifact_digest")
        add(findings, path.is_file() and observed == file_digest(path), "EVIDENCE_ARTIFACT_DIGEST_MISMATCH", f"receipt/evidence/{evidence_id}", "evidence digest differs from retained file bytes")


def verify_documents(
    documents: dict[str, Any],
    *,
    paths: dict[str, Path] | None = None,
    include_schemas: bool = True,
) -> list[Finding]:
    findings: list[Finding] = []
    data = documents["input"]
    trace = documents["trace"]
    output = documents["output"]
    work = documents["synthetic_pearl_work"]
    audit = documents["audit"]
    receipt = documents["receipt"]
    if include_schemas:
        findings.extend(schema_findings(data, "e009-input-v0.schema.json", "input"))
        findings.extend(schema_findings(trace, "e009-trace-v0.schema.json", "trace"))
        findings.extend(schema_findings(audit, "e009-audit-v0.schema.json", "audit"))
        findings.extend(schema_findings(receipt, "aeye-evidence-receipt-v0.schema.json", "receipt"))
    try:
        validate_input_contract(data, findings)
        roots = initial_roots(data)
        subject = completed_subject(data, roots, trace, output)
        events = event_map(trace, findings)
        exact_event_checks(data, roots, events, output, findings)
        linear_and_audit_checks(data, subject, events, audit, findings)
        subject_and_policy_checks(data, roots, subject, trace, output, work, audit, receipt, events, findings)
        if paths is not None:
            artifact_digest_checks(paths, work, audit, receipt, findings)
    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
        findings.append(Finding("MALFORMED_BUNDLE", "bundle", f"fail-closed exception: {exc}"))
    return sorted(set(findings))


def bundle_paths(artifact_dir: Path) -> dict[str, Path]:
    return {
        "input": EXPERIMENT_DIR / "input.json",
        "run_index": artifact_dir / "run.json",
        "trace": artifact_dir / "trace.json",
        "output": artifact_dir / "output.json",
        "synthetic_pearl_work": artifact_dir / "synthetic-pearl-work.json",
        "audit": artifact_dir / "audit.json",
        "provider_measurements": artifact_dir / "provider-measurements.json",
        "receipt": artifact_dir / "receipt.json",
    }


def load_documents(paths: dict[str, Path]) -> dict[str, Any]:
    return {name: load_json(path) for name, path in paths.items() if name not in {"run_index", "provider_measurements"}}


def preregistration_findings(paths: dict[str, Path]) -> list[Finding]:
    findings: list[Finding] = []
    prereg = load_json(PREREGISTRATION)
    add(findings, prereg.get("status") == "preregistered" and prereg.get("result") is None, "PREREGISTRATION_STATE_MISMATCH", "preregistration", "retained preregistration is not an unfinished preregistered manifest")
    values = {
        item.get("input_id"): item.get("value")
        for item in prereg.get("frozen_inputs", [])
        if isinstance(item, dict)
    }
    required = {
        "e009_input": paths["input"],
        "generator_implementation": EXPERIMENT_DIR / "generate.py",
        "independent_verifier_implementation": Path(__file__).resolve(),
        "input_schema": SCHEMA_DIR / "e009-input-v0.schema.json",
        "trace_schema": SCHEMA_DIR / "e009-trace-v0.schema.json",
        "audit_schema": SCHEMA_DIR / "e009-audit-v0.schema.json",
        "operator_authorization": EXPERIMENT_DIR / "OPERATOR_AUTHORIZATION.md",
    }
    for identifier, path in required.items():
        expected_path = str(path.relative_to(REPOSITORY_ROOT))
        add(findings, values.get(identifier) == expected_path, "PREREGISTRATION_PATH_MISMATCH", f"preregistration/{identifier}", "frozen artifact path differs")
        add(findings, values.get(f"{identifier}_sha256") == file_digest(path).removeprefix("sha256:"), "PREREGISTRATION_DIGEST_MISMATCH", f"preregistration/{identifier}_sha256", "frozen artifact digest differs")
    return findings


def run_index_findings(paths: dict[str, Path]) -> list[Finding]:
    findings: list[Finding] = []
    index = load_json(paths["run_index"])
    add(findings, index.get("input", {}).get("sha256") == file_digest(paths["input"]), "RUN_INPUT_DIGEST_MISMATCH", "run/input", "run index input digest differs")
    for name, record in index.get("artifacts", {}).items():
        if name not in paths:
            findings.append(Finding("RUN_ARTIFACT_UNKNOWN", f"run/artifacts/{name}", "run index names an unknown artifact"))
            continue
        path = paths[name]
        add(findings, record.get("path") == str(path.relative_to(REPOSITORY_ROOT)), "RUN_ARTIFACT_PATH_MISMATCH", f"run/artifacts/{name}", "artifact path differs")
        add(findings, path.is_file() and record.get("sha256") == file_digest(path), "RUN_ARTIFACT_DIGEST_MISMATCH", f"run/artifacts/{name}", "artifact bytes differ from run index")
        add(findings, path.is_file() and record.get("bytes") == path.stat().st_size, "RUN_ARTIFACT_SIZE_MISMATCH", f"run/artifacts/{name}", "artifact size differs from run index")
    return findings


def mutation_cases(documents: dict[str, Any]) -> list[tuple[str, str, Callable[[dict[str, Any]], None]]]:
    prime = documents["input"]["arithmetic_profile"]["field_prime"]

    def execution_operand_mismatch(bundle: dict[str, Any]) -> None:
        evidence = next(item for item in bundle["receipt"]["evidence"] if item["evidence_id"] == "e009:r1:coded-execution-audit")
        evidence["native_public_inputs"]["operand_root_a"] = "sha256:" + "0" * 64

    def altered_linear_output(bundle: dict[str, Any]) -> None:
        event = next(item for item in bundle["trace"]["events"] if item["event_id"] == "q_linear")
        event["outputs"]["y"][0] = (event["outputs"]["y"][0] + 1) % prime
        relation = next(item for item in bundle["audit"]["relations"] if item["event_id"] == "q_linear")
        relation["output"][0] = event["outputs"]["y"][0]

    def skip_nonlinear(bundle: dict[str, Any]) -> None:
        bundle["trace"]["events"] = [item for item in bundle["trace"]["events"] if item["event_id"] != "relu"]
        bundle["trace"]["event_count"] -= 1

    def output_graft(bundle: dict[str, Any]) -> None:
        bundle["output"]["token_id"] = 4
        bundle["output"]["token"] = "jade"

    def early_challenge(bundle: dict[str, Any]) -> None:
        bundle["receipt"]["timeline"]["challenge_sampled_sequence"] = 2

    def request_row_graft(bundle: dict[str, Any]) -> None:
        event = next(item for item in bundle["trace"]["events"] if item["event_id"] == "q_linear")
        event["inputs"]["x"][0] = (event["inputs"]["x"][0] + 1) % prime
        relation = next(item for item in bundle["audit"]["relations"] if item["event_id"] == "q_linear")
        relation["input"][0] = event["inputs"]["x"][0]

    def wrong_preprocessing(bundle: dict[str, Any]) -> None:
        relation = next(item for item in bundle["audit"]["relations"] if item["event_id"] == "q_linear")
        relation["preprocessing"][0][0] = (relation["preprocessing"][0][0] + 1) % prime

    def coordinate_laundering(bundle: dict[str, Any]) -> None:
        result = bundle["receipt"]["claimed_results"]["WORK"]
        result["status"] = "satisfied"
        result["assurance"] = "cryptographic"
        result["coverage"] = {
            "known": True,
            "scope": "one falsely upgraded synthetic work object",
            "unit": "winning_pouw_instance",
            "numerator": 1,
            "denominator": 1,
        }

    return [
        ("execution_operand_root_mismatch", "CROSS_EVIDENCE_BINDING_MISMATCH", execution_operand_mismatch),
        ("altered_linear_output", "CODED_LINEAR_REJECT", altered_linear_output),
        ("skipped_nonlinear_event", "EVENT_UNIVERSE_MISMATCH", skip_nonlinear),
        ("output_graft", "OUTPUT_TRACE_MISMATCH", output_graft),
        ("challenge_before_subject", "CHALLENGE_ORDER", early_challenge),
        ("cross_request_row_graft", "REQUEST_ROW_GRAFT", request_row_graft),
        ("wrong_model_preprocessing", "PREPROCESSING_AUTHENTICATION_FAILED", wrong_preprocessing),
        ("synthetic_work_coordinate_laundering", "SYNTHETIC_WORK_UPGRADE", coordinate_laundering),
    ]


def run_mutations(documents: dict[str, Any]) -> dict[str, Any]:
    outcomes: list[dict[str, Any]] = []
    for case_id, expected_code, mutate in mutation_cases(documents):
        candidate = copy.deepcopy(documents)
        mutate(candidate)
        findings = verify_documents(candidate, include_schemas=False)
        codes = sorted({item.code for item in findings})
        outcomes.append(
            {
                "case_id": case_id,
                "expected_code": expected_code,
                "observed_codes": codes,
                "rejected": bool(findings),
                "expected_failure_observed": expected_code in codes,
            }
        )
    return {
        "schema_version": "aeye.e009-mutation-results.v0",
        "experiment_id": documents["input"]["experiment_id"],
        "run_id": documents["input"]["run_id"],
        "case_count": len(outcomes),
        "all_rejected": all(item["rejected"] for item in outcomes),
        "all_expected_failures_observed": all(item["expected_failure_observed"] for item in outcomes),
        "outcomes": outcomes,
    }


def timing_distribution(samples: list[int]) -> dict[str, int]:
    ordered = sorted(samples)
    return {
        "minimum_ns": ordered[0],
        "median_ns": int(statistics.median(ordered)),
        "p95_ns": ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)],
        "mean_ns": int(statistics.fmean(ordered)),
    }


def benchmark_verifier(documents: dict[str, Any]) -> dict[str, Any]:
    profile = documents["input"]["measurement_profile"]
    warmup = profile["warmup"]
    repetitions = profile["verifier_repetitions"]
    operation = lambda: verify_documents(documents, include_schemas=False)
    for _ in range(warmup):
        operation()
    samples: list[int] = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        result = operation()
        elapsed = time.perf_counter_ns() - start
        if result:
            raise RuntimeError("benchmark encountered a verification failure")
        samples.append(elapsed)
    return {
        "schema_version": "aeye.e009-verifier-measurements.v0",
        "experiment_id": documents["input"]["experiment_id"],
        "run_id": documents["input"]["run_id"],
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
            "scope": "Complete independent relation replay excluding JSON Schema and file-integrity checks; includes preprocessing authentication, 80 coded equations, exact state/nonlinear/decode checks, and policy checks.",
        },
        "timings": {"independent_relation_replay": timing_distribution(samples)},
        "diagnostics": [
            "Local Python toy result only; it is not a production verifier benchmark.",
            "Schema parsing and disk I/O are excluded from the timed relation replay and remain part of untimed end-to-end acceptance.",
        ],
    }


def make_report(documents: dict[str, Any], receipt_path: Path) -> dict[str, Any]:
    data = documents["input"]
    results = copy.deepcopy(documents["receipt"]["claimed_results"])
    results["WORK"]["diagnostics"].append("Independent code-path replay confirms only root equality; no Pearl verifier was executed.")
    results["EXECUTION"]["diagnostics"].append("A separately implemented verifier accepted all 13 events and the conditional coded-audit equations.")
    results["SEMANTICS"]["diagnostics"].append("Conformance is exact only for the frozen finite-field/hard-attention profile.")
    results["DEMAND"]["diagnostics"].append("No demand relation was presented to the verifier.")
    policy_digest = canonical_digest(
        {
            "event_universe": data["event_universe"],
            "arithmetic_profile": data["arithmetic_profile"],
            "audit_profile": data["audit_profile"],
            "coordinate_policy": {
                "WORK": "unknown",
                "EXECUTION": "satisfied",
                "SEMANTICS": "satisfied",
                "DEMAND": "unsupported",
            },
        }
    )
    return {
        "schema_version": "aeye.verification-report.v0",
        "report_id": "e009:r1:independent-code-path-appraisal",
        "receipt_path": str(receipt_path.relative_to(REPOSITORY_ROOT)),
        "receipt_digest": file_digest(receipt_path),
        "generated_at": data["artifact_times"]["report_generated_at"],
        "verifier": {
            "principal_id": "e009:independent-code-path-verifier",
            "independence_statement": "This verifier shares no generator modules or arithmetic helpers. It is code-path separation by the same research process, not independent human, institutional, or third-party review.",
        },
        "appraisal_policy": {
            "policy_id": "aeye:e009-r1-appraisal",
            "version": "v0",
            "artifact_digest": policy_digest,
        },
        "results": results,
        "conflicts": [],
    }


def execute(artifact_dir: Path, write_outputs: bool) -> tuple[list[Finding], dict[str, Any] | None]:
    paths = bundle_paths(artifact_dir)
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        return [Finding("ARTIFACT_MISSING", "bundle", f"missing artifacts: {missing}")], None
    documents = load_documents(paths)
    findings = []
    findings.extend(preregistration_findings(paths))
    findings.extend(run_index_findings(paths))
    findings.extend(verify_documents(documents, paths=paths))
    findings = sorted(set(findings))
    if findings:
        return findings, None
    mutations = run_mutations(documents)
    if not mutations["all_rejected"] or not mutations["all_expected_failures_observed"]:
        findings.append(Finding("MUTATION_SUITE_FAILED", "mutations", "one or more preregistered controls did not fail as expected"))
        return sorted(set(findings)), None
    measurements = benchmark_verifier(documents)
    report = make_report(documents, paths["receipt"])
    report_schema_findings = schema_findings(report, "verification-report-v0.schema.json", "verification-report")
    if report_schema_findings:
        return sorted(set(report_schema_findings)), None
    audit = documents["audit"]
    result = {
        "schema_version": "aeye.e009-result.v0",
        "experiment_id": documents["input"]["experiment_id"],
        "run_id": documents["input"]["run_id"],
        "status": "supported",
        "unmodified_bundle_accepted": True,
        "coordinate_results": {
            name: value["status"] for name, value in report["results"].items()
        },
        "event_coverage": {
            "numerator": len(EXPECTED_EVENTS),
            "denominator": len(EXPECTED_EVENTS),
            "coded_linear": len(LINEAR_EVENTS),
            "exact": len(EXPECTED_EVENTS) - len(LINEAR_EVENTS),
        },
        "conditional_union_bound": audit["conditional_union_bound"],
        "mutation_controls": {
            "rejected": sum(1 for item in mutations["outcomes"] if item["rejected"]),
            "total": mutations["case_count"],
            "all_expected_failures_observed": mutations["all_expected_failures_observed"],
        },
        "independence": "code-path only; no independent person or institution reviewed this result",
        "non_claims": documents["input"]["non_claims"],
    }
    if write_outputs:
        write_json(artifact_dir / "mutation-results.json", mutations)
        write_json(artifact_dir / "verifier-measurements.json", measurements)
        write_json(artifact_dir / "verification-report.json", report)
        write_json(artifact_dir / "result.json", result)
    return [], result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ARTIFACT_DIR)
    parser.add_argument("--write", action="store_true", help="write report, mutation, measurement, and result artifacts")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    arguments = parser.parse_args()
    findings, result = execute(arguments.artifacts.resolve(), arguments.write)
    payload = {
        "ok": not findings,
        "findings": [item.as_dict() for item in findings],
        "result": result,
        "non_claim": "Code-path replay is not Pearl verification, hardware fidelity, production performance, demand evidence, or independent peer review.",
    }
    if arguments.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        print(f"E-009 independent replay: REJECT ({len(findings)} finding(s))")
        for finding in findings:
            print(f"{finding.code} {finding.location}: {finding.message}")
    else:
        assert result is not None
        print("E-009 independent replay: ACCEPT")
        print(
            "coordinates: "
            + ", ".join(
                f"{coordinate}={status}"
                for coordinate, status in result["coordinate_results"].items()
            )
        )
        mutation = result["mutation_controls"]
        print(f"known-bad controls: {mutation['rejected']}/{mutation['total']} rejected")
        print(payload["non_claim"])
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
