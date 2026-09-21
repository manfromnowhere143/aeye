# Aeye–Pearl Coupling Profile

Status: `proposed` Pearl profile; toy execution-side relation implemented in E-009-R1; native Pearl relation not implemented  
Date: 2026-09-20  
Profile identifier: `aeye:pearl-work-to-execution-coupling:v0`

## Verdict

The defensible Aeye contribution is not a replacement for Pearl and not another proof of
matrix multiplication. It is a strict extension of the **claim surface**:

1. preserve Pearl's native `WORK` statement and certificate bytes unchanged;
2. independently prove or audit that the same operand commitments occurred on the causal
   path of a committed request/model/output execution; and
3. keep arithmetic semantics and external demand as separate coordinates.

This is stronger than a Pearl work certificate for the question “did this work belong to
this inference?” It is not automatically cheaper, more secure, or a better consensus
mechanism. No such superiority claim is supported today.

## 1. Version firewall

Pearl is not one timeless protocol. Aeye must never combine facts from these lineages in a
single unversioned claim.

| Lineage | Retained authority | Arithmetic and verification shape | Aeye treatment |
|---|---|---|---|
| INT certificate-v3 | Pearl repository commit `4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0` and [PoUW paper v4](https://arxiv.org/abs/2504.09971v4) | INT7-like operands, INT32 accumulation, low-rank noising/correction, live certificate-v3 rules in the retained snapshot | Historical, pinned experiment target for E-000. Claims apply only to that commit and fork context. |
| FP8 certificate-v4 proposal | [September 2026 FP specification](https://pearlresearch.ai/Pearl_Whitepaper.pdf) and [open PR #311](https://github.com/pearl-research-labs/pearl/pull/311), head `f7fe16c83dd89a91cb957e3a3644e232ecd7da2a` at retrieval | Post-noise nonlinear quantization, FP8 tile recomputation, jackpot policy, declared B200/Blackwell device semantics | Current proposal under review. The retained PR was open and unmerged; Aeye makes no deployment or consensus-activation claim. |

The FP8 document replaces the older batch-low-rank formulation with an explicit informal
**quantized-subspace hardness** premise for its work-security argument. The two assumptions
must have different identifiers. A result may not silently inherit the v3 assumption after
parsing a v4 certificate, or vice versa.

## 2. Exact relations

Let `ω_v` contain the version-pinned Pearl network, block/header, certificate, fork rules,
device/quantization parameters, finality policy, and verifier version. Let `h_A,h_B` be the
native operand commitments accepted by that verifier.

Pearl supplies the relation

\[
R_W^{(v)}(\omega_v,h_A,h_B;\pi_W)=1.
\]

This is a `WORK` statement in Pearl's native context. It does not take an Aeye `job_id`,
trace root, output root, or demand event as a public input.

Let an Aeye execution subject be

\[
\sigma=(I,J,r_R,r_M,r_E,r_D,r_T,r_Y,r_\sigma),
\]

where the two-stage construction fixes pre-authorization intent `I`, final job `J`, trace,
and output without a demand-event hash cycle. An execution backend must establish

\[
R_X(\sigma,h_A,h_B;\pi_X)=1,
\]

where the openings of `h_A,h_B` are consumed by named events on a checked causal path to
`r_Y`. Copying the two roots into a manifest is not this relation.

The coupled relation is only the conjunction

\[
R_{WX}^{(v)}=R_W^{(v)}\land R_X.
\]

The structural checker compares `h_A,h_B` as **native public inputs** of both evidence
objects. It does not interpret receipt placement as a proof binding and does not turn the
conjunction into a fifth coordinate or a global Boolean.

## 3. Strict-extension result

Projection is immediate: every accepted `R_WX` transcript contains an unchanged accepted
`R_W` transcript. Aeye therefore does not weaken Pearl's work test.

The converse is false. A valid Pearl work transcript can be paired with random or replayed
activations, a registered slab outside a model execution, an incomplete graph, or a grafted
output. Pearl's work relation may still accept while `R_X` rejects or is absent. The
retained [Usefulness Gap study](https://arxiv.org/abs/2606.04819v2)
provides empirical evidence for accepted random-matrix work in the studied v3 setting; the
logical non-implication follows independently from the missing execution public inputs.

Under work soundness error `ε_W`, execution soundness error `ε_X`, and parser/commitment
binding error `ε_B`, the conservative coupled bound is

\[
\Pr[\text{false coupled acceptance}]\leq
\epsilon_W+\epsilon_X+\epsilon_B.
\]

This is a union bound, not a completed reduction. For both retained Pearl lineages,
`ε_W` remains conditional on a non-standard stated assumption. For Aeye, `ε_X` remains
symbolic until a concrete backend and exact relation are implemented.

## 4. What FP8 certificate-v4 changes

The FP8 proposal materially improves the specificity of Pearl's own work statement:

- `Device` and `Quant` are public parameters;
- a winning tile is recomputed under bit-exact declared device arithmetic;
- the verifier authenticates opened strips and checks ticket and jackpot policy;
- noise-floor, tamed-product, and unpredictability checks address explicit degenerate
  strategies.

Those are meaningful `WORK`-relation and local-semantics improvements. They do not supply
the missing Aeye relation. The retained specification also makes the boundary unusually
clear:

- the work model counts selected-tile MACs and excludes quantization, noise generation,
  hashing, commitment verification, and memory movement;
- a Merkle opening authenticates disclosed rows/strips but is not knowledge of every
  undisclosed matrix element;
- input crafting, precision shortcuts, seed/commitment grinding, work reuse, and superior
  hardware/kernels remain security-analysis dimensions;
- no native input binds a client request, model graph, full execution trace, final output,
  or external demand event.

Aeye should treat the richer FP8 parameters as inputs to a more precise Pearl adapter, not
as evidence that the four-coordinate problem disappeared.

## 5. Minimal sidecar construction

`aeye:pearl-work-to-execution-coupling:v0` requires no initial Pearl consensus change.

1. **Retain native Pearl evidence.** Store the exact certificate/header bytes, version,
   fork context, native work-context digest, operand roots, and finality appraisal.
2. **Fix the Aeye subject.** Commit `intent_id`, authorization-derived `job_id`, execution
   manifest, event-DAG root, and output root before any external audit challenge.
3. **Verify execution independently.** The selected backend exposes `job_id`,
   `subject_root`, `h_A`, and `h_B` as native public inputs and checks the causal relation.
4. **Check equality.** The cross-evidence binding accepts only if both operand roots are
   non-null and byte-identical across the native `WORK` and `EXECUTION` inputs.
5. **Appraise coordinates separately.** Independent reports retain each relation's
   assumptions, coverage, verifier, and diagnostics. `SEMANTICS` and `DEMAND` do not follow
   from `R_WX`.

The original positive fixture is structural. E-009-R1 now provides a claim-bearing toy
execution-side relation over synthetic clean roots: five coded linear events and eight
exact state/nonlinear/decode/output events are bound to one final subject. A separate code
path accepts the unmodified 13-event bundle and rejects eight preregistered substitutions,
including an execution-side root mismatch. No native Pearl certificate is present, so R1
does not instantiate `R_W^(v)` or the complete `R_WX^(v)` conjunction.

## 6. 2026 execution-backend frontier

No retained technique simultaneously provides native-serving fidelity, public
transferability, negligible overhead, privacy, and full-model coverage. The profile is
therefore backend-neutral, but not relation-neutral.

| Technique | Valuable mathematical/system idea | Candidate Aeye use | Boundary |
|---|---|---|---|
| [Maverick](https://arxiv.org/abs/2609.10264v1) | Information-theoretic delegated matrix-vector verification with transparent preprocessing and batch verification; nonlinear operations remain client-side | Low-server-overhead online checking of selected linear transitions with explicit client state | Not automatically a publicly transferable receipt, Pearl work proof, full server event-DAG proof, or demand evidence |
| [DeepProve](https://eprint.iacr.org/2026/1112) | End-to-end cryptographic relation for quantized autoregressive inference | Strong `Z3` lane for a supported complete quantized relation | High prover cost; circuit semantics are not native B200/GPU execution or physical work |
| [zkComposer](https://arxiv.org/abs/2607.08095v1) | Contiguous layer subproofs linked by activation commitments, with sequence partitioning | Partition a large proof while retaining boundary equality | Composition optimization; security is inherited from the component proof system and exact boundary relation |
| [Sound Debloating](https://arxiv.org/abs/2609.10149v1) | Provenance-guided removal of constraints shown irrelevant to the retained relation | Reduce prover cost after the Aeye public-input relation is frozen | Cannot remove a required causal check or broaden semantics; it optimizes rather than strengthens the relation |
| [Jolt Atlas](https://arxiv.org/abs/2602.17452v1) | Lookup-centric ONNX zkML and streaming prover organization | Candidate for model-format-level proving and bounded memory | Proves the compiled ONNX/circuit relation, not native serving scheduler/GPU semantics |
| Random-path auditing | Post-commit local transition checks with explicit detection probability | `A1` lane for low-cost partial coverage | Concentrated corruption can evade small samples; openings may leak data |
| Optimistic dispute | Duplicate/reference execution and bisection under one-honest-challenger assumptions | `O2` lane when data availability and challenge windows are acceptable | Requires independent challenger, availability, and often duplicate compute |
| [Repeated-game restaking analysis](https://arxiv.org/abs/2608.09055v1) | History-dependent challenges, reputation-weighted slashing, and stake vesting address failure of one-round incentive arguments | Economic wrapper around repeated sampled/optimistic service | Incentive compatibility is model-conditional, not cryptographic execution soundness; stake identity, collusion, discount factor, and detection response remain assumptions |

The strongest near-term research direction is a **hybrid execution lane**: use transparent
online verification for the dominant linear transitions, explicit local relations for
nonlinear/cache/sampling events, and a proof or dispute mechanism for boundary continuity.
That is a hypothesis to test, not a supported performance claim.

## 7. Required falsification tests

The coupling profile fails if any of these pass:

- a Pearl work root and execution root differ but the cross-evidence binding accepts;
- the execution proof omits `job_id`, `subject_root`, either operand root, or output linkage;
- a registered `h_B` plus garbage or replayed `h_A` is reported as satisfied execution;
- a valid v3 parser accepts v4 bytes, or a v4 result inherits the v3 hardness identifier;
- a post-subject challenge can be predicted before `trace_root` and `output_root` are fixed;
- the receipt reports known full coverage when batching, cache, nonlinear, or sampling
  events are outside the backend relation;
- a valid coupled `WORK+EXECUTION` result is relabelled as arithmetic conformance, physical
  hardware provenance, external demand, or intrinsic usefulness.

## 8. Present evidence boundary

Implemented:

- research schema fields separating receipt scope from native public inputs;
- two-stage intent/job binding;
- deterministic cross-evidence equality validation;
- one structural positive fixture and a mismatched-root negative fixture;
- formal projection, non-implication, and conditional union-bound arguments.
- E-009-R1: a frozen 13-event finite-field causal execution, five authenticated coded-MVM
  relations, eight exact boundaries, post-subject challenges, a four-coordinate receipt,
  a separate verifier implementation, 8/8 mutation rejection, and retained toy costs;
- an R1 conditional five-relation coded-audit bound of approximately `4.99e-25`
  (`2^-80.73`), explicitly excluding hash, Fiat–Shamir/grinding, parser, implementation,
  and Pearl terms.

Not implemented or established:

- verification of a live Pearl certificate in Aeye;
- any realistic or native-serving `R_X` backend beyond the E-009 toy relation;
- an independent v4/B200 arithmetic reproduction;
- a mainnet operand census;
- production-scale overhead, end-to-end security level, privacy, or economic-value
  measurements; E-009's local Python toy costs are retained but not predictive;
- operator or independent-review acceptance.

The immediate technical blocker is authenticated preprocessing: E-009's verifier
recomputes `Q=G^T M` from the full model, which preserves correctness but removes the
intended large-matrix verifier advantage. A scalable profile needs a one-time proof or
authenticated commitment from the exact model/layout root to `Q`, plus a defensible
anti-grinding challenge transform and a version-specific bridge to actual Pearl roots.

That boundary is the reason to show the profile as a research result rather than announce a
breakthrough. An expert can now attack exact relations, retained transcripts, assumptions,
costs, and fixtures instead of debating an undefined phrase such as “verified useful
inference.”
