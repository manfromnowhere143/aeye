# Aeye — Master Plan v0.1

Status: `proposed` — architecture for adversarial review, not an accepted design
Date: 2026-08-30
Evidence base: [`PEARL_FORENSICS_2026-08-30.md`](PEARL_FORENSICS_2026-08-30.md)
(Pearl @ `4a0c24b`, Hawkeye arXiv:2603.20421 + vendored source, arXiv:2504.09971,
arXiv:2606.04819, and the 2025–2026 verifiable-inference literature surveyed in §9.)

> **Superseded — 2026-09-20.** This is the retained initial proposal, not the accepted Aeye
> architecture. Its load-bearing “public checkpoint tensor verbatim” premise is
> contradicted by runtime fusion/slicing/packing; its commitment-only L3 does not establish
> execution; its proposed “V4 fold” is unrelated to Pearl's later FP8 certificate-v4; and
> its mainnet-census-first ordering is replaced by E-000. Use
> [the current verdict](VERDICT_2026-09-20.md),
> [coupling profile](PEARL_COUPLING_PROFILE.md), and
> [pre-implementation gate](PRE_IMPLEMENTATION_GATE.md). Substantive historical text is
> preserved below so the correction remains auditable.

---

## 0. Thesis

> **Make every AI execution independently observable, attributable, and verifiable.**

And the first deliverable claim, deliberately narrower than the thesis:

> **Pearl's chain already commits to the operands of every mined matrix multiplication.
> Aeye makes those commitments accountable — it supplies, and lets anyone check, the
> pre-image story behind `hash_a` and `hash_b`.**

Aeye is not a new zkML stack. It is not a new proof system. In its first phase it is not
even a prover. It is a **pre-image accountability layer** over commitments that are
already on-chain, plus the discipline to say exactly what each layer does and does not
establish.

---

## 1. Verdict on the draft architecture

The four-claim decomposition — WORK / EXECUTION / SEMANTICS / DEMAND — is right and is
retained. Seven things in the draft change after forensics.

| # | Draft position | Verdict | Correction |
|---|---|---|---|
| 1 | "Pearl is strongest on WORK" | **Understated** | Pearl proves *operand-bound* work: a specific committed `(A,B)` pair, seeded by their own commitments. That is much stronger than "computation occurred," and it is the foundation Aeye stands on. |
| 2 | "Hawkeye gives us SEMANTICS (3)" | **Wrong for the mined path** | Pearl mines `Int7×Int7→Int32`. Integer MMA is exact and device-independent. Hawkeye's simulators are float (FP16/BF16/FP8). Hawkeye applies to the *glue*, not to the work. (F6) |
| 3 | "Bind provenance before the mining challenge" | **Already true** | Pearl derives noise seeds *from* the operand commitments. The concern is real only for activations, which the miner chooses freely — not for weights, which are deterministic. |
| 4 | `AER = Commit(M,R,E,G,Y,P)` — one flat receipt | **Wrong shape** | Under continuous batching, `A`'s `m` rows belong to many different requests. A receipt must be two-level: a **batch-step receipt** plus **per-request receipts derived by opening rows**. |
| 5 | "Bind every layer/GEMM commitment" | **Not the right granularity** | The link from layer *i*'s output to layer *i+1*'s input passes through float glue and a re-quantiser. Commit at **quantisation boundaries**; declare the transitions. |
| 6 | "Do not depend on Plonky2" | **Right, and stronger** | Aeye v0 needs **no proof system at all**. L0–L3 are commitment-opening checks over BLAKE3. Introduce a `ProofBackend` only at L4+. |
| 7 | Experiment 001 = "one transformer block" | **Too weak to go first** | It proves nothing about Pearl and nothing about the world. The first experiment must be the **mainnet census** (§7). It is the result nobody currently has. |

Two additions the draft does not contain, both load-bearing:

- **The pre-image reframe** (§2). It converts a "semantics" problem, which cryptography
  handles badly, into a pre-image problem, which cryptography handles natively — and it
  answers arXiv:2606.04819's "structurally unfixable at the hash level" head-on.
- **The four-model registry** (F5). The oracle is not a research aspiration; the entire
  weight universe of Pearl's own reference miner is four public checkpoints.

One naming note, `unknown` and not worth a fight: "AEye" is an existing lidar company.
Check before any public use.

---

## 2. The reframe

Pearl's block header transitively commits to `hash_a` and `hash_b` (F3). So the chain
already answers:

> *"Was a specific, committed pair of matrices fully multiplied?"* — **yes, provably.**

What it does not answer:

> *"What were those matrices?"*

That is a **pre-image accountability** question. It has three properties that make it the
right place to attack:

1. **It needs no new commitment.** The commitment exists, is 256-bit, keyed, and
   consensus-anchored.
2. **Half of it is already public.** `B` is a checkpoint tensor. Its pre-image is
   downloadable. (F5)
3. **It is falsifiable this month**, from public data only, with no GPU and no permission.

arXiv:2606.04819 is correct that the gap is unfixable *at the hash level*. It is silent on
the pre-image level — and names "bind matrix provenance to externally verifiable
commitments" as future work. Aeye is that work, done properly.

---

## 3. The claim ladder

Six rungs. Each is a strictly stronger statement about the *same on-chain object*. Each is
independently deployable and independently falsifiable. Nothing higher is implied by
anything lower.

```
                          what it establishes                        who can check it        cost to Pearl
L0  WORK                  hash_jackpot meets target under cfg        any node                  — (shipped)
L1  OPERAND BINDING       the work was on the operands committed     any node                  — (shipped)
                          as hash_a / hash_b under this job_key
─────────────────────────── everything above is Pearl today ───────────────────────────
L2  MODEL BINDING         hash_b opens to a registered model's       ANYONE, from public       zero
    (PoME)                weight slab (model_root, layer, shard)     data, no cooperation
L3  EXECUTION LINEAGE     hash_a opens to an activation tensor       holder of the receipt;    zero (sidecar)
    (CEL)                 that is the committed successor of the     anyone, if anchored       32 bytes (anchored)
                          prior checkpoint, for a committed batch
L4  ARITHMETIC SEMANTICS  the float glue ran under a declared,       auditor with the          zero
                          versioned accelerator arithmetic           semantics profile
L5  DEMAND                the request was committed on-chain         any node                  zero (tx payload)
                          before the header that seeded the job
```

### The honesty column — what each rung does **not** give you

- **L2 does not prove inference.** `B` is public and deterministic; an adversary holding
  the checkpoint can present a real `hash_b` beside a garbage `A`. L2 proves *weight
  participation*, nothing more.
  What it *does* buy is economic and it is not small: to pass L2 you must hold and stream a
  real model's weight shards through real GEMM shapes on inference-class hardware. That
  eliminates the entire stripped-miner class demonstrated in arXiv:2606.04819 — random
  matrices, CPU, Apple Silicon, AMD — in one step.
- **L3 does not prove the prompt was meaningful.** A provider can run the real model on
  garbage forever and satisfy L0–L4 perfectly. Only L5 touches this, and only by pricing it.
- **L4 is not a proof.** It is a declaration plus a reproduction oracle. It is falsifiable
  (an auditor can re-run and disagree) but not sound against an adversary who lies about
  the hardware and is never audited.
- **L5 is not proof of demand.** Sybil demand remains possible. L5 makes fabricated demand
  *cost an on-chain transaction, before the challenge is known*. Demand becomes **priced,
  not proved.** Say this in every document. Never write "proof of demand."

`derived` The ladder's value is that these limits are *stated per rung* instead of being
laundered by a composite word like "verified."

---

## 4. Layer designs

### 4.1 L2 — PoME, Proof of Model Execution *(no protocol change)*

For every mined block:

```
job_key  = blake3( incomplete_header || mining_config )          # both on-chain
hash_b   = certificate.PublicData[84:116]                        # on-chain
(m,n,k)  = certificate fields + mining_config.common_dim         # on-chain

slab(model, layer, tp_degree, shard) = the int8 bytes of w_q for that shard
match ⟺ ∃ slab :  MerkleRoot( slab, key=job_key ) == hash_b
```

`derived` A 256-bit keyed match is negligibly forgeable, so **any match is a true match**;
the oracle has no false positives, only false negatives (private or unregistered models).
Its output is therefore a rigorous **lower bound** on model-backed work, and must always be
reported as one.

Registry object:

```
ModelRoot = blake3( "aeye/model/v1" || checkpoint_manifest )
  manifest: ordered (tensor_name, dtype, shape, blake3(bytes)) over the whole checkpoint
SlabId    = ( model_root, tensor_name, tp_degree, shard_index )
ShapeIdx  = (n, k) → { SlabId }        # prunes candidates to ~a handful per block
```

Deployment: a public dashboard reporting, per epoch,
`matched / unmatched / undecidable` blocks with the lower-bound caveat printed on the page.

### 4.2 L3 — CEL, Computational Execution Lineage

**Granularity decision.** Not per-operation. The commitment unit is the
**quantisation boundary**, because that is the only place where a bit-exact, device-
independent tensor exists in a Pearl-mining vLLM worker. Between two boundaries sits float
glue that no cheap commitment can pin (L4's job).

```
checkpoint_c  :=  the int7/int8 tensor entering a mined GEMM
transition    :=  the declared float program carrying checkpoint_c to checkpoint_{c+1}
                  (dequant · residual · norm · rope · attention · hadamard · smooth · requant)
```

**Batch co-tenancy.** `A`'s `m` rows are tokens from many requests. So:

```
RowMap        = ordered (row_index → request_slot_id)  for all m rows
hash_rowmap   = MerkleRoot( RowMap_canonical_bytes, key=job_key )
```

`derived` This is the dense analogue of Pearl's own MoE routing commitment
(`hash_router = H(H(Routing,key) || H(offsets,key))`, folded into `hash_a`). Pearl has
already built and shipped exactly this machinery for experts. Aeye reuses its shape for
requests. That is the strongest available argument that CEL is *native* to Pearl rather
than bolted on.

**Two-level receipt.**

```
StepReceipt (per mined GEMM)
  job_key, hash_a, hash_b, m, n, k
  slab_id                     -- ties to L2
  hash_rowmap
  parent_step_root            -- previous checkpoint in this worker's transcript
  transition_id               -- names the float program + semantics profile (L4)

RequestReceipt (derived, per request)
  request_commitment
  ordered list of (StepReceipt, row multiproof for this request's rows)
  output_commitment
```

`derived` A request receipt is *derived by opening rows*, never minted separately. This is
what makes the design survive continuous batching, prefix caching and rebatching: the
receipt does not assume a request owns a GEMM.

**Anchoring (Phase II, one 32-byte field).** Pearl's A-side fold today:

```
hash_activations = blake3( hash_a || hash_router )
```

Proposal for certificate **V4**:

```
hash_activations = blake3( hash_a || hash_router || hash_lineage )
hash_lineage     = blake3( "aeye/lineage/v1" || parent_step_root || hash_rowmap || slab_id )
```

Zero prover cost, one extra BLAKE3 block, no circuit change to the matmul chip, and it
makes the entire lineage consensus-bound. This is the *only* consensus change Aeye ever
proposes, and it should be written as a Pearl Improvement Proposal
(`evidence/external/pearl-pips/`), not as a fork.

### 4.3 L4 — Hardware semantics, correctly scoped

**Split by arithmetic domain.** This is the single most important design decision here.

| domain | where | verification |
|---|---|---|
| **Integer, exact** | the mined GEMM (`Int7×Int7→Int32`) | algebraic: Freivalds over a prime field, or GKR sum-check. `O(mk+kn+mn)`, genuinely sub-1%, **no hardware profile needed** |
| **Float, non-deterministic** | norms, RoPE, attention/softmax, residuals, dequant scales, Hadamard, sampling | declared `HardwareSemanticsID` + reproduction oracle (Hawkeye-class) |

`derived` The mined path — the part that carries the money — needs *no* Hawkeye and *no*
hardware trust. Confining Hawkeye to the glue is both more honest and much cheaper than the
draft's "put Hawkeye on Pearl."

```
HardwareSemanticsID = blake3("aeye/hwsem/v1" || canonical_descriptor)
descriptor: vendor | architecture | mma_shape | input_dtype | accumulator_width
          | accumulation_group_size | accumulation_order | rounding_mode
          | subnormal_policy | kernel_family | kernel_version | conformance_vector_root
```

Hawkeye is the **first provider**, not the protocol: its published Hopper (17-element
groups, 25-bit internal) and Ampere (9-element, 24-bit) characterisations become two
registered descriptors with conformance-vector roots. AMD CDNA, Blackwell, TPU and future
parts register their own. The descriptor outlives any one provider.

**Batch-invariance is a prerequisite, not a detail.** Under continuous batching the float
glue is not reproducible at all unless the worker runs batch-invariant kernels
(Thinking Machines' `batch_invariant_ops`; adopted in vLLM and SGLang). Reported cost is
large — ~61.5% throughput baseline, ~34% with CUDA-graph integration in SGLang. So L4 is
**opt-in per deployment**, and a receipt must record whether batch-invariant kernels were
active. A receipt that claims L4 without them is making a false claim.

### 4.4 L5 — Demand, priced not proved

```
t0  request_commitment  = blake3("aeye/request/v1" || nonce || model_root || prompt_hash || payer)
    → included in a Pearl transaction at height h  ⇒ inside merkle_root of block h
t1  job_key derived from a header at height h' > h
t2  execution; StepReceipts reference request_commitment
```

`derived` Because `job_key` contains the tx `merkle_root`, a request committed at height
`h` provably preceded any job seeded at `h' > h`. Fabricating demand costs one on-chain
transaction *per fabricated request, before the challenge is known*. That is a measurable
price, not a proof. State it that way, permanently.

---

## 5. What Aeye is **not** building

- Not another zkML prover. TensorCommitments (arXiv:2602.12630 — 0.97% prover / 0.12%
  verifier on LLaMA-2), NANOZK, zkLLM, zkGPT own that space. Aeye *cites* them; if L3 ever
  needs a succinct opening, it adopts one behind a `ProofBackend` trait.
- Not a consensus fork. One 32-byte field, proposed as a PIP, at Phase II, or nothing.
- Not a TEE product. GPU confidential computing (Hopper/Blackwell attestation) is a
  registerable *semantics provider* under L4, never the root of trust.
- Not a claim of "proof of demand," "verified inference," or "useful work proven."
- Not a red-team operation against Pearl mainnet. Read-only observation of public data.

---

## 6. Repository architecture

```
aeye/
├── crates/
│   ├── aeye-core/          canonical binary encoding, domain separation, receipt types,
│   │                       verifier. No proof system. No JSON in any pre-image.
│   ├── aeye-pearl/         re-derive job_key / hash_a / hash_b exactly; certificate
│   │                       parser (V1/V2/V3); read-only chain client
│   ├── aeye-registry/      checkpoint → model_root, slab enumeration (layer × TP × shard),
│   │                       (n,k) shape index
│   ├── aeye-oracle/        L2 scanner: block → candidate slabs → verdict + census metrics
│   ├── aeye-semantics/     HardwareSemanticsID descriptors, Hawkeye adapter,
│   │                       conformance vectors
│   ├── aeye-proof/         ProofBackend trait — EMPTY in v0, deliberately
│   └── aegis/              adversarial harness, advantage metric, differential vectors
├── python/aeye-vllm/       sidecar: quant-boundary tap, RowMap emission, lineage export
├── experiments/
│   ├── 001-mainnet-census/     ← the first result
│   ├── 002-cel-single-block/
│   ├── 003-negative-suite/
│   └── 004-semantics-conformance/
├── specs/  AER-v0 · CEL-v0 · PoME-v0 · HWSEM-v0 · PIP-LINEAGE-FOLD-v4
├── threat-model/
└── evidence/  papers, external checkouts, retained digests
```

Rules: Rust at the cryptographic boundary; Python only where PyTorch/vLLM forces it.
BLAKE3 keyed exactly as Pearl does it, so a Pearl engineer can read our derivations without
a new dependency. Canonical little-endian binary in every pre-image; **no JSON anywhere
near a hash**. Every domain-separation constant is a hardcoded 32-byte array with a test
re-deriving it from its ASCII context string — the pattern Pearl itself uses in
`zk-pow/src/api/seed.rs`.

---

## 7. Experiment 001 — the Pearl Mainnet Census

**Question.** For what fraction of recent Pearl mainnet blocks does `hash_b` open to a
weight slab of a publicly registered model?

**Method.** Public data only. Sync headers + certificates. Build slab index for the four
`pearl-ai` checkpoints across plausible TP degrees. For each block: derive `job_key`,
prune candidates by `(n,k)`, test keyed Merkle roots.

**Acceptance criteria.**
1. Fully reproducible by a third party from public data, deterministic, content-addressed.
2. Zero false positives by construction; any match is exhibited with its opening.
3. Result reported as a **lower bound**, with `unmatched` and `undecidable` reported
   separately and never collapsed into a single number.
4. Published as a method and an instrument, never as an accusation.

**Why this first.** Both outcomes are valuable and neither is spin:
- High match rate ⇒ the strongest published criticism of Pearl is empirically answered,
  and Aeye is the instrument that answered it.
- Low match rate ⇒ the gap is quantified for the first time, and Aeye is the instrument
  that measured it — and L2 becomes the obvious remedy.

**Then, and only then:** E-002 (one real block through CEL) and E-003 (the negative suite:
mutate request, one weight bit, layer id, shape, replay activation, reorder, substitute
arbitrary GEMM, substitute output, change semantics id, change job binding — each must
invalidate exactly the rungs it should and no others).

---

## 8. AEGIS

Purpose: falsify our own invariants and Pearl's stated conjecture — never to claim either
is proven.

```
advantage = [ P(win | strategy) / cost(strategy) ] / [ P(win | honest) / cost(honest) ]
target: advantage ≤ 1 + ε
```

Corpus, ordered by expected value given F4 (shape grinding is already closed, so it is a
*regression check*, not a hunt):

1. slab replay — real `hash_b`, garbage `A` **(expected to succeed; it is L2's stated limit)**
2. row-map equivocation — one committed `A` opened under two RowMaps
3. dimension reinterpretation — the live class from #280/#281/#299, re-run against L2/L3
4. cross-request tensor grafting under continuous batching
5. prefix-cache and KV-cache grafting
6. semantics-ID spoofing without batch-invariant kernels
7. certificate-version confusion across V1/V2/V3 seed derivations
8. Rust ↔ Python ↔ CUDA serialisation divergence on the same tensor
9. XOR-reduction transcript structure — `derived`: the inner hash is linear over GF(2)
   before the BLAKE3 finaliser; `hypothesis`, unverified, whether the `rotl13` cycling
   fully removes exploitable structure. **Investigate statically only.**
10. shape/rank grinding — regression only, expected `advantage ≈ 1`

Discipline: never invent a vulnerability; stop at minimal local reproduction; never touch
mainnet, miners, pools or wallets; anything plausible goes to Pearl's private advisory
channel (`SECURITY.md`) and is not published.

---

## 9. Novelty, stated without inflation

| Prior work | What it already does | What Aeye does not claim |
|---|---|---|
| TensorCommitments (2602.12630) | tensor-native inference commitments, 0.97% prover | Aeye does not claim a new commitment scheme |
| zkLLM / zkGPT / NANOZK | succinct proofs of inference | Aeye does not claim a proof system |
| DiFR (2511.20621) | inference verification despite non-determinism | Aeye does not claim novel non-determinism handling |
| Verde / TAO / SPEX | refereed delegation, tolerance-aware optimistic verification | Aeye does not claim a new dispute game |
| Hawkeye (2603.20421) | bit-exact CPU reproduction of float tensor cores | Aeye does not claim hardware reverse-engineering |
| Kernel Contracts (2604.22032) | kernel-correctness specification across silicon | Aeye's HWSEM is an application of this idea |
| NVIDIA GPU-CC attestation | hardware-rooted attestation | Aeye does not root trust in a vendor |

**What is actually new**, as narrowly as it can be stated:

1. The observation that a deployed PoUW chain **already publishes keyed commitments to its
   matmul operands**, and that the weight operand's pre-image is **publicly reconstructible**
   — making usefulness measurable by an outside observer with no protocol change. (F3+F5)
2. **PoME**: a zero-cooperation, zero-consensus-change model-provenance oracle, and the
   census it makes possible.
3. The **arithmetic split**: exact algebraic verification for the integer mined path,
   declared semantics only for the float glue. (F6)
4. **Quantisation-boundary lineage with row-level request attribution**, i.e. a receipt
   design that survives continuous batching rather than assuming it away.
5. A **claim ladder with per-rung non-claims**, replacing composite "verified inference"
   language.

Points 1 and 2 are the ones that would be new to the Pearl team. Points 3–5 are careful
engineering that the literature supports but has not assembled in this combination.

---

## 10. Risks that could kill it

1. **F5 fails in practice.** TP sharding, fused QKV/MLP projections, per-job B-caching
   (PR #208), or a CUDA/Python hashing divergence could mean `hash_b` never equals a naive
   checkpoint slab root. *This is the single highest-value thing to falsify first.*
2. **The census comes back near zero and no one cares.** Mitigation: publish the
   instrument, not the verdict; the method stands either way.
3. **L2 is dismissed as "not a proof."** It isn't one. It is a measurement with a stated
   lower-bound semantics. Overclaiming here destroys the whole project's credibility.
4. **L4 is unaffordable.** Batch-invariant kernels cost ~34–61% throughput. L4 may only
   ever be viable for audited, high-assurance workloads. Say so in the spec.
5. **Pearl changes the derivation.** V3 landed weeks ago; V4 could move `hash_b`. Aeye must
   version its derivations against certificate versions from day one, exactly as
   `SeedDerivation` does.

---

## 11. Sequence

```
Phase 0   forensics + verdicts (this document + the two independent reviews)
Phase I   L2: registry, oracle, E-001 census                        no protocol change
Phase II  L3: CEL sidecar, E-002/E-003, PIP for the 32-byte fold    proposed, not forked
Phase III L4: HWSEM registry + Hawkeye adapter, conformance suite   opt-in
Phase IV  L5: demand anchoring                                      last, never first
AEGIS     runs continuously from Phase I onward
```

Gate between every phase: a dated verdict with disconfirming evidence, per the
[Agent Charter](../AGENTS.md). No rung is described as implemented until its known-bad
fixture demonstrates that it rejects an invalid receipt.
</content>
