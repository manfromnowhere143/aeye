# ADR-0007: Bind Trace and Output Before an Audit Challenge

Status: `proposed`  
Date: 2026-09-20

## Decision

Define an execution subject root over `job_id`, `trace_root`, and `output_root`. Fix this root
before sampling any external challenge used by a sampled or optimistic verification lane.
The final receipt may be sealed later because it adds evidence and appraisal material, but
it may not change the challenged subject.

## Rationale

The earlier sequence fixed `trace_root` before the challenge but sealed `output_root`
afterward, even though output emission belongs to the semantic event DAG. That ordering
allows an under-bound challenge statement and makes output-grafting analysis ambiguous.

## Consequence

The validator recomputes `subject_root` and rejects output mutation or challenge-before-
subject fixtures. Fiat–Shamir or backend-internal challenges remain governed by their exact
proof transcript; this decision concerns external challenge-driven lanes.
