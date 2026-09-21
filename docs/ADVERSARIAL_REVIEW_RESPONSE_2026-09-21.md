# Adversarial Review Disposition — E-009-R1

Status: `observed` reproduction, `derived` disposition, and `proposed` next actions as labelled  
Date: 2026-09-21  
Reviewed input: separate same-workstation machine-review session and its retained scratch probe  
Independence ceiling: machine review on the same workstation; not human, institutional, or cryptographic independence

## Verdict

The review's central conclusion is accepted.

E-009-R1 is a careful, preregistered toy interface witness. It is not a Pearl result, a
production security result, a performance result, or evidence that Aeye is presently a
frontier verifiable-inference system. Its coded-linear core is established technique. Its
scientific value is that it makes the proposed execution relation executable and
falsifiable while preserving the four-coordinate claim boundary. That value should not be
presented as a novel cryptographic primitive.

The present repository should therefore not be sent to Pearl with E-009 as its headline.
The next external brief should lead with either a reproducible measurement of Pearl's own
public system or a source-pinned statement about Pearl's own proof relation that the
current protocol does not express.

## Finding-by-finding disposition

| Review finding | Disposition | Evidence and consequence |
|---|---|---|
| The coded check is standard | `accepted / derived` | Reed–Solomon/Vandermonde encoding, a random linear equality, repeated sparse challenges, and Fiat–Shamir-style derivation are prior technique. Aeye makes no primitive-novelty claim. |
| R1 preprocessing authentication costs more than exact replay | `accepted / observed` | Reproduced count: 832 field multiplications to recompute the five `Q=G^T M` objects versus 90 to recompute all five `Mx` products exactly, a 9.244444× ratio within that operation-count model. Hashing, additions, parsing, and other work are excluded. At R1 scale the coded path is strictly dominated; it is only an interface rehearsal. |
| The eight frozen mutations do not model a fully self-consistent issuer | `accepted with qualification / observed` | The additional post-hoc probe regenerates every downstream event, root, subject, and challenge after changing one `q_linear` coordinate, then falsifies the retained acceptance fields. The verifier rejects through `CODED_LINEAR_REJECT` and three coded-transcript aggregate diagnostics. No binding, ordering, or exact downstream-event diagnostic fires. This narrows the interpretation of the eight controls; it does not falsify the coded relation. |
| `EXECUTION=satisfied` is trivial in this public toy setting | `accepted as a system-value criticism; not a logical contradiction` | The verifier has the full public model, input, and trace. The status means only that the declared sampled toy relation accepted. It does not mean physical execution occurred, that a private prompt was bound, or that a Pearl activation root was opened. Exact replay is stronger and cheaper here. |
| The WORK bridge is synthetic | `accepted / observed` | Provider generation creates the synthetic WORK object from the same `q_linear` event. It tests the schema and equality contract, not Pearl's actual keyed BLAKE3 strip commitment. Native coupling remains unsolved and unpriced. |
| The implementation is not independently reviewed | `accepted / observed` | Separate provider and verifier code paths reduce one class of shared execution error. They do not establish independent authorship, custody, organization, hardware, or peer review. The adversarial readback remains machine review on the same workstation. |
| The tone should de-emphasize the toy bound and architecture | `accepted / derived` | The `2^-80.73` conditional arithmetic is retained because it is correct under its stated model, but it is not the headline security posture. The public-model cost dominance and missing native Pearl relation come first. |
| The frozen verifier trusts some issuer-authored claim metadata | `accepted / observed` | Independent replay confirmed that valid-schema changes could inflate `EXECUTION`/`SEMANTICS` coverage, remove their assumptions, or replace their statement identifiers without a finding; the verifier then copied `claimed_results` into its report. The frozen verifier is preregistered and remains byte-for-byte unchanged. A versioned post-hoc overlay now allowlists the claim/evidence contract and derives its report vector from verifier-owned policy. |
| The preprocessing note understates direct recomputation cost | `accepted / corrected` | The former `Theta(mn+Nn)` entry count was not the arithmetic cost of forming `Q=G^T M`. The direct E-009 implementation performs `Theta(mNn)` field arithmetic; with `N=2m`, this is `Theta(m^2 n)`. The capsule now separates field operations from entries read and compared. |
| PAB-1 falsifiers included stronger DEMAND and output claims | `accepted / corrected` | A valid activation-origin proof need not reject absent demand authorization or a grafted downstream output. Those cases now test the composite appraiser: it must preserve `DEMAND=unsupported` and partial execution coverage unless separate relations verify the stronger claims. |

## Reproduced claim-metadata appraisal gap

The executable post-hoc overlay is
[`experiments/e-009/posthoc_claim_appraisal.py`](../experiments/e-009/posthoc_claim_appraisal.py).
Its retained output is
[`posthoc-claim-appraisal.json`](../experiments/e-009/artifacts/posthoc-claim-appraisal.json).

The frozen verifier, whose preregistered SHA-256 digest remains
`9c4f6f4eed0c490b8261214a694db133ba33575f0fbe34c318cb6a853de7cf31`, accepts the
unchanged bundle and the three claim-metadata mutations. The v1 overlay accepts the
unchanged bundle but rejects the mutations with `CLAIM_COVERAGE_MISMATCH`,
`CLAIM_ASSUMPTION_MISMATCH` / `EVIDENCE_ASSUMPTION_MISMATCH`, and
`EVIDENCE_STATEMENT_MISMATCH`. An incorrect-output control is rejected by both paths.

The repair is deliberately compositional. It first requires the frozen relation replay,
then checks a content-addressed policy contract, and constructs the result vector from
that policy and the verifier's frozen 13-event universe. No `claimed_results` field is
copied from the receipt. This closes the reproduced appraisal gap for E-009-R1; it does
not retroactively join the preregistration or establish exhaustive malicious-provider
security.

## Reproduced post-hoc probe

The executable probe is
[`experiments/e-009/posthoc_adversarial_probe.py`](../experiments/e-009/posthoc_adversarial_probe.py).
Its retained output is
[`posthoc-adversarial-probe.json`](../experiments/e-009/artifacts/posthoc-adversarial-probe.json).

The attack changes `q_linear[0]` from `4` to `5`, recomputes the causally downstream
trace and all commitment/challenge material, and lies in the retained coded-check result
fields. Sixteen of the 80 coded equations naturally reject. The independent verifier
reports exactly:

```text
AUDIT_ACCEPTANCE_MISMATCH
CODED_CHECK_TRANSCRIPT_MISMATCH
CODED_LINEAR_REJECT
RELATION_ACCEPTANCE_MISMATCH
```

An honestly regenerated control produces no findings. The probe is
`observed-post-hoc`; it neither joins the eight preregistered mutations nor upgrades R1.

The correct interpretation is two-sided:

1. The verifier does not trust issuer-authored acceptance fields and catches the false
   linear relation.
2. Once a provider regenerates a self-consistent downstream trace, the binding, ordering,
   and exact-event checks provide no additional rejection for that attack. The linear
   relation's sampled soundness is load-bearing.

## What remains supported

- R1 was preregistered before execution and its frozen bytes remain unchanged.
- The independent code path accepts the unmodified public toy bundle.
- The five coded relations accept 80/80 checks; the eight exact relations accept; all
  eight preregistered targeted mutations reject with their required codes.
- The post-hoc self-consistent forgery rejects through the expected coded relation.
- The conditional coded-audit arithmetic is correct under the named challenge, code, hash,
  grinding, parser, and verifier assumptions.
- The only defensible vector remains `WORK=unknown`,
  `EXECUTION=satisfied/sampled`, `SEMANTICS=satisfied/hybrid` for the declared toy profile,
  and `DEMAND=unsupported`.

Nothing in this review adds a native Pearl certificate, private-input proof, realistic
transformer semantics, GPU fidelity, demand evidence, competitive cost, or independent
peer review.

## Ranked next work

### 1. E-000 public-weight opening and census

Status: `proposed`; execution remains blocked until a separate reviewer freezes the final
acceptance checklist and the operator accepts it.

Reconstruct actual certificate-v3 `hash_b` candidates from published checkpoint revisions
through Pearl's pinned fusion, slicing, sharding, packing, padding, keyed-Merkle, and seed
derivation path. Then classify a preregistered mainnet sample only as `MATCH`,
`IN-COVERAGE-NO-MATCH`, `OUT-OF-COVERAGE`, or `UNRETRIEVED`. The headline quantity is the
whole-sample lower bound `MATCH / sampled`; coverage and retrieval remain adjacent.

This would be an empirical result about Pearl rather than another architecture claim.

### 2. Pearl-native execution-binding memo

Status: `proposed construction now specified`; not implemented.

The [Pearl activation-origin binding note](PEARL_ACTIVATION_ORIGIN_BINDING_2026-09-21.md)
now states Pearl's exact certificate inputs and `hash_a` relation at the pinned commit. It
also corrects an overbroad formulation in the review: the block header contains a
transaction Merkle root and enters `job_key`, so the native statement is not wholly
unrelated to request-capable commitments. What remains absent is the relation that proves
transaction inclusion, request authorization and chronology, or derivation of the
selected activation bytes from that request.

The proposed PAB-1 companion relation terminates at Pearl's actual selected strip prefixes
under the same keyed root and positions. Its disclosed-input and zero-knowledge lanes,
hash-cost formulas, omitted scale/profile material, soundness budget, and required
falsifiers are specified. This is a source-grounded design result, not a completed proof or
security claim.

### 3. Authenticated preprocessing only after the preceding boundaries

Status: `proposed`.

APC-1 remains a legitimate successor experiment, but sumcheck, polynomial commitments,
and amortized preprocessing are prior techniques. Its possible contribution is a precise
composition contract and an end-to-end measured system boundary, not a new primitive.

## Role decision

The reviewer and implementation owner should not write each other's evidence.

- The separate reviewer lane should retain its own review and freeze the E-000 acceptance checklist
  before any candidate block or checkpoint is inspected. That preserves the limited
  separation the workflow actually has.
- The Aeye implementation owner should retain this response, the reproduced probe, the
  Pearl-native binding analysis, and—only after the checklist is frozen and accepted—the
  E-000 instrument and replay package.
- A human cryptographer or Pearl engineer should later review the result. Neither code-path
  separation nor a second model is a substitute for that review.

No external contact is authorized by this document. Any plausible upstream vulnerability
stops at a minimal private reproduction and follows Pearl's security channel.
