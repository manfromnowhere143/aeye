# ADR-0003: Commitment-Only Evidence Cannot Satisfy Execution

Status: `proposed`  
Date: 2026-08-30

## Decision

A lineage, trace, row-map, or output root without independent transition verification is
reported as `status=unknown`, `assurance=commitment_only` for `EXECUTION`.

## Rationale

A malicious provider can commit consistently to a fabricated execution story. Binding
prevents equivocation; it does not prove the committed relation is true.

## Consequence

`EXECUTION=satisfied` requires a sampled verifier, one-honest-challenger protocol, reviewed
attestation relation, or sound proof of the exact public-input relation. Aeye v0 may ship a
fast commitment lane only if it preserves this distinction.

