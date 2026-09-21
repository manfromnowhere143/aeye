# Aeye Experiment Program

Status: `proposed`; execution requires the gate for each experiment

## Ordering

### E-000 — Pearl byte-path and FB-4 reconstruction gate

Question: can public source artifacts reconstruct the exact runtime weight slab and then
the on-chain `hash_b` without capturing bytes from a miner?

Required work:

1. Pin Pearl, its vLLM dependency, certificate/fork rules, and one checkpoint revision that
   predates the candidate block.
2. Specify checkpoint loading, fused QKV and gate/up layouts, tensor/expert parallel slicing,
   MoE stacking, contiguity, transpose, dtype, padding, leaf count, and BLAKE3 keying.
3. Reproduce CPU/Python/Rust/CUDA tensor-hash vectors independently. CUDA parity may be
   `blocked` on this machine but cannot be assumed from repository tests.
4. Exhibit one non-self-mined mainnet certificate opening with retained raw bytes, height,
   finality context, checkpoint revision, transformation recipe, slab ID, and 32-byte result.

Current evidence **contradicts the naive FB-4 statement** that `w_q` is generally one
checkpoint tensor byte-for-byte. Pinned vLLM fuses Q/K/V and gate/up projections, slices
for tensor parallelism, and packs MoE experts before Pearl hashes the contiguous runtime
slab. The narrower deterministic-reconstruction hypothesis remains `unknown`.

Acceptance: independent replay produces the exact `hash_b`.  
Failure: unresolved transform/config ambiguity, revision drift, or mismatch. Do not patch
the census around a failure.

### E-001 — Preregistered Pearl mainnet census

Runs only after E-000. It is a read-only measurement of registered weight participation,
not execution.

Pre-register:

- chain/network and finality rule;
- fixed height interval or random seed and sampling frame;
- all checkpoint revisions predating each adjudicated block;
- transformation/TP/EP configurations and explicit registry coverage;
- retrieval retry policy and terminal buckets;
- primary and secondary statistics.

Buckets are `MATCH`, `IN_COVERAGE_NO_MATCH`, `OUT_OF_COVERAGE`, and `UNRETRIEVED` as
defined in `PROTOCOL_SPEC.md`. Report:

```
whole-sample lower bound = MATCH / planned_sample
retrieval rate           = retrieved / planned_sample
coverage rate            = in_coverage / retrieved
conditional match rate   = MATCH / in_coverage   # secondary and labelled
```

Use exact binomial confidence intervals where sampling is random; do not attach population
inference to an exhaustive fixed window. A low match rate is not evidence of random or
useless work. A high rate is not evidence of valid activations or full inference.

### E-002 — One semantic execution DAG

Instrument one small public model and two concurrent requests through prefill and decode.
Include a shared prefix-cache hit, one rebatch, and deterministic output. Emit semantic
events independent of internal callback names.

Acceptance:

- independent replay reconstructs all roots;
- each request receipt opens exactly its rows/tokens;
- cache provenance and output linkage are complete;
- changing scheduler layout without semantic change produces an equivalent semantic DAG
  or an explicitly different execution manifest;
- no claim above `commitment_only` is made yet.

### E-003 — AEGIS negative suite

Mutate one invariant per fixture: request, model root, adapter set, layer/op ID, parent edge,
row map, cache origin, attempt ID, output token, ordering, profile, challenge time, Pearl
certificate version, network, registry label, and demand principal.

Acceptance: every mutation invalidates exactly the affected coordinate(s) and never upgrades
an unaffected one. A plausible-looking `overall_verified` input is rejected structurally.

### E-004 — Arithmetic profile conformance

Cross-check Hawkeye and MMA-Sim against retained A100/SM80 and H100/SM90 device results for
the exact instructions Aeye intends to cover. Include arbitrary accumulator `C`, special
values, random-bit patterns, compiler/CUBIN retention, and known-bad grouping/rounding/
split-K profiles.

Acceptance: bitwise agreement for the preregistered surface with zero unclassified
disagreements. This accepts a profile, not a physical-hardware claim and not full-model
semantics.

### E-005 — Verification-lane tournament

Run the same E-002 semantic relation under:

- random-path local checks;
- an optimistic two-provider/referee prototype;
- a supported full/layerwise ZK backend where feasible;
- optional attested execution in an isolated environment.

Measure detection, assumptions, data exposure, prover/verifier cost, bytes, and failure
modes. Do not rank unlike security statements by speed alone.

### E-006 — Serving overhead

Baseline and treatment must use identical model bytes, quantization, vLLM commit, kernels,
GPU SKU/count, driver/toolkit, batch and sequence distributions, cache policy, scheduler,
warmup, duration, and load generator. Measure:

- request throughput and useful tokens/s;
- time to first token and inter-token latency distributions;
- GPU/CPU utilization and memory;
- commitment/proof generation latency;
- receipt/proof bytes and evidence storage;
- verifier latency and resources;
- failure/retry rate.

Report raw samples, repetitions, median, p95/p99, dispersion/confidence intervals, and both
incremental provider cost and total system cost. `<1%` is a predeclared target only for the
`C0` fast path.

### E-007 — Demand-policy adversarial simulation

Test replay, late authorization, revoked signatures, reorgs, same-principal self-payment,
Sybil principals, refunded/circular fees, bundled requests, and aggregator omission. The
result must name which observable event passed; it may not label prompts useful.

### E-008 — Pearl FP8 certificate-v4 verifier parity

Keep the September 2026 FP8 proposal completely separate from E-000's INT
certificate-v3 reconstruction. Freeze the retained specification, PR patch/head, Device,
Quant, parser, commitments, ticket, selected-tile arithmetic, correction, and jackpot
policy. Build two independent verifier implementations and cross-check ordinary, boundary,
and adversarial vectors against an authorized B200 path.

Acceptance requires byte-for-byte agreement, rejection of every preregistered degenerate
case, an explicit specification-to-code difference map, and retention of the informal
quantized-subspace hardness premise. Software agreement without independent B200 vectors
cannot establish physical arithmetic conformance. Even a passing result is only a
certificate-v4 `WORK`/bounded-semantics result; it does not establish Aeye `EXECUTION` or
`DEMAND`.

### E-009 — CX-1 toy coupled execution

Status: `supported` for the exact R1 toy question.

R1 froze a 13-event finite-field transformer-shaped causal block, five coded-linear
relations, eight exact state/nonlinear/decode/output relations, `t=4`, `ell=16`, all source
and schema digests, eight mutations, and one measurement protocol before execution. A
separate code path accepted 13/13 events and all 80 coded equations, rejected 8/8 controls
with the preregistered codes, and recomputed the conditional five-relation bound at about
`4.99e-25` (`2^-80.73`). The result vector is `WORK=unknown`,
`EXECUTION=satisfied/sampled`, `SEMANTICS=satisfied/hybrid` for the declared toy profile,
and `DEMAND=unsupported`.

The Pearl object remains synthetic. The verifier authenticates preprocessing by touching
the full toy matrices, the transcript is public, challenge grinding has only a declared
conditional model, and the local Python costs are not production predictions. See
`E009_RESULT_2026-09-20.md`.

### E-010 — proposed authenticated preprocessing and native-root bridge

The next execution experiment should not repeat R1 at a larger dimension. It should answer
the load-bearing questions R1 exposed:

1. Can a one-time proof or commitment authenticate `Q=G^T M` against the exact
   model/layout root and amortize setup across requests?
2. Can a public challenge source resist practical subject grinding under an explicit
   query bound or external-beacon model?
3. Can actual version-pinned Pearl clean roots enter the same execution relation without
   duplicating dominant work or changing Pearl consensus?
4. Can batched request membership, realistic quantized attention/normalization, KV-cache
   provenance, decoding, and output binding be covered without an implicit denominator?
5. Does the complete cost surface beat a named full-proof baseline on identical work?

E-010 now has a proposed manifest, not a preregistration or result. Selecting a
proof/authentication primitive, workload, privacy policy, comparator, and native Pearl
lineage remains a research decision, not an implementation fact. The construction is
specified in `AUTHENTICATED_PREPROCESSING_CAPSULE.md`.

## Decision gates

| Gate | Advance condition | Pivot/stop condition |
|---|---|---|
| `G0` architecture | Schemas, claims, threat model, known-bad fixtures, and validator pass independent review | Any coordinate lacks a relation/non-claim |
| `G1` Pearl reconstruction | E-000 independently reproduces a non-self-mined block | FB-4 remains ambiguous or depends on captured runtime bytes |
| `G2` census | Preregistration and registry provenance accepted | Incomplete transforms silently classified as no-match |
| `G3` execution | E-003 rejects lineage/substitution attacks with quantified coverage | Commitment-only lineage advertised as satisfied execution |
| `G4` semantics | Accepted profiles and full operator coverage accounting | GPU architecture label used as a profile |
| `G5` economics | Policy-specific event claims survive attacks | “Demand proved” or intrinsic utility inferred |
| `G6` performance | Reproducible workload-specific envelope | Bare overhead percentage or incomparable baseline |

## Initial four-week research slice

- Week 1: E-000 reconstruction, version/serialization map, registry trust contract.
- Week 2: E-002 semantic DAG and AER schema; no security upgrade above commitments.
- Week 3: E-003 attack harness plus E-004 profile-vector preparation.
- Week 4: benchmark the `C0` fast path, issue a falsification report, and decide whether
  E-001 and stronger lanes warrant engineering investment.

The census and single-execution prototype may proceed in parallel only after E-000; neither
is permitted to stand in for the other.
