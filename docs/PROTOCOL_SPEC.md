# AER-v0 Protocol Specification

Status: `proposed`; research schemas and structural validator implemented; no wire-format,
cryptographic, scientific, performance, or security acceptance  
Name: **Aeye Evidence Receipt**, deliberately not “execution proof”

## 1. Protocol output

An AER is a content-addressed envelope containing immutable manifests, evidence references,
and four independent verification results. A verifier evaluates each coordinate and emits
a `VerificationReport`; it does not trust the results embedded by the issuer.

```
AER = Header
    + RequestIntent
    + ModelManifest
    + ExecutionManifest
    + DemandEvent
    + TraceDescriptor
    + OutputManifest
    + EvidenceIndex
    + CrossEvidenceBindings
    + ClaimedResultVector
```

`ClaimedResultVector` is an issuer assertion. Only the independently produced
`VerificationReport` is a verifier result.

## 2. Standards and encoding posture

`AEB-v0` is withdrawn as an implementation commitment by ADR-0006. Aeye maps its roles and
messages to the RATS architecture. A future production profile should use CMW to identify
conceptual messages, deterministic CBOR/CDDL for representation, and COSE for protection.
EAT is reserved for actual entity-attestation evidence. SCITT may provide transparent
registration and non-equivocation, never truth.

The checked JSON schemas are a restricted **research interchange**. They make protocol
invariants executable and fixtures reviewable, but they are not a production wire format or
a claim of RATS, EAT, CMW, COSE, or SCITT conformance. The standards crosswalk records the
remaining profile and registration work.

The research fixture profile uses one unambiguous framing function for bindings over
already-computed byte strings:

```
H_F(domain, x[0..n]) = SHA-256(
    ASCII(domain) || 0x00 ||
    Σ (len(x[i]):u64 big-endian || x[i])
)
```

It forbids implicit string concatenation. Manifest-root serialization is deliberately not
accepted yet; a future CDDL profile and positive/negative byte vectors must define it.
Pearl commitments are never rewritten. The Pearl adapter must reproduce the exact
certificate-version BLAKE3/Merkle derivation and link the native 32-byte value as evidence.

## 3. Job binding and sequence

```
request_root   = Digest_P("aeye/request/v0", RequestIntent)
model_root     = Digest_P("aeye/model/v0", ModelManifest)
execution_root = Digest_P("aeye/execution-manifest/v0", ExecutionManifest)
intent_id      = H_F("aeye/intent/v0",
                     [request_root, model_root, execution_root,
                      client_nonce, UTF8(freshness_domain)])
demand_root    = Digest_P("aeye/demand-event/v0",
                          DemandEvent authenticating intent_id)
job_id         = H_F("aeye/job/v0", [intent_id, demand_root])
subject_root   = H_F("aeye/execution-subject/v0",
                     [job_id, trace_root, output_root])
```

`P` is the declared manifest-serialization profile. The research fixtures supply synthetic
roots; they do not instantiate `Digest_P`. No production manifest profile is accepted until
the CDDL/COSE work and byte-vector review in ADR-0006 are complete.

The two-stage identifier is mandatory. A demand event cannot both contain the final
`job_id` and be hashed into that same identifier without a circular construction. The
requester authenticates `intent_id`; `job_id` then binds the exact retained demand-event
bytes. ADR-0009 records the correction.

Required ordering:

```
t0  RequestIntent, model/execution manifests, arithmetic profile, appraisal policy,
    nonce, freshness and intent_id fixed
t1  DemandEvent authenticating intent_id fixed; job_id fixed
t2  execution complete; trace_root, output_root and subject_root fixed
t3  unpredictable external audit challenge sampled (if applicable)
t4  evidence/proof generated and appraised
t5  final envelope protected/sealed; optional transparency registration
```

A challenge at or before `subject_root` is fixed, or an execution/arithmetic/appraisal
profile selected after `intent_id`, makes the affected coordinate `invalid`. The final envelope may add
evidence and appraisal results after `t3`, but it cannot change the challenged subject.
Fiat–Shamir and backend-internal challenges follow the exact proof transcript rather than
this external-challenge sequence.

## 4. Stable execution object

The protocol commits to an **execution-event DAG**, not vLLM callbacks and not “one layer.”
An event has:

```
event_id, job_id, event_type, logical_op_id, attempt_id,
ordered_parent_event_ids, external_input_roots,
input_tensor_roots, output_tensor_roots,
request_membership_root, cache_provenance,
kernel_profile_id, arithmetic_profile_id,
start_sequence, end_sequence, event_metadata_root
```

Required event classes include request admission, tokenization, model inputs, cache
read/write, transformations, matrix operations, attention/nonlinear operations, sampling or
argmax, stop decision, and token/output emission. A serving adapter may fuse events
physically, but its manifest must map the fusion back to a stable semantic relation.

Continuous batching uses a membership commitment from tensor rows/token slots to
`(job_id, token_position, attempt_id)`. It is an assertion until a verification backend
checks the openings and transitions. Prefix/KV cache reads are authenticated external
parents with origin job/model/position and reuse policy; they are not invisible shortcuts.

Speculative decoding records proposed, accepted, and rejected tokens. Retries, rebatches,
migrations, tensor/pipeline/expert parallel edges, and LoRA/adapters are explicit events or
manifest references. The final output is token IDs plus decoding/serialization policy,
not text alone.

## 5. Evidence records

Every evidence object binds:

```
evidence_id, evidence_type, statement_id, producer_id,
receipt_job_id, native_public_inputs, claim_coordinates, assurance,
scope and aggregate_membership_ref,
artifact_digest, assumptions, coverage
```

`receipt_job_id` is issuer-declared placement. `native_public_inputs` records only values
authenticated by the evidence relation itself, with explicit nulls for absence. The
validator may not infer that Pearl, a registry, or a commitment authenticated an Aeye
subject merely because the evidence appears inside its receipt.

The independent `VerificationReport` separately binds verifier identity, appraisal-policy
identifier and digest, receipt digest, per-coordinate results, and conflicts. Keeping the
verifier out of the producer's evidence assertion prevents a self-declared verifier field
from masquerading as independence.

Evidence cannot be reused across jobs unless its statement explicitly declares an
aggregate scope and provides a membership proof. Cross-network, cross-epoch, or
cross-protocol replay is rejected.

## 6. Pearl work adapter

For an accepted Pearl block, retain:

- chain/network identifier, height, block hash, header and finality checkpoint;
- certificate version and fork-rule version;
- exact public-data and proof-commitment bytes;
- mining configuration, `m`, `n`, `k`, operand roots, jackpot hash;
- reconstructed `job_key` and seed-derivation mode;
- inclusion/opening linking the relevant operand root to an Aeye event when available.

The adapter reports `scope=winning_pouw_instance` or an explicit aggregate scope. It must
not report per-request `WORK` merely because the request shared a batch or epoch. The
adapter also pins the Pearl lineage: the retained INT certificate-v3 rules and the proposed
FP8 certificate-v4 rules have different parsers, arithmetic profiles, and hardness
assumptions. They are not interchangeable.

### Pearl work-to-execution coupling

A cross-evidence binding may link one Pearl `WORK` object to one independent `EXECUTION`
object only when both relations expose identical native `operand_root_a` and
`operand_root_b`. The execution relation must additionally expose this receipt's `job_id`
and `subject_root`. The equality check does not verify either artifact and does not create a
new result coordinate. The exact relation, reduction target, and current 2026 backend
options are in `PEARL_COUPLING_PROFILE.md`.

### Registered-weight observation (`MOBS-v0`)

The model-operand binding scanner is a measurement adapter, not “proof of model execution.”
For preregistered block `b` and registry `R` it emits exactly one bucket:

- `MATCH`: at least one canonical slab reproduces `hash_b` under the exact job key;
- `IN_COVERAGE_NO_MATCH`: exhaustive enumeration for the observed shape, no match;
- `OUT_OF_COVERAGE`: shape absent or required layout/revision outside registry scope;
- `UNRETRIEVED`: required certificate bytes unavailable.

Headline lower bound: `|MATCH| / |preregistered sample|`. A covered-sample conditional rate
may be secondary only with retrieval and coverage adjacent. `MATCH` is conditional on hash
security and registry integrity. It proves registered-slab participation, not activation
correctness, layer completeness, output correctness, or useful demand.

Registry entries bind source revision, bytes digest, tensor name, logical fusion, shape,
dtype, layout, TP/EP configuration, transformation recipe, and trust tier. Floating
revisions are invalid. Trust levels distinguish source-authenticated bytes from independently
reproduced transformations; no fixture can detect a malicious but internally consistent
publisher.

## 7. Verification backends

Backends implement the same versioned statement relation; proof encoding is replaceable.

```
verify(statement_id, public_inputs, evidence) ->
    {status, assurance, coverage, assumptions, diagnostics}
```

- `C0`: checks encodings, signatures, roots, sequence, and openings only.
- `A1`: samples after `trace_root`; opens and recomputes local transitions. The report must
  include adversarial detection probability, not just sample count.
- `O2`: duplicate/referee path, with challenger identity, availability bond, and challenge
  window in the assumptions.
- `T2`: verifies an attestation chain and nonce/job binding, keeping vendor/firmware and
  physical-security assumptions visible.
- `Z3`: verifies a proof of the exact versioned execution relation over committed public
  inputs; native-vs-quantized semantics are part of the statement ID.

`C0` may support `WORK` or `DEMAND` binding facts, but cannot make
`EXECUTION=satisfied` by itself.

## 8. Arithmetic profiles

An arithmetic profile is an executable relation plus evidence, not a marketing hardware
name. Hawkeye and MMA-Sim can populate candidate instruction profiles. A profile enters
`accepted` only after independent real-device conformance over ordinary, adversarial, and
special-value vectors with exact binary/toolchain retention.

Full `SEMANTICS` coverage is the ratio of verified semantic events to all required semantic
events, weighted only by a preregistered unit (`events`, `operations`, or arithmetic work).
Unsupported glue remains `unsupported`; it is never inferred from covered GEMMs.

## 9. Demand policies

The receipt names a policy, for example:

- `AUTH_ONLY`: valid external signature over `intent_id`, principal/scope, validity, and
  freshness policy, with the retained event root bound into `job_id`;
- `ESCROWED_FEE`: authorization plus non-reverted escrow/payment event;
- `INDEPENDENT_PRINCIPAL`: requester and worker economic principals meet a disclosed
  non-common-control test;
- `NON_CIRCULAR_NET_FEE`: value transferred is not returned/subsidized under the declared
  observation window.

These policies prove observable events under assumptions. None proves intrinsic utility.

## 10. Failure semantics

- Missing evidence → `unknown` or `unsupported`, never `failed` and never zero coverage.
- Malformed binding or violated sequence → `invalid`.
- A completed verifier showing the relation false → `failed`.
- Unsupported operator/profile → `unsupported` for its coverage, even if neighboring
  operations pass.
- Any evidence/backend disagreement is retained; the issuer cannot choose only the passing
  result without recording the conflict.
