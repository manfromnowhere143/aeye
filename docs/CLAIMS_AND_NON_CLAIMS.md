# Aeye Claims and Non-Claims

Status: `proposed`  
Protocol family: `AER-v0`

## Objects

Let:

- `R` be a canonical request-intent manifest;
- `M` be a model manifest binding graph, public or committed weights, tokenizer,
  quantization, adapters, and decoding policy;
- `E` be an execution manifest binding runtime, parallelism, scheduler constraints,
  kernels, arithmetic profiles, proof profile, and freshness domain;
- `T` be a content-addressed execution-event DAG;
- `Y` be an output manifest over token IDs and presentation bytes;
- `A` be a demand/authorization event;
- `P` be a set of evidence objects;
- `I = H_F("aeye/intent/v0", [R.root, M.root, E.root, nonce, freshness])`;
- `A` authenticate `I` under a named policy;
- `J = H_F("aeye/job/v0", [I, A.root])`;
- `S = H_F("aeye/execution-subject/v0", [J, T.root, Y.root])`.

`H_F` length-frames every byte string as defined in the protocol spec. Manifest roots remain
parameterized by an unaccepted serialization profile; the research fixtures use synthetic
roots and instantiate only the intent, job, and subject bindings. The two-stage construction
avoids asking a signed demand event to contain an identifier that already hashes that same
event.

## Verification result

Verification returns:

\[
V(AER) = (v_W, v_X, v_S, v_D)
\]

Each coordinate contains:

```
status       ∈ {satisfied, failed, unknown, unsupported, invalid}
assurance    ∈ {none, commitment_only, sampled, optimistic, attested,
                cryptographic, hybrid}
coverage     = {known, scope, unit, numerator|null, denominator|null}
assumptions  = [named, versioned assumptions]
evidence     = [content-addressed evidence references]
diagnostics  = [machine-readable reasons]
```

There is intentionally no `overall_verified` field and no truth table that converts this
vector to a single badge.

Evidence is admissible for a coordinate only when its exact statement names that
coordinate, exposes the required values as native relation public inputs or an independently
checked aggregate membership proof, and retains all assumptions. `receipt_job_id` is scope
metadata, not proof binding. The formal composition and separation claims are specified in
`FORMAL_COMPOSITION.md`.

## `WORK`

`WORK(J, P_W)` is satisfied only when a named work verifier accepts evidence bound to `J`
and its security statement implies a stated lower bound or cost class under explicit
assumptions.

For the Pearl adapter this means, at minimum, a version-correct accepted certificate,
header/fork context, public parameters, and a binding from the certificate's operand roots
to the Aeye event or aggregate scope. The result remains conditional on Pearl's conjectured
work assumption for that exact protocol lineage and the selected chain's consensus/finality
policy. Certificate-v3 INT and proposed certificate-v4 FP8 evidence use different parser,
arithmetic, and assumption identifiers.

Non-claims:

- It does not establish that the work was economically useful.
- It does not establish a whole inference, all layers, or all requests in a batch.
- It does not establish the physical hardware used.
- A reference from one query to an epoch certificate is aggregate coverage, not proof that
  the query itself produced the winning ticket.
- Receipt placement is not a Pearl-native binding to an Aeye job. A coupled claim requires
  an execution relation exposing byte-identical native operand roots.

## `EXECUTION`

`EXECUTION(J, R, M, E, T, Y, P_X)` is satisfied only when an independent verifier accepts
that:

1. `R`, `M`, `E`, `T`, and `Y` share `J` and were bound before the relevant challenge;
2. every required event in `E` appears exactly once or has an explicit permitted reuse
   edge;
3. every event's inputs are outputs of declared parents or authenticated external inputs;
4. request attribution survives batching, rebatching, cache use, migration, and retries;
5. tokenization, sampling/argmax, stop conditions, and output serialization are covered;
6. the selected verification backend accepts the declared execution relation.

A trace root, row-map root, lineage fold, signature, or model-slab match alone is
`commitment_only`; it cannot satisfy `EXECUTION`.

Non-claims:

- Execution correctness does not imply substantial work if the committed model is hollow,
  pruned, structured, or otherwise cheap.
- Execution correctness under a quantized circuit does not imply native GPU execution.
- A registry slab match establishes weight participation, not full-model completeness.

## `SEMANTICS`

`SEMANTICS(J, T, E, P_S)` is satisfied over declared coverage only when the verifier checks
each covered event against a frozen arithmetic relation identified by
`arithmetic_profile_id`.

The minimum profile binds instruction/opcode, input/accumulator/output types, layouts,
rounding, subnormal/exception behavior, saturation, kernel/CUBIN or equivalent digest,
tiling, split-K/reduction topology, epilogue, compiler/toolkit/library versions, stream and
workspace policy, device architecture/SKU/SM count, and retained conformance-vector root.

Hawkeye and MMA-Sim are untrusted reference adapters. Agreement with either establishes
consistency with an empirical profile, not origin on the physical device.

Non-claims:

- `ARITHMETIC_CONFORMANCE` is not `PHYSICAL_HARDWARE_PROVENANCE`.
- Instruction-level MMA coverage is not coverage of RMSNorm, RoPE, attention, softmax,
  residuals, quantization, cache logic, or sampling.
- Architecture name alone is not an arithmetic profile.

Physical-device provenance, if requested, is an optional subclaim with a separate
attestation trust chain and threat model. It never upgrades arithmetic coverage.

## `DEMAND`

`DEMAND(I, J, R, A, P_D)` is satisfied only relative to a named policy `Π_D` when an
independently verifiable authorization event:

1. authenticates `I`, the requester/principal identity or pseudonym, scope, and validity
   interval;
2. is content-addressed into `J` before execution and before an audit challenge;
3. passes freshness, replay, revocation, and chain-reorg rules;
4. meets the policy's independence and, when claimed, non-circular payment/bond criteria.

Non-claims:

- Aeye cannot cryptographically establish that a prompt is meaningful, wise, human-origin,
  welfare-enhancing, or economically useful.
- A signed request can be Sybil-generated; a payment can be circular or subsidized.
- “An authorization/payment event occurred under policy `Π_D`” is permitted. “Demand was
  proved” is not.

## Assurance profiles

| Profile | Mechanism | Defensible execution statement | Principal residual assumption |
|---|---|---|---|
| `C0` | Commitments/signatures only | The prover cannot later change its declared bytes under binding assumptions. | Declarations may be false. |
| `A1` | Post-commit random path/tile audits | Sampled transitions were locally consistent; detection probability is stated. | Corruption may lie outside the sample; data must be available. |
| `O2` | Optimistic duplicate/referee protocol | The relation holds if at least one challenger is honest and online. | Honest challenger, challenge window, deterministic reference. |
| `T2` | TEE/GPU attestation | Measured software/device state reported execution under the attestation threat model. | Vendor, firmware, physical-security, quote-binding assumptions. |
| `Z3` | Full or layerwise proof | The committed public inputs and witness satisfy the supported circuit/relation. | Proof-system assumptions and circuit/quantization fidelity. |
| `H4` | Explicit hybrid | Only the conjunction of its separately reported coordinates. | Union of all named assumptions; no hidden upgrade. |

`C0` is useful infrastructure but is insufficient for `EXECUTION=satisfied`.
