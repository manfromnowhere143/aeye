# ADR-0013: Keep the Protocol Manifest Immutable and Bind Acceptance Externally

Status: `accepted`; incorporated in E-000, pending fresh reviewer readback  
Date: 2026-09-21

## Decision

The E-000 protocol manifest is immutable once submitted for fresh review. It does not
contain paths or digests for the fresh reviewer freeze, source-bound readback, or operator
acceptance record. Those later artifacts bind the manifest from the outside:

1. the fresh reviewer freeze cites the exact SHA-256 digest of the immutable manifest;
2. the source-bound readback cites both the manifest and reviewer-freeze digests;
3. the Phase 6 operator record cites the manifest, fresh review artifacts, registry,
   recipe, implementation trees and toolchains, and complete control matrix;
4. the operator record's UTC timestamp is `T_accept`;
5. the candidate-selection clock begins at `T_accept + 3600 s`.

The candidate-selection rule is copied into the manifest. Its definition of `T_accept`
names the fresh Phase 6 artifacts and does not refer to the predecessor freeze.

The predecessor reviewer freeze and checklist remain content-addressed historical
evidence. Only their terminal-state semantics and named control contracts are imported.
Their phase-numbered gates, acceptance predicate, invalidation predicate, checklist gate
ordering, and reviewer-observation policy are superseded.

For the fresh Phase 6 review, registry identities, immutable revision identifiers, file
and LFS digests, retrieval receipts, tensor inventory, transformation metadata, and other
public metadata may be inspected. Mainnet queries, candidate data, certificates,
`hash_b`, and model-weight bytes remain prohibited.

## Rationale

Embedding a future review digest inside the manifest changes the manifest digest and
creates a non-terminating reference cycle. Importing the predecessor's selection rule by
pointer also imports a definition of `T_accept` tied to the predecessor freeze, while its
phase-numbered predicates contradict ADR-0012. Finally, the predecessor's ban on reading
checkpoint revisions prevents the reviewer from checking the registry that Phase 6 is
required to review.

An immutable protocol object plus external attestations forms an acyclic binding graph.
Explicit historical status prevents obsolete rules from becoming active merely because
their bytes remain retained. A narrow metadata-only review boundary preserves outcome
blindness while making the registry review possible.

## Consequence

- A reviewer can hash and freeze one stable manifest byte-string.
- No operator may fill reviewer fields in place or create a second accepted manifest.
- `T_accept` is undefined until the complete external Phase 6 record exists.
- The predecessor artifacts remain auditable but cannot determine current phase order or
  acceptance semantics.
- Any fresh freeze that imports the superseded predicates or reads prohibited outcome or
  weight bytes fails the protocol.
- This correction does not start E-000, select a candidate, or change its claim ceiling,
  terminal states, controls, one-reveal rule, or security stop.
