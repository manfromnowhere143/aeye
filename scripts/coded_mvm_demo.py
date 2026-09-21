#!/usr/bin/env python3
"""Deterministic demonstrator for the CX-1 coded-MVM interface.

This is an isolated finite-field relation test. It is not a Maverick implementation,
an Aeye execution backend, a Pearl verifier, a proof, or a performance benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence


FIELD = 2**61 - 1
CHALLENGE_DOMAIN = b"aeye/coded-mvm-challenge/v0\x00"


def _check_matrix(matrix: Sequence[Sequence[int]]) -> tuple[int, int]:
    if not matrix or not matrix[0]:
        raise ValueError("matrix must be non-empty")
    columns = len(matrix[0])
    if any(len(row) != columns for row in matrix):
        raise ValueError("matrix rows must have equal length")
    return len(matrix), columns


def dot(left: Sequence[int], right: Sequence[int], field: int = FIELD) -> int:
    if len(left) != len(right):
        raise ValueError("dot-product dimensions differ")
    return sum((a % field) * (b % field) for a, b in zip(left, right)) % field


def matrix_vector(
    matrix: Sequence[Sequence[int]], vector: Sequence[int], field: int = FIELD
) -> list[int]:
    _, columns = _check_matrix(matrix)
    if len(vector) != columns:
        raise ValueError("matrix/vector dimensions differ")
    return [dot(row, vector, field) for row in matrix]


def reed_solomon_generator(
    message_length: int, block_length: int, field: int = FIELD
) -> list[list[int]]:
    """Return G in F^(message_length x block_length) for evaluation at 1..N."""
    if not 1 <= message_length <= block_length < field:
        raise ValueError("require 1 <= message_length <= block_length < field")
    return [
        [pow(point, degree, field) for point in range(1, block_length + 1)]
        for degree in range(message_length)
    ]


def preprocess(
    matrix: Sequence[Sequence[int]],
    generator: Sequence[Sequence[int]],
    field: int = FIELD,
) -> list[list[int]]:
    """Compute Q = G^T M."""
    rows, columns = _check_matrix(matrix)
    generator_rows, block_length = _check_matrix(generator)
    if generator_rows != rows:
        raise ValueError("generator message dimension must equal matrix output dimension")
    return [
        [
            sum(generator[row][position] * matrix[row][column] for row in range(rows))
            % field
            for column in range(columns)
        ]
        for position in range(block_length)
    ]


def encode(
    message: Sequence[int], generator: Sequence[Sequence[int]], field: int = FIELD
) -> list[int]:
    rows, block_length = _check_matrix(generator)
    if len(message) != rows:
        raise ValueError("message/generator dimensions differ")
    return [
        sum(generator[row][position] * message[row] for row in range(rows)) % field
        for position in range(block_length)
    ]


class HashStream:
    """Domain-separated deterministic stream used only for reproducible fixtures."""

    def __init__(self, subject_root: bytes, repetition: int) -> None:
        if repetition < 0:
            raise ValueError("repetition must be non-negative")
        self._seed = CHALLENGE_DOMAIN + subject_root + repetition.to_bytes(8, "big")
        self._counter = 0

    def uniform_below(self, limit: int) -> int:
        if limit <= 0:
            raise ValueError("limit must be positive")
        modulus = 1 << 256
        cutoff = modulus - (modulus % limit)
        while True:
            material = self._seed + self._counter.to_bytes(8, "big")
            self._counter += 1
            candidate = int.from_bytes(hashlib.sha256(material).digest(), "big")
            if candidate < cutoff:
                return candidate % limit


def sparse_challenge(
    subject_root: bytes,
    repetition: int,
    block_length: int,
    sparsity: int,
    field: int = FIELD,
) -> tuple[tuple[int, int], ...]:
    if not 1 <= sparsity <= block_length:
        raise ValueError("require 1 <= sparsity <= block_length")
    stream = HashStream(subject_root, repetition)
    positions: set[int] = set()
    while len(positions) < sparsity:
        positions.add(stream.uniform_below(block_length))
    return tuple(
        (position, 1 + stream.uniform_below(field - 1))
        for position in sorted(positions)
    )


def sparse_linear_combination(
    challenge: Iterable[tuple[int, int]],
    vectors: Sequence[Sequence[int]],
    field: int = FIELD,
) -> list[int]:
    rows, columns = _check_matrix(vectors)
    result = [0] * columns
    for position, coefficient in challenge:
        if not 0 <= position < rows:
            raise ValueError("challenge position is outside the vector set")
        for column in range(columns):
            result[column] = (
                result[column] + coefficient * vectors[position][column]
            ) % field
    return result


def verify_repetition(
    preprocessed: Sequence[Sequence[int]],
    generator: Sequence[Sequence[int]],
    x: Sequence[int],
    y: Sequence[int],
    challenge: Sequence[tuple[int, int]],
    field: int = FIELD,
) -> bool:
    projected_matrix = sparse_linear_combination(challenge, preprocessed, field)
    encoded_y = encode(y, generator, field)
    right_vectors = [[value] for value in encoded_y]
    projected_y = sparse_linear_combination(challenge, right_vectors, field)[0]
    return dot(projected_matrix, x, field) == projected_y


def verify(
    preprocessed: Sequence[Sequence[int]],
    generator: Sequence[Sequence[int]],
    x: Sequence[int],
    y: Sequence[int],
    subject_root: bytes,
    sparsity: int,
    repetitions: int,
    field: int = FIELD,
) -> bool:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    block_length = len(preprocessed)
    return all(
        verify_repetition(
            preprocessed,
            generator,
            x,
            y,
            sparse_challenge(subject_root, repetition, block_length, sparsity, field),
            field,
        )
        for repetition in range(repetitions)
    )


def soundness_bound(
    message_length: int,
    block_length: int,
    sparsity: int,
    repetitions: int,
    field: int = FIELD,
) -> Fraction:
    """Paper bound for an MDS code, excluding code-sampling failure (zero here)."""
    if not 1 <= message_length <= block_length:
        raise ValueError("invalid code dimensions")
    if not 1 <= sparsity <= block_length or repetitions < 1:
        raise ValueError("invalid challenge parameters")
    distance = block_length - message_length + 1
    delta = Fraction(distance, block_length)
    one_round = (1 - delta) ** sparsity + Fraction(1, field - 1)
    return one_round**repetitions


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


@dataclass(frozen=True)
class Demonstration:
    field: int
    message_length: int
    block_length: int
    sparsity: int
    repetitions: int
    subject_root: str
    generator_digest: str
    preprocessing_digest: str
    correct_accepts: bool
    altered_output_accepts: bool
    soundness_bound_numerator: int
    soundness_bound_denominator: int

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "aeye.coded-mvm-demo.v0",
            "status": "structural-demonstration",
            "parameters": {
                "field": self.field,
                "message_length": self.message_length,
                "block_length": self.block_length,
                "minimum_distance": self.block_length - self.message_length + 1,
                "sparsity": self.sparsity,
                "repetitions": self.repetitions,
                "subject_root": self.subject_root,
                "generator_digest": self.generator_digest,
                "preprocessing_digest": self.preprocessing_digest,
            },
            "observations": {
                "correct_accepts": self.correct_accepts,
                "altered_output_accepts": self.altered_output_accepts,
                "symbolic_soundness_bound": {
                    "numerator": self.soundness_bound_numerator,
                    "denominator": self.soundness_bound_denominator,
                },
            },
            "non_claim": (
                "This deterministic finite-field demonstrator is not E-009, a Maverick "
                "implementation, a Pearl verifier, a transferable proof, native GPU "
                "semantics, or a performance result."
            ),
        }


def run_demonstration() -> Demonstration:
    matrix = [
        [3, 1, 4, 1],
        [5, 9, 2, 6],
        [5, 3, 5, 8],
        [9, 7, 9, 3],
    ]
    x = [2, 7, 1, 8]
    message_length = len(matrix)
    block_length = 8
    sparsity = 3
    repetitions = 8
    generator = reed_solomon_generator(message_length, block_length)
    prepared = preprocess(matrix, generator)
    y = matrix_vector(matrix, x)
    generator_digest = canonical_digest(generator)
    preprocessing_digest = canonical_digest(prepared)
    subject_root_text = canonical_digest(
        {
            "domain": "aeye/coded-mvm-demo-subject/v0",
            "matrix": matrix,
            "input": x,
            "output": y,
            "generator_digest": generator_digest,
            "preprocessing_digest": preprocessing_digest,
        }
    )
    subject_root = bytes.fromhex(subject_root_text.removeprefix("sha256:"))
    altered_y = y.copy()
    altered_y[0] = (altered_y[0] + 1) % FIELD
    bound = soundness_bound(
        message_length, block_length, sparsity, repetitions, FIELD
    )
    return Demonstration(
        field=FIELD,
        message_length=message_length,
        block_length=block_length,
        sparsity=sparsity,
        repetitions=repetitions,
        subject_root=subject_root_text,
        generator_digest=generator_digest,
        preprocessing_digest=preprocessing_digest,
        correct_accepts=verify(
            prepared, generator, x, y, subject_root, sparsity, repetitions
        ),
        altered_output_accepts=verify(
            prepared, generator, x, altered_y, subject_root, sparsity, repetitions
        ),
        soundness_bound_numerator=bound.numerator,
        soundness_bound_denominator=bound.denominator,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit compact JSON")
    arguments = parser.parse_args()
    result = run_demonstration().as_dict()
    print(json.dumps(result, indent=None if arguments.json else 2, sort_keys=True))
    observations = result["observations"]
    assert isinstance(observations, dict)
    return 0 if (
        observations["correct_accepts"] is True
        and observations["altered_output_accepts"] is False
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
