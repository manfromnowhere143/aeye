#!/usr/bin/env python3
"""Small, independent BLAKE3 reference lane for E-000 conformance checks.

This module intentionally does not import Aeye's primary conformance implementation or
the optimized ``blake3`` package.  It implements only the fixed 32-byte hash needed by
E-000.  It is a cross-checking instrument, not a production cryptographic library or an
independent security review.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


OUT_LEN = 32
BLOCK_LEN = 64
CHUNK_LEN = 1024

CHUNK_START = 1 << 0
CHUNK_END = 1 << 1
PARENT = 1 << 2
ROOT = 1 << 3
KEYED_HASH = 1 << 4

_MASK32 = (1 << 32) - 1
_IV = (
    0x6A09E667,
    0xBB67AE85,
    0x3C6EF372,
    0xA54FF53A,
    0x510E527F,
    0x9B05688C,
    0x1F83D9AB,
    0x5BE0CD19,
)
_MSG_PERMUTATION = (2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8)


def _rotate_right(value: int, count: int) -> int:
    return ((value >> count) | ((value << (32 - count)) & _MASK32)) & _MASK32


def _g(state: list[int], a: int, b: int, c: int, d: int, mx: int, my: int) -> None:
    state[a] = (state[a] + state[b] + mx) & _MASK32
    state[d] = _rotate_right(state[d] ^ state[a], 16)
    state[c] = (state[c] + state[d]) & _MASK32
    state[b] = _rotate_right(state[b] ^ state[c], 12)
    state[a] = (state[a] + state[b] + my) & _MASK32
    state[d] = _rotate_right(state[d] ^ state[a], 8)
    state[c] = (state[c] + state[d]) & _MASK32
    state[b] = _rotate_right(state[b] ^ state[c], 7)


def _round(state: list[int], message: Sequence[int]) -> None:
    _g(state, 0, 4, 8, 12, message[0], message[1])
    _g(state, 1, 5, 9, 13, message[2], message[3])
    _g(state, 2, 6, 10, 14, message[4], message[5])
    _g(state, 3, 7, 11, 15, message[6], message[7])
    _g(state, 0, 5, 10, 15, message[8], message[9])
    _g(state, 1, 6, 11, 12, message[10], message[11])
    _g(state, 2, 7, 8, 13, message[12], message[13])
    _g(state, 3, 4, 9, 14, message[14], message[15])


def _permute(message: Sequence[int]) -> tuple[int, ...]:
    return tuple(message[index] for index in _MSG_PERMUTATION)


def _words_from_bytes(value: bytes, expected_words: int) -> tuple[int, ...]:
    if len(value) != expected_words * 4:
        raise ValueError(f"expected {expected_words * 4} bytes, got {len(value)}")
    return tuple(
        int.from_bytes(value[offset : offset + 4], "little")
        for offset in range(0, len(value), 4)
    )


def _words_to_bytes(words: Iterable[int]) -> bytes:
    return b"".join((word & _MASK32).to_bytes(4, "little") for word in words)


def _compress(
    chaining_value: Sequence[int],
    block_words: Sequence[int],
    counter: int,
    block_length: int,
    flags: int,
) -> tuple[int, ...]:
    if len(chaining_value) != 8 or len(block_words) != 16:
        raise ValueError("invalid BLAKE3 compression input width")
    if not 0 <= counter < 1 << 64:
        raise ValueError("counter must fit u64")
    if not 0 <= block_length <= BLOCK_LEN:
        raise ValueError("block length must be in 0..64")

    state = [
        *chaining_value,
        *_IV[:4],
        counter & _MASK32,
        (counter >> 32) & _MASK32,
        block_length,
        flags,
    ]
    message = tuple(block_words)
    for round_index in range(7):
        _round(state, message)
        if round_index != 6:
            message = _permute(message)

    return tuple(
        [state[index] ^ state[index + 8] for index in range(8)]
        + [state[index + 8] ^ chaining_value[index] for index in range(8)]
    )


@dataclass(frozen=True)
class _Output:
    input_chaining_value: tuple[int, ...]
    block_words: tuple[int, ...]
    counter: int
    block_length: int
    flags: int

    def chaining_value(self) -> tuple[int, ...]:
        return _compress(
            self.input_chaining_value,
            self.block_words,
            self.counter,
            self.block_length,
            self.flags,
        )[:8]

    def root_bytes(self) -> bytes:
        # E-000 needs only the first 32 bytes of BLAKE3's extendable output.
        words = _compress(
            self.input_chaining_value,
            self.block_words,
            0,
            self.block_length,
            self.flags | ROOT,
        )
        return _words_to_bytes(words)[:OUT_LEN]


def _block_words(block: bytes) -> tuple[int, ...]:
    if len(block) > BLOCK_LEN:
        raise ValueError("BLAKE3 block exceeds 64 bytes")
    return _words_from_bytes(block.ljust(BLOCK_LEN, b"\x00"), 16)


def _chunk_output(
    chunk: bytes,
    chunk_counter: int,
    key_words: tuple[int, ...],
    flags: int,
) -> _Output:
    if len(chunk) > CHUNK_LEN:
        raise ValueError("BLAKE3 chunk exceeds 1024 bytes")

    blocks = [chunk[offset : offset + BLOCK_LEN] for offset in range(0, len(chunk), BLOCK_LEN)]
    if not blocks:
        blocks = [b""]

    chaining_value = key_words
    final_output: _Output | None = None
    for block_index, block in enumerate(blocks):
        block_flags = flags
        if block_index == 0:
            block_flags |= CHUNK_START
        if block_index == len(blocks) - 1:
            block_flags |= CHUNK_END
        final_output = _Output(
            input_chaining_value=chaining_value,
            block_words=_block_words(block),
            counter=chunk_counter,
            block_length=len(block),
            flags=block_flags,
        )
        if block_index != len(blocks) - 1:
            chaining_value = final_output.chaining_value()

    assert final_output is not None
    return final_output


def _parent_output(
    left: Sequence[int],
    right: Sequence[int],
    key_words: tuple[int, ...],
    flags: int,
) -> _Output:
    return _Output(
        input_chaining_value=key_words,
        block_words=tuple(left) + tuple(right),
        counter=0,
        block_length=BLOCK_LEN,
        flags=flags | PARENT,
    )


def _mode(key: bytes | None) -> tuple[tuple[int, ...], int]:
    if key is None:
        return _IV, 0
    if len(key) != OUT_LEN:
        raise ValueError(f"BLAKE3 keyed mode requires 32 bytes, got {len(key)}")
    return _words_from_bytes(key, 8), KEYED_HASH


def initial_chunk_chaining_values(data: bytes, key: bytes | None = None) -> tuple[bytes, ...]:
    """Return the non-root chaining value for each initial 1,024-byte chunk."""
    key_words, flags = _mode(key)
    chunks = [data[offset : offset + CHUNK_LEN] for offset in range(0, len(data), CHUNK_LEN)]
    if not chunks:
        chunks = [b""]
    return tuple(
        _words_to_bytes(_chunk_output(chunk, index, key_words, flags).chaining_value())
        for index, chunk in enumerate(chunks)
    )


def digest(data: bytes, key: bytes | None = None) -> bytes:
    """Compute a 32-byte unkeyed or keyed BLAKE3 digest."""
    key_words, flags = _mode(key)
    chunks = [data[offset : offset + CHUNK_LEN] for offset in range(0, len(data), CHUNK_LEN)]
    if not chunks:
        chunks = [b""]

    chunk_outputs = [
        _chunk_output(chunk, chunk_counter, key_words, flags)
        for chunk_counter, chunk in enumerate(chunks)
    ]
    if len(chunk_outputs) == 1:
        return chunk_outputs[0].root_bytes()

    level = [output.chaining_value() for output in chunk_outputs]
    while len(level) > 2:
        next_level: list[tuple[int, ...]] = []
        for offset in range(0, len(level), 2):
            if offset + 1 == len(level):
                next_level.append(level[offset])
            else:
                next_level.append(
                    _parent_output(
                        level[offset], level[offset + 1], key_words, flags
                    ).chaining_value()
                )
        level = next_level

    return _parent_output(level[0], level[1], key_words, flags).root_bytes()


__all__ = ["BLOCK_LEN", "CHUNK_LEN", "OUT_LEN", "digest", "initial_chunk_chaining_values"]
