# ADR-0002: Bind a Semantic Event DAG, Not a Layer List

Status: `proposed`  
Date: 2026-08-30

## Decision

Aeye's stable execution object is a content-addressed semantic event DAG. Quantization
boundaries and GEMMs are event types, not the universal commitment granularity.

## Rationale

Continuous batching, prefix/KV-cache reuse, speculative decoding, fused operations,
parallelism, retries, and migration are non-linear provenance structures. An ordered layer
list permits ambiguous or missing parents and couples the protocol to one runtime layout.

## Consequence

Serving adapters must map internal callbacks/kernels into versioned semantic relations.
The mapping itself is untrusted until a verification backend checks it.

