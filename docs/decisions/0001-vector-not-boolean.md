# ADR-0001: Verification Is a Four-Coordinate Vector

Status: `proposed`  
Date: 2026-08-30

## Decision

An Aeye verifier returns independent `WORK`, `EXECUTION`, `SEMANTICS`, and `DEMAND`
results. Each result carries status, assurance, coverage, assumptions, evidence, and
diagnostics. The protocol has no global `verified` bit.

## Rationale

Every retained primitive covers a strict subset: Pearl does not bind full execution;
proofs of a circuit do not prove physical work or hardware; arithmetic replay does not bind
a request; economic events do not prove utility. A Boolean output would necessarily hide
one of those gaps.

## Consequence

Consumers must state their acceptance policy over the vector. Two policies can reach
different operational decisions without changing the underlying scientific report.

