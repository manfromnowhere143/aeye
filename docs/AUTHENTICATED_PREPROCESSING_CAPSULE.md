# Authenticated Preprocessing Capsule — The Next Aeye Construction

Status: `proposed` mathematical construction; no cryptographic backend selected or implemented  
Date: 2026-09-20  
Working identifier: `APC-1`

## Executive result

E-009-R1 resolves one question and exposes another. Sparse coded verification can bind a
claimed matrix–vector result into a complete causal receipt. It is not scalable if each
independent verifier must recompute

\[
Q=G^\top M
\]

from the full matrix. Conversely, accepting an unauthenticated `Q` changes the verified
statement from “`y=Mx` for the committed model” to “`y=M'x` for some implicit matrix
consistent with the provider's preprocessing.”

`APC-1` separates this into a one-time **model/setup relation** and a cheap repeated
**online execution relation**. The capsule is independent of Pearl. A versioned Pearl
adapter may later prove that Pearl's native clean weight root and the capsule's model/layout
root represent the same operands.

## Prior-art and novelty boundary

[Maverick](https://arxiv.org/abs/2609.10264v1) already defines transparent
preprocessing for public `M`: any client may validate `Q` at cost comparable to
preprocessing and reuse it, or a publisher may attach a proof of correct preprocessing.
That observation is the direct foundation for this note. Sumcheck, multilinear polynomial
commitments, Freivalds-style random linear combinations, authenticated registries, and
amortized setup are also prior techniques.

`APC-1` does not claim to invent those primitives. Its proposed contribution is the exact
Aeye composition contract: bind preprocessing to canonical model bytes and serving layout,
separate one-time setup evidence from repeated execution evidence, include challenge
grinding and every party's cost, preserve a complete semantic event denominator, and admit
a versioned native-Pearl root bridge without letting setup evidence become WORK or
EXECUTION by itself. Whether that composition is novel or useful remains subject to a
broader literature review and experiment.

## 1. The preprocessing-substitution boundary

Let `M in F^(m×n)`, let full-row-rank `G in F^(m×N)`, and let
`Q=G^T M in F^(N×n)`. The online coded check for input `x`, claimed output `y`, and sparse
challenge `e` is

\[
(e^\top Q)x=e^\top G^\top y.
\]

If a verifier authenticates `Q` against `M`, an incorrect `y` induces a nonzero encoded
error and the code-distance analysis applies. If `Q` is supplied without that relation,
the check makes no claim about the committed `M`.

### Proposition: unauthenticated preprocessing permits model substitution

Suppose an online verifier receives `Q`, `x`, and `y`, evaluates only the coded equality
above, and does not verify any binding relation between `Q` and the committed model root.
For any substituted matrix `M'`, the provider can set `Q'=G^T M'` and `y=M'x`. Every coded
equality then holds for every challenge, although `y` need not equal `Mx`.

**Proof.** By substitution,

\[
(e^\top Q')x=e^\top(G^\top M')x=e^\top G^\top(M'x)=e^\top G^\top y.
\]

The acceptance probability is one. Code distance is irrelevant because the claimed output
is a valid codeword for the wrong matrix. Therefore the model-to-preprocessing relation is
not an optimization detail; it is part of `EXECUTION`.

E-009 avoids this attack by recomputing `Q` from `M`. That is correct and intentionally
expensive. A scalable construction must replace full recomputation with evidence, not omit
the relation.

## 2. Two relations, two amortization domains

### Setup relation

For an exact model/layout manifest `L`, matrix `M`, generator profile `g`, preprocessing
`Q`, and commitments `C_M,C_Q`, define

\[
R_{setup}(r_M,C_M,C_Q,g,L;M,Q,\pi_{open})=1
\]

iff:

1. `r_M` binds the canonical model bytes, tensor name, shape, dtype/field encoding,
   quantization parameters, layout, shard coordinates, and version;
2. `C_M` binds the field matrix produced by that exact byte-to-field transform;
3. `C_Q` binds a matrix with the declared dimensions;
4. `G` is derived from the versioned generator profile `g`; and
5. `Q=G^T M`.

The output is an immutable capsule

\[
K=(r_M,C_M,C_Q,g,L,r_{setup},\pi_{setup},t_{setup}),
\]

where `r_setup` binds the complete setup statement and `t_setup` records its evidence type,
verifier, assumptions, and validity interval or revocation policy.

### Online relation

For job subject `sigma`, capsule `K`, input/output commitments `h_A,h_Y`, and challenge
transcript `tau`, define

\[
R_{online}(\sigma,K,h_A,h_Y;x,y,\tau)=1
\]

iff:

1. `K` is accepted under the appraiser's setup policy;
2. `sigma` binds the exact capsule/model revision and execution event;
3. `x,y` open the event's committed input/output roots;
4. the trace and output subject was fixed before challenge derivation;
5. every coded equation accepts under `C_Q`, `g`, `t`, and `ell`; and
6. the event connects to the checked nonlinear/state/decode/output path.

The composed matrix statement is

\[
R_M=R_{setup}\land R_{online}.
\]

Neither relation may verify its own consequence without an independent appraisal path.

## 3. Candidate setup proof

The core identity is a linear tensor relation:

\[
D[j,k]=Q[j,k]-\sum_i G[i,j]M[i,k]=0
\quad\text{for every }(j,k).
\]

A committed sumcheck/PCS construction can reduce the full equality to a random linear
combination. After `C_M,C_Q` are fixed, sample verifier challenges `beta,gamma` and check

\[
\sum_{j,k}\operatorname{eq}(\beta,j)\operatorname{eq}(\gamma,k)Q[j,k]
-
\sum_{i,j,k}\operatorname{eq}(\beta,j)\operatorname{eq}(\gamma,k)G[i,j]M[i,k]
=0.
\]

Sumcheck reduces this identity to a small number of committed multilinear evaluations.
The verifier derives `G` from the public profile rather than accepting a provider-selected
matrix. The exact error is the sum of the polynomial-identity, commitment-binding,
Fiat–Shamir or beacon, parser, and byte-to-field bridge terms.

A simpler bilinear audit illustrates the algebra. For independent random vectors
`r in F^N` and `s in F^n`, check

\[
r^TQs=(Gr)^TMs.
\]

For nonzero `D=Q-G^TM`, a single uniformly random pair misses the error with probability
at most

\[
\Pr[Ds=0]+\Pr[r^TDs=0\mid Ds\ne0]
\leq \frac{2}{|F|}-\frac{1}{|F|^2}.
\]

This is not yet a succinct public proof: without homomorphic or polynomial commitments,
the verifier still needs the full matrices to evaluate both sides. It is the identity a
PCS/sumcheck backend must prove, not a license to claim compression from hashing alone.

## 4. Candidate evidence lanes

| Setup lane | Verifier cost | Trust/privacy boundary | Aeye status |
|---|---:|---|---|
| Full deterministic recomputation | `Theta(mNn)` field arithmetic for the current direct algorithm, plus `Theta(mn+Nn)` entries read and compared | No extra cryptographic assumption; public matrices | Implemented in E-009; correct but not scalable |
| Independent setup auditor plus signed/transparency-logged capsule | Small online | Trust in auditor key, policy, availability, and revocation; auditor sees matrices | Practical conditional lane; not yet implemented |
| Multilinear PCS plus sumcheck | Polylogarithmic/small opening work after proof | Commitment and Fiat–Shamir/beacon assumptions; hiding layer needed for private weights | Strong public lane; backend and exact costs unselected |
| General SNARK/STARK for `Q=G^T M` | Succinct verification | Potentially large one-time prover cost; circuit/field/commitment assumptions | Strong setup lane if amortization wins |
| TEE-generated capsule | Small online | Vendor, firmware, quote binding, rollback, and physical-attack assumptions | Conditional provenance lane, never cryptographic equality by itself |
| Unauthenticated registry entry | Small | Provider or registry can substitute `Q` | Invalid for satisfied `EXECUTION` |

No lane is selected merely because it has the smallest verifier time. The setup statement,
weight privacy, update frequency, proof bytes, prover memory, independent verification,
and amortized request count must be fixed first.

The distinction between arithmetic and data volume is load-bearing. Directly recomputing
`Q=G^T M` forms `N*n` outputs, each with an `m`-term dot product: `m*N*n` field
multiplications and `N*n*(m-1)` field additions, before comparison. The earlier
`Theta(mn+Nn)` expression described only the matrix entries read and compared; it
understated the implemented arithmetic. With E-009's `N=2m`, direct preprocessing is
`Theta(m^2 n)`. Across its five frozen matrices, the observed operation count is 832 field
multiplications for `Q`, versus 90 for exact replay of the five `Mx` products. Those counts
exclude additions, hashing, parsing, and other work and do not predict large-model timing.

## 5. Amortized cost criterion

For `K` executions using one immutable capsule, report

\[
C_{per\ request}(K)=
C_{online}+C_{verify}+C_{network}+C_{storage}+C_{privacy}
+\frac{C_{setup}+C_{setup\ verify}}{K}.
\]

Both the observed request count and the assumed amortization horizon must be reported. A
large setup cost divided by a hypothetical future volume is not an observed result. Model,
adapter, quantization, layout, sharding, generator, or commitment changes invalidate the
capsule unless the relation explicitly proves an allowed transformation.

The stop criterion is direct: if the capsule cannot be authenticated and amortized below a
named complete-proof comparator on the same model/workload while preserving the same
relation, the coded online lane has no demonstrated system advantage.

## 6. Public challenge without hidden grinding

E-009 derives the online challenge from the final subject with SHA-256. Public replay is
straightforward, but a malicious provider can query many candidate subjects before
publishing one. A complete bound needs one of:

1. a random-oracle Fiat–Shamir theorem with explicit maximum query/grinding factor `q_H`;
2. an unpredictable external beacon value finalized after the subject commitment;
3. an interactive, authenticated challenger whose signed challenge is retained; or
4. a proof system whose soundness already covers non-interactive challenge generation.

If the base false-accept probability is `epsilon`, a coarse bounded-query analysis may
carry a term on the order of `q_H epsilon`; the exact reduction depends on the transcript
and adversarial model. Aeye must never present the base field/code bound alone as the
public-transcript security level.

## 7. Batched online relation

Continuous batching must not erase per-request membership. Let committed rows
`(x_b,y_b)` belong to jobs `J_b`. After every row, membership map, and final subject is
fixed, sample independent aggregation coefficients `alpha_b` and a coded challenge `e`.
A candidate shared check is

\[
(e^TQ)\left(\sum_b\alpha_bx_b\right)
=
e^TG^T\left(\sum_b\alpha_by_b\right).
\]

This can amortize matrix-side work, but it is valid for a request receipt only if the
aggregate commitment proves the row's job, event ID, token position, attempt, and causal
parents. The aggregation coefficient and coded challenge must be sampled after the batch
membership map is committed. A successful aggregate does not authorize dividing one
indivisible WORK claim equally among requests.

## 8. Pearl adapter

The capsule core should not depend on Pearl. A version-specific adapter may add

\[
R_{bridge}^{(v)}(\omega_v,h_A,h_B,r_M,C_M;\pi_B)=1,
\]

establishing that Pearl's native clean operand encodings and the capsule/execution
encodings represent the same tensors under the exact version-`v` layout and quantization
rules.

For certificate-v3 this includes the retained INT runtime slab, fusion/slicing/packing,
noise, correction, and parser rules. For proposed certificate-v4 it includes the distinct
clean encoding, post-noise quantization, `Device`/`Quant`, selected-tile arithmetic,
ticket, and jackpot policy. One adapter cannot silently cover both lineages.

The composed statement becomes

\[
R_W^{(v)}\land R_{bridge}^{(v)}\land R_{setup}\land R_{online}.
\]

Projection preserves Pearl's accepted native work statement. Failure of the bridge, setup,
or execution relation cannot be hidden by a valid `R_W`.

## 9. Conditional error budget

A conservative capsule/execution bound is

\[
\epsilon_X\leq
\epsilon_{setup-proof}+
\epsilon_{setup-bind}+
\epsilon_{online-code}+
\epsilon_{challenge}+
\epsilon_{event-boundaries}+
\epsilon_{membership}+
\epsilon_{parser}.
\]

Pearl composition adds

\[
\epsilon_{WX}\leq
\epsilon_W^{(v)}+epsilon_{bridge}^{(v)}+epsilon_X+epsilon_{cross-bind}.
\]

Terms derived from trust, empirical conformance, one-honest-party assumptions, or
availability are not field probabilities and must remain typed separately rather than
being forced into one numeric sum.

## 10. Falsification program

`APC-1` fails if any of the following accepts:

- a capsule for `M'` verifies under the committed root of `M`;
- changing one `Q` coordinate leaves the setup proof valid;
- changing dtype, quantization, layout, shard, padding, or generator version preserves a
  capsule without an explicit allowed-transform proof;
- one capsule is replayed across an incompatible model revision;
- the provider can choose batch membership or subject bytes after observing the challenge;
- an aggregate check passes while one request's row map or causal parent is grafted;
- an actual Pearl root is joined by receipt placement rather than the native bridge;
- setup cost, verifier preprocessing, proof bytes, model-update frequency, privacy loss,
  or failed-capsule recovery is omitted from the comparison;
- a conditional auditor/TEE lane is labelled cryptographic without its trust assumptions.

## 11. Minimum experiment before implementation claims

The proposed successor to E-009 should freeze, before execution:

- one public matrix family large enough for setup cost to dominate toy noise;
- exact field, layout, generator, commitment, and proof backend;
- public versus private-weight policy;
- setup verifier and online verifier implementations with separate code paths;
- challenge source and explicit grinding/query model;
- capsule update/revocation policy and amortization counts `K`;
- one full-proof or deterministic-recompute comparator on identical matrices and rows;
- mutations for model, layout, `Q`, generator, capsule revision, challenge order, batch
  membership, output, and coordinate laundering;
- provider, setup prover, setup verifier, online client/challenger, online provider,
  receipt verifier, network, storage, privacy, and recovery costs.

No positive run should begin until a concrete PCS/proof/auditor lane and comparator are
selected. E-009 shows the relation is worth testing; it does not choose the cryptographic
backend.

## 12. Why this can be independent of Pearl

`APC-1` authenticates a model-derived preprocessing artifact and binds repeated execution
events to it. Any work proof, attestation, optimistic dispute, or payment system can attach
as a typed adapter. Pearl is especially interesting because it already exposes a
matrix-work relation and clean operand commitments, but Aeye's central value is the
composition discipline:

- model/setup evidence cannot become execution evidence;
- execution evidence cannot become physical-work evidence;
- arithmetic conformance cannot become device origin;
- authorization cannot become intrinsic utility;
- no adapter controls the final scientific verdict.

That makes the capsule direction a plausible independent research program. Its merit will
be decided by a concrete authenticated-setup experiment and complete cost comparison, not
by a new name.
