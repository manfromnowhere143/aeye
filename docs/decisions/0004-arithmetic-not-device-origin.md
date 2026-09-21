# ADR-0004: Arithmetic Conformance Is Not Device Origin

Status: `proposed`  
Date: 2026-08-30

## Decision

`SEMANTICS` reports arithmetic conformance over covered operations. Physical hardware
provenance is an optional, separate attestation subclaim.

## Rationale

Hawkeye/MMA-Sim-compatible bits can be produced by a CPU, emulator, or different device.
Conversely, a valid attestation does not by itself prove every arithmetic transition.

## Consequence

Receipts must not say “ran on H100” merely because the output matches an H100 profile.

