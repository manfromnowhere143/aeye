# Technical Frontier and Construction Target — 2026

Status: `derived` survey plus one `supported` toy construction; no production performance or security result  
Cutoff: 2026-09-21

## Research target

The useful target is not “beat Pearl” or “beat zkML” on one headline. It is to instantiate
the missing execution relation

\[
R_X(\sigma,h_A,h_B;\pi_X)
\]

with the lowest complete system cost compatible with its stated coverage. A successful
backend must bind the Aeye subject and Pearl's clean operand roots, cover the required
serving-event universe, and expose an assurance statement a third party can actually
verify.

The design objective is multi-dimensional:

\[
\min(\text{provider cost},\text{client cost},\text{verifier cost},
\text{latency},\text{bytes},\text{privacy loss})
\]

subject to fixed relation, coverage, soundness, availability, and independence constraints.
A scheme that lowers server overhead by moving the whole model to the client has changed
the cost boundary, not solved it for free.

## 1. Coded sparse verification for linear transitions

The most important new primitive is
[Maverick's](https://arxiv.org/abs/2609.10264v1) delegated matrix-vector verification. For a
public matrix `M`, claimed input/output pair `x,y`, and a linear code with generator
`G ∈ F^{m×N}`, transparent preprocessing computes

\[
Q=G^\top M.
\]

For a random `t`-sparse challenge `e`, the verifier checks

\[
(e^\top Q)x=e^\top G^\top y.
\]

If the code has relative distance `δ`, field `F`, and `ℓ` independent repetitions, the
paper bounds false acceptance for an incorrect MVM by

\[
\epsilon_{\mathrm{MVM}}
\leq p_{\mathrm{code}}+
\left((1-\delta)^t+\frac{1}{|F|-1}\right)^\ell,
\]

where `p_code` accounts for sampling a code below the required distance. With constant
rate/distance and linear-time encoding, online client work is asymptotically linear in the
input and output dimensions rather than the matrix size.

Why it matters for Aeye: a transformer linear layer over token rows is a batch of MVMs.
The verifier can potentially check the exact clean `A,B` relation whose commitments Pearl
exposes while leaving the provider's dominant multiplication close to native.

Why it is not yet `R_X`:

- Maverick's end-to-end design keeps nonlinear operations at the client;
- transparent preprocessing `Q` must be authenticated to the exact model/layout root;
- a private verifier session is not automatically a publicly transferable receipt;
- challenges must be unpredictable after subject commitment, and any Fiat–Shamir or public
  beacon transform needs its own proof and replay domain;
- finite-field MVM equality is not automatically FP8/B200 or INT runtime equality;
- cache, attention, normalization, sampling, retries, and output serialization remain.

The paper's batch protocol can share a primary challenge without a simple union-bound factor
in its stated experiment because acceptance of any fixed incorrect claim implies that claim
passes the shared check. Aeye may not extrapolate this to adaptive multi-request service
without preserving transcript order, code parameters, and the exact adversarial model.

Aeye retains both a small algebraic demonstrator and the completed
[E-009-R1 experiment](E009_RESULT_2026-09-20.md). R1 uses Reed–Solomon/Vandermonde codes
over `2^61−1`, authenticates five `Q=G^T M` objects, derives 80 sparse challenges only
after the complete execution subject, and binds them to eight exact state/nonlinear/decode
events. A separately implemented verifier accepted the unmodified bundle and rejected all
eight preregistered mutations. This is a claim-bearing toy `R_X`; it is still not
Maverick's fast-code implementation, a native Pearl proof, or a production result.

## 2. Version-specific Pearl bridge

Pearl commits clean operands before deriving noise. Aeye needs a versioned bridge relation

\[
B_v(E,h_A,h_B;\pi_B)=1
\]

showing that execution event `E` opened the clean tensors committed by the native Pearl
roots and then applied the exact version-`v` noise, quantization, correction, and tile/work
rules. The bridge differs by lineage:

- certificate-v3: retained INT operand encoding, seed derivation, low-rank correction, and
  exact integer accumulator rules;
- certificate-v4 proposal: clean FP10-like commit encoding, post-noise quantization,
  `Device`/`Quant`, selected-tile B200 arithmetic, and jackpot policy.

Root equality alone checks identity of public inputs. `B_v` checks that those inputs have
the claimed execution meaning. This is the next formal relation to implement on a toy
event; it must not be hidden inside prose or a registry label.

## 3. Nonlinear and stateful boundaries

A low-overhead linear verifier covers most arithmetic but not the inference relation. The
smallest complete hybrid partitions the semantic event universe `U` into explicit sets:

\[
U=U_{lin}\cup U_{nonlin}\cup U_{state}\cup U_{decode}\cup U_{output}.
\]

- `U_lin`: coded MVM/batched-MVM verification;
- `U_nonlin`: lookup or local proof relations for normalization, activation, RoPE, and
  softmax approximations;
- `U_state`: authenticated KV/prefix-cache origin, position, mutation, reuse, and migration;
- `U_decode`: logits transform, sampling/argmax, speculative acceptance, and stop rule;
- `U_output`: token IDs and presentation serialization bound into `subject_root`.

Composite coverage is the intersection of checked event identifiers in a preregistered
universe. It is not the minimum or average of five percentages. If the mappings are absent,
coverage is `unknown`.

## 4. Proof-system techniques that fit the relation

### Sumcheck and lookup-centric proving

[DeepProve](https://eprint.iacr.org/2026/1112) and
[Jolt Atlas](https://arxiv.org/abs/2602.17452v1) demonstrate two current directions: arithmetize a complete
quantized model relation, or organize tensor/ONNX operations as lookup and sumcheck proof
DAGs. Lookups are especially valuable for range-constrained nonlinearities and bit-level
behavior; streaming reduces peak memory by trading extra passes for space.

For Aeye, these are strong lanes only when `intent_id`, `job_id`, `subject_root`, model root,
output root, arithmetic profile, and Pearl operand roots are exact public inputs. A proof of
an otherwise correct ONNX graph that omits cache provenance or output binding proves a
different relation.

### Layer and sequence composition

[zkComposer](https://arxiv.org/abs/2607.08095v1) links contiguous subproofs by reusing commitments to boundary activations. This
is directly useful for Aeye's event DAG: a boundary commitment can be both the output of
partition `i` and the input of partition `i+1`. Layer and sequence partitioning adds
parallelism and lowers per-partition memory, but increases proof/material coordination and
does not itself cover missing events.

### Commit-and-prove consistency

[Artemis](https://arxiv.org/abs/2409.12055v2) shows that efficiently tying a
proof witness to an external commitment is already a developed commit-and-prove SNARK
problem. Its construction reduces equality of internal and externally committed witness
polynomials to a masked evaluation check and supports homomorphic polynomial commitments,
including transparent choices. This is directly relevant prior art for any Aeye model-root
or preprocessing-capsule claim.

It does not eliminate Aeye's native boundary. Pearl exposes keyed BLAKE3 trees over exact
runtime bytes, not a homomorphic polynomial commitment over the companion proof's witness.
Using Artemis therefore requires either changing the native commitment or proving a typed
translation relation between the polynomial commitment and Pearl's exact positions and
bytes. The former is not a Pearl bridge; the latter must be costed and reviewed as part of
the relation. Generic commitment consistency is not an Aeye novelty claim.

### Provenance-guided constraint reduction

[Sound Debloating](https://arxiv.org/abs/2609.10149v1) removes a constraint only when the surviving circuit still entails what
that constraint enforced under its abstract-interpretation/provenance rules. In set terms,
the required safety property is

\[
\{w:w\models C'\}=\{w:w\models C\}
\]

for the relevant relation, despite `C' ⊂ C`. This technique should be applied only after
the Aeye relation and public inputs are frozen. Debloating an already under-bound circuit
makes the wrong proof faster.

## 5. Proposed hybrid: CX-1

`CX-1` is now instantiated for the finite-field toy profile in E-009-R1. The numbered
construction remains the target for any realistic backend; only the explicitly marked R1
subset is implemented.

1. Freeze the complete semantic event universe and two-stage Aeye subject.
2. Retain native Pearl `R_W^(v)` evidence and roots without changing certificate bytes.
3. Authenticate each fixed model matrix and Maverick-style preprocessing object to the
   model/layout root.
4. Commit linear outputs and the whole trace/output subject before deriving public audit
   challenges.
5. Verify `U_lin` with coded sparse checks; bind both Pearl clean-operand roots through the
   versioned bridge `B_v`.
6. Prove or independently recompute `U_nonlin`, `U_state`, `U_decode`, and `U_output` using
   lookup, partitioned proof, sampled, or optimistic subrelations with explicit types.
7. Link every partition through shared boundary commitments and verify request/batch
   membership separately.
8. Emit the four coordinates and their coverage; never a global verdict.

The conservative execution error is

\[
\epsilon_X\leq
\epsilon_{lin}+\epsilon_{nonlin}+\epsilon_{state}+\epsilon_{decode}+
\epsilon_{output}+\epsilon_{partition}+\epsilon_{parser}.
\]

The coupled work/execution error adds Pearl and cross-binding terms:

\[
\epsilon_{WX}\leq\epsilon_W+\epsilon_X+\epsilon_{bridge}+\epsilon_{bind}.
\]

Every term must be numeric under a named experiment or remain symbolic. Different trust
failures—such as one-honest-challenger or vendor attestation—cannot be silently converted
into a field-sized probability.

The source-pinned [PAB-1 construction](PEARL_ACTIVATION_ORIGIN_BINDING_2026-09-21.md)
sharpens the Pearl bridge. Rather than placing a request identifier beside a work proof,
it composes the native proof's selected `hash_a` strip openings with a separate relation
that derives and opens the same bytes at the same positions. This is established
commitment composition applied to Pearl's exact witness boundary, not a new primitive or
implemented security result.

## 6. What would count as a substantive advance

Aeye should claim an advance only if retained experiments establish all of the following:

1. **Strict statement gain:** valid native Pearl work is projected unchanged, while the
   coupled result rejects replay, garbage activations, omitted events, and output grafts.
2. **Transferability:** a third party can appraise the evidence without inheriting an
   undisclosed client secret or live session state.
3. **Complete declared coverage:** every required serving event is included or explicitly
   unsupported; caches and batching are not outside the denominator.
4. **Competitive total cost:** provider, client, verifier, network, storage, preprocessing,
   and privacy costs beat a named full-proof baseline on the same workload.
5. **No semantic downgrade:** optimized proofs accept exactly the frozen relation, not an
   easier quantized/compiled relation presented under the native-runtime name.
6. **Independent rejection:** known-bad artifacts fail in an implementation not controlled
   by the evidence producer.

E-009 now satisfies the strict-statement and complete-declared-coverage conditions for one
toy execution, and supplies public retained bytes that a separate code path can replay. It
does not satisfy the native-Pearl, realistic-semantics, competitive-cost, privacy, or
independent-review conditions. No comparative system-value claim is supported. The precise
claim is that Aeye specifies, and now instantiates once on a toy execution, a broader
machine-testable question than Pearl's native work statement.

## 7. Result and immediate frontier

E-009-R1 completed the intended toy construction with a larger surface than originally
required: 13 explicit events, five coded-linear relations, 80 checks, eight exact boundary
relations, a four-coordinate receipt, a separate verifier implementation, eight mutation
controls, and a complete retained toy cost record. Its conditional five-relation bound is
approximately `4.99e-25`, but only under the declared MDS, Fiat–Shamir, binding, grinding,
hash, and implementation assumptions.

The result exposes the next problem cleanly. The verifier currently recomputes every
`Q=G^T M` from the public model to authenticate preprocessing. That is acceptable for
falsifying the interface, but it touches the full matrices and defeats the intended
large-model verifier advantage. A post-hoc operation count gives 832 field
multiplications for that preprocessing authentication versus 90 for exact replay of the
five `Mx` products; within this narrow count the coded path is 9.244444 times more
expensive and weaker. The 85,584-byte provider bundle is also about 385.5 times the
222-byte toy output. R1's preregistered timing combined challenge generation and response
construction; a later `exploratory-post-hoc` artifact split them by local party, but does
not upgrade the result or measure a production boundary.

The next construction should therefore prove or authenticate `Q` once against the exact
model/layout root and amortize that setup over many requests. It should then add an
anti-grinding challenge analysis, per-request membership under batching, a realistic
quantized attention/normalization profile, and an adapter consuming actual native Pearl
operand roots. Competitive cost must be measured across setup, provider, client/challenger,
verifier, bytes, storage, privacy, and failure recovery on the identical workload.

The proposed relation, model-substitution proposition, sumcheck/PCS target, amortized cost
equation, Pearl adapter, and falsification program are specified in
[Authenticated Preprocessing Capsule](AUTHENTICATED_PREPROCESSING_CAPSULE.md). Maverick
already identifies proof-backed validation as an option for transparent preprocessing;
the Aeye proposal specializes the missing model/layout/root and evidence-composition
contract rather than claiming the underlying algebra as new.
