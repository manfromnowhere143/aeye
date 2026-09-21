# ADR-0011: Appraisers Derive Claims and Preserve Relation Scope

Status: `proposed`  
Date: 2026-09-21

## Decision

A consequential appraiser must construct every reported coordinate result from a
versioned verifier-owned policy and verified facts. It may compare issuer-authored claim
metadata with that policy, but it may not copy coverage, assumptions, assurance,
statement identifiers, evidence references, or coordinate status into its report as
authority. Unknown statement versions and missing assumptions fail closed.

When a frozen verifier is later found to violate this rule, its preregistered bytes and
result remain immutable. A content-addressed successor appraiser composes the frozen
relation replay with the corrected policy, reproduces the defect, and carries an explicit
post-hoc status. It cannot retroactively join or upgrade the original run.

Negative controls are assigned to the smallest relation capable of rejecting them. A
valid activation-origin relation is not required to reject an unbound downstream output
or missing economic authorization. The composite appraiser must instead preserve partial
`EXECUTION` coverage and `DEMAND=unsupported` unless separately named output and demand
relations verify.

## Rationale

E-009-R1's frozen verifier correctly recomputes its toy arithmetic and bindings, but a
post-hoc probe showed that it accepts valid-schema changes to some issuer-authored claim
metadata and then copies that metadata into its report. Inflated coverage, removed
assumptions, and unknown statement identifiers therefore crossed the appraisal boundary
without a finding. Rewriting the frozen verifier would hide the scientific record and
invalidate its preregistered digest.

The same type error appeared in the proposed PAB-1 falsifier list. Activation origin at a
named Pearl boundary does not imply request authorization, useful demand, or correctness
of the later output. Requiring the PAB verifier to reject those cases would silently
enlarge its statement; accepting them as stronger composite claims would launder
evidence. Typed, relation-specific outcomes avoid both errors.

## Consequence

- E-009 retains its frozen verifier and R1 result. The post-hoc v1 claim appraiser is a
  separate executable artifact with independent known-bad metadata mutations.
- Future appraisers derive result vectors from policy and verified relations. Receipt
  claim fields are inputs to compare, never report authority.
- PAB-1 keeps activation-origin falsifiers separate from output-binding and DEMAND
  anti-laundering controls.
- A successful narrow proof remains valid within its coverage when a stronger composition
  is unsupported; the stronger coordinate or scope remains unsupported or unknown.

