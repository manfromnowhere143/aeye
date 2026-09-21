# ADR-0009: Separate Pre-Authorization Intent from the Final Job

Status: `proposed`  
Date: 2026-09-20

## Decision

Aeye uses two domain-separated identifiers:

\[
I=H_F(\textsf{aeye/intent/v0},r_R,r_M,r_E,nonce,freshness)
\]

and, after a demand event authenticates `I`,

\[
J=H_F(\textsf{aeye/job/v0},I,r_D).
\]

The authorization signs or otherwise authenticates `I`, its policy, principal, scope, and
validity interval. The final `job_id` binds that pre-authorized intent to the retained
`demand_root`.

## Rationale

The earlier draft said both that `job_id` contained `demand_root` and that the demand event
itself bound `job_id`. If the signed demand event is part of `demand_root`, that description
is circular: computing either value requires the other. A fixed-point convention would be
unnecessary, fragile, and incompatible with ordinary signature verification.

The two-stage construction gives the requester a stable pre-execution value to authorize,
then gives the receipt a final value that includes the exact authorization bytes. Domain
separation prevents an intent identifier from being interpreted as a job identifier.

## Consequence

Schemas, validators, and fixtures carry both `intent_id` and `job_id`. Satisfied `DEMAND`
evidence must expose `intent_id` as a native authenticated public input. The
`intent-underbinding` fixture demonstrates rejection when it is changed, and the
`authorization-before-intent` fixture enforces the required ordering.
