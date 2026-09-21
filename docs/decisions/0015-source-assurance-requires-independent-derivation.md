# ADR-0015: Source Assurance Requires Independent Derivation

Status: `proposed`; candidate-blind owner analysis awaiting adversarial readback  
Date: 2026-09-21

## Context

ADR-0014 makes two complete deliveries of every checkpoint shard a prerequisite for T1
transport corroboration. The two deliveries may come from different hosts, TLS sessions,
IP addresses, autonomous systems, and registrants while remaining anchored to the same
publisher revision, object length, and SHA-256 digest.

That distinction is operationally observable, but it does not create a stronger source
statement. Let a publisher revision fix object length `L` and digest `D`. A transfer is
accepted only when

```text
|W_i| = L  and  SHA256(W_i) = D.
```

If two transfers satisfy the predicate, both equal the publisher-associated object under
the same collision and second-preimage assumptions already required by the first
transfer. A second route may reveal unavailability or an implementation fault. It cannot
detect a self-consistent publisher error, establish independent publication, correct a
parser, or validate the transformation that produced the checkpoint.

The September 21 exporter calibration made this cost visible. Its first and only allowed
capture ended before the declared `Content-Length`; the stop rule then prohibited the
second capture and comparison. That terminal failure is retained separately. It neither
supports nor refutes the source-assurance argument.

## Proposed decision

Replace route-based source tiers with two classes that state the actual evidence:

- `S0_PUBLISHER_ASSOCIATED` requires one complete digest-matching stream for every shard,
  retained publisher revision and metadata, same-stream tensor transcripts, independent
  parser replay, and explicit single-publisher trust.
- `S1_INDEPENDENTLY_DERIVED` requires `S0` plus separately pinned upstream material, a
  frozen transformation recipe, a separate implementation, exact reproduced-byte
  equality, and disclosure of the upstream-source assumption.

Route, host, TLS, ASN, and registrant observations remain typed transport evidence. They
may support completeness, availability, and diagnosis. They do not promote `S0` to `S1`.

For E-000's narrow question, `S0` would be the minimum class. A positive comparison would
mean only that a candidate `hash_b` opens to one registered weight byte string associated
with the named publisher revision under the frozen recipe and `job_key`. It would not
establish live runtime participation, model identity beyond those bytes, activations,
inference, hardware origin, usefulness, or demand.

## Migration boundary

This ADR does not change the active experiment. ADR-0014 and manifest digest
`011d3c232ce9638fc265730f01b13dd3e11d87c225d19ad17842a44d7a78ddc5`
remain binding until a reviewed successor is accepted.

If this proposal survives adversarial readback:

1. preserve ADR-0014, the failed calibration, and its terminal disposition as historical
   evidence;
2. issue an immutable `E-000-R2` manifest rather than editing E-000;
3. bind `S0` and optional `S1` before any operator acceptance or candidate selection;
4. re-freeze every imported scope, recipe, implementation, and control artifact; and
5. carry no acceptance state from E-000 into the successor.

## Falsifier

Reject this proposal if a reviewer identifies an adversary within E-000's declared claim
that passes one complete transfer against the frozen publisher digest but is stopped by a
second same-publisher digest-matching transfer, without introducing a new publisher,
digest authority, independent derivation, or verifier. Operational redundancy by itself
does not satisfy this criterion.

## Non-claims

This is same-workstation owner analysis. It is not an accepted protocol decision,
independent review, source authentication, checkpoint correctness, runtime equivalence,
an E-000 result, or evidence for any Aeye coordinate.
