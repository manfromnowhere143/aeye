# Pearl Activation-Origin Binding

Status: `observed` Pearl mechanics, `derived` propositions, and `proposed` construction as labelled  
Date: 2026-09-21  
Protocol scope: Pearl INT certificate-v3 at commit
`4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0`, dense mainnet lane at and after
height `99000`; verifier route `zk-pow/src/api` + `zk-pow/src/circuit` +
`zk-pow/src/ffi`, with `SeedDerivation::Salted`  
Transfer rule: no conclusion in this note transfers to another Pearl version without a new
source inspection and fixture

## Executive conclusion

Pearl already supplies most of the cryptographic *meeting point* needed for an execution
binding: a keyed BLAKE3 root `hash_a` and in-circuit openings of the selected activation
strips that enter its work relation. It does not establish where those activation bytes
came from.

The smallest credible extension is therefore not a replacement work proof and not a new
field in Pearl's certificate. It is a separate **activation-origin companion relation**
that:

1. consumes Pearl's exact block-header and public-data bytes;
2. derives Pearl's exact `job_key`, row indices, strip length, and `hash_a` from those
   bytes;
3. proves that the bytes at those exact positions arise from a committed request, model,
   pre-state, and execution profile; and
4. opens those bytes against the same `hash_a` under the same `job_key`.

If the native Pearl proof and the companion proof both verify, Merkle position binding
forces their private strip values to agree except with the component soundness and hash-
binding error. The two proofs need not share a witness or be rebuilt into one circuit.

This is a precise composition target, not a completed protocol. It would upgrade
`EXECUTION` only for Pearl's selected strip prefixes. It would not by itself establish the
rest of the model path, output binding, native GPU semantics, physical device origin, or
independent `DEMAND`.

## 1. Source-pinned facts

The table distinguishes the base STARK public-input layout from the complete certificate
input reconstructed by the verifier. Quoting only the six 256-bit layer-0 fields is not a
sufficient description of the final recursive verification statement.

| Fact | Status | Pinned evidence |
|---|---|---|
| The incomplete block header contains protocol version, previous-block hash, transaction Merkle root, timestamp, and difficulty bits. | `observed` | [`proof.rs:5–16`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/api/proof.rs#L5-L16) |
| `job_key = BLAKE3(block_header_bytes || mining_config_bytes)`. | `observed` | [`proof_utils.rs:345–353`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/api/proof_utils.rs#L345-L353) |
| The current layer-0 STARK exposes `JOB_KEY`, `COMMITMENT_HASH`, `HASH_A`, `HASH_B`, `HASH_ROUTING`, and `HASH_JACKPOT`, each as eight 32-bit words; `HASH_ROUTING` is zero for dense proofs. | `observed` | [`pearl_layout.rs:87–95`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/circuit/pearl_layout.rs#L87-L95), [`pearl_trace.rs:156–214`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/circuit/pearl_trace.rs#L156-L214) |
| V3 embeds the V2 variable-length envelope and routes to `verify_zk_proof_v3`; dense public data is exactly 164 bytes, while the parser also defines a longer MoE form that mainnet consensus excludes before V3 activates. | `observed` | [`certificate_v3.go:12–24`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/node/wire/certificate_v3.go#L12-L24), [`verify.go:38–52`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/node/zkpow/verify.go#L38-L52), [`proof_utils.rs:1141–1165`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/api/proof_utils.rs#L1141-L1165), [`validate.go:536–551`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/node/blockchain/validate.go#L536-L551) |
| V3 selects `SeedDerivation::Salted`; this salts the raw A/B roots for the noise-seed chain but does not alter the raw `hash_a` or `hash_b` carried on wire. | `observed` | [`plain_proof.rs:158–178`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/ffi/plain_proof.rs#L158-L178), [`seed.rs:1–67`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/api/seed.rs#L1-L67) |
| The dense certificate's 164-byte public data carries the mining configuration, `hash_a`, `hash_b`, `hash_jackpot`, `m`, `n`, `t_rows`, and `t_cols`. | `observed` | [`proof.rs:76–105`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/api/proof.rs#L76-L105), [`proof_utils.rs:1167–1235`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/api/proof_utils.rs#L1167-L1235) |
| The recursive verifier additionally binds the public-data commitment, preprocessed evaluations, recursion verifier data, and circuit digest. | `observed` | [`pearl_circuit.rs:294–340`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/circuit/pearl_circuit.rs#L294-L340), [`pearl_circuit.rs:609–662`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/circuit/pearl_circuit.rs#L609-L662) |
| Selected dense A-row indices are `rows_pattern + t_rows`; the opened prefix length is `d = k - (k mod rank)`, not unconditionally all `k` bytes. | `observed` | [`proof_utils.rs:258–284`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/api/proof_utils.rs#L258-L284), [`proof_utils.rs:327–353`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/api/proof_utils.rs#L327-L353), [`program.rs:191–221`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/circuit/chip/blake3/program.rs#L191-L221) |
| The private witness contains selected A and B strips plus BLAKE3 messages and sibling chaining values; the V3 FFI parser extracts those strips and checks the reconstructed roots. | `observed` | [`proof.rs:142–164`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/api/proof.rs#L142-L164), [`plain_proof.rs:549–637`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/ffi/plain_proof.rs#L549-L637) |
| Matrix roots are keyed BLAKE3 over flattened `int8` bytes, zero-padded to a 1,024-byte chunk boundary. | `observed` | [`matrix_merkle_tree.py:8–47`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/miner/miner-base/src/miner_base/matrix_merkle_tree.py#L8-L47) |
| The proof program hashes selected strip material and auxiliary material to `hash_a` and `hash_b`; one BLAKE3 compression occupies eight trace rows. | `observed` | [`program.rs:25–29`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/circuit/chip/blake3/program.rs#L25-L29), [`program.rs:182–221`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/zk-pow/src/circuit/chip/blake3/program.rs#L182-L221) |

These facts establish a real cryptographic handle on selected bytes. They do not establish
the semantic origin of those bytes.

## 2. The exact gap

Let `P` denote the versioned certificate input, including the exact serialized block
header, dense 164-byte public data, certificate version `3`, the implied
`SeedDerivation::Salted`, and proof-system parameters. From `P`, define

\[
J(P)=\operatorname{BLAKE3}(\operatorname{header}(P)\,\|\,
\operatorname{mining\_config}(P)),
\]

\[
I_A(P)=\operatorname{rows\_pattern}(P)+t_{rows}(P),\qquad
d(P)=k-(k\bmod r).
\]

Suppressing the B side and jackpot terms, Pearl's native relation contains a statement of
the following shape:

\[
R_W(P;\pi_W)=1\Longrightarrow
\exists S_A,\mu_A:\ 
\operatorname{Open}_{\mathrm{BLAKE3},J(P)}
\bigl(h_A(P),I_A(P),[0,d(P)),S_A;\mu_A\bigr)=1
\land R_{work}(P,S_A,\ldots)=1.
\]

Here `S_A` is the selected set of row prefixes and `mu_A` is the auxiliary BLAKE3 material.
The implication is scoped to the accepted native relation and its assumptions; it is not a
statement that all of `A` was publicly disclosed or independently executed.

Pearl's vLLM path constructs `A` by applying an optional block Hadamard transform and
SmoothQuant scale, taking a row maximum, computing a scale with an approximate reciprocal,
rounding and clamping to the 7-bit range, and returning both `x_q` and a per-token floating
scale. The mining kernel hashes the `int8` `A` and `B` tensors before passing the separate
scales into GEMM:

- [`quantization_operators.py:36–79`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/miner/vllm-miner/src/vllm_miner/quantization_operators.py#L36-L79)
- [`hadamard.py:331–469`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/miner/pearl-gemm/src/pearl_gemm/quantization/hadamard.py#L331-L469)
- [`vllm_kernels.py:187–224`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/miner/vllm-miner/src/vllm_miner/vllm_kernels.py#L187-L224)
- [`gemm_operators.py:118–150`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/miner/vllm-miner/src/vllm_miner/gemm_operators.py#L118-L150)
- [`gemm_operators.py:187–217`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/miner/vllm-miner/src/vllm_miner/gemm_operators.py#L187-L217)

Consequently, the following boundary is `derived` from the pinned implementation:

| Material | Bound by `hash_a` or `hash_b`? | Consequence |
|---|---:|---|
| Flattened, padded activation `int8` bytes | Yes, by `hash_a` | Selected native strips can be position-bound to an origin relation. |
| Flattened, padded weight `int8` bytes | Yes, by `hash_b` | A public reconstruction can test these bytes, but this alone is not a complete model identity. |
| Per-token activation scales `x_s` | No | Native acceptance does not identify the dequantized activation values or output scaling. |
| Weight scales `w_s` | No | The same `hash_b` can accompany different scale metadata outside the native root. |
| SmoothQuant scale | Not separately | Its effect may change `x_q`, but the native root does not name the scale and different source/scale pairs can quantize to the same bytes. |
| Hadamard block size and transform profile | Not separately | Their effect may change `x_q`, but the origin proof must bind the profile explicitly. |
| Layer identity, checkpoint revision, tokenizer, request, cache, or pre-state | No direct relation | They require an external model/subject relation. |
| GEMM output `C` or final inference output | No | Activation-origin binding alone cannot prevent an output graft. |

### Correction to the overly broad request claim

It would be wrong to say that nothing in Pearl's statement references a request-capable
commitment. The block header includes a transaction Merkle root, and that header enters
`job_key`. Thus `hash_a` is domain-separated by a value that may commit to transactions.

That is not yet `DEMAND` or execution derivation. For any admissible header and any
unrelated activation matrix `A'`, a prover can compute
`hash_a' = BLAKE3(A', key=job_key)` and attempt the same native work relation. The native
constraints contain no transaction-membership witness, request schema, requester
authentication, temporal authorization rule, or function connecting a transaction leaf to
`A'`. The header-to-key edge says *which job namespace hashes the bytes*; it does not say
*why those bytes exist*.

An independently committed demand claim would additionally require, at minimum:

1. a transaction inclusion proof under the exact header root;
2. a versioned request and authorization schema;
3. an authenticated requester or qualifying economic actor;
4. an ordering rule showing authorization preceded the covered execution; and
5. a relation connecting that request to the same activation-origin subject.

## 3. Proposed minimal construction: PAB-1

`PAB-1` is a working label for the **Pearl activation-binding companion relation**. It is
not implemented and no novelty claim is attached to the name.

### 3.1 Public bridge

The companion verifier consumes exact bytes, not independently re-encoded semantic
equivalents:

\[
\beta=(v,\operatorname{header}_{76},\operatorname{public\_data}_{164},
\operatorname{pow\_bits},\operatorname{rate\_bits},
\sigma,r_{req},r_{model},r_{profile},r_{pre},b).
\]

`v` is the certificate/parser version, `sigma` is the Aeye subject root, `r_req` is the
request root, `r_model` is a complete model lineage root, `r_profile` is the numerical and
runtime profile, `r_pre` is the relevant pre-state/cache root, and `b` identifies the exact
model boundary whose activation becomes Pearl matrix `A`.

The companion verifier must parse the Pearl bytes with the version-pinned parser and
recompute `J(P)`, `h_A(P)`, `h_B(P)`, `I_A(P)`, and `d(P)`. A digest of decoded fields is
insufficient unless byte-level canonicalization and domain separation are independently
proved.

### 3.2 Private witness and relation

For the zero-knowledge lane, the private witness contains the request/pre-state openings,
the required model material, intermediate activation state, selected quantized strips, and
BLAKE3 multiproof material. The relation is:

\[
\begin{aligned}
R_O(\beta;\pi_O)=1\Longleftrightarrow\exists \xi,Z,A^*,S^*,\mu^*:\quad
&\operatorname{SubjectOpen}(\sigma;\xi)=
(r_{req},r_{model},r_{profile},r_{pre},b)\\
\land\;&Z=\operatorname{PrefixExec}_{r_{profile}}
(r_{req},r_{model},r_{pre},b;\xi)\\
\land\;&A^*=\operatorname{Quantize}_{r_{profile}}(Z)\\
\land\;&S^*=A^*[I_A(P),0:d(P)]\\
\land\;&\operatorname{Open}_{\mathrm{BLAKE3},J(P)}
(h_A(P),I_A(P),[0,d(P)),S^*;\mu^*)=1.
\end{aligned}
\]

The first implementation may replace `PrefixExec` with disclosed deterministic replay.
That changes privacy and trust properties, not the byte-level bridge.

The model relation must separately connect `r_model` to `h_B(P)` and to all semantic
material omitted from `hash_b`, including weight scales. Its checked predicate must name
the checkpoint revision, tensor names, scales, layer boundary, vLLM/Pearl code pins, TP
rank and degree, fusion order, layout, and quantization profile; derive the exact runtime
`B^T` byte-string; and establish

\[
\operatorname{BLAKE3}_{J(P)}
\bigl(\operatorname{pad}_{1024}(\operatorname{bytes}_{i8}(B^T))\bigr)=h_B(P).
\]

For a public checkpoint, a successful E-000 reconstruction is one candidate input to this
predicate, not the predicate itself. For a private model, this requires a proof or typed
attestation; naming a checkpoint beside `hash_b` is not binding.

### 3.3 Positional bridge lemma

Let `V_W(P,pi_W)=1` be an accepted native Pearl proof and
`V_O(beta,pi_O)=1` be an accepted sound companion proof whose embedded `P` is byte-for-byte
identical. Require deterministic parser, version-route, canonicalization, endianness, and
domain-separation checks to succeed before either proof result is composed. Assume the keyed
BLAKE3 tree is position-binding for `J(P)`. Then the native Pearl strip witness `S_A` and the
origin-derived strip witness `S*` are equal at every covered byte position, except with
probability bounded by

\[
\epsilon_{bridge}\leq
\epsilon_W+\epsilon_O+\operatorname{Adv}^{pos-bind}_{\mathrm{BLAKE3}}.
\]

**Proof sketch (`derived`).** Native acceptance authenticates `S_A` at the positions
derived from `P` under root `h_A(P)`. Companion acceptance authenticates `S*` at the same
positions under the same key and root. If `S_A != S*` at any covered position while both
openings verify, one component proof is unsound or the commitment admits two values at one
position. Union-bound those cryptographic events. Parser disagreement, a wrong certificate
route, or a domain mismatch is a deterministic implementation failure and rejects the
composition; it is not assigned a fictitious probability. No private witness equality is
assumed across the two proof systems.

This is standard commitment composition, not a new cryptographic primitive. The useful
engineering claim is the exact Pearl-native statement to which it must be applied.

## 4. Three honest evidence lanes

| Lane | What establishes origin | Main price | Result type |
|---|---|---|---|
| Disclosed deterministic replay | An auditor obtains the request, model/profile, and required state; replays through boundary `b`; quantizes; and checks the same keyed root/positions. | Request/state privacy, model access, full prefix cost, and numerical reproducibility. | Strong software evidence for the disclosed profile; not zero knowledge or device origin. |
| Zero-knowledge companion proof | A proof establishes `R_O` and exact keyed BLAKE3 membership without disclosing the private request/state. | Potentially dominant prefix-execution, floating-point/quantization, and BLAKE3 constraint cost. | Cryptographic sampled execution-origin evidence under the encoded semantics. |
| Typed TEE or independent-auditor attestation | A named trust domain authenticates the subject, profile, exact Pearl bytes, and selected strips. | Hardware/operator trust, revocation, freshness, and quote-to-job binding. | Conditional provenance evidence; never relabelled as mathematical proof. |

A signature over `(subject_root, hash_a)` without replay, proof, or a named trust domain is
not a fourth lane. It authenticates an assertion, not the derivation asserted.

Maverick-style delegated verification can reduce the online cost of covered linear
transitions, and zkComposer-style boundary commitments can partition a complete proof.
Neither removes the need to terminate at Pearl's exact positions and keyed root. Sound
debloating may optimize `R_O` only after its accepted-witness set is frozen.

## 5. Cost surface: what can and cannot be priced now

### 5.1 Exact BLAKE3 accounting

For a fully materialized activation matrix with `L = m*k` bytes and
`C = ceil(L/1024)` zero-padded chunks, standard BLAKE3 evaluation performs

\[
N_{compress}^{full}=16C+(C-1)=17C-1
\]

compression calls: 16 data-block compressions per 1,024-byte chunk and `C-1` parent
compressions. At Pearl's eight trace rows per compression, a direct in-AIR full-root path
has

\[
N_{rows}^{full}=8(17C-1)=136C-8
\]

BLAKE3 rows before any origin, parser, range, or composition constraints.

For a selected multiproof, let `U` be the distinct 1,024-byte chunks intersecting the
selected strip prefixes, and let `N_parent(U,C)` be the number of non-auxiliary parent
compressions in the canonical multiproof. Its hash work is

\[
N_{compress}^{multi}=16|U|+N_{parent}(U,C),\qquad
N_{rows}^{multi}=8N_{compress}^{multi}.
\]

`N_parent` must be computed from the frozen indices and tree, not replaced by a headline
asymptotic. Shared paths reduce it; non-power-of-two chunk counts and Pearl's exact tree
layout must be preserved.

### 5.2 Quantization is not a cheap afterthought

For `s` selected activation rows of width `k` and Hadamard block size `q`, the reference
operation surface includes approximately:

- `s*k*log2(q)/2` butterflies, or `s*k*log2(q)` scalar additions/subtractions;
- `s*k` normalization multiplications and, when enabled, `s*k` SmoothQuant
  multiplications;
- at least `s*(k-1)` comparisons for row maxima;
- one scale and approximate reciprocal path per row; and
- `s*k` multiply, rounding, clamping, conversion, and range-check paths.

This is not a circuit count. The pinned GPU kernel uses float32 intermediates,
`rcp_approx`, warp reductions, and a particular rounding/clamping sequence
([`hadamard.py:418–469`](https://github.com/pearl-research-labs/pearl/blob/4a0c24bc18dcb67cebca93c1ad38fb04837cb1a0/miner/pearl-gemm/src/pearl_gemm/quantization/hadamard.py#L418-L469)).
An exact constraint count is unknowable until the proof backend, field, lookup tables,
floating-point profile, row count, width, block size, checkpoint, and boundary are frozen.

The row maximum also means that proving one selected prefix generally requires the full
pre-quantized row, not merely that prefix. Earlier transformer state may require still
broader context and cache material. Any estimate that prices only `d(P)` quantized output
bytes omits load-bearing work.

### 5.3 Consensus and wire cost

The external composition changes zero Pearl consensus bytes and zero Pearl constraints.
Its extra proof bytes, verifier time, and subject material belong to Aeye and must be
reported separately. Adding a 32-byte request root to Pearl would be security-null unless
Pearl or a companion relation constrained it to the activation origin.

## 6. Required falsifiers and composition controls

### 6.1 Core PAB-1 relation falsifiers

No PAB implementation may claim support before an independent verifier rejects all of the
following with specific failure codes:

1. correct Pearl proof, changed request root;
2. correct request, changed `hash_a`;
3. correct roots, changed block header or `job_key`;
4. correct root, wrong `t_rows`, row pattern, row order, or strip length;
5. a full-row opening treated as equivalent to Pearl's actual prefix, or vice versa;
6. correct activation bytes under the wrong layer/boundary identifier;
7. unchanged `hash_a` with changed SmoothQuant scale, Hadamard profile, rounding profile,
   per-token scale, or cache pre-state;
8. unchanged `hash_b` with changed weight scales or checkpoint lineage;
9. certificate-version, parser, endianness, padding, or domain-separator substitution;
10. a companion proof whose decoded fields match while its Pearl wire bytes differ.

The positive fixture and every negative fixture must be generated independently from the
consequential verifier path. A producer cannot certify its own bridge.

### 6.2 Composition-only claim-laundering controls

Two important controls belong to the composite Aeye appraiser, not to the PAB-1 relation:

1. A valid PAB-1 proof accompanied by a transaction-root assertion but no transaction
   inclusion, authorization, ordering, and anti-self-dealing evidence may still satisfy
   the activation-origin relation. The appraiser must keep `DEMAND=unsupported` and emit a
   typed missing-demand finding; it must not require PAB-1 itself to reject.
2. A valid PAB-1 proof paired with a grafted or otherwise unbound output may still satisfy
   origin for the selected activation strips. The appraiser must keep the output path
   outside covered `EXECUTION` and emit a typed output-binding gap; an independent
   output/full-path relation, if claimed, is responsible for rejecting the graft.

These are mandatory anti-laundering tests for any composite receipt. Treating them as
PAB-1 failures would silently enlarge the companion statement from activation origin into
DEMAND and end-to-end output correctness.

## 7. Exact claim vector after a successful PAB-1

Assuming a valid native Pearl proof and a valid PAB-1 companion proof:

| Coordinate | Maximum defensible status | Ceiling |
|---|---|---|
| `WORK` | Native Pearl result, unchanged | Whatever the exact certificate version and its assumptions establish; PAB adds nothing to work soundness. |
| `EXECUTION` | `satisfied / sampled-native-strips` | The selected A-row prefixes at one named boundary derive from the committed origin relation. It is not automatically full-model or output-bound execution. |
| `SEMANTICS` | At most the companion profile for covered operations | No physical GPU origin; omitted float, scheduler, cache, or kernel behavior remains explicit. |
| `DEMAND` | `unsupported` unless the separate inclusion, authorization, ordering, and anti-self-dealing relation verifies | Header domain separation alone is insufficient. |

If a complete execution proof extends from the request through every required boundary to
the output, the execution coordinate may be stronger. That is a larger relation than
PAB-1 and must carry its own event denominator.

## 8. Novelty and research verdict

The components—Merkle position binding, proof composition, zkML, deterministic replay,
and request commitments—are established techniques. PAB-1 should not be advertised as a
new primitive.

The potentially valuable contribution is narrower and more concrete: it identifies the
exact private Pearl witness that can serve as the cross-proof equality boundary, corrects
the transaction-root nuance, exposes the scale/profile material omitted by native operand
roots, gives a versioned bridge tuple and error budget, and states precisely how much
`EXECUTION` would and would not follow. Whether that system formulation is novel remains
`unknown` pending independent literature and cryptographic review.

For an expert audience, the credible sequence is:

1. freeze this relation and its negative fixtures under independent review;
2. obtain emitted-code and positive GPU vectors for the row-consistent quantizer relation;
   build PAB-0 only as quantizer consistency, not request or activation origin;
3. run E-000's preregistered public-checkpoint opening to learn whether
   `hash_b` corresponds to published model material in practice;
4. freeze one real layer, shape, profile, and privacy lane, then produce a measured
   companion proof or a falsifying cost result; and
5. obtain independent cryptographic and protocol-engineering review before any security,
   performance, novelty, or adoption claim.

The strongest current verdict is therefore: **PAB-1 is a source-grounded candidate for the
missing Pearl-to-execution bridge, not yet a result. E-000 remains the highest-value
empirical result available to Aeye.**

### 8.1 PAB-0 review correction

The latest same-workstation reviewer packet accepts with amendments only a
row-consistent membership relation for Pearl's quantizer. For each disclosed row, one
verifier-enumerated reciprocal witness must explain every output byte, and bit-equal
denominators share one deterministic witness inside the declared context. A
prover-supplied reciprocal is only a hint.

The earlier per-byte lane is withdrawn because independent per-element witness choices
do not model one row-level quantizer context. Exact GPU stability is rejected without
emitted-code and positive device vectors. PAB-0 is therefore blocked. Even if completed,
its maximum claim is selected-row quantizer consistency under the declared profile. It
does not establish request binding, activation origin, `EXECUTION`, output correctness,
or demand.
