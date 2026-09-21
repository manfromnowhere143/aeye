#!/usr/bin/env python3
"""Target-agnostic Pearl certificate-v3 byte conformance for Aeye E-000.

The module parses and round-trips the pinned INT certificate-v3 envelope, derives the
exact ``job_key``, and computes Pearl's keyed BLAKE3 matrix commitment in two separately
implemented lanes.  It deliberately contains no network retrieval, candidate selection,
checkpoint discovery, or live target-comparison command.  Those remain gated on the
reviewer freeze and explicit operator acceptance.

Passing these checks establishes parser and byte-path conformance only.  It does not
verify a Pearl proof or establish WORK, EXECUTION, SEMANTICS, or DEMAND.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from blake3 import blake3
except ImportError as exc:  # pragma: no cover - fail-closed environment guard
    raise SystemExit("missing dependency: install the hash-locked development requirements") from exc

try:
    from blake3_reference import digest as reference_blake3
    from blake3_reference import initial_chunk_chaining_values
except ImportError:  # imported through a file loader in tests
    _HERE = Path(__file__).resolve().parent
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    from blake3_reference import digest as reference_blake3
    from blake3_reference import initial_chunk_chaining_values


PEARL_COMMIT = "4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0"
CERTIFICATE_VERSION = 3
INCOMPLETE_HEADER_SIZE = 76
FULL_HEADER_SIZE = 108
MINING_CONFIG_SIZE = 52
PUBLIC_DATA_CORE_SIZE = 164
PUBLIC_DATA_MIN_MOE_SIZE = 199
PUBLIC_DATA_MAX_SIZE = 4807
MAX_PROOF_SIZE = 60_000
BLAKE3_CHUNK_SIZE = 1024
MAX_EXPERTS = 1024
MAX_OUTER_INDICES = 128
TILE_D = 16
TILE_H = 2
DWORD_SIZE = 8


class ConformanceError(ValueError):
    """Fail-closed protocol error carrying a stable diagnostic code."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ConformanceError(code, message)


def sha256_hex(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def double_sha256(value: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(value).digest()).digest()


@dataclass(frozen=True)
class PeriodicPattern:
    shape: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]

    @classmethod
    def parse(cls, raw: bytes) -> "PeriodicPattern":
        _require(
            len(raw) == 6,
            "E000_PATTERN_LENGTH",
            f"periodic pattern must be 6 bytes, got {len(raw)}",
        )
        shape: list[tuple[int, int]] = []
        minimum_stride = 1
        finished = False
        for offset in range(0, 6, 2):
            factor = raw[offset] + 1
            length = raw[offset + 1] + 1
            if length == 1 or finished:
                _require(
                    factor == 1 and length == 1,
                    "E000_PATTERN_NONCANONICAL",
                    "unused periodic-pattern dimensions must encode factor=1,length=1",
                )
                finished = True
            elif factor <= 1 and minimum_stride != 1:
                raise ConformanceError(
                    "E000_PATTERN_BROKEN_STRIDE",
                    "a single stride may not be broken across dimensions",
                )
            _require(
                minimum_stride <= (1 << 24) // (factor * length),
                "E000_PATTERN_PERIOD_OVERFLOW",
                "periodic-pattern period exceeds 2^24",
            )
            stride = factor * minimum_stride
            shape.append((stride, length))
            minimum_stride = stride * length
        result = cls(tuple(shape))  # type: ignore[arg-type]
        _require(
            result.to_bytes() == raw,
            "E000_PATTERN_ROUNDTRIP",
            "periodic pattern does not round-trip canonically",
        )
        return result

    def to_bytes(self) -> bytes:
        output = bytearray(6)
        minimum_stride = 1
        for index, (stride, length) in enumerate(self.shape):
            _require(
                minimum_stride > 0 and stride % minimum_stride == 0,
                "E000_PATTERN_INVALID_SHAPE",
                "stride is not an integral multiple of the prior period",
            )
            factor = stride // minimum_stride
            _require(
                1 <= factor <= 256 and 1 <= length <= 256,
                "E000_PATTERN_INVALID_SHAPE",
                "factor or length cannot be encoded in the six-byte pattern",
            )
            output[index * 2] = factor - 1
            output[index * 2 + 1] = length - 1
            minimum_stride = stride * length
        return bytes(output)

    @property
    def size(self) -> int:
        result = 1
        for _, length in self.shape:
            result *= length
        return result

    @property
    def maximum(self) -> int:
        return max(self.indices_with_offset(0))

    def indices_with_offset(self, offset: int) -> tuple[int, ...]:
        values = [0]
        for stride, length in self.shape:
            values = [base + multiplier * stride for multiplier in range(length) for base in values]
        return tuple(value + offset for value in values)

    def offset_is_valid(self, offset: int) -> bool:
        for stride, length in reversed(self.shape):
            offset %= stride * length
            if offset >= stride:
                return False
        return True


@dataclass(frozen=True)
class MiningConfiguration:
    common_dim: int
    rank: int
    mma_type: int
    rows_pattern: PeriodicPattern
    cols_pattern: PeriodicPattern
    experts: int | None
    top_k: int | None

    @classmethod
    def parse(cls, raw: bytes) -> "MiningConfiguration":
        _require(
            len(raw) == MINING_CONFIG_SIZE,
            "E000_MINING_CONFIG_LENGTH",
            f"mining configuration must be 52 bytes, got {len(raw)}",
        )
        common_dim, rank, mma_type = struct.unpack_from("<IHH", raw, 0)
        _require(
            mma_type == 0,
            "E000_MMA_TYPE",
            f"certificate-v3 INT lineage accepts MMA type 0, got {mma_type}",
        )
        rows = PeriodicPattern.parse(raw[8:14])
        cols = PeriodicPattern.parse(raw[14:20])
        experts, top_k = struct.unpack_from("<HH", raw, 20)
        _require(
            raw[24:52] == bytes(28),
            "E000_MINING_CONFIG_RESERVED",
            "reserved mining-configuration trailer bytes must be zero",
        )
        _require(
            experts != 0 or top_k == 0,
            "E000_MOE_DISCRIMINANT",
            "top_k must be zero when the expert count is zero",
        )
        result = cls(
            common_dim=common_dim,
            rank=rank,
            mma_type=mma_type,
            rows_pattern=rows,
            cols_pattern=cols,
            experts=experts or None,
            top_k=top_k if experts else None,
        )
        _require(
            result.to_bytes() == raw,
            "E000_MINING_CONFIG_ROUNDTRIP",
            "mining configuration does not round-trip canonically",
        )
        return result

    def to_bytes(self) -> bytes:
        trailer = bytearray(32)
        if self.experts is not None:
            _require(
                self.top_k is not None,
                "E000_MOE_DISCRIMINANT",
                "MoE configuration requires top_k",
            )
            struct.pack_into("<HH", trailer, 0, self.experts, self.top_k)
        return b"".join(
            (
                struct.pack("<IHH", self.common_dim, self.rank, self.mma_type),
                self.rows_pattern.to_bytes(),
                self.cols_pattern.to_bytes(),
                bytes(trailer),
            )
        )

    @property
    def dot_product_length(self) -> int:
        _require(self.rank != 0, "E000_RANK_ZERO", "rank cannot be zero")
        return self.common_dim - self.common_dim % self.rank


@dataclass(frozen=True)
class IncompleteBlockHeader:
    version: int
    prev_block_display_order: bytes
    merkle_root_display_order: bytes
    timestamp: int
    nbits: int

    @classmethod
    def parse(cls, raw: bytes) -> "IncompleteBlockHeader":
        _require(
            len(raw) == INCOMPLETE_HEADER_SIZE,
            "E000_HEADER_LENGTH",
            f"incomplete block header must be 76 bytes, got {len(raw)}",
        )
        version = struct.unpack_from("<I", raw, 0)[0]
        timestamp, nbits = struct.unpack_from("<II", raw, 68)
        result = cls(
            version=version,
            prev_block_display_order=raw[4:36][::-1],
            merkle_root_display_order=raw[36:68][::-1],
            timestamp=timestamp,
            nbits=nbits,
        )
        _require(
            result.to_bytes() == raw,
            "E000_HEADER_ROUNDTRIP",
            "incomplete header does not round-trip exactly",
        )
        return result

    def to_bytes(self) -> bytes:
        _require(
            len(self.prev_block_display_order) == 32 and len(self.merkle_root_display_order) == 32,
            "E000_HEADER_HASH_LENGTH",
            "header hashes must be 32 bytes",
        )
        return b"".join(
            (
                struct.pack("<I", self.version),
                self.prev_block_display_order[::-1],
                self.merkle_root_display_order[::-1],
                struct.pack("<II", self.timestamp, self.nbits),
            )
        )


@dataclass(frozen=True)
class BlockHeader:
    incomplete: IncompleteBlockHeader
    proof_commitment: bytes
    raw: bytes

    @classmethod
    def parse(cls, raw: bytes) -> "BlockHeader":
        _require(
            len(raw) == FULL_HEADER_SIZE,
            "E000_FULL_HEADER_LENGTH",
            f"full block header must be 108 bytes, got {len(raw)}",
        )
        result = cls(
            incomplete=IncompleteBlockHeader.parse(raw[:INCOMPLETE_HEADER_SIZE]),
            proof_commitment=raw[INCOMPLETE_HEADER_SIZE:],
            raw=raw,
        )
        _require(
            result.to_bytes() == raw,
            "E000_FULL_HEADER_ROUNDTRIP",
            "full header does not round-trip exactly",
        )
        return result

    def to_bytes(self) -> bytes:
        _require(
            len(self.proof_commitment) == 32,
            "E000_PROOF_COMMITMENT_LENGTH",
            "proof commitment must be 32 bytes",
        )
        return self.incomplete.to_bytes() + self.proof_commitment

    @property
    def block_hash(self) -> bytes:
        return double_sha256(self.raw)


@dataclass(frozen=True)
class MoEPublicData:
    expert_index: int
    routing_offsets: tuple[int, ...]
    hash_routing: bytes
    outer_indices: tuple[int, ...]


@dataclass(frozen=True)
class PublicProofDataV3:
    mining_config: MiningConfiguration
    hash_a: bytes
    hash_b: bytes
    hash_jackpot: bytes
    m: int
    n: int
    t_rows: int
    t_cols: int
    moe: MoEPublicData | None
    raw: bytes

    @classmethod
    def parse(cls, raw: bytes) -> "PublicProofDataV3":
        _require(
            len(raw) == PUBLIC_DATA_CORE_SIZE
            or PUBLIC_DATA_MIN_MOE_SIZE <= len(raw) <= PUBLIC_DATA_MAX_SIZE,
            "E000_PUBLIC_DATA_LENGTH",
            f"invalid certificate-v3 public_data length {len(raw)}",
        )
        config = MiningConfiguration.parse(raw[:MINING_CONFIG_SIZE])
        m, n, t_rows, t_cols = struct.unpack_from("<IIII", raw, 148)

        moe: MoEPublicData | None = None
        if len(raw) == PUBLIC_DATA_CORE_SIZE:
            _require(
                config.experts is None,
                "E000_MOE_TAIL_MISSING",
                "GROUPED_GEMM mining configuration requires an MoE public-data tail",
            )
        else:
            _require(
                config.experts is not None and config.top_k is not None,
                "E000_MOE_TAIL_UNEXPECTED",
                "MoE public-data tail requires a GROUPED_GEMM mining configuration",
            )
            experts = config.experts
            _require(
                experts <= MAX_EXPERTS,
                "E000_MOE_EXPERT_LIMIT",
                f"expert count {experts} exceeds {MAX_EXPERTS}",
            )
            minimum_length = PUBLIC_DATA_MIN_MOE_SIZE + 4 * experts
            _require(
                len(raw) >= minimum_length,
                "E000_MOE_TAIL_TRUNCATED",
                f"MoE public data needs at least {minimum_length} bytes",
            )
            cursor = PUBLIC_DATA_CORE_SIZE
            expert_index = struct.unpack_from("<H", raw, cursor)[0]
            cursor += 2
            routing_offsets = struct.unpack_from(f"<{experts}I", raw, cursor)
            cursor += 4 * experts
            hash_routing = raw[cursor : cursor + 32]
            cursor += 32
            outer_count = raw[cursor]
            cursor += 1
            _require(
                outer_count <= MAX_OUTER_INDICES,
                "E000_MOE_OUTER_LIMIT",
                f"outer-index count {outer_count} exceeds {MAX_OUTER_INDICES}",
            )
            expected_length = cursor + 4 * outer_count
            _require(
                len(raw) == expected_length,
                "E000_MOE_TAIL_LENGTH",
                f"MoE public data must be {expected_length} bytes, got {len(raw)}",
            )
            outer_indices = struct.unpack_from(f"<{outer_count}I", raw, cursor)
            moe = MoEPublicData(
                expert_index=expert_index,
                routing_offsets=tuple(routing_offsets),
                hash_routing=hash_routing,
                outer_indices=tuple(outer_indices),
            )

        result = cls(
            mining_config=config,
            hash_a=raw[52:84],
            hash_b=raw[84:116],
            hash_jackpot=raw[116:148],
            m=m,
            n=n,
            t_rows=t_rows,
            t_cols=t_cols,
            moe=moe,
            raw=raw,
        )
        result._sanity_check()
        _require(
            result.to_bytes() == raw,
            "E000_PUBLIC_DATA_ROUNDTRIP",
            "certificate-v3 public data does not round-trip exactly",
        )
        return result

    def _sanity_check(self) -> None:
        config = self.mining_config
        k = config.common_dim
        rank = config.rank
        h = config.rows_pattern.size
        w = config.cols_pattern.size
        dot_product_length = config.dot_product_length

        _require(
            rank != 0 and rank & (rank - 1) == 0 and 32 <= rank <= 1024,
            "E000_RANK_RANGE",
            f"rank must be a power of two in 32..1024, got {rank}",
        )
        _require(rank % TILE_D == 0, "E000_RANK_TILE", f"rank {rank} is not divisible by {TILE_D}")
        _require(k <= 1 << 16, "E000_COMMON_DIM_MAX", f"common dimension {k} exceeds 2^16")
        _require(k % 64 == 0, "E000_COMMON_DIM_ALIGNMENT", f"common dimension {k} is not divisible by 64")
        _require(k <= 4 * rank * rank, "E000_COMMON_DIM_RANK_MAX", "common dimension exceeds 4r^2")
        _require(k >= 16 * rank, "E000_COMMON_DIM_RANK_MIN", "common dimension is below 16r")
        _require(k >= 1024, "E000_COMMON_DIM_COLLISION", "common dimension is below 1024")
        _require(h % TILE_H == 0 and w % TILE_H == 0, "E000_PATTERN_TILE", "pattern sizes must be divisible by 2")
        _require(32 <= h * w <= 256, "E000_INNER_HASH_SIZE", f"pattern product must be 32..256, got {h * w}")
        _require(dot_product_length % DWORD_SIZE == 0, "E000_DOT_ALIGNMENT", "dot-product length is not dword aligned")
        _require(self.m <= 1 << 24 and self.n <= 1 << 24, "E000_MATRIX_DIM_MAX", "matrix dimension exceeds 2^24")
        _require((h + w) * dot_product_length <= 1 << 22, "E000_WORKER_INPUT_MAX", "worker input exceeds 4 MiB")
        _require(self.t_rows + config.rows_pattern.maximum < self.m, "E000_T_ROWS_RANGE", "row pattern exceeds matrix A")
        _require(self.t_cols + config.cols_pattern.maximum < self.n, "E000_T_COLS_RANGE", "column pattern exceeds matrix B")
        _require(config.rows_pattern.offset_is_valid(self.t_rows), "E000_T_ROWS_OFFSET", "t_rows is not a valid pattern offset")
        _require(config.cols_pattern.offset_is_valid(self.t_cols), "E000_T_COLS_OFFSET", "t_cols is not a valid pattern offset")

        if self.moe is None:
            _require(config.experts is None, "E000_MOE_PRESENCE", "MoE configuration/tail presence differs")
            return

        _require(
            config.experts is not None and config.top_k is not None,
            "E000_MOE_PRESENCE",
            "MoE configuration/tail presence differs",
        )
        experts, top_k = config.experts, config.top_k
        _require(experts > 0, "E000_MOE_EXPERTS_ZERO", "MoE expert count must be positive")
        _require(0 < top_k < experts, "E000_MOE_TOP_K", "top_k must be positive and below expert count")
        _require(self.moe.expert_index < experts, "E000_MOE_EXPERT_INDEX", "expert index is out of range")
        _require(len(self.moe.routing_offsets) == experts, "E000_MOE_ROUTING_COUNT", "routing-offset count differs from expert count")
        total_routing = self.m * top_k
        _require(total_routing < 1 << 32, "E000_MOE_ROUTING_OVERFLOW", "m*top_k does not fit u32")
        _require(self.moe.routing_offsets[-1] == total_routing, "E000_MOE_ROUTING_TOTAL", "last routing offset differs from m*top_k")
        _require(
            all(left <= right for left, right in zip(self.moe.routing_offsets, self.moe.routing_offsets[1:])),
            "E000_MOE_ROUTING_ORDER",
            "routing offsets are not monotone",
        )
        _require(
            self.moe.routing_offsets[0] <= self.m
            and all(right - left <= self.m for left, right in zip(self.moe.routing_offsets, self.moe.routing_offsets[1:])),
            "E000_MOE_ROUTING_SPAN",
            "an expert routing span exceeds m",
        )
        _require(self.n * experts <= 1 << 24, "E000_MOE_TOTAL_N", "total expert columns exceed 2^24")
        inner_indices = config.rows_pattern.indices_with_offset(self.t_rows)
        expert_start = 0 if self.moe.expert_index == 0 else self.moe.routing_offsets[self.moe.expert_index - 1]
        expert_stop = self.moe.routing_offsets[self.moe.expert_index]
        _require(
            all(expert_start + inner < total_routing for inner in inner_indices),
            "E000_MOE_ROUTING_PADDING",
            "a sampled routing index falls in the padded region",
        )
        _require(
            all(expert_start + inner < expert_stop for inner in inner_indices),
            "E000_MOE_ROUTING_EXPERT",
            "a sampled routing index falls in the next expert region",
        )
        _require(
            len(self.moe.outer_indices) == len(inner_indices),
            "E000_MOE_OUTER_COUNT",
            "outer-index count differs from the sampled A-row count",
        )
        _require(
            all(left < right for left, right in zip(self.moe.outer_indices, self.moe.outer_indices[1:])),
            "E000_MOE_OUTER_ORDER",
            "outer indices are not strictly increasing",
        )
        _require(all(index < self.m for index in self.moe.outer_indices), "E000_MOE_OUTER_RANGE", "outer index exceeds m")

    def to_bytes(self) -> bytes:
        output = bytearray(PUBLIC_DATA_CORE_SIZE)
        output[:52] = self.mining_config.to_bytes()
        output[52:84] = self.hash_a
        output[84:116] = self.hash_b
        output[116:148] = self.hash_jackpot
        struct.pack_into("<IIII", output, 148, self.m, self.n, self.t_rows, self.t_cols)
        if self.moe is not None:
            output.extend(struct.pack("<H", self.moe.expert_index))
            output.extend(struct.pack(f"<{len(self.moe.routing_offsets)}I", *self.moe.routing_offsets))
            output.extend(self.moe.hash_routing)
            output.append(len(self.moe.outer_indices))
            output.extend(struct.pack(f"<{len(self.moe.outer_indices)}I", *self.moe.outer_indices))
        return bytes(output)

    def job_key(self, header: IncompleteBlockHeader) -> bytes:
        preimage = header.to_bytes() + self.mining_config.to_bytes()
        primary = blake3(preimage).digest()
        reference = reference_blake3(preimage)
        _require(
            primary == reference,
            "E000_JOB_KEY_ENGINE_DIVERGENCE",
            "primary and reference BLAKE3 lanes disagree on job_key",
        )
        return primary


@dataclass(frozen=True)
class CertificateV3:
    header_hash: bytes
    public_data: PublicProofDataV3
    proof_data: bytes
    raw: bytes

    @classmethod
    def parse(cls, raw: bytes) -> "CertificateV3":
        _require(len(raw) >= 44, "E000_CERTIFICATE_TRUNCATED", "certificate is shorter than its fixed envelope")
        version = struct.unpack_from("<I", raw, 0)[0]
        _require(
            version == CERTIFICATE_VERSION,
            "E000_CERTIFICATE_VERSION",
            f"expected certificate version 3, got {version}",
        )
        public_length = struct.unpack_from("<I", raw, 36)[0]
        _require(public_length <= PUBLIC_DATA_MAX_SIZE, "E000_PUBLIC_DATA_MAX", "public_data exceeds 4,807 bytes")
        public_start = 40
        public_end = public_start + public_length
        _require(len(raw) >= public_end + 4, "E000_CERTIFICATE_TRUNCATED", "certificate ends inside public_data")
        proof_length = struct.unpack_from("<I", raw, public_end)[0]
        _require(proof_length <= MAX_PROOF_SIZE, "E000_PROOF_SIZE", "proof_data exceeds 60,000 bytes")
        expected_length = public_end + 4 + proof_length
        _require(
            len(raw) == expected_length,
            "E000_CERTIFICATE_LENGTH",
            f"certificate envelope declares {expected_length} bytes, got {len(raw)}",
        )
        result = cls(
            header_hash=raw[4:36],
            public_data=PublicProofDataV3.parse(raw[public_start:public_end]),
            proof_data=raw[public_end + 4 :],
            raw=raw,
        )
        _require(result.to_bytes() == raw, "E000_CERTIFICATE_ROUNDTRIP", "certificate does not round-trip exactly")
        return result

    def to_bytes(self) -> bytes:
        public = self.public_data.to_bytes()
        return b"".join(
            (
                struct.pack("<I", CERTIFICATE_VERSION),
                self.header_hash,
                struct.pack("<I", len(public)),
                public,
                struct.pack("<I", len(self.proof_data)),
                self.proof_data,
            )
        )

    @property
    def proof_commitment(self) -> bytes:
        return double_sha256(struct.pack("<I", CERTIFICATE_VERSION) + self.public_data.raw)


def verify_header_certificate_binding(header: BlockHeader, certificate: CertificateV3) -> None:
    _require(
        certificate.header_hash == header.block_hash,
        "E000_CERTIFICATE_BLOCK_HASH",
        "certificate header hash does not match the double-SHA256 block header",
    )
    _require(
        certificate.proof_commitment == header.proof_commitment,
        "E000_CERTIFICATE_PROOF_COMMITMENT",
        "certificate public data does not match the header proof commitment",
    )


def pad_to_chunk_boundary(raw: bytes) -> bytes:
    _require(bool(raw), "E000_EMPTY_SLAB", "Pearl matrix commitments require a non-empty slab")
    padded_length = ((len(raw) + BLAKE3_CHUNK_SIZE - 1) // BLAKE3_CHUNK_SIZE) * BLAKE3_CHUNK_SIZE
    return raw.ljust(padded_length, b"\x00")


def matrix_commitment_transcript(raw: bytes, job_key: bytes) -> dict[str, Any]:
    _require(len(job_key) == 32, "E000_JOB_KEY_LENGTH", f"job_key must be 32 bytes, got {len(job_key)}")
    padded = pad_to_chunk_boundary(raw)
    primary_root = blake3(padded, key=job_key).digest()
    reference_root = reference_blake3(padded, key=job_key)
    _require(
        primary_root == reference_root,
        "E000_MATRIX_ROOT_ENGINE_DIVERGENCE",
        "primary and reference BLAKE3 lanes disagree on the matrix root",
    )
    chunks = [padded[offset : offset + BLAKE3_CHUNK_SIZE] for offset in range(0, len(padded), BLAKE3_CHUNK_SIZE)]
    reference_cvs = initial_chunk_chaining_values(padded, key=job_key)
    return {
        "schema_version": "aeye.e000-matrix-commitment-transcript.v0",
        "protocol": {
            "pearl_commit": PEARL_COMMIT,
            "certificate_version": CERTIFICATE_VERSION,
            "hash": "BLAKE3-256 keyed",
            "chunk_bytes": BLAKE3_CHUNK_SIZE,
        },
        "input": {
            "raw_bytes": len(raw),
            "raw_sha256": sha256_hex(raw),
            "padded_bytes": len(padded),
            "padded_sha256": sha256_hex(padded),
            "zero_padding_bytes": len(padded) - len(raw),
            "leaf_count": len(chunks),
            "chunk_sha256": [sha256_hex(chunk) for chunk in chunks],
        },
        "job_key_hex": job_key.hex(),
        "reference_chunk_cv_hex": [value.hex() for value in reference_cvs],
        "primary_root_hex": primary_root.hex(),
        "reference_root_hex": reference_root.hex(),
        "engines_agree": True,
        "claim_ceiling": "byte-path conformance only; no Pearl proof or Aeye claim coordinate is verified",
    }


def _self_test() -> dict[str, Any]:
    empty_expected = bytes.fromhex("af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262")
    empty_primary = blake3(b"").digest()
    empty_reference = reference_blake3(b"")
    _require(empty_primary == empty_expected, "E000_PRIMARY_BLAKE3_VECTOR", "optimized BLAKE3 failed the empty vector")
    _require(empty_reference == empty_expected, "E000_REFERENCE_BLAKE3_VECTOR", "reference BLAKE3 failed the empty vector")

    key = bytes(range(32))
    slab = bytes((index * 73 + 19) % 256 for index in range(3 * BLAKE3_CHUNK_SIZE + 17))
    transcript = matrix_commitment_transcript(slab, key)
    return {
        "schema_version": "aeye.e000-conformance-self-test.v0",
        "status": "synthetic_conformance_only",
        "pearl_commit": PEARL_COMMIT,
        "certificate_version": CERTIFICATE_VERSION,
        "optimized_and_reference_blake3_agree": transcript["engines_agree"],
        "synthetic_root_hex": transcript["primary_root_hex"],
        "candidate_inspected": False,
        "live_target_comparison_available": False,
        "claim_ceiling": "parser/hash instrument self-test; not an E-000 result",
    }


def main() -> int:
    try:
        print(json.dumps(_self_test(), indent=2, sort_keys=True))
    except ConformanceError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "message": exc.message}, indent=2, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
