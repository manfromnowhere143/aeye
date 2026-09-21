# Pearl Forensics — verified fact base

Status: `observed` / `derived` as marked per line
Date: 2026-08-30
Subject: `github.com/pearl-research-labs/pearl` @ `4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0`
(`master`, "fix(zkpow): reject usize->u32/u16 narrowing of proof dimensions (#299)", 2026-08-30 12:17 +0300)
Local clean checkout: `~/workspace/pearl`

> **Supersession notice — 2026-09-20.** This is a retained historical analysis, not the
> current Aeye fact base. F5's derived assertion that the hashed weight slab is generally a
> released checkpoint tensor “verbatim” is `contradicted`: the pinned serving path can fuse,
> slice, pack, transpose, and materialize runtime parameters before hashing. The resulting
> deterministic public-reconstruction hypothesis is E-000 and remains `unknown`. F7's
> conclusion that random-matrix work therefore becomes publicly detectable is not
> established until E-000 and a preregistered registry-coverage census succeed. F6 applies
> only to the retained INT certificate-v3 lineage; September 2026's proposed FP8
> certificate-v4 has a distinct arithmetic relation and assumption. F3 and wire-format
> statements are likewise version-pinned, not generic claims about current Pearl. Use
> [the current coupling profile](PEARL_COUPLING_PROFILE.md),
> [state-of-the-art survey](STATE_OF_THE_ART_2026.md), and
> [2026-09-20 verdict](VERDICT_2026-09-20.md) for present conclusions.

Every claim below is tagged. `observed` = read directly in the named file.
`derived` = follows from observed facts by argument stated inline.
`hypothesis` = not yet checked; must be verified before use.
Nothing here may be cited downstream without re-verification against the named path.

---

## F0. The repository is the right one and it is live

`observed` The monorepo README names the protocol paper as arXiv:2504.09971 and lays out
`node/` (pearld, Go), `zk-pow/` (Rust, Plonky2/STARKy), `miner/` (Python/CUDA vLLM miner),
`py-pearl-mining/` (Rust/PyO3), `plonky2/` (vendored), `wallet/`, `spv/`, `xmss/`.

`observed` HEAD is dated the same day as this analysis. Consensus work is active and recent:

| commit | PR | subject |
|---|---|---|
| `4a0c24b` | #299 | reject `usize→u32/u16` narrowing of proof dimensions |
| `10a0ee1` | #281 | pin Merkle tree leaf counts to declared dimensions |
| `fadd42a` | #282 | delay mainnet salted-seed fork height |
| `fc5ca65` | #280 | **salted noise-seed hardfork** (certificate V3) |
| `51a6e11` | #275 | **rank-penalty softfork** |
| `670da8c` | #260 | dense-only softfork rejecting MoE certificates |

`derived` #280, #281 and #299 are three fixes in one attack class: *decoupling a commitment
from the operands it is supposed to bind, by reinterpreting declared dimensions*. This is
precisely the neighbourhood Aeye proposes to work in. Any Aeye design must be read as
adjacent to live consensus hardening, not as a greenfield idea.

---

## F1. Mining is a keyed commitment to two matrices, then a full GEMM over them

Path: `miner/miner-base/src/miner_base/commitment_hash.py`,
`miner/miner-base/src/miner_base/noisy_gemm.py`,
`miner/miner-base/src/miner_base/noise_generation.py`.

`observed` The job key:

```
job_key = blake3( incomplete_header_bytes || mining_config.to_bytes() )
```

`incomplete_header_bytes` = `version(4) || prev_block(32) || merkle_root(32) || timestamp(4) || nbits(4)`
(`zk-pow/src/api/proof.rs::IncompleteBlockHeader`).
`mining_config` is 52 bytes: `common_dim k(4) | rank(2) | mma_type(2) | rows_pattern(6) | cols_pattern(6) | moe-trailer(32)`
(`zk-pow/src/api/proof.rs::MiningConfiguration`).

`observed` The operand commitments:

```
hash_a = MerkleRoot( A,   key=job_key )     # A is m x k, int8
hash_b = MerkleRoot( B^T, key=job_key )     # B is k x n, int8;  B^T is n x k
```

BLAKE3 keyed, leaves padded to the BLAKE3 chunk boundary
(`miner/miner-base/src/miner_base/matrix_merkle_tree.py`).

`observed` The noise seeds, certificate V3 (`SeedDerivation::Salted`, `zk-pow/src/api/seed.rs`):

```
a'      = blake3( hash_a || m_le32 || 28 zero bytes , key = blake3("pearl/cert-v3/noise-seed/A") )
b'      = blake3( hash_b || n_le32 || 28 zero bytes , key = blake3("pearl/cert-v3/noise-seed/B") )
seed_B  = blake3( job_key || b' )
seed_A  = blake3( seed_B  || a' )     # in MoE, a' is first folded with the routing roots
```

`derived` **The noise is a function of the operands.** The miner must commit A and B
*before* it learns the challenge that governs its own PoW attempts. Grinding the operands
is possible, but each grind costs a fresh commitment and a fresh full GEMM. This is the
core of Pearl's construction and it is sound in shape.

`observed` The noise is low-rank. With rank `r` (default 128):
`E_A = E_AL·E_AR` (m×r · r×k) and `E_B = E_BL·E_BR` (k×r · r×n), all int8, drawn from
keyed BLAKE3 streams. `E_AL`/`E_BR` are uniform in a bounded range; `E_AR`/`E_BL` are
sparse ±1 (`+1` at one index, `−1` at another) — `noise_generation.py::__generate_permutation_matrix`.

`observed` The miner computes `C_noised = (A+E_A)(B+E_B)` and recovers the true product by
subtracting two rank-`r` corrections:

```
C = C_noised − (A·E_BL)·E_BR − E_AL·(E_AR·(B+E_B))
```

`derived` The correction costs `O(r·(mn+mk+kn))` against a GEMM of `O(mnk)`. With `k ≥ 16r`
enforced (F4), the overhead is bounded and small. **This is the `1+o(1)` claim, and it is
structurally real, not marketing.**

## F2. The PoW inner loop

`observed` (`noisy_gemm.py`, `inner_hash.py`) For each `16×16` hash tile of the running int32
accumulator, after each rank-sized `k` step:

```
h        = XOR-reduce( tile as uint32 )                 # inner_hash.py::xor_reduction
T[i%16]  = rotl32(T[i%16], 13) XOR h                    # 64-byte transcript, HASH_ACCUMULATE_ROTATION=13
win      ⟺ blake3(T, key = seed_A) ≤ target
```

`derived` The PoW attempt count equals the number of hash tiles, i.e. `(m/16)·(n/16)` per
GEMM, while cost is `Θ(mnk)`. Attempts are therefore *cheaper per FLOP at small k* — but
see F4, which normalises exactly this.

`observed` On a win the miner records `OpenedBlockInfo` = the 16 A-row indices and 16
B-column indices of the winning tile, plus the un-noised `A` and `Bᵀ` for the opening
(`noisy_gemm.py::_record_opened_block`).

## F3. **The operand commitments are on-chain, in every block**

`observed` `zk-pow/src/api/proof.rs::PublicProofParams` wire layout:

```
mining_config(52) | hash_a(32) | hash_b(32) | hash_jackpot(32) | m(4) | n(4) | t_rows(4) | t_cols(4)
```

= 164 bytes for a dense proof (`node/wire/certificate_v1.go::PublicDataSizeV1`,
`node/wire/certificate_v2.go::PublicDataSizeDenseV2`).

`observed` `node/wire/certificate_v2.go::proofCommitment`:
`ProofCommitment = SHA256d( cert_version_le32 || PublicData )`.

`observed` `node/wire/blockheader.go::BlockHeader` carries `ProofCommitment` as a header
field, hashed into `BlockHash()`.

> `derived` — **THE CENTRAL FINDING.**
> Every Pearl block header transitively commits to `hash_a` and `hash_b`: keyed BLAKE3
> Merkle roots of the *actual operand matrices* of the matmul that produced that block.
> The chain already publishes a commitment to the operands of every mined GEMM.
> The usefulness question is therefore not a missing-commitment problem.
> It is a **pre-image accountability problem**: nothing today says what `hash_a` and
> `hash_b` are commitments *of*. That, and only that, is the gap.

## F4. Difficulty is normalised by work-per-attempt (shape grinding is already handled)

`observed` `zk-pow/src/api/sanity_checks.rs`:

```
difficulty_adjustment_factor(cfg) = tile_size(cfg) * dot_product_length(cfg)     # ≈ h·w·k
bound = nbits_target * adjustment_factor
```

and the rank-penalty softfork (#275):

```
penalized_adjustment_factor(cfg) = tile_size * (dot_product_length / rank) * 128
```

`observed` Shape constraints enforced on every accepted proof:
`r` a power of two in `[32,1024]`; `k ≤ 2^16`; `k ≡ 0 mod 64`; `k ≤ 4r²`; `k ≥ 16r`;
`k ≥ 1024`; `h·w ∈ [32,256]`; `m,n ≤ 2^24`.

`derived` The naive "mine at minimum k to maximise attempts per FLOP" strategy is
neutralised: the target is scaled linearly in `k` and in tile size, and the rank penalty
removes the corresponding gain from raising `r`. **Any Aeye analysis that presents shape
grinding as an open attack is wrong.** It is closed by construction, in code, on-chain.

## F5. In the vLLM miner, A is activations and B is the *checkpoint weight tensor, verbatim*

Path: `miner/vllm-miner/src/vllm_miner/vllm_kernels.py::_apply_weights_mining`,
`miner/vllm-miner/src/vllm_miner/vllm_scheme.py::PearlScheme.create_weights`.

`observed`

```python
x_q, x_s, _ = quant_7bit(x, smooth_scale=..., block_size=hadamard_block_size)
m, k, n = x_q.shape[0], x_q.shape[1], w_q.shape[0]
pearl_gemm_noisy(x_q.contiguous(), w_q.contiguous(), ...)
```

`observed` `w_q` is registered as `ModelWeightParameter(dtype=torch.int8)` loaded straight
from a `compressed-tensors` checkpoint, and `process_weights_after_loading` re-wraps it
**without modifying its values** — "Pearl GEMM kernels expect non-transposed weights".

`observed` Naming in `zk-pow/src/api/proof.rs` confirms the roles:
`hash_activations = blake3(hash_a || hash_router)` in the MoE setting.

`derived` Therefore, for a mining GEMM:
- `A` = per-batch quantised activations, `m` = **number of tokens in the batch**;
- `B` = the layer's weight shard; `Bᵀ` = `w_q` exactly, row-major, `n × k`;
- `hash_b` = keyed BLAKE3 Merkle root over **the raw bytes of a public checkpoint tensor**.

> `derived` — **THE SECOND CENTRAL FINDING.**
> `hash_b` is a deterministic, publicly recomputable function of
> `(job_key, model, layer, tensor-parallel shard)`.
> `job_key` is public (block header + 52-byte config).
> Pearl Research Labs publishes its mining checkpoints openly.
> ⇒ **For any Pearl block, anyone can test whether its `hash_b` is the commitment of a
> known model's weight slab — with no protocol change, no miner cooperation, and no
> access to anything private.**

`observed` Pearl's public checkpoints (huggingface.co/pearl-ai, retrieved 2026-08-30):
`Llama-3.3-70B-Instruct-pearl` (71B), `Llama-3.1-8B-Instruct-pearl` (8B),
`Qwen3-30B-A3B-Instruct-2507-pearl` (31B), `Gemma-4-31B-it-pearl` (31B).
The registry that makes the oracle work is **four models wide**.

`hypothesis` (must be verified) The CUDA `tensor_hash.cu` path hashes byte-identically to
the Python `MatrixMerkleTree`; tensor-parallel sharding partitions `w_q` by output rows so
the slab set is `(layer × TP-degree × shard)`; `should_use_noisy_gemm(m,n,k)` plus the F4
shape bounds restrict which layers ever mine.

## F6. Pearl's mined arithmetic is integer-exact — Hawkeye does not apply to it

`observed` `MMAType::Int7xInt7ToInt32` is the only accepted MMA type
(`zk-pow/src/api/proof.rs`). Operands are int8 restricted to a 7-bit range; accumulation is
int32; `noisy_gemm.py` validates the range so that `A + E_A` cannot overflow int8.

`observed` The vendored Hawkeye implementation
(`evidence/external/hawkeye/include/{Ampere,Hopper,Hopper_fp8}_simulator.h`, `gfloat.h`)
models **floating-point** tensor-core behaviour: FP16/BF16/FP8 with a 25-bit internal
Hopper accumulator, 17-element accumulation groups, subnormal and rounding discovery.

`derived` **Hawkeye is not needed for Pearl's mined GEMM, and cannot be applied to it.**
Integer MMA with int32 accumulation is associative, exact, and bit-identical on every
device. The float non-determinism Hawkeye reproduces lives in the *glue between* the mined
GEMMs — RMSNorm, RoPE, attention/softmax, residual adds, the dequantisation scales, the
Hadamard rotation, sampling.

`observed` Hawkeye and the Pearl PoUW paper share an author (Ilan Komargodski). Hawkeye:
Badash, Boneh, Komargodski, Srivastava, MLSys 2026.

---

## F7. The published criticism, stated precisely

Source: arXiv:2606.04819, *The Usefulness Gap in Proof-of-Useful-Work: An Empirical Study
of Pearl's cuPOW Protocol*. Retained at `evidence/papers/pearl-usefulness-gap-2606.04819.pdf`.
All figures below are `author_claim`, not independently reproduced here.

`author_claim` A stripped miner ("turbo4") running the full NoisyGEMM pipeline on
**uniformly random matrices** (M=N=131072, K=4096, entries in {−64..64}) passed
`verify_plain_proof()` 20/20 locally and produced **44 pool-accepted shares** across
NVIDIA, AMD, CPU and Apple Silicon.

`author_claim` A distribution defence is not sufficient: uniform-random kurtosis 1.79 vs
quantised-weight 3.33, but `N(0,18)` clipped to `[−64,64]` reaches 2.97 at zero cost.

`author_claim` Network: ~24 EH/s, ~112 MW, ~320k GPU-equivalents; 8,012 analysed workers
all on inference-capable hardware; the dominant mining binary contains no inference code.

`author_claim` §5.6 "Toward Closing the Gap" lists five directions. Direction 4 is
*"Cryptographic data commitments: bind matrix provenance to externally verifiable
commitments; requires external PKI infrastructure."*

`author_claim` §5.1 asserts the gap is *"structurally unfixable at the hash level"* because
"the protocol cannot reward useful matrices more than random ones because the hash function
is agnostic to input semantics."

`derived` The last claim is true and irrelevant to F3+F5. The gap is indeed unfixable *at
the hash level*. It is addressable at the **pre-image level**, because the hash already
binds the operands and the weight operand is publicly reconstructible. That distinction is
the entire opening.

`derived` Under F5, the specific attack demonstrated in that paper — random matrices, any
hardware, including CPU and Apple Silicon — becomes **publicly detectable**, because a
random-matrix miner cannot produce a `hash_b` that opens to any registered weight slab.

---

## F8. What Pearl does *not* bind (the honest list)

| # | Not bound | Consequence |
|---|---|---|
| 1 | The pre-image of `hash_b` | Weights may be anything. Addressed by L2 (PoME). |
| 2 | The pre-image of `hash_a` | Activations may be anything. Addressed by L3 (CEL). |
| 3 | Which layer / model / shard `B` is | No layer index anywhere on the wire. |
| 4 | Causal succession between GEMMs | Each job is independent; nothing links op *i* to op *i+1*. |
| 5 | Which request each of the `m` rows of `A` belongs to | Batch co-tenancy is invisible. |
| 6 | The float glue between mined GEMMs | Never touched by any Pearl proof. |
| 7 | Any external demand event | Explicitly out of scope in Pearl's design. |
| 8 | Sampling / output tokens | Never committed. |

`derived` Items 1–3 are addressable by a pure observer with zero protocol change.
Items 4–5 need a sidecar receipt and, to become consensus-bound, one 32-byte field.
Items 6–8 need declared semantics and a demand anchor, and can only ever be
*conditionally* verified.
