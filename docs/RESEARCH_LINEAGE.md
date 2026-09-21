# Aeye Research Lineage

Status: `observed` repository provenance map  
Cutoff: 2026-09-21

This document records how Aeye's present claims emerged, what superseded what, and which
artifacts carry scientific authority. It is not an authorship or ownership statement and
does not rewrite repository history.

## Authority order

When two artifacts disagree, use this order:

1. `AGENTS.md` defines the current mission, authorization boundary, and research discipline.
2. Accepted architecture decisions define protocol invariants.
3. Schemas and deterministic validators define the machine-enforced research contracts.
4. Current dated specifications, threat models, source ledger, and experiment manifests
   define the active claim surface.
5. Retained experiment bytes and independent appraisal reports define observed results.
6. Historical plans and verdicts remain evidence of reasoning history, not current
   authority.

Generated prose, model review, repository placement, and consensus among documents do not
override retained primary evidence or a failing experiment.

## Development line

| Stage | Artifact or result | Status now | Scientific change |
|---|---|---|---|
| Initial concept | `AEYE_MASTER_PLAN.md` and early Pearl/Hawkeye notes | historical proposal | Introduced broad verified-inference and useful-work ambitions; did not yet separate every claim or retain sufficient evidence. |
| First dated review | `VERDICT_2026-08-30.md` | retained history | Identified promise and major blockers, but included a Pearl checkpoint-to-runtime assumption later contradicted by source inspection. |
| Evidence reconstruction | Source ledger, pinned repositories, retained papers/standards/patches | observed inputs | Replaced memory and secondary description with exact versions, dates, URLs, digests, commits, and evidence scopes. |
| Claim separation | Scientific charter, claims/non-claims, formal composition, protocol schema | active architecture | Separated `WORK`, `EXECUTION`, `SEMANTICS`, and `DEMAND`; prohibited a global verification bit and unknown-to-zero coercion. |
| Pearl version firewall | INT certificate-v3 versus proposed FP8 certificate-v4 profiles | active invariant | Prevented parser, arithmetic, device, wire, and hardness claims from crossing protocol lineages. |
| Binding repair | Two-stage intent → authorization → final job; native-input discipline | active invariant | Removed a demand-hash cycle and distinguished evidence placement from values authenticated by the native relation. |
| Structural falsification | Receipt/report schemas, 18 fixtures, validator | observed structural result | Demonstrated deterministic rejection of 15 designed architectural failures without claiming cryptographic or empirical execution truth. |
| Algebraic interface | Standalone coded-MVM demonstrator | observed limited result | Tested the Reed–Solomon/Vandermonde equation and exact bound on a deterministic relation; explicitly not an execution receipt. |
| E-009-R1 | Preregistered 13-event causal execution and separate verifier | supported toy result | First claim-bearing `R_X(subject,h_A,h_B)` witness: 80/80 coded checks, eight exact boundaries, and 8/8 mutations rejected. WORK remained synthetic/unknown. |
| E-000 static scope | Source-derived 8B layouts and Python/Rust byte identities | owner observed; same-workstation review with amendments | Replaced a generic runtime-slab claim with a finite 3,248-layout `(n,k)` byte registry and kept candidate-dependent `m` separate. |
| E-000 MC1 | Preregistered 15-class real-byte tree calibration | owner result awaiting adversarial readback | Python and Rust reconstructed equal bytes; both keyed roots agreed with pinned Pearl under a synthetic non-candidate key. No certificate was inspected. |
| E-000 exporter calibration | Frozen two-capture plan | terminal failure | The first transfer ended before `Content-Length`; the stop rule prevented capture two and comparison. No tier was assigned. |
| ADR-0015 | Source assurance by publisher association or independent derivation | proposed; no active effect | Challenges route diversity as a scientific source tier and requires an immutable successor if accepted. |
| APC-1 / E-010 | Authenticated preprocessing capsule | proposed, blocked | Formalized why unauthenticated `Q` permits model substitution and split one-time model/setup evidence from repeated online execution evidence. |

## Pearl-specific lineage

Aeye retains two distinct Pearl evidence branches:

```text
Pearl INT certificate-v3
  └─ pinned implementation + PoUW paper v4
     ├─ E-000 registered weight-byte opening: proposed / blocked
     └─ E-001 mainnet census: gated on E-000

Pearl FP8 certificate-v4 proposal
  └─ September 2026 specification + retained open PR #311 patch
     └─ E-008 verifier/B200 parity: proposed / blocked
```

No result may inherit the INT batch-low-rank assumption after parsing FP8 proposal bytes,
or inherit FP8 device/quantization claims after parsing certificate-v3. Neither branch has
yet supplied native operand roots to an Aeye execution receipt.

## E-009 evidence chain

The first claim-bearing result has an explicit byte lineage:

```text
operator instruction within the isolated-research boundary
  → operator authorization record (not DEMAND evidence)
  → frozen input, model, event universe, schemas, generator, verifier
  → retained preregistration digest
  → provider trace, output, audit, and four-coordinate receipt
  → separate code-path replay
  → eight independent in-memory mutations
  → verification report, measurements, and machine-readable result
  → current verdict and README
```

The preregistration digest is
`f47422817c023655d8daeae53f3ad69288b08e2a0be8328e6146bf2ffffef248`.
The main result document records every retained artifact and non-claim.

## Corrections preserved rather than erased

1. The earlier implication that a Pearl `hash_b` generally hashes a checkpoint tensor
   verbatim is contradicted by runtime fusion, slicing, packing, and layout behavior.
   E-000 now asks whether exact public reconstruction is possible under a pinned runtime
   path.
2. A signed demand event cannot bind a final job identifier whose own construction includes
   that event. Aeye now signs/commits the pre-authorization intent and derives the final
   job afterward.
3. A root copied into a receipt is not a public input of the underlying proof. Cross-system
   coupling now requires both native relations to authenticate the same non-null roots.
4. A model name or arithmetic-profile label does not establish semantics. Coverage and
   conformance evidence remain explicit.
5. E-009 advances the execution claim but leaves Pearl WORK unknown. The result is not
   allowed to back-propagate into the missing native work relation.

## Current frontier

E-009 shows that Aeye's central execution relation is implementable on a complete toy
surface. It also shows why the construction is not yet scalable: authenticating
`Q=G^T M` by recomputation touches the full matrix, the public audit is large, and the
challenge transform carries a grinding condition.

The immediate decision is whether E-000's source gate should require route diversity or
independent byte derivation. ADR-0015 states a falsifiable replacement, but the active
manifest cannot be rewritten. If the proposal survives review, E-000-R2 must restart the
freeze and preserve the failed calibration.

Beyond the native opening, the scalable execution question remains authenticated
preprocessing. A one-time capsule must preserve the exact model/layout relation, amortize
setup across real requests, and remain cheaper than a complete proof after every party and
cost is counted. E-010 records that question without pretending the proof backend has
already been chosen.

## External interpretation

The repository contains no independent human or institutional review and claims no
external endorsement. Public-source provenance must not be converted into personal,
institutional, or upstream-project attribution.

The current packet is suitable for adversarial technical review. Any public-release,
collaboration, deployment, security, performance, company, token, or ownership conclusion
requires separate evidence and authorization.
