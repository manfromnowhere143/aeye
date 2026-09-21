# Aeye Review Protocol — Reviewer stance and pre-registered criteria

Status: `proposed`, pre-registered
Date: 2026-08-30
Author role: independent adversarial reviewer
Implementation owner: same-session implementation work, pinned Pearl `4a0c24b`

> **Status correction — 2026-09-20.** This retained document is a historical proposed
> review protocol, not an independent review. Labels such as “separate reviewer” or
> “independent adversarial reviewer” do not establish organizational, evidentiary, or
> cryptographic independence. Gate A therefore remains unchecked. Its FB-4 criteria are
> superseded where they assume a checkpoint tensor is hashed verbatim; E-000 now requires
> reconstruction through the pinned fusion/slicing/packing runtime path. Its statement that
> the demonstrated random-matrix class “becomes publicly detectable” remains a hypothesis
> until E-000 and a preregistered census succeed. Use
> [the current verdict](VERDICT_2026-09-20.md) and
> [pre-implementation gate](PRE_IMPLEMENTATION_GATE.md) as present authority.

Written **before** any implementation result is seen. Criteria fixed after the fact are
not criteria.

---

## 1. Role boundary

- I do **not** treat `docs/AEYE_MASTER_PLAN.md` as authority. It is a *submitted proposal*,
  not an accepted design, and may be rejected whole.
- This protocol reviews implementation decisions weighted toward those that differ from or
  go beyond the submitted proposal. Where implementation converges on the proposal, review of
  that part carries little evidential weight and I will say so rather than claim agreement
  as confirmation.
- `docs/PEARL_FORENSICS_2026-08-30.md` is a set of falsifiable claims with paths attached,
  written to be audited. It is an input to be checked, never a premise to be inherited.
- Both of us checking FB-4 is not a conflict. Reviewer independence is about architecture;
  a reviewer who cannot independently check the load-bearing fact is not a reviewer.

## 2. FB-4 is two claims, not one

They will be reported separately or the verdict is rejected.

| | Claim | What settles it |
|---|---|---|
| **FB-4a** *recomputability* | `hash_b` for a block is reproducible as `MerkleRoot(slab, key=job_key)` from **published checkpoint bytes** | one exhibited opening |
| **FB-4b** *productivity* | Blocks **mined by the network** match registry slabs at a measurable rate | the census, on mainnet blocks not mined by us |

FB-4a true and FB-4b near-zero is a coherent and important outcome: the oracle works, and
the network isn't running registry models. That is a result, not a failure, and it must not
be reported as either "verified" or "refuted" alone.

## 3. Pre-registered acceptance — FB-4a TRUE

All five required:

1. **Block provenance.** A stated mainnet height, with the certificate bytes retained and
   content-addressed. Not simnet, testnet, testnet2 or regtest.
2. **Not self-mined.** A block we mined proves recomputability trivially and says nothing
   about the network. If the exhibit is self-mined it is labelled `FB-4a (self-mined)` and
   does not discharge FB-4a for network blocks.
3. **Public pre-image.** The slab bytes come from the **published checkpoint**, at a named
   HF repo revision with its own digest — *not* from a tensor captured out of a locally
   running miner. Hashing what our own process handed the kernel proves self-consistency,
   not public recomputability. **This is the most likely route to a wrong TRUE.**
4. **Independent key derivation.** `job_key` derived from the on-chain header fields and
   the certificate's own `mining_config`, with the certificate version's `SeedDerivation`
   (Legacy vs Salted) selected explicitly, never defaulted.
5. **Third-party replay.** Given `(height, checkpoint revision, slab id)` a third party can
   rerun and obtain the same 32 bytes.

## 4. Pre-registered acceptance — FB-4a/b FALSE

A negative verdict requires a **demonstrated-exhaustive** enumeration, not an absence of
matches:

1. The slab index covers every `(n,k)` actually observed in the sampled certificates, or
   the uncovered ones are reported separately as `undecidable`.
2. Enumeration spans all four checkpoints × every plausible TP degree × every mining-eligible
   tensor, **including fused parameters**.
3. Checkpoint revision predates the sampled blocks.
4. Sample size and selection rule stated in advance.

Absent these, the verdict is `unknown`, not `FALSE`. Missing is never rendered as zero.

## 5. What I will check the result against

**Routes to a wrong TRUE**
- self-consistency loop (§3.3) — hashing our own runtime tensor
- non-mainnet or self-mined block presented as network evidence
- padding / leaf-count / `MERKLE_LEAF_SIZE` conventions taken from the same code path on
  both sides, so a shared bug cancels
- matching `hash_a` where `hash_b` was claimed
- Legacy seed derivation applied to a V3 certificate, or vice versa

**Routes to a wrong FALSE**
- TP degree not enumerated (70B almost certainly sharded; 8B may not be)
- **fused projections missed** — `output_partition_sizes` means QKV and gate/up register as
  one concatenated parameter; the slab is the concatenation, not the individual tensors.
  Missing this eliminates every match and is the single most likely cause of a spurious
  refutation
- transpose confusion: `Bᵀ = w_q`, `n × k`, row-major
- unkeyed BLAKE3, or keyed with a salted root instead of `job_key`
- `pad_to_chunk_boundary` omitted or applied at the wrong granularity
- **checkpoint revision drift** — the `pearl-ai` repos show update dates of 2026-04-27,
  06-18 and 06-28; a checkpoint revised after a block was mined will never match it
- MoE stacking: for `Qwen3-30B-A3B`, `B` is experts stacked, with `n` the per-expert
  intermediate dim

## 6. Standing constraints on any result I will accept

- Every figure states its baseline, hardware, model, batch and sequence dimensions,
  precision, repetitions and dispersion. A bare percentage is rejected.
- No composite claim words: "verified inference", "proof of demand", "useful work proven".
- A rung is not implemented until a known-bad fixture shows it **rejects** an invalid receipt.
- Any plausible vulnerability stops at minimal local reproduction, stays out of every
  public document, and goes to Pearl's `SECURITY.md` advisory channel.
- Read-only public data. No mainnet transactions, no interaction with live miners, pools
  or wallets.

---

## 7. Census bucket assignment — pre-registered (added after the FB-4a/4b split)

The third result — coverage/completeness — is accepted and required. A three-way split
is only rigorous if the assignment rule is decidable and fixed in advance; otherwise every
awkward block drifts into "undecidable" and the match rate flatters whichever side is
telling the story.

For sampled block `b`, with registry `R` (models × tensors × TP degrees × revisions):

| Bucket | Rule | What it is evidence of |
|---|---|---|
| `MATCH` | ∃ slab `s ∈ R` with `MerkleRoot(s, key=job_key_b) == hash_b` | **registry-model weights, provably.** Zero false positives at 256 bits |
| `IN-COVERAGE-NO-MATCH` | `(n,k)` of `b` is in `R`'s shape index **and** enumeration over every slab of that shape was exhaustive **and** no match | *not any registry slab.* Weaker than "not model work" |
| `OUT-OF-COVERAGE` | `(n,k)` absent from `R`'s shape index | **nothing.** Private model, unenumerated TP layout, unregistered checkpoint |
| `UNRETRIEVED` | block in the sample window whose certificate we did not obtain | nothing. Reported separately; never silently dropped from the denominator |

### The shape-collision limit

`(n,k)` membership in the shape index is **not** evidence about `b`. Hidden dimensions
collide across models and layers — 4096, 8192 and their multiples recur everywhere. Two
distinct models can present identical `(n,k)`. So `IN-COVERAGE-NO-MATCH` means only "not
any *registry* slab", and a private model of the same shape is indistinguishable from
random matrices by this method. That bucket is a bound on our registry, not a finding about
the miner.

### The only informative number

```
lower bound on registry-model-backed work  =  |MATCH| / |sampled|
```

Everything else is a bound on our own ignorance. Specifically:

- **Never divide by `(MATCH + IN-COVERAGE-NO-MATCH)`.** That drops `OUT-OF-COVERAGE` from
  the denominator and inflates the rate in whichever direction the author was hoping for.
  Any figure computed this way is rejected on sight.
- `|MATCH|` is a **lower bound only**. It rises with registry completeness and can never be
  read as an upper bound on useful work.
- `IN-COVERAGE-NO-MATCH` may **not** be reported as "provably non-model", "random matrices",
  or "useless". The permitted phrasing is "did not open to any registered slab".
- `OUT-OF-COVERAGE` and `UNRETRIEVED` are reported as raw counts beside every rate. A rate
  published without them attached is incomplete, not conservative.

### Consequence, stated plainly

The census produces exactly one informative quantity and three measures of our own
ignorance. If `|MATCH|` is high, that is a strong, publishable, defensible result. If it is
low, the honest output is *"we could not observe registry-model work at rate X, with
coverage Y"* — never *"the network is doing no useful work"*. The critique in
arXiv:2606.04819 is answerable in one direction only. Building the instrument is still
worth it; pretending it is symmetric is not.

---

## 8. Amendments (corrections accepted, 2026-08-30)

**8.1 — `MATCH` is negligible, not zero.** §7 said "zero false positives at 256 bits".
Corrected: the false-positive probability is negligible **under BLAKE3 collision and
pre-image assumptions and under a registry-integrity assumption**. The second was implicit
and must be explicit: a wrong slab admitted into our own registry produces a wrong match.
That failure mode is ours, not the hash's, and needs its own known-bad fixture.

**8.2 — A high match rate does not answer the usefulness-gap thesis.** This corrects the
reviewer's own prior statement, not only the document. Registered-slab replay — real
`hash_b`, garbage `A` — passes L2 cleanly. The census therefore measures **one substitution
class**.

Precisely:

- arXiv:2606.04819's **demonstrated experiment** is the random-matrix class (turbo4,
  uniform matrices, CPU / Apple Silicon / AMD shares). The census answers that.
- arXiv:2606.04819's **thesis** is broader. The census does not answer the thesis.
- Permitted claim: *"the demonstrated substitution class becomes publicly detectable."*
  Forbidden claim: *"the usefulness gap is closed."*

**8.3 — The conditional rate is permitted; the earlier prohibition was over-broad.** §7 said
the covered-sample ratio would be rejected on sight. Corrected: a conditional rate carrying
its conditioning set is legitimate statistics. The hazard is an *unlabelled* ratio.

Rule as amended:

- **Headline:** `|MATCH| / |sampled|` — whole-sample, conservative lower bound.
- **Permitted alongside:** the covered-sample conditional rate, provided `coverage` and
  `retrieval` are reported adjacent to it and it is never presented as the headline.
- Still forbidden: any single figure whose denominator silently excludes `OUT-OF-COVERAGE`
  or `UNRETRIEVED`.

**8.4 — Terminal position of the whole program, recorded now to prevent later drift.**

The usefulness gap is **partially closable by cryptography and not fully closable by it.**

| class | closed by |
|---|---|
| arbitrary / random matrices | L2 — publicly detectable, no protocol change |
| substituted or unlinked activations | L3 — receipt, anchored by the V4 fold |
| misdeclared arithmetic on the float glue | L4 — declared semantics + reproduction oracle, opt-in |
| **real model, real lineage, garbage prompts** | **nothing below L5 — and L5 only prices it** |

No rung above closes the last row, and no combination of them does. Aeye's contribution is
to state exactly which row is closed by what, and to decline the composite claim.

---

## 9. Registry trust model — must be named, not engineered away

A registry-integrity fixture proves the pipeline *propagates* a poisoned slab into a false
conclusion. It cannot detect poisoning in the wild. Detection is procedural, and the
procedure rests on a trust assumption that is currently unstated.

This matters asymmetrically: `MATCH` is the only informative figure the census publishes
(§7), so a **false MATCH is strictly worse than a false NO-MATCH**. Registry integrity
guards the one number that carries weight.

### Three tiers — state which one the registry actually achieves

| Tier | Construction | Poisoning requires |
|---|---|---|
| **T0** | registry entry = "the bytes we downloaded" | compromising, or being lied to by, one publisher |
| **T1** | + HF git revision SHA pinned, retrieval date recorded, artifact digest retained, second retrieval over an independent network path | as T0 — detects tampering *in transit*, not *at source* |
| **T2** | + the int8 checkpoint shown to be a **deterministic function** of a base model from a *different* publisher plus a published quantisation recipe | compromising **two independent publishers** |

T2 is the only tier that removes single-source trust. **Open question, and worth answering
early because it bounds what the census can claim:** is a `pearl-ai` W8A8 checkpoint
reproducible from `meta-llama/Llama-3.3-70B-Instruct` plus a published recipe? SmoothQuant
scales and the Hadamard block size are calibration-dependent, so the honest prior is
**probably not** — in which case T2 is unreachable, the registry stops at T1, and the
single-source assumption is named in the census report rather than quietly carried.

### Required regardless of tier

1. Registry entries are content-addressed: `(repo, git revision SHA, per-tensor blake3,
   retrieval timestamp)`. No floating `main`.
2. Revision must **predate** every block it is used to adjudicate (§5, revision drift).
3. The census report states its tier and its trust assumption in the same paragraph as its
   headline number.
4. A known-bad fixture demonstrates the pipeline yields a false MATCH on a poisoned slab —
   the retained fixture — **and** the report states that this fixture tests propagation, not
   detection.

### Second-order note

Publishing the registry hands an adversary the exact slab list to replay. This is marginal
— the checkpoints are already public and downloadable — but it should be acknowledged
rather than discovered later: publication moves slab replay from "work out what to load"
to "hash these byte ranges". It does not change the L2 non-claim, which already concedes
replay (§8.2).
