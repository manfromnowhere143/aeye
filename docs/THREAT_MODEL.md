# Aeye Threat Model

Status: `proposed`  
Scope: protocol and isolated experiments; no live offensive activity

## Security objective

Prevent evidence for one job, model, event, arithmetic profile, scope, or economic policy
from being replayed or re-labelled as evidence for another. When prevention is impossible,
the verifier must return `unknown`, `unsupported`, or a conditional assurance class rather
than a stronger claim.

## Principals

- client/request principal;
- inference provider and scheduler;
- Pearl miner/pool/block producer;
- model/checkpoint/registry publisher;
- trace/evidence store;
- audit challenger or duplicate provider;
- proof producer and proof-system implementer;
- arithmetic-profile author and target-device operator;
- TEE/GPU/firmware vendor and physical host;
- demand/payment anchor and chain consensus;
- receipt verifier/operator.

Any subset may collude unless a profile explicitly assumes independence. In particular,
miner, inference provider, requester, registry publisher, and payer are not independent by
default.

## Attack matrix

| Attack | Coordinate that may still pass | Required detection or residual assumption |
|---|---|---|
| Random operands substituted for inference | `WORK` | Model-operand scan can reject random `B` only within registry coverage; garbage `A` remains possible. |
| Certificate-v3/v4 parser or assumption confusion | Superficially valid `WORK` label | Exact lineage, fork, parser, device/quantization profile, and hardness identifier are native evidence inputs; never infer “current Pearl.” |
| Registered slab replay with garbage activations | `WORK`, model-binding observation | `EXECUTION` backend must validate causal transitions; census cannot. |
| Receipt placement relabelled as native proof input | Any envelope can look job-bound | Separate `receipt_job_id` from `native_public_inputs`; null means the relation did not authenticate that value. |
| Pearl and execution evidence expose different operand roots | Both relations may pass separately | Cross-evidence equality must reject; neither certificate nor execution proof may be rewritten to force a match. |
| One valid layer/slab repeated, other layers omitted | `WORK`, some sampled checks | Manifest completeness plus proof/audit coverage; sampling probability must account for concentrated omission. |
| Model substitution or wrong checkpoint revision | Some output-level tests | Canonical model root and transition verification; private weights need stronger provenance. |
| Hollow/structured private weights that satisfy a circuit cheaply | `EXECUTION` under that private relation | Public canonical weight root or separate `WORK` evidence; relation correctness is not effort. |
| Activation graft from another request/batch | `WORK`, `SEMANTICS` on the grafted op | Job-bound parent edges and independently checked membership/transition relation. |
| Output graft onto a valid trace | `WORK`, internal checks | Output token IDs, decoding policy, and final event must be public inputs to the execution verifier. |
| Row-map equivocation | Operand commitment | Row map fixed before challenge and checked against tensor openings; a root alone remains self-report. |
| Prefix/KV-cache graft | Matmul checks | Cache origin model/job/position and reuse policy are authenticated DAG parents. |
| Speculative-decoding omission | Accepted-token output may look valid | Commit draft, acceptance/rejection, and final decode events or scope the relation to final tokens explicitly. |
| Retry/rebatch/migration splice | Local event checks | `attempt_id`, parent roots, monotone sequence and explicit migration edges. |
| LoRA/adaptor omission or substitution | Base model root | Adapter set/order is part of `ModelManifest` and transition relation. |
| TP/PP/EP or fused-parameter ambiguity | Shape-based registry lookup | Canonical transformation recipe and layout; shape alone never labels a slab. |
| Checkpoint/registry poisoning | Cryptographically valid `MATCH` | Signed/pinned registry provenance, independent retrieval/reproduction when available, and explicit trust tier. A fixture tests propagation, not wild detection. |
| Challenge chosen before trace commitment | Sampled audit | Public unpredictability and ordering proof; otherwise `invalid`. |
| Selective disclosure of only passing audits | Individual audit | Append-only challenge log and required conflict retention. |
| Data withholding after optimistic commitment | Commitment | Data-availability rule, bond, timeout outcome `unknown/failed`; timeout never means acceptance. |
| All optimistic providers/challengers collude | Optimistic evidence | Explicit one-honest-party assumption; use ZK/attestation or remain conditional. |
| One-round slashing appears sufficient but repeated cheating lowers future penalty exposure | Economic audit policy | Model repeated service, stake vesting/ejection, discount factor, history-dependent challenges, ownership, and collusion; never relabel incentive compatibility as cryptographic soundness. |
| Proof/public-input under-binding | ZK proof verifies | Job/model/request/output/profile roots must be public inputs; known-bad mutation for every field. |
| Arithmetic-profile substitution after execution | Other coordinates | Profile fixed at `t1`, before trace/challenge. |
| Emulator/CPU produces GPU-compatible bits | `ARITHMETIC_CONFORMANCE` | This is allowed by that relation; physical origin is a separate subclaim. |
| Kernel/toolkit/schedule drift under same architecture label | Superficial semantics | Full effective profile and target-device conformance vectors, not architecture name. |
| NaN, infinity, signed zero, subnormal edge cases | Random normal conformance tests | Bit-stream and adversarial vectors; unsupported behavior remains unsupported. |
| Forged/relayed TEE or GPU quote | `attested` path | Vendor/physical threat model and job-bound channel; TEE.fail demonstrates residual risk. |
| Request replay or execution before authorization | Other three coordinates | Nonce, validity interval, monotonic anchor/finality and `t0 < t1`. |
| Demand event asked to sign a job hash containing itself | No well-founded binding exists | Two-stage `intent_id`, then authenticated demand root, then final `job_id`; reject cyclic prose or encodings. |
| Sybil/self-funded/circular demand | `DEMAND` under weak policy | Report exact policy/principal linkage; no cryptographic mechanism proves intrinsic demand. |
| Chain reorg or cross-network receipt replay | Initially valid anchor | Network/epoch/finality domain in every evidence statement; revoke on reorg per policy. |
| Privacy extraction from sampled activations | Stronger audit result | Minimize openings, access controls, redaction policy, or a reviewed zero-knowledge backend. |

## Highest-risk architectural mistakes

1. Treating a self-consistent commitment chain as proof that the computation happened.
2. Treating a registered weight match as full-model execution.
3. Treating arithmetic compatibility as physical-device provenance.
4. Treating an amortized fleet audit rate as per-receipt soundness.
5. Treating a signed or paid request as non-collusive economic value.

## Security parameters and probability reporting

No report may use “negligible” without a named computational assumption/security parameter,
or “high detection” without the attack distribution, sample rule, number of trials, and
confidence interval. Sampled transition checks must publish worst-case bounds for
concentrated corruption, not only averages over diffuse attacks.

## Coordinated disclosure

Potential Pearl vulnerabilities are reproduced only with minimal static/local tests. They
do not enter public verdict prose until coordinated through the repository's `SECURITY.md`
process. The AEGIS harness never targets mainnet, pools, miners, wallets, or credentials.
