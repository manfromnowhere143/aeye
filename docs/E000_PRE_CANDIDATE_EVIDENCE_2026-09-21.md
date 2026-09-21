# E-000 Pre-candidate Evidence Record

Status: owner observations and same-workstation machine review; E-000 remains `blocked`  
Date: 2026-09-21  
Candidate, certificate, and `hash_b` inspected: **no**

## Purpose

E-000 asks whether one future-selected Pearl certificate-v3 `hash_b` can be opened from
public checkpoint bytes without trusting a miner-supplied tensor. This record separates
the pre-candidate engineering evidence now available from the result that does not yet
exist.

## Source-derived static scope

For the pinned `pearl-ai/Llama-3.1-8B-Instruct-pearl` revision, the owner derived 5,040
positional static layouts over tensor-parallel degrees `{1,2,4,8,16,32}`. Applying only
the candidate-independent `n` and `k` thresholds leaves 3,248 layouts:

| Family | Dimension-prequalified layouts |
|---|---:|
| `gate_up_proj` | 2,016 |
| `qkv_proj` | 1,008 |
| `o_proj` | 224 |
| Total | 3,248 |

The remaining 1,792 layouts are `o_proj` cases whose static dimensions fall below the
pinned threshold at TP 8, 16, or 32. The runtime `m` dimension is candidate-dependent and
is not part of static registry coverage. It must be evaluated separately after reveal.

Therefore the finite byte-coverage predicate is based on `(n,k)`. A true runtime
dimension predicate is necessary for mining eligibility, but it cannot establish that a
live miner used the registered bytes or runtime path.

A Python compiler and a separately authored Rust compiler read the same retained T0 I8
tensor extractions and produced equal identities, shapes, source bindings, byte lengths,
and unkeyed SHA-256 values for all 3,248 layouts. This is code-path agreement on one
workstation and one source interpretation, not independent validation.

## MC1 real-byte calibration

MC1 fixed its selection rule before computing a keyed root. It selected one slab from
each distinct `(family,n,k)` class of the reviewed registry, 15 classes in total.

| Observation | Retained value |
|---|---:|
| Selected classes | 15 / 15 |
| `gate_up_proj` / `o_proj` / `qkv_proj` | 6 / 3 / 6 |
| Raw slab bytes processed per owner lane | 311,427,072 |
| Python and Rust slab identities equal | 15 / 15 |
| Python, Rust, and pinned Pearl keyed roots equal | 15 / 15 |
| Signed-I8 byte mapping control | pass |
| Preregistered one-bit mutation | changed the byte identity and keyed root |
| Post-hoc comparator mutations | 9 / 9 rejected |

The frozen key is synthetic, public, and explicitly not a candidate `job_key`. All 15
slabs were already aligned to Pearl's 1,024-byte tree chunk, so this result does not test
nonzero real-byte padding. Synthetic conformance vectors test padding separately.

The exact source and retained outputs are in the
[MC1 packet](../experiments/e-000/mc1/README.md). A clean locked-environment owner replay
reproduced the three result files byte-for-byte. The public packet binds the checkpoint
revision, shard streams, extraction receipts, and registry by digest. It does not retain
the checkpoint payload, tensor-extraction bundles, or exact extraction receipts, so a
fresh clone alone cannot reproduce the real-byte run.

Maximum MC1 claim: for the 15 preregistered 8B classes, two owner implementations
reconstructed equal byte identities and Python, Rust, and pinned Pearl code produced
equal keyed roots under the frozen synthetic key.

MC1 does not establish a candidate opening, `hash_b` equality, source independence,
runtime participation, inference, an Aeye coordinate, performance, security, or
independent validation.

## Transport-calibration failure

The first and only capture allowed by the frozen exporter-calibration plan ended with
exit code `1` and typed outcome `EARLY_EOF_BEFORE_CONTENT_LENGTH`. It created no success
receipt. The plan made any first-capture failure terminal, so the second capture and
comparator did not run. There was no retry under the owner-observed procedure.

The frozen implementation did not emit a failure receipt. Exact logical prefix length
and prefix digest are therefore unknown, and an operating-system network counter is not
substituted for either. The public projection is retained as
[`calibration-terminal-observation-v0.json`](../experiments/e-000/artifacts/calibration-terminal-observation-v0.json).

This is a terminal negative engineering result, not a near-pass. It establishes no route
tier or adapter equivalence. The no-retry statement is procedural owner evidence, not a
cryptographic proof of process absence.

## Source-assurance correction under review

The failed transfer prompted a more important candidate-blind question: what scientific
claim does a second delivery of the same publisher-digested object add?

The owner analysis concludes that it adds availability and diagnostic evidence, but no
new byte-identity or source-provenance statement. A malicious or mistaken publisher can
serve one self-consistent wrong object through two routes. A parser error survives two
routes. An incorrect checkpoint transformation survives two routes. Different TLS
sessions, hosts, AS numbers, or registrants do not alter those facts.

[ADR-0015](decisions/0015-source-assurance-requires-independent-derivation.md) therefore
proposes two explicit classes:

- `S0_PUBLISHER_ASSOCIATED`, one complete content-addressed source with the
  single-publisher assumption disclosed;
- `S1_INDEPENDENTLY_DERIVED`, exact byte reproduction from separately pinned upstream
  material through a frozen recipe and separate implementation.

The proposal has not replaced ADR-0014. The active E-000 manifest is immutable, still
requires its current gate, and remains blocked. If the source-assurance correction
survives adversarial review, it requires an `E-000-R2` manifest and a fresh freeze. No
prior acceptance state may transfer.

## Current phase state

| Item | Status | Authority ceiling |
|---|---|---|
| V3 parser, `job_key`, tree, and seed conformance | implemented and tested on synthetic vectors | protocol conformance only |
| Static 8B layout derivation | owner observed; same-workstation review with amendments | source-derived layout description |
| 3,248-layout cross-language byte identities | owner observed | code-path agreement on shared T0 inputs |
| MC1 15-class keyed-root parity | owner result awaiting adversarial readback | pre-candidate calibration only |
| Exporter calibration | terminal failure | failure observation only |
| Source-assurance replacement | proposed | no active protocol effect |
| Candidate selection | forbidden | no candidate information inspected |
| E-000 outcome | absent | no `MATCH` or other terminal classification |

## Claim ceiling

The strongest result in this record is real-byte calibration of the public-checkpoint to
Pearl keyed-tree path under a synthetic key. It closes a byte-path engineering question.
It does not close E-000's native mainnet question, and it does not establish any of
`WORK`, `EXECUTION`, `SEMANTICS`, or `DEMAND`.
