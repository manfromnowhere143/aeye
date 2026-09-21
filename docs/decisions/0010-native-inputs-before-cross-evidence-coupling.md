# ADR-0010: Cross-Evidence Coupling Uses Native Public Inputs

Status: `proposed`  
Date: 2026-09-20

## Decision

Every evidence record distinguishes:

- `receipt_job_id`: the issuer's declared placement or scope; and
- `native_public_inputs`: values authenticated by the evidence relation itself.

Absence is encoded as `null`. Receipt placement, a registry label, or repeated prose may
not be substituted for a native proof input.

The first cross-evidence binding profile links Pearl `WORK` evidence to `EXECUTION`
evidence only when both native relations expose identical `operand_root_a` and
`operand_root_b`. The execution relation must also natively bind the receipt's `job_id`
and `subject_root`. This equality witness is structural; it never upgrades either
coordinate and does not verify either cryptographic artifact.

## Rationale

Pearl authenticates its own work context and operand commitments. It does not natively
authenticate an Aeye job, request, model graph, output, or demand event. Pretending that an
Aeye identifier was a Pearl public input would make the composition circular by assertion.

Conversely, a sound execution backend can expose the exact operand commitments used on a
causal path to the output. Equality of those commitments is the narrow bridge required for
the conjunction. It preserves Pearl's native certificate unchanged and makes a mismatch
machine-rejectable.

## Consequence

The receipt schema includes `cross_evidence_bindings`; the validator rejects missing or
unequal operand roots. `pearl-execution-coupled-receipt.json` is a structural positive
fixture, while `pearl-execution-binding-mismatch.json` is its known-bad counterpart. Both
remain synthetic: Aeye has not implemented a Pearl verifier or an execution proof system.

