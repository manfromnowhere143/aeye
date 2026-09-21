# E-000 Acceptance Checklist — reviewer freeze before candidate selection

Status: `proposed`, reviewer-owned, frozen before any candidate, certificate, `hash_b`, or
checkpoint was inspected  
Date: 2026-09-21T05:42:23Z  
Reviewer role: adversarial preregistration reviewer, same workstation, machine review  
Machine-readable twin: [`experiments/e-000/reviewer-freeze.json`](../experiments/e-000/reviewer-freeze.json)  
Pearl pin: `4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0`, verified at `evidence/external/pearl`

> This document is same-workstation machine adversarial review. It fixes ordering and
> criteria before an outcome exists. It is not independent validation, not peer review,
> and not operator acceptance. Its verdict does not move E-000 from `proposed`.

## Verdict

**ACCEPT_WITH_AMENDMENTS.** The present manifest states the right question and several
correct failure conditions, but it does not yet fix a candidate-selection rule, a finality
rule, the actual certificate-v3 code route, the dense-only scope, a sealed-reveal order, the
`BLOCKED`/`INVALID` terminal states, or an independence standard. One retained control is
mis-scoped. Every required amendment is listed in section K and in the JSON twin. Until all
of them are applied and operator-accepted with a record citing this freeze's SHA-256, the
standing verdict for the unamended manifest is **REJECT**.

## Version-route adjudication (prerequisite to acceptance)

`observed`, from the pinned checkout:

| Question | Finding | Source |
|---|---|---|
| Does `CertificateV3` use the V1 fixed-size body? | No. It embeds `CertificateV2`: `BlockHash(32) | PublicDataLen(4 LE) | PublicData | ProofLen(4 LE) | ProofData`. Only `Version()` and `ProofCommitment()` are overridden. | `node/wire/certificate_v3.go:12-24`, `certificate_v2.go:14-46` |
| Which Rust path verifies V3? | `verifyCertificateV3 → VerifyZKProofFFI → verify_zk_proof_v3`. V1 goes to `verify_zk_proof_v1`. | `node/zkpow/verify.go:38-52, 126-141` |
| Which seed derivation? | `CertificateVersion::ZkV3 → SeedDerivation::Salted`; `ZkDense`/`ZkMoe → Legacy`. | `zk-pow/src/ffi/plain_proof.rs:158-178` |
| Is `zk-pow/src/v1` the V3 path? | No. It is the legacy V1 ("master") verifier kept for compatibility. | `zk-pow/src/v1/compat_test.rs:1-3` |
| Is V3 public data exactly 164 bytes? | Only for dense proofs (`WIRE_SIZE = 164`). MoE is variable: `199 + 4·e + 4·outer_count`, bounded by `MAX_WIRE_SIZE`. | `zk-pow/src/api/proof_utils.rs:1143-1165` |
| Does salting change `hash_b`? | No. Salting alters the noise-seed chain (`commitment_hash`); the wire carries raw roots. | `zk-pow/src/api/seed.rs:1-25`, `proof_utils.rs:362-375` |
| Can a MoE V3 certificate exist on mainnet at the pin? | No. V3 is required from height 99000; MoE is rejected from height 91630 (dense-only softfork). | `node/chaincfg/params.go:364-371`, `node/blockchain/validate.go:536-551` |
| Do V1 and V3 dense bytes coincide? | Yes, byte-for-byte for the 164-byte core. Semantics differ: V1 trailer is 32 reserved bytes; V2/V3 trailer is `e(2) | top_k(2) | 28 zeros` with `e == 0` meaning dense. | `zk-pow/src/v1/api/proof.rs:43-50`, `zk-pow/src/api/proof_utils.rs:462-486` |

Consequences, `derived`:

1. The PAB note (`docs/PEARL_ACTIVATION_ORIGIN_BINDING_2026-09-21.md`) claims certificate-v3
   scope but cites `zk-pow/src/v1/api` and `zk-pow/src/v1/circuit`. Its stated facts about
   `job_key` and the 164-byte layout happen to be byte-identical on the `api` path for dense
   proofs, which is exactly why the error is dangerous: it is invisible on every mainnet
   block and wrong in principle. **Correction of that note to the `zk-pow/src/api`,
   `zk-pow/src/circuit`, and `zk-pow/src/ffi` route, with the Salted derivation and the
   dense-only length stated, is a prerequisite to ACCEPT.** The reviewer does not edit it.
2. No E-000 implementation may import, port, or paraphrase parsing semantics from
   `zk-pow/src/v1` because the field prefixes look alike. Control `E000-KB-01` enforces this.
3. The manifest's control "use the wrong certificate seed-derivation version; the vector must
   fail" cannot falsify a `hash_b` reconstruction. It is re-scoped to the noise-seed vector
   (`E000-KB-23`) and must be reworded in the manifest.
4. Affected criteria: D.1, D.2, D.3, D.7, controls KB-01 through KB-04 and KB-23, manifest
   `known_bad_controls[2]`, and the PAB note's citations.

## A. Scope and claims

- **Lineage.** Pearl INT certificate-v3, dense, at commit `4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0`,
  vLLM `0.20.2`, mainnet (`wire.MainNet = 0x50524C4D`). Code route: `node/wire/certificate_v3.go`
  → `node/zkpow/verify.go` → `zk-pow/src/ffi` → `zk-pow/src/api` with `SeedDerivation::Salted`.
- **Claim.** `hash_b`-only. The permitted statement after success is: *the selected block's
  `hash_b` opened to one registered runtime weight byte-string*. Nothing else.
- **Forbidden interpretations.** `WORK`, `EXECUTION`, `SEMANTICS`, or `DEMAND` satisfied; full
  inference; valid activations; useful work; hardware origin; economic authorization; model
  identity beyond the slab byte-string; any rate.
- **Registered-runtime-slab participation** is a byte-string equality. It says a weight slab
  that appears in a public checkpoint was the `B` operand's pre-image under this `job_key`.
  It does not say the `A` operand was activations, that any layer ran, that the model ran,
  or that anyone asked for it.
- **Dense and MoE.** Dense V3 is in scope. MoE V3 is excluded *before selection* as an
  eligibility criterion (`PublicDataLen == 164`) and justified by consensus at the pin. A V3
  certificate at height ≥ 99000 with `PublicDataLen != 164` is consensus-contradictory and is
  recorded as `E000-INV-CONSENSUS-CONTRADICTION`, never parsed as MoE, never used as an
  escape after a result.
- **FP8 certificate-v4** is entirely outside this experiment. Any v4 artifact in the lane is
  `E000-REJ-VERSION-ROUTE`.
- **Four-coordinate vector after any outcome:** `WORK=unknown`, `EXECUTION=unknown`,
  `SEMANTICS=unknown`, `DEMAND=unsupported`. E-000 does not run Pearl's proof verifier.

## B. Candidate selection, fixed before observation

Genuine blinding is unavailable: `hash_b` is public. The strongest auditable separation is
temporal. The candidate must not exist when registry, recipe, implementations, and this
freeze are accepted.

1. `T_accept` = UTC time of the operator acceptance record citing this freeze's SHA-256 and
   the amended manifest's SHA-256.
2. `T_start = T_accept + 3600 s` (exceeds `MaxTimeOffsetMinutes = 5` and several
   `TargetTimePerBlock = 3m14s` intervals).
3. `H_ref` = lowest mainnet height whose header timestamp ≥ `T_start`, agreed by two
   independent public sources.
4. Scan `h = H_ref, H_ref+1, …` ascending. The candidate is the first `h` with all of:
   mainnet; `h ≥ 99000`; certificate version field `== 3`; `PublicDataLen == 164`;
   confirmation depth ≥ 100 at both sources; identical block hash at both sources; the
   consensus-drift check passes (no rule activated after the pin that alters envelope,
   public-data layout, `job_key`, `mining_config`, or `hash_b` construction).
5. Tie-breaking is unnecessary; heights are totally ordered.
6. Exhaustion: no eligible height among the first 2000 at or above `H_ref`, or fewer than
   `H_ref + 100` blocks within 14 days of `T_accept` → `BLOCKED`,
   `E000-BLK-NO-ELIGIBLE-CANDIDATE`. No second window under this experiment ID.
7. Non-self-mined: operator attestation that no Pearl mining was ever performed from any
   operator-controlled key, machine, or pool account, plus retained coinbase outputs. This
   is attestation. Public data cannot prove a negative.

**Facts that may be learned during eligibility:** height, block hash, header timestamp,
version field, `PublicDataLen`, confirmation depth, coinbase outputs.
**Facts that stay sealed until Phase 8:** the 32 bytes at `public_data[84:116]` (`hash_b`).
**Facts read at Phase 7 for coverage:** `mining_config`, `m`, `n`, `t_rows`, `t_cols`;
`hash_a` and `hash_jackpot` may be read but compared to nothing.

**Selection-time bias.** "The latest block now" is rejected. Because the candidate is a
future block relative to acceptance, neither owner nor reviewer can have pre-computed its
classification, and `T_accept` cannot be chosen after seeing an outcome that does not yet
exist. This is procedural separation and is labelled as such.

## C. Public-source and temporal provenance

- Raw artifacts: full header bytes; full `MsgCertificate` bytes; the 164 public-data bytes;
  height and hash; two retrieval receipts (URL, UTC time, status, SHA-256 of raw response);
  the reconstructed 76-byte `IncompleteBlockHeader`.
- Registry entry: HF repo id; git revision SHA; publisher commit timestamp (recorded, never
  load-bearing); Aeye retrieval receipt time; full file list with LFS `sha256`; config and
  quantization-config digests; tensor names, dtypes, shapes; recipe id; TP degree set; tier.
- **Temporal rule.** Phase 3 (registry freeze) completes before Phase 7 (selection). Since
  the candidate is a future block, every registry revision predates it by Aeye's own
  retrieval receipt, independent of publisher timestamps. A "last updated" timestamp alone
  is insufficient; without immutable revision history and exact file digests, a repo is out.
- **Registry-freeze rule.** After Phase 3 nothing is added, removed, or edited: no revision,
  tensor, TP/EP layout, model, or transformation. The registry digest is cited by the run.
- **Trust tiers** follow REVIEW_PROTOCOL §9: `T0` bytes only; `T1` + pinned revision SHA,
  receipts, per-file digests, second retrieval over an independent path; `T2` + independent
  reproduction from another publisher's base model. Minimum `T1`. Publisher-signed but
  unreproduced stays publisher-only. The tier is stated beside the result.
- **No model-weight bytes are committed to Aeye.** Digests, shapes, names, receipts only.

## D. Certificate-v3 byte-path contract

Target function, `observed` from `pearl-blake3/src/merkle.rs:14-27, 455-472` and
`miner/vllm-miner/src/vllm_miner/gemm_operators.py:95-138`:

```
hash_b == BLAKE3_keyed(key = job_key,
                       data = zero_pad_to_1024(row_major_int8_bytes(B_T)))
B_T = runtime weight slab exactly as passed to the kernel, shape n x k, C-contiguous
job_key == BLAKE3(header_76 || mining_config_52)          # unkeyed, 128-byte preimage
```

| # | Rule | Source |
|---|---|---|
| D1 | Version-first envelope; dispatch strictly on `3`; never parse a V3 body with V1 fixed-size logic although a dense body is also 164 bytes. | `certificate.go:128-155` |
| D2 | V3 body = V2 layout; `ProofCommitment = SHA256d(LE32(3) ‖ public_data)`; Salted derivation is a version property, not on the wire. | `certificate_v3.go`, `certificate_v2.go:64-75`, `seed.rs` |
| D3 | Dense public data is exactly 164 bytes. Any other length at height ≥ 91630 is consensus-invalid at the pin → `INVALID`, not MoE. | `proof_utils.rs:1143`, `validate.go:546-551` |
| D4 | `header_76 = version LE32 ‖ prev_block(32, wire order) ‖ merkle_root(32, wire order) ‖ timestamp LE32 ‖ nbits LE32`. Go reverses to display order; Rust reverses back. Both implementations must state their convention and emit identical bytes. | `verify.go:214-226`, `api/proof_utils.rs:513-521` |
| D5 | `certificate.Hash == header.BlockHash()` and `header.ProofCommitment == SHA256d(LE32(3) ‖ public_data)` before any `hash_b` use. | `verify.go:104-115` |
| D6 | `mining_config_52 = common_dim LE32 ‖ rank LE16 ‖ mma_type LE16 (0) ‖ rows_pattern(6) ‖ cols_pattern(6) ‖ e LE16 ‖ top_k LE16 ‖ 28 zero bytes`; `e == 0`; reserved zero; byte-identical round-trip. | `api/proof_utils.rs:448-486` |
| D7 | `job_key = BLAKE3(header_76 ‖ mining_config_52)`. | `api/proof_utils.rs:348-353` |
| D8 | `hash_a = [52:84]`, `hash_b = [84:116]`, `hash_jackpot = [116:148]`, `m,n,t_rows,t_cols` LE32 at `[148:164]`. | `api/proof_utils.rs:1166-1190, 1232-1235` |
| D9 | int8 → single two's-complement byte; the miner casts int8 to uint8 modulo 256. Saturating or sign-magnitude casts are wrong. | `gemm_operators.py:125-137` |
| D10 | Orientation `n x k`, row-major, contiguous, as `w_q.contiguous()`. Transposed, Fortran, or strided views are wrong. | `vllm_kernels.py:204-220` |
| D11 | Fused QKV / gate-up: the slab is the fused runtime parameter in runtime order. Exact ordering, partition sizes, and per-parameter versus per-projection hashing must be frozen from pinned vLLM source with `file:line` before Phase 7. Unresolved → `BLOCKED`. | to be frozen by owner |
| D12 | TP: degree set and per-class slicing rule frozen from pinned source with `file:line`. Each rank of each degree is a distinct slab. Unresolved → `BLOCKED`. | to be frozen by owner |
| D13 | EP / MoE stacking / per-expert `n` versus stacked rows: out of scope by consensus exclusion; any MoE artifact in the lane → `INVALID`. MoE models may enter the registry only through their dense parameters under the frozen recipe. | `params.go:367`, `validate.go:546` |
| D14 | Zero-pad to a multiple of 1024; leaf count `ceil(len/1024)`; root = standard keyed BLAKE3 of padded bytes. | `merkle.rs:14-27, 455-472` |
| D15 | Every recipe parameter is `fixed` with source or the run is `BLOCKED` before Phase 7. No default from convenience, shape, or the observed target. | — |
| D16 | **Not bound by `hash_b`:** weight scales, SmoothQuant scales, Hadamard block size, layer identity, model identity, checkpoint revision, tokenizer, request, activations, output. A MATCH identifies a byte-string, not an execution. | PAB note §2, re-cited on the `api` route |

## E. Independence standard for the two implementations

- **Definition.** Two implementations are independent for E-000 when they share no
  Aeye-authored source file, module, function, or fixture generator for envelope parsing,
  header/config serialization, `job_key`, checkpoint parsing, transformation, padding,
  hashing orchestration, or comparison; were written against pinned Pearl source rather than
  against each other; and differ in language or in tensor-file parsing library.
- **No shared Aeye helper module.** Not for serialization, transformation, tree construction,
  or comparison.
- **Permitted shared primitives.** A BLAKE3 implementation (both must pass official keyed-mode
  vectors; at least one must not be the same codebase as the other); standard-library SHA-256;
  the checkpoint bytes and their frozen digests; the pinned Pearl checkout as read-only oracle.
- **Residual common-mode risks, stated.** One author; one reading of the vLLM transform; one
  reading of any misdocumented pinned line; one upstream BLAKE3 bug; one workstation.
- **Transcript comparison.** Byte-for-byte at every stage: `header_76`, `mining_config_52`,
  `job_key`, per-source-tensor digests, slab digest and shape, padded length and leaf count,
  root. Equal roots with a divergent intermediate is `E000-INV-TRANSCRIPT-DIVERGENCE`.
- **Pearl parity oracle.** Pinned `pearl-blake3::MerkleTree` and the pinned Python
  `MatrixMerkleTree` path must reproduce root and `job_key` on the frozen slab and every
  fixture. Reusing Pearl code inside an Aeye implementation is not independence.
- **Third-party replay.** One documented command; retained public artifacts and frozen
  registry identities only; no network except optional checkpoint re-download verified
  against frozen digests.
- **Non-claims.** No human, institutional, or cryptographic independence. Code-path
  separation is not peer review.

## F. Pre-comparison freeze, exact order

| Phase | Name | Gate |
|---|---|---|
| 1 | Raw-source retention | Pearl checkout and vLLM 0.20.2 source digested |
| 2 | Operator acceptance | Record cites this freeze's SHA-256 and amended manifest SHA-256; `T_accept` fixed |
| 3 | Checkpoint/registry freeze | Identities, digests, shapes, TP set, tier; no weight bytes in repo |
| 4 | Transformation-recipe freeze | Every parameter `fixed` with `file:line`; any unknown → `BLOCKED` |
| 5 | Implementation/version freeze | Both implementation digests, toolchains, replay command |
| 6 | Known-bad tests | All 30 controls reject with expected diagnostics on both implementations and the oracle |
| 7 | Selection, eligibility, coverage, candidate roots | Rule of section B; `hash_b` bytes written to a sealed file whose digest is recorded and whose content is not read; `mining_config, m, n` read; every registry slab of shape `(n,k)` computed by both implementations |
| 8 | Reveal | Sealed `hash_b` opened once; timestamp recorded; no registry, recipe, parser, or code change permitted thereafter |
| 9 | Exactly one comparison | Compare once; emit terminal state; write result |

Every stage is content-addressed. Corrections require a new revision id (`E-000-R2`, …) with
its own freeze and must preserve the original outcome and artifacts. **Reveal** is the first
moment any process or person reads, logs, displays, or compares `public_data[84:116]`; a
sealed-digest mismatch at reveal is `INVALID`. Same-machine procedural separation is
auditable ordering, not concealment.

## G. Known-bad controls

Every control must produce its diagnostic on both implementations. Full list with IDs in the
JSON twin. Summary:

| ID | Mutation | Diagnostic |
|---|---|---|
| KB-01 | Legacy V1 bytes / V1 parser behavior to the V3 lane | `E000-REJ-VERSION-ROUTE` |
| KB-02 | V2 version field to the V3 lane | `E000-REJ-VERSION-ROUTE` |
| KB-03 | Proposed v4/FP8 material to the V3 lane | `E000-REJ-VERSION-ROUTE` |
| KB-04 | `PublicDataLen != 164` (MoE tail or arbitrary) | `E000-REJ-PUBLIC-DATA-LENGTH` |
| KB-05 | Truncated (163) and extended (165) public data | `E000-REJ-PUBLIC-DATA-LENGTH` |
| KB-06 | Corrupted certificate block hash | `E000-REJ-BLOCK-HASH-BINDING` |
| KB-07 | Corrupted proof commitment, including version-2 domain | `E000-REJ-PROOF-COMMITMENT` |
| KB-08 | Unfused tensor where recipe fuses | `E000-DIV-SLAB-DIGEST` |
| KB-09 | Q/K/V order permuted | `E000-DIV-SLAB-DIGEST` |
| KB-10 | Gate/up order swapped | `E000-DIV-SLAB-DIGEST` |
| KB-11 | Wrong TP rank or degree | `E000-DIV-SLAB-DIGEST` |
| KB-12 | Any EP rank/degree, expert order, omitted/duplicated expert | `E000-REJ-MOE-OUT-OF-SCOPE` |
| KB-13 | Transposed slab | `E000-DIV-SLAB-DIGEST` |
| KB-14 | Fortran / non-contiguous layout | `E000-DIV-SLAB-DIGEST` |
| KB-15 | Wrong signed-byte encoding | `E000-DIV-SLAB-DIGEST` |
| KB-16 | Changed leaf count | `E000-DIV-LEAF-COUNT` |
| KB-17 | Padding omitted, doubled, or wrong granularity | `E000-DIV-ROOT` |
| KB-18 | Unkeyed or derive-key BLAKE3 | `E000-DIV-ROOT` |
| KB-19 | One-bit `job_key` mutation | `E000-DIV-ROOT` |
| KB-20 | Header hashes in display order (exactly one reversal) | `E000-DIV-JOB-KEY` — **cancelling-error control** |
| KB-21 | Big-endian header fields or swapped timestamp/nbits | `E000-DIV-JOB-KEY` |
| KB-22 | Non-zero reserved trailer, `e != 0`, `mma_type != 0`, wrong config length | `E000-REJ-MINING-CONFIG` |
| KB-23 | Legacy seed derivation on a V3 fixture | `E000-REJ-SEED-DERIVATION` — on the noise-seed vector only; **does not falsify `hash_b`** |
| KB-24 | Registry revision retrieved after `T_accept` | `E000-REJ-REGISTRY-TEMPORAL` |
| KB-25 | Miner-captured tensor substituted for public reconstruction | `E000-REJ-PROVENANCE` |
| KB-26 | Poisoned registry entry | `E000-PROPAGATE-FALSE-MATCH` — tests propagation, not detection |
| KB-27 | `hash_a` compared where `hash_b` claimed | `E000-REJ-FIELD-SELECTION` |
| KB-28 | Unresolved parameter with a convenient default | `E000-BLK-UNRESOLVED-TRANSFORM` — producing any root fails |
| KB-29 | Equal roots with divergent intermediate | `E000-INV-TRANSCRIPT-DIVERGENCE` — Aeye-side shared-bug route |
| KB-30 | Official BLAKE3 keyed vectors and pinned `seed.rs` commitment vectors | `E000-ORACLE-PARITY` — positive parity |

KB-20 is the required shared-bug detector. The Go side reverses header hashes to display
order and the Rust side reverses again, so the `job_key` preimage uses wire order. An
implementation that reverses zero times agrees with one that reverses twice; one that
reverses exactly once diverges. Both implementations must declare their convention, and the
pinned Pearl `job_key` on the fixture is the tie-breaker.

## H. Terminal state machine

Precedence, highest first: `INVALID` > `BLOCKED` > `UNRETRIEVED` > `OUT_OF_COVERAGE` >
(`MATCH` | `IN_COVERAGE_NO_MATCH`).

- `INVALID`: protocol violation — phase order, prohibited observation, post-reveal edit,
  digest mismatch, transcript divergence, version-route mismatch after Phase 4, consensus
  contradiction, or a parameter discovered unresolved after reveal. No scientific
  classification is emitted.
- `BLOCKED`: a prerequisite failed before Phase 8 — unresolved transform, registry not
  freezable at `T1`, no eligible candidate, consensus drift, oracle parity failure, security
  stop. Not a scientific negative.
- `UNRETRIEVED`: eligible candidate whose bytes could not be retrieved consistently from two
  sources. Reported, never dropped.
- `OUT_OF_COVERAGE`: `(n,k)` not in the frozen shape index. Evidence of nothing about the miner.
- `MATCH`: at least one frozen slab's root equals `hash_b`, both implementations and the
  oracle agreeing at every stage. Report the matching slab-id set.
- `IN_COVERAGE_NO_MATCH`: shape in index, every slab of that shape across all frozen models,
  revisions, TP degrees, and transforms computed with agreement, none equal. Permitted
  phrasing: "did not open to any registered slab."

**Resolution of the single-opening versus census tension.** E-000 emits one classification
for one block; rates belong to E-001. `IN_COVERAGE_NO_MATCH` is legal here only because
Phase 7 requires exhaustive enumeration of the candidate's shape *before* reveal. If
enumeration proves incomplete after reveal, the state is `INVALID`, never a negative. A
non-match falsifies public reconstruction for this candidate, registry, and recipe only. It
never becomes `FALSE` for FB-4a or the network. Missing, ambiguous, unsupported, unmeasured,
or unavailable never becomes zero or success.

## I. Acceptance, falsification, pivot, and stop rules

**Single-opening claim is accepted iff all hold:** terminal `MATCH`; no `INVALID` code;
phases 1–9 in order; operator acceptance citing this freeze; registry at `T1`+ before
Phase 7 with tier stated; every recipe parameter fixed with `file:line`; byte-for-byte
transcript agreement; oracle parity; 30/30 controls; complete eligibility record with
two-source finality ≥ 100 and consensus-drift check; non-self-mining attestation; checkpoint
bytes match frozen digests; result reported only as registered-runtime-slab participation.

**Run is invalid, not negative, when:** any post-reveal change; `hash_b` observed before
Phase 8; sealed-digest mismatch; selection by any other rule or `T_start`; transcript
divergence; V1 semantics on a V3 body; captured operand bytes in provenance; any frozen
digest mismatch; a parameter unresolved after reveal; acceptance missing or after Phase 7.

**Falsification, scoped:** `IN_COVERAGE_NO_MATCH` under a clean run falsifies public
reconstruction for the frozen candidate, registry, and recipe. It does not falsify
reconstruction in general or say anything about the miner.

**E-001 gating.** A clean `MATCH` or `IN_COVERAGE_NO_MATCH` gates E-001 (the instrument ran
end to end); the direction of the outcome does not. `INVALID` or `BLOCKED` blocks E-001.

**Blocking, never optimized away:** version-route mismatch; unresolved runtime transform;
inability to establish registry retrieval before `T_accept`; consensus drift after the pin.

**Security-disclosure stop.** Any plausible Pearl weakness observed during reconstruction
stops the run as `BLOCKED`, `E000-BLK-SECURITY-STOP`. Only a minimal local reproduction is
retained, outside public artifacts. No exploit or vulnerability detail enters any document,
JSON, log, or commit. Disclosure follows Pearl's `SECURITY.md` with the operator's decision.

## J. Required output packet

Machine-readable run manifest; two-source retrieval receipts; source digests (Pearl, vLLM,
both implementations, registry, recipe); eligibility decision with the sealed-`hash_b`
digest; frozen registry; exact recipe with `file:line` per parameter; intermediate
byte/digest transcript from both implementations; implementation identities; Pearl
parity-oracle result; 30-row negative-control matrix; comparison result with reveal
timestamp; terminal classification with precedence trace; four-coordinate vector;
assumptions and non-claims; one replay command; E-001 denominator and rate rules, marked
out of scope for this single run:

```
headline            = |MATCH| / |planned_sample|
retrieval rate      = retrieved / planned_sample
coverage rate       = in_coverage / retrieved
conditional match   = MATCH / in_coverage        # secondary, labelled
forbidden           = any denominator that silently drops OUT_OF_COVERAGE or UNRETRIEVED
```

## K. Manifest amendments required before operator acceptance

Apply to `experiments/e-000/manifest.json`; the JSON twin carries the same list as
`required_manifest_amendments`.

| ID | Field | Amendment |
|---|---|---|
| A1 | `frozen_inputs` | Add `certificate_code_route` = `zk-pow/src/api + circuit + ffi; SeedDerivation::Salted; src/v1 excluded`, `fixed`. |
| A2 | `frozen_inputs` | Add `mainnet_fork_heights_at_pin` `{71935, 91630, 96251, 99000}` and `candidate_min_height = 99000`, `fixed`. |
| A3 | `frozen_inputs` | Add `public_data_length = 164` and `moe_scope = excluded by consensus at pin`, `fixed`; set `expert_parallel_degree` to `fixed`, "not applicable (dense-only)". |
| A4 | `frozen_inputs` | Add `candidate_selection_rule` → `reviewer-freeze.json#candidate_selection_rule` and `reviewer_freeze_sha256`, `fixed`. |
| A5 | `frozen_inputs` | Add `finality_rule` = "≥ 100 confirmations at two independent public sources agreeing on block hash", `fixed`. |
| A6 | `procedure` | Replace with the nine ordered phases, including sealed `hash_b` and single comparison. |
| A7 | `known_bad_controls` | Reword item 3 (seed derivation) to the noise-seed vector only; add `E000-KB-01`…`E000-KB-30` by id. |
| A8 | `acceptance` | Add: `api` route with no V1 semantics; `hash_b` sealed then revealed once; intermediate-stage agreement; oracle parity; non-self-mining attestation. |
| A9 | `failure` | Add: route mismatch / unresolved transform / registry-retrieval-after-`T_accept` → `BLOCKED`, never optimized away; `hash_b` read before Phase 8 → `INVALID`. |
| A10 | `blocking_conditions` | Add: PAB note citations not yet corrected to the `api` route; `BLOCKED`/`INVALID` not yet in the manifest's classification set. |
| A11 | `procedure`/`acceptance` | State the six terminal states with precedence and the exhaustive-enumeration requirement for `IN_COVERAGE_NO_MATCH`. |
| A12 | `acceptance` | Add the security-disclosure stop condition. |

## L. Unresolved questions carried into the run

1. Whether mainnet has reached height 99000 at `T_accept`; if not, `BLOCKED` until it does
   within the exhaustion window.
2. Whether any consensus rule affecting parsing, `job_key`, `mining_config`, or `hash_b` has
   activated after the pin; the drift check runs against the public repository at selection.
3. The exact pinned vLLM 0.20.2 fusion, partition-size, and TP slicing rules per checkpoint.
   Not resolved by this review; must be frozen with `file:line` before Phase 7.
4. Whether pearl-ai Hugging Face repos expose immutable revision history with LFS `sha256`
   per file; if not, `T1` is unreachable and the run is `BLOCKED`.
5. CUDA `tensor_hash` parity with the CPU keyed BLAKE3 path; E-000 uses the CPU reference and
   records CUDA parity as `unknown` unless separately established.
6. `T2` reproducibility of pearl-ai W8A8 checkpoints; prior "probably not."
7. Which layers ever mine under `should_use_noisy_gemm` and the shape bounds; this bounds
   which slabs can appear on chain at all.

## M. Reviewed files

SHA-256 of every Aeye document and every pinned Pearl source file inspected for this freeze
is recorded in the JSON twin under `reviewed_file_sha256`. The Pearl checkout at
`evidence/external/pearl` was verified at `4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0`
before any file was read.
