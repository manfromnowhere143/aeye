# Aeye / Pearl: A Tested Work-to-Execution Relation

Status: `review draft`; not sent; not an endorsement or publication  
Date: 2026-09-20

I began with a narrow question: what does a valid Pearl certificate establish, and what
additional relation is required before that work can be attributed to a specific model
execution?

My present answer is that Pearl and Aeye should not be framed as competing proofs. Pearl
provides the work relation. Aeye adds a separate execution relation over the same native
operand commitments. I have now instantiated that execution-side relation on a frozen toy
causal block; I have not yet connected it to a native Pearl certificate.

For a version-pinned Pearl context `ω_v`, let

\[
R_W^{(v)}(\omega_v,h_A,h_B;\pi_W)=1
\]

be the native accepted work statement. For an Aeye subject `σ` binding a pre-authorized
intent, final job, model/execution manifest, semantic event DAG, and output, let

\[
R_X(\sigma,h_A,h_B;\pi_X)=1
\]

mean that the clean operands committed by `h_A,h_B` were consumed by checked events on a
causal path to the bound output.

The proposed coupled statement is only

\[
R_{WX}^{(v)}=R_W^{(v)}\land R_X.
\]

It has a simple projection property: every accepting coupled transcript contains an
unchanged valid Pearl work transcript. The converse does not hold. Valid Pearl work on
arbitrary or replayed operands, garbage activations, an incomplete graph, or a grafted
output can leave `R_W` true while `R_X` is false or absent.

This distinction matters because writing an Aeye job identifier next to a Pearl certificate
does not create a cryptographic binding. The receipt therefore separates issuer-declared
scope from the values authenticated by each native relation. The first coupling profile
accepts only when Pearl and execution evidence expose byte-identical `h_A,h_B`, and the
execution relation also binds the Aeye `job_id` and `subject_root`.

## Version boundary

I am treating the retained INT certificate-v3 lineage and the September 2026 FP8
certificate-v4 proposal as different protocols.

The FP8 design makes the native work statement more precise: post-noise nonlinear
quantization, `Device`/`Quant` parameters, selected-tile bit-exact recomputation, and
jackpot checks. I do not read those improvements as binding a request, complete model
graph, final output, or external demand. I also retain quantized-subspace hardness as an
explicit informal assumption rather than assigning it a standard security reduction.

## Execution path and first result

The most promising low-server-overhead primitive I found is coded delegated MVM
verification. With transparent preprocessing `Q=G^T M`, a sparse post-commit challenge `e`
checks

\[
(e^TQ)x=e^TG^Ty.
\]

For code distance `δ`, sparsity `t`, field `F`, and `ℓ` repetitions, the retained analysis
bounds false acceptance by

\[
p_{code}+((1-\delta)^t+(|F|-1)^{-1})^\ell.
\]

This is attractive for the linear events that dominate inference, but by itself it is not
a complete public receipt. Nonlinear operations, cache/state transitions, decode policy,
output binding, finite-field versus device arithmetic, challenge transferability, and
batch membership remain explicit parts of `R_X`.

E-009-R1 tests the complete interface on a deliberately small finite-field,
transformer-shaped causal block. Before execution I froze the model, 13-event universe,
field, generator, five code distances, challenge parameters `t=4, ell=16`, source-code
digests, mutation set, and measurement protocol. The provider committed the complete trace
and output before deriving 80 coded challenges. A second implementation, sharing no
provider arithmetic modules, then:

- accepted all five coded-linear and eight exact state/nonlinear/decode/output relations;
- recomputed every request/model/job/trace/output/subject and clean-operand binding;
- rejected all eight preregistered mutations for the required reason; and
- preserved `WORK=unknown`, `EXECUTION=satisfied/sampled`,
  `SEMANTICS=satisfied/hybrid` only for the declared toy profile, and
  `DEMAND=unsupported`.

The five-relation coded-audit union bound is approximately `4.99e-25` (`2^-80.73`),
conditional on the fixed MDS premise, Fiat–Shamir random-oracle and bounded-grinding
model, subject/hash binding, and implementation correctness. It is not an end-to-end
Pearl or system security level.

## What the result changes

The main contribution is no longer only a taxonomy. R1 is a reproducible constructive
witness that `R_X(subject,h_A,h_B)` can bind clean operands into a complete declared
causal path while preventing a successful execution result from laundering a synthetic
WORK object. The retained receipt, transcript, report, challenge equations, measurements,
and mutations are public repository artifacts.

The negative result is also important. The R1 verifier authenticates `Q=G^T M` by
recomputing it from the model, which touches every matrix and loses the hoped-for
large-model verifier advantage. The provider bundle is 85,584 bytes for a 222-byte toy
output. Median local Python timings are 29.458 microseconds for the identical execution
baseline, 112.041 microseconds for execution plus trace/subject construction,
1,461.354 microseconds for challenges plus coded responses, and 1,940.771 microseconds for
independent relation replay. A post-hoc diagnostic split measured 703.584 microseconds for
client challenge derivation and 699.687 microseconds for provider response construction;
it is exploratory and does not upgrade R1. These are diagnostic toy measurements, not
production overhead claims.

Maverick explicitly anticipates this setup boundary: a client can validate transparent
preprocessing once at comparable preprocessing cost, or a publisher can attach a proof of
correct preprocessing. My proposed APC-1 successor does not claim that observation as new;
it asks for the exact proof and model/layout/root composition needed to turn it into a
reusable Aeye evidence object.

No live Pearl certificate, actual Pearl operand root, B200 arithmetic profile, ordinary
softmax transformer, privacy mechanism, mainnet census, or economic demand claim has been
established. Code-path separation is not independent human or institutional review.

## Questions for adversarial review

1. Is the native Pearl relation above stated too weakly, too strongly, or with the wrong
   public-input boundary for either the INT certificate-v3 or proposed FP8 certificate-v4
   lineage?
2. Is equality of clean operand commitments plus a sound causal execution relation the
   minimal bridge, or must `R_X` also expose a Pearl-native network/block/device context?
3. What is the cleanest way to authenticate and amortize `Q=G^T M` against the exact
   model/layout root without making each verifier touch the full matrix or trust the
   provider's preprocessing?
4. Does the public Fiat–Shamir transcript preserve an appraisable coded-MVM soundness
   statement under bounded grinding, or should the construction use an external beacon,
   interaction, polynomial commitment, or different proof entirely?
5. For certificate-v4, what is the smallest executable statement of quantized-subspace
   hardness that permits parameter analysis rather than leaving the premise informal?
6. Can native clean roots be exposed and coupled without duplicating the dominant
   multiplication, weakening privacy, or changing Pearl consensus?
7. Which counterexample most directly falsifies the claim that this is a strict and useful
   extension of Pearl's work statement?

I would rather have one load-bearing premise broken early than preserve a broad claim that
cannot survive exact review. The compact result and replay instructions are in
[`docs/E009_RESULT_2026-09-20.md`](E009_RESULT_2026-09-20.md); the brief has not been sent
and does not attribute any view or endorsement to Pearl or its authors.
