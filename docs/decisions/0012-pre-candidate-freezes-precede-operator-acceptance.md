# ADR-0012: Pre-candidate Freezes Precede Operator Acceptance

Status: `accepted`; incorporated in the E-000 manifest, pending fresh reviewer readback  
Date: 2026-09-21

## Decision

E-000 must not create `T_accept` until every target-independent artifact that can change
the eventual classification has been frozen and tested. The required order is:

1. retain and digest the pinned protocol sources;
2. freeze the finite checkpoint registry, retrieval receipts, tensor inventory, and
   tensor-parallel degree set;
3. freeze every checkpoint-to-runtime transformation parameter with pinned source
   citations;
4. freeze two code-path-independent implementations and their toolchains;
5. pass all 30 fixed controls in both implementations and the Pearl oracle where it has
   authority;
6. obtain a new reviewer readback and an operator record citing the manifest, review,
   registry, recipe, implementation, and control-matrix digests; this time is `T_accept`;
7. begin the future-block rule at `T_accept + 3600 s`, then seal, reveal, and compare in
   the already specified order.

The packet retained at commit `8ed1498e` remains valuable evidence that amendments
A1–A12 were incorporated, but it must not be used to start the selection clock. A revised
manifest and review freeze are required before operator acceptance. No candidate identity,
certificate, or `hash_b` may be inspected while this decision remains proposed.

## Rationale

The retained manifest puts operator acceptance in Phase 2 and the registry, recipe,
implementations, and controls in Phases 3–6. Other retained rules require registry
retrieval before `T_accept` and say that the candidate must not exist when the registry,
recipe, and implementations are accepted. Because `T_start = T_accept + 3600 s`, work on
Phases 3–6 can continue after the deterministic candidate already exists. The current
ordering therefore cannot simultaneously satisfy its temporal-provenance and
pre-outcome-freeze claims.

Moving operator acceptance to the final pre-candidate gate removes the contradiction. It
also makes the operator decision meaningful: the accepted object is a complete,
content-addressed instrument, not criteria whose decisive implementation details may
still change after the future-block clock starts.

## Consequence

- E-000 remains `proposed` and pre-candidate blocked; the sequence is corrected, but the
  previously reviewed digest triple is not an acceptable operator-acceptance target and
  the corrected manifest awaits fresh reviewer readback.
- Registry acquisition, transformation research, implementation, and synthetic controls
  may proceed as explicitly pre-candidate work. They do not start `T_accept` and are not an
  E-000 result.
- The revised manifest preserves the existing terminal states, claim ceiling,
  candidate-selection rule, one-reveal/one-comparison discipline, and security stop while
  reordering the pre-candidate gates.
- Any model retrieval used to qualify a T1 registry entry must complete before the new
  `T_accept`. A later retrieval cannot be backdated or silently substituted.
- The revised packet requires a fresh adversarial review. The implementation owner cannot
  certify the correction or convert machine review into operator acceptance.
