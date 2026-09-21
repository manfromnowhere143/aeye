#!/usr/bin/env python3
"""Deterministic, fail-closed runtime-slab transformation recipes for E-000.

The engine never guesses a vLLM transformation.  Fusion order, TP/EP selection, expert
order, transposition, and final shape must be explicit in a schema-validated recipe.  It
operates on already materialized int8 checkpoint tensors; checkpoint extraction and proof
of temporal provenance are separate gates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - fail-closed environment guard
    raise SystemExit("missing dependency: install the hash-locked development requirements") from exc

try:
    from conformance import ConformanceError, PublicProofDataV3, sha256_hex
except ImportError:  # imported through a file loader in tests
    import sys

    _HERE = Path(__file__).resolve().parent
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    from conformance import ConformanceError, PublicProofDataV3, sha256_hex


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schemas" / "e000-slab-recipe-v0.schema.json"


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ConformanceError(code, message)


@dataclass(frozen=True)
class Int8Matrix:
    rows: int
    cols: int
    data: bytes

    def __post_init__(self) -> None:
        _require(self.rows > 0 and self.cols > 0, "E000_MATRIX_SHAPE", "matrix dimensions must be positive")
        _require(
            len(self.data) == self.rows * self.cols,
            "E000_MATRIX_BYTE_LENGTH",
            f"{self.rows}x{self.cols} int8 matrix requires {self.rows * self.cols} bytes, got {len(self.data)}",
        )

    def row_slice(self, start: int, stop: int) -> "Int8Matrix":
        _require(0 <= start < stop <= self.rows, "E000_ROW_SLICE", f"invalid row slice [{start},{stop})")
        return Int8Matrix(stop - start, self.cols, self.data[start * self.cols : stop * self.cols])

    def column_slice(self, start: int, stop: int) -> "Int8Matrix":
        _require(0 <= start < stop <= self.cols, "E000_COLUMN_SLICE", f"invalid column slice [{start},{stop})")
        width = stop - start
        output = bytearray(self.rows * width)
        cursor = 0
        for row in range(self.rows):
            row_start = row * self.cols + start
            output[cursor : cursor + width] = self.data[row_start : row_start + width]
            cursor += width
        return Int8Matrix(self.rows, width, bytes(output))

    def transpose(self) -> "Int8Matrix":
        output = bytearray(len(self.data))
        for row in range(self.rows):
            for col in range(self.cols):
                output[col * self.rows + row] = self.data[row * self.cols + col]
        return Int8Matrix(self.cols, self.rows, bytes(output))

    @classmethod
    def concat_rows(cls, matrices: list["Int8Matrix"]) -> "Int8Matrix":
        _require(bool(matrices), "E000_CONCAT_EMPTY", "row concatenation needs at least one matrix")
        cols = matrices[0].cols
        _require(all(matrix.cols == cols for matrix in matrices), "E000_CONCAT_COLS", "row-concatenated matrices have different column counts")
        return cls(sum(matrix.rows for matrix in matrices), cols, b"".join(matrix.data for matrix in matrices))


def _validate_recipe(recipe: Mapping[str, Any]) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(recipe), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        pointer = "/".join(str(part) for part in error.absolute_path)
        raise ConformanceError("E000_RECIPE_SCHEMA", f"{pointer or '/'}: {error.message}")


def _safe_source_path(base: Path, relative: str) -> Path:
    candidate = base.joinpath(relative).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as exc:
        raise ConformanceError("E000_SOURCE_PATH_ESCAPE", f"source path escapes recipe root: {relative}") from exc
    _require(not candidate.is_symlink(), "E000_SOURCE_SYMLINK", f"source path may not be a symlink: {relative}")
    _require(candidate.is_file(), "E000_SOURCE_MISSING", f"source file does not exist: {relative}")
    return candidate


def load_sources(recipe: Mapping[str, Any], base: Path) -> dict[str, Int8Matrix]:
    """Load content-addressed raw int8 tensors named by a validated recipe."""
    _validate_recipe(recipe)
    matrices: dict[str, Int8Matrix] = {}
    for source in recipe["sources"]:
        source_id = source["source_id"]
        _require(source_id not in matrices, "E000_SOURCE_DUPLICATE", f"duplicate source id {source_id!r}")
        path = _safe_source_path(base, source["path"])
        data = path.read_bytes()
        observed = sha256_hex(data)
        _require(
            observed == source["sha256"],
            "E000_SOURCE_DIGEST",
            f"{source_id}: observed {observed}, expected {source['sha256']}",
        )
        matrices[source_id] = Int8Matrix(source["rows"], source["cols"], data)
    return matrices


def evaluate_recipe(
    recipe: Mapping[str, Any],
    sources: Mapping[str, Int8Matrix],
) -> tuple[Int8Matrix, dict[str, Any]]:
    """Evaluate a recipe and return the exact slab plus a content-addressed transcript."""
    _validate_recipe(recipe)
    state = dict(sources)
    expected_source_ids = {source["source_id"] for source in recipe["sources"]}
    _require(set(state) == expected_source_ids, "E000_SOURCE_SET", "provided source IDs differ from the recipe")
    for source in recipe["sources"]:
        matrix = state[source["source_id"]]
        _require(
            (matrix.rows, matrix.cols) == (source["rows"], source["cols"]),
            "E000_SOURCE_SHAPE",
            f"{source['source_id']}: provided matrix shape differs from recipe",
        )
        _require(sha256_hex(matrix.data) == source["sha256"], "E000_SOURCE_DIGEST", f"{source['source_id']}: source digest differs")

    transcript_steps: list[dict[str, Any]] = []
    for step in recipe["steps"]:
        step_id = step["step_id"]
        _require(step_id not in state, "E000_STEP_DUPLICATE", f"step id {step_id!r} is already defined")
        operation = step["op"]
        inputs: list[str]
        labels: list[str] | None = None
        if operation in {"slice_rows", "slice_columns", "select_row_ranges", "transpose"}:
            inputs = [step["input"]]
        else:
            inputs = list(step["inputs"])
        _require(all(item in state for item in inputs), "E000_STEP_INPUT", f"{step_id}: an input does not resolve")

        if operation == "slice_rows":
            result = state[inputs[0]].row_slice(step["start"], step["stop"])
        elif operation == "slice_columns":
            result = state[inputs[0]].column_slice(step["start"], step["stop"])
        elif operation == "select_row_ranges":
            source = state[inputs[0]]
            labels = [item["label"] for item in step["ranges"]]
            _require(len(labels) == len(set(labels)), "E000_FUSION_LABEL_DUPLICATE", f"{step_id}: row-range labels repeat")
            parts = [source.row_slice(item["start"], item["stop"]) for item in step["ranges"]]
            result = Int8Matrix.concat_rows(parts)
        elif operation == "transpose":
            result = state[inputs[0]].transpose()
        elif operation == "concat_rows":
            result = Int8Matrix.concat_rows([state[item] for item in inputs])
        elif operation == "stack_experts":
            expert_ids = step["expert_ids"]
            _require(len(expert_ids) == len(inputs), "E000_EXPERT_COUNT", f"{step_id}: expert IDs and inputs differ in length")
            _require(
                expert_ids == list(range(len(expert_ids))),
                "E000_EXPERT_ORDER",
                f"{step_id}: experts must be explicitly stacked in canonical 0..e-1 order",
            )
            result = Int8Matrix.concat_rows([state[item] for item in inputs])
        else:  # schema validation makes this unreachable
            raise ConformanceError("E000_OPERATION", f"unsupported operation {operation!r}")

        state[step_id] = result
        transcript_steps.append(
            {
                "step_id": step_id,
                "op": operation,
                "inputs": inputs,
                "labels": labels,
                "rows": result.rows,
                "cols": result.cols,
                "sha256": sha256_hex(result.data),
            }
        )

    output = recipe["output"]
    _require(output["matrix_id"] in state, "E000_OUTPUT_MISSING", "recipe output matrix does not resolve")
    matrix = state[output["matrix_id"]]
    _require(
        (matrix.rows, matrix.cols) == (output["expected_rows"], output["expected_cols"]),
        "E000_OUTPUT_SHAPE",
        f"recipe output is {matrix.rows}x{matrix.cols}, expected {output['expected_rows']}x{output['expected_cols']}",
    )
    canonical_recipe = json.dumps(recipe, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    transcript = {
        "schema_version": "aeye.e000-slab-transform-transcript.v0",
        "recipe_sha256": sha256_hex(canonical_recipe),
        "source_matrices": [
            {
                "source_id": source["source_id"],
                "rows": state[source["source_id"]].rows,
                "cols": state[source["source_id"]].cols,
                "sha256": sha256_hex(state[source["source_id"]].data),
            }
            for source in recipe["sources"]
        ],
        "steps": transcript_steps,
        "output": {
            "matrix_id": output["matrix_id"],
            "rows": matrix.rows,
            "cols": matrix.cols,
            "sha256": sha256_hex(matrix.data),
            "semantic_layout": output["semantic_layout"],
        },
        "claim_ceiling": "deterministic int8 byte transformation only; checkpoint provenance and runtime equivalence remain separate gates",
    }
    return matrix, transcript


def validate_slab_against_public_data(matrix: Int8Matrix, public_data: PublicProofDataV3) -> None:
    """Check only the native B^T shape implied by parsed V3 public data."""
    experts = public_data.mining_config.experts or 1
    expected_rows = public_data.n * experts
    expected_cols = public_data.mining_config.common_dim
    _require(
        (matrix.rows, matrix.cols) == (expected_rows, expected_cols),
        "E000_NATIVE_SLAB_SHAPE",
        f"runtime slab is {matrix.rows}x{matrix.cols}; V3 public data requires {expected_rows}x{expected_cols}",
    )


__all__ = ["Int8Matrix", "evaluate_recipe", "load_sources", "validate_slab_against_public_data"]
