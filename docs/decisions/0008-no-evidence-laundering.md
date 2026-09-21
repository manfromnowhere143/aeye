# ADR-0008: Evidence Cannot Upgrade an Unnamed Coordinate

Status: `proposed`  
Date: 2026-09-20

## Decision

An evidence object is admissible for a coordinate only if its exact versioned statement
names that coordinate, binds the same subject or verifies aggregate membership, retains all
assumptions, and is appraised through an independent path required by policy.

## Rationale

Most false “verified inference” claims are type errors: work becomes execution, a signed
commitment becomes truth, arithmetic compatibility becomes device origin, or payment-shaped
activity becomes useful demand. Cryptographic validity of the original statement does not
authorize the relabelling.

## Consequence

The verifier reports four results and rejects cross-coordinate evidence laundering. The
formal rule and its limits are in `docs/FORMAL_COMPOSITION.md`; known-bad fixtures exercise
all four coordinates.
