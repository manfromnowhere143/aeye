# ADR-0006: Standards Profile Before a New Wire Format

Status: `proposed`  
Date: 2026-09-20

## Decision

Withdraw `AEB-v0` as an implementation commitment. Use the executable JSON schemas only as
a restricted research interchange. A production candidate must first be expressed as a
profile over RATS conceptual messages, CMW, deterministic CBOR/CDDL, and COSE, with EAT used
only for claims that are genuinely entity-attestation claims. SCITT may register signed
statements and receipts but cannot validate their truth.

## Rationale

RFCs 9334, 9711, 9943, and 9999 already define the relevant roles and message categories.
RFCs 8949 and 9052 provide mature encoding and protection structures. Creating a private
field encoding before performing this crosswalk adds interoperability and parser risk while
making a generic envelope appear more novel than it is.

## Consequence

The research validator checks JSON instances and exact artifact bytes. It makes no wire-
format conformance claim. CDDL, COSE policy, media/profile identifiers, and byte vectors are
blocking work before a production protocol can be proposed.
