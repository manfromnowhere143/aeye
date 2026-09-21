# ADR-0005: No Pearl Consensus Change Before a Verified Statement Exists

Status: `proposed`  
Date: 2026-08-30

## Decision

Aeye will not propose the submitted 32-byte “V4 lineage fold” during the current phase.
“V4 lineage fold” is a historical Aeye label, not Pearl's later FP8 certificate-v4.

## Rationale

The fold makes an unverified assertion consensus-bound but does not validate execution.
Moreover, Pearl's live monorepo uses certificate V3 for salted INT seed derivation while
draft PIP-3 assigns V3 to an incompatible floating-point protocol. Version allocation and
the exact consensus-checked relation are unresolved.

## Consequence

First validate a sidecar event DAG and independent backend. Any later PIP must use a
domain-separated extension with migration, public-input, and known-bad test vectors.

## 2026-09-20 clarification

Pearl's retained September proposal now assigns certificate-v4 to its FP8 plain-peel
scheme. That does not resolve or revive the lineage-fold proposal. Aeye's current sidecar
profile preserves native Pearl bytes and checks equal operand roots across independent
`WORK` and `EXECUTION` relations. No Pearl consensus field is requested before that
relation is instantiated and reviewed.
