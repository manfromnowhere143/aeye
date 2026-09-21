# Aeye Composition Calculus

Status: `proposed` formal model and proof sketches; not a security proof  
Date: 2026-09-20

## 1. Purpose

The central Aeye question is not whether several evidence mechanisms can be placed in one
envelope. They can. The hard question is whether composition preserves the exact statement,
subject, coverage, assumptions, and failure probability of each mechanism without silently
upgrading one claim into another.

This note defines the smallest calculus needed to answer that question. It is intentionally
backend-neutral. Pearl, a sampled audit, a ZK proof, an arithmetic oracle, an attestation,
and a signed authorization remain different relations after composition.

## 2. Objects

Let the coordinate set be

\[
\mathcal C = \{W,X,S,D\},
\]

where `W=WORK`, `X=EXECUTION`, `S=SEMANTICS`, and `D=DEMAND`.

An execution subject is

\[
\sigma=(I,J,r_R,r_M,r_E,r_D,r_T,r_Y,r_\sigma),
\]

where `I` is the pre-authorization intent and `J` is the final job. The roots bind the
request, model, execution manifest, demand event, event DAG, output, and complete execution
subject. In the research profile:

\[
I=H_{\textsf{intent}}(r_R,r_M,r_E,nonce,freshness),
\qquad
J=H_{\textsf{job}}(I,r_D)
\]

and

\[
r_\sigma=H_{\textsf{subject}}(J,r_T,r_Y).
\]

The demand event authenticates `I`, avoiding the hash cycle that would arise if a signed
event both contained `J` and were hashed into `J`. Both `trace_root` and `output_root` are
fixed before a challenge-driven verifier samples its challenge.

An evidence object is a tuple

\[
e=(id,s_e,u_e,C_e,\mathcal R_e,\pi_e,A_e,K_e,p_e),
\]

with:

- declared receipt scope `s_e` and native public-input vector `u_e`;
- declared coordinate set `C_e ⊆ C`;
- versioned statement relation `R_e` and evidence bytes `π_e`;
- explicit assumption set `A_e`;
- coverage object `K_e`;
- producer `p_e`.

An appraisal is performed by a verifier `v_e` under a versioned policy. Producer and
verifier identities are not evidence of independence; the policy must state the required
independence relation.

`s_e` is placement metadata. It is not evidence that `R_e` authenticated an Aeye job. Only
values in `u_e` are treated as native relation inputs; absent values remain explicit nulls.

## 3. Primitive relations

The intended relations are:

\[
\mathcal R_W(\omega,h_A,h_B;\pi_W),
\]

\[
\mathcal R_X(\sigma,h_A,h_B;\pi_X),
\]

\[
\mathcal R_S(\sigma,P_S,U_S;\pi_S),
\]

\[
\mathcal R_D(I,A,\Pi_D;\pi_D).
\]

`R_W` establishes only the named work statement. For a version-pinned Pearl adapter, `h_A` and
`h_B` are the operand commitments of one accepted winning PoUW instance and `ω` is its
native block/certificate/fork context. Pearl does not natively accept an Aeye job identifier.
Soundness is conditional on the selected protocol version's stated assumption and the
selected consensus/finality rules.

`R_X` must establish a causal path in the committed semantic event DAG from the bound
request and model through the exact events that consume the same `h_A,h_B` operands to the
bound output. Merely copying those roots into a manifest does not satisfy `R_X`.

`R_S` establishes conformance to arithmetic profile `P_S` only on the explicitly covered
event set `U_S`. `R_D` authenticates the pre-authorization intent `I` and the observable
authorization or economic event specified by policy `Π_D`; it does not establish intrinsic
usefulness.

## 4. Admissible evidence

Evidence `e` is admissible for coordinate `c` and subject `σ` only if all of the following
hold:

1. `c ∈ C_e`.
2. `u_e` contains every subject value required by the exact coordinate relation, or the
   evidence declares an aggregate subject and verifies a membership proof. For Pearl
   `WORK`, this is its native work context and operand roots; an Aeye execution subject is
   not invented as a Pearl input.
3. The verifier accepts the exact versioned relation `R_e` over the committed public
   inputs.
4. The verifier is independent to the degree required by the appraisal policy.
5. Every assumption in `A_e` is retained in the result.
6. Coverage `K_e` is expressed over a named universe and unit.
7. Any challenge-dependent evidence binds `r_σ` before the challenge is sampled.

No signature, log receipt, consensus inclusion, or content address waives these conditions.

## 5. Composition rules

For evidence selected to establish a conjunction, the result carries:

\[
A_{\wedge}=\bigcup_i A_i.
\]

Assumptions accumulate; they do not cancel each other.

If every coverage object maps into a common preregistered universe `U`, conjunctive coverage
is

\[
K_{\wedge}=\bigcap_i K_i.
\]

The intersection must be computed over identifiers in `U`. Taking the minimum of two
reported percentages is not generally valid: two mechanisms may cover disjoint events while
both report 90 percent. If the universes cannot be aligned, composite coverage is `unknown`.

Assurance mechanisms are tagged types, not an ordered numeric scale. `sampled`,
`optimistic`, `attested`, and `cryptographic` expose different failure events and trust
assumptions. A hybrid reports the constituent mechanisms and their assumption union; the
word `hybrid` is not itself a stronger guarantee.

For soundness errors `ε_i` defined over compatible experiments, a conservative composition
bound is

\[
\epsilon_{\wedge}\leq\epsilon_{bind}+\sum_i\epsilon_i.
\]

No independence assumption is needed for this union bound. A tighter multiplicative claim
requires a separate proof and may not be inferred from independent-looking components.
Where a component has only a conjectural or empirical security statement, `ε_i` remains
symbolic or unknown.

## 6. No-laundering theorem

**Theorem 1 — Coordinate non-escalation (proposed).** Under the admissibility rules, a
verifier cannot derive `status=satisfied` for coordinate `c` solely from evidence whose
declared coordinate sets omit `c`.

**Proof sketch.** Rule 1 is checked for every evidence reference before the coordinate
appraisal runs. Evidence with `c ∉ C_e` is not an input to the acceptance predicate for
`c`. Therefore an accepting derivation must contain at least one admissible evidence object
whose statement explicitly includes `c`. This is a type-safety property, not a claim that
the included relation is itself sound. The negative fixtures `work-from-demand`,
`semantics-from-work`, and `demand-from-work` exercise the rule.

**Corollary.** A Pearl certificate can remain valid `WORK` evidence while being unusable as
`EXECUTION`, `SEMANTICS`, or `DEMAND` evidence. Composition preserves, rather than repairs,
its boundary.

## 7. Demand-separation impossibility

**Theorem 2 — Demand is not derivable from task-oblivious computation (proposed).** Let a
verifier's view contain the complete work, execution, and semantics transcript but no event
authenticated by a principal or mechanism independent under policy `Π_D`. Then no verifier
can distinguish with non-zero advantage between:

- world `G`: an external qualifying principal authorized the job; and
- world `S`: the worker generated the same request, execution, output, and payment-shaped
  public transcript itself.

**Proof sketch.** Couple the worlds so that every value in the verifier's view is identical.
The distinguishing bit—whether an external qualifying authorization occurred—is outside the
view. Any deterministic verifier returns the same value; a randomized verifier has the same
output distribution. Therefore the advantage is zero. A `DEMAND` statement requires an
additional authenticated event and a policy defining independence, freshness, and any
non-circularity test.

This does not say strong demand is easy once an anchor exists. Sybil control, common
ownership, refunds, subsidies, and off-ledger side payments remain policy and measurement
problems.

## 8. Pearl work-to-execution coupling

Let `ω` be a version-pinned Pearl work context. Define the coupled statement:

\[
\mathcal R_{WX}=\mathcal R_W(\omega,h_A,h_B;\pi_W)\land
\mathcal R_X(\sigma,h_A,h_B;\pi_X).
\]

`R_X` must expose or bind the same operand roots accepted by `R_W` and prove that their
openings occur on a causal path within the committed execution relation. A model-slab
registry match may identify `h_B`; it does not prove `R_X` because registered weights can be
paired with garbage activations or replayed outside the model.

The cross-evidence object checks equality of native inputs `h_A,h_B`; it is not a fifth
claim coordinate and does not verify either relation.

**Theorem 3 — Projection (proposed).** Every accepting `R_WX` transcript projects to an
accepting Pearl `R_W` transcript by discarding `σ` and `π_X`.

**Proof.** `R_WX` is a conjunction containing `R_W` unchanged. Its acceptance predicate
therefore implies the left conjunct. Aeye adds no premise to Pearl's work relation and
cannot weaken or repair Pearl's native assumption.

**Proposition 4 — The extension is strict relative to execution (proposed).** `R_W` does
not imply `R_WX`.

**Witness.** Use any valid Pearl work transcript on arbitrary accepted operands, then pair
it with either (a) no execution transcript, (b) an execution using a different activation
root, or (c) a trace whose bound output is grafted after the work event. `R_W` is unchanged,
while `R_X` rejects or is absent. The retained Usefulness Gap experiment supplies empirical
evidence that accepted work need not be inference; the logical separation itself follows
from the relations' different public inputs and does not depend on that experiment.

Thus Aeye is a strict claim-surface extension, not a claim of being a universally better
work protocol. It preserves a valid Pearl certificate and asks an additional falsifiable
question.

**Theorem 5 — Conditional coupling reduction (proposed).** Suppose:

1. the Pearl work verifier is sound under assumption set `A_W` with error `ε_W`;
2. the execution backend is sound for the exact public-input relation under `A_X` with error
   `ε_X`;
3. the commitment and parser suite is binding and unambiguous with error `ε_B`; and
4. `R_X` requires the same `h_A,h_B` accepted by `R_W`, plus `J` and `r_σ`, on the causal
   path to `r_Y`.

Then an adversary that makes `R_WX` accept while no accepted Pearl work instance is bound to
that execution succeeds with probability at most

\[
\epsilon_W+\epsilon_X+\epsilon_B.
\]

**Proof sketch.** If both relations are sound and the binding is unbroken, the accepted
public inputs identify the same job and operand commitments in both relations. An accepted
counterexample therefore implies either a false accepted work relation, a false accepted
execution relation, or two distinct subjects/operands with the same binding representation.
Apply the union bound.

The complete theorem is not yet instantiated. Pearl's `ε_W` is not presently reduced to a
standard assumption. E-009-R1 implements one finite-field toy instance of `R_X`; no native
Pearl or production-serving instance exists. The value today is an exact engineering
target: a future backend either exposes the required native public inputs or it cannot
close the coupling claim. The original positive fixture demonstrates the structural
interface; E-009 adds one claim-bearing toy execution witness and eight targeted
rejections, without supplying `R_W`.

## 9. Aggregate scope and shared work

Continuous batching and a winning Pearl instance create aggregate evidence. Let aggregate
subject `Σ` contain jobs `J_1,…,J_n`. A request receipt for `J_i` may reference evidence for
`Σ` only with a verified membership relation

\[
\mathcal R_{mem}(\Sigma,J_i,event\_ids,row\_slots;\pi_{mem}).
\]

Membership does not divide an indivisible work claim automatically. Unless a policy defines
and justifies an allocation rule, per-request `WORK` coverage is `unknown` or explicitly
aggregate. `1/n` is not a neutral default when requests have different token counts,
operators, cache reuse, or causal contribution to the winning tile.

## 10. Failure-state preservation

For each coordinate:

- `invalid`: the statement is malformed, under-bound, replayed, or ordered incorrectly;
- `failed`: a completed verifier established that the stated relation is false;
- `unsupported`: no accepted backend/profile covers the requested relation;
- `unknown`: evidence is missing or inconclusive;
- `satisfied`: an admissible verifier accepted the exact relation over declared coverage.

These states are not a total order. In particular, `unknown` is not `failed`, and zero is a
measurement rather than a representation of missing data. Conflicting results are retained
as conflicts; the issuer may not select only the favorable branch.

## 11. What would falsify the calculus

The calculus must be revised if any of the following is demonstrated:

- a coordinate can be satisfied without evidence whose statement names that coordinate;
- aggregate membership can be forged without breaking a named assumption;
- two distinct execution subjects yield one accepted binding without a hash/parser failure;
- coverage intersections are reported correctly without a common universe or explicit
  mapping;
- the Pearl and execution relations accept different operand roots while the coupled native
  public inputs are claimed to be identical;
- an authorization can authenticate the final job without either a two-stage intent or a
  precisely specified non-circular construction;
- an unauthenticated task-oblivious transcript distinguishes external demand from an
  identically distributed self-generated world.

The current validator checks structural instances of these obligations. It does not prove
the cryptographic premises.
