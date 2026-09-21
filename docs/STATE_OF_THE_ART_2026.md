# State of the Art: Verifiable Inference and Useful Work

Status: `observed` and `derived` as labelled  
Cutoff: 2026-09-21

This survey uses retained primary papers and pinned repositories. Performance figures are
`author_claim` unless an Aeye experiment is explicitly identified. Different rows prove
different relations and their percentages are not directly comparable.

## Evidence matrix

| System | Strongest actual primitive | Scope evaluated | Important boundary for Aeye |
|---|---|---|---|
| Aeye E-009-R1 | Complete toy causal execution receipt combining five coded-linear relations with eight exact state/nonlinear/decode/output relations under one subject | One 13-event finite-field hard-attention block; separate code path accepted 80/80 coded equations and rejected 8/8 mutations | First retained `R_X(subject,h_A,h_B)` witness, but WORK roots are synthetic, preprocessing authentication touches every model matrix, Fiat–Shamir soundness is grinding-conditional, the trace is public, and local Python costs are not production evidence. |
| Aeye E-000 MC1 | Real public-checkpoint byte reconstruction and keyed-tree parity across Python, Rust, and pinned Pearl | 15 preregistered 8B family/shape classes; 311,427,072 raw bytes per owner lane under a synthetic non-candidate key | Closes a pre-candidate byte-path calibration question. It does not inspect a certificate, compare `hash_b`, establish runtime participation or source independence, or support an Aeye coordinate. |
| Aeye PAB-1 proposal | Cross-proof position binding between Pearl's native selected activation strips and a separate request/model/pre-state origin relation | Source-pinned INT certificate-v3 construction and cost formulas; no implementation | Uses established commitment composition rather than a new primitive. It could establish sampled activation origin without changing Pearl consensus, but full execution, output binding, native GPU semantics, demand, cost, and independent review remain open. |
| Pearl PoUW INT certificate-v3, arXiv:2504.09971 and pinned commit `4a0c24b` | Near-naive matrix-work evidence from arbitrary committed operands | Matrix multiplication under the retained INT certificate-v3 lineage | Security relies on the paper's non-standard batch low-rank correlated-equations conjecture; the paper explicitly separates economic value and does not bind request/model/graph/output. One certificate is not a whole inference. |
| Pearl FP8 certificate-v4 proposal, September 2026 specification and open PR #311 | FP8 matrix-work evidence using post-noise nonlinear quantization, bit-exact selected-tile recomputation, and a jackpot policy | Proposed Blackwell/B200 device and quantization profile; PR head `f7fe16c8` at retrieval | Security rests on an explicit informal quantized-subspace hardness assumption. The work model omits several ancillary costs, and the relation still does not bind a request, complete model execution, output, or demand. Open/unmerged is not deployed consensus. |
| Hawkeye, MLSys 2026 | Empirical CPU reproduction of selected NVIDIA Tensor Core MMA arithmetic | Public artifact: Ampere/Hopper FP16/BF16 and Hopper E4M3 FP8; paper reports 100,000 random 16×16 trials | Arithmetic conformance only. No commitment, proof, device attestation, full vLLM path, or physical-origin guarantee. Large PyTorch GEMMs may select different schedules. |
| MMA-Sim, arXiv:2511.10909v2 | Broader bit-accurate MMA instruction models with differential tests | Ten NVIDIA/AMD architectures; many FP formats; authors report one million randomized tests including bit-stream edge cases | Stronger profile implementation than Hawkeye, but still an empirical instruction oracle, not execution provenance. Aeye should require agreement plus retained target-device vectors. |
| DeepProve, ePrint 2026/1112 | End-to-end ZK relation for quantized autoregressive inference | GPT-2 124M and Gemma 3 270M; author reports 174/86 tokens per minute, 1–3.7s verification, and multi-MiB proofs | The strongest current full-relation lane retained here. It proves its integer/quantized relation, not native GPU arithmetic, physical work, or external demand; it is far from <1% incremental serving cost. |
| Maverick, arXiv:2609.10264v1 | Information-theoretically sound delegated matrix-vector verification with transparent preprocessing and efficient batch verification; LPN-based masking adds privacy | End-to-end Qwen3-4B prototype; server performs ordinary linear multiplication while the client evaluates nonlinear operations | A strong low-server-overhead online execution candidate, but not automatically a publicly transferable receipt, complete server event-DAG proof, physical-work proof, or demand evidence. Preprocessing, client state/work, and exact finite-field/model semantics remain in scope. |
| Artemis, arXiv:2409.12055v2 | Generic commit-and-prove SNARK linking proof witnesses to external homomorphic polynomial commitments through a polynomial-equality check | Halo2 implementation over models from MNIST through distilled GPT-2; authors report large reductions in commitment-check overhead, including VGG overhead from 11.5x to 1.1x | Establishes that commitment consistency is already a developed primitive, narrowing Aeye's possible contribution to the exact Pearl-native composition boundary. Pearl's keyed BLAKE3 tree is not a homomorphic polynomial commitment, so Artemis does not directly open or translate `hash_a`/`hash_b`. It adds neither WORK nor DEMAND. |
| Sound Debloating, arXiv:2609.10149v1 | Provenance-guided abstract interpretation removes only constraints whose enforced facts remain derivable | ezkl/zkml circuits up to 25.3M constraints; authors report up to 48.7% constraint removal and 72.8% prover-time reduction | Optimizes a frozen relation without enlarging its accepted-witness set under the proved entailment rules. It cannot repair an under-specified Aeye public-input relation or remove a required causal check. |
| zkComposer, arXiv:2607.08095v1 | Parallel contiguous-layer/sequence subproofs linked by shared activation commitments | CNNs and GPT-2; authors report up to 4.83× layer-partition and 6.84× layer+sequence prover-time speedups, with proof-size/resource tradeoffs | Composition/parallelization technique, not new execution semantics. Boundary commitments must bind the exact Aeye activation relation and inherit component proof assumptions. |
| Jolt Atlas, arXiv:2602.17452v1 | Lookup-centric sumcheck proof DAG over ONNX tensor operations with streaming/small-space techniques | nanoGPT and GPT-2 125M; author reports about 38s end-to-end for the GPT-2 proof breakdown | Promising compiled-model lane, but ONNX/circuit semantics are not native serving scheduler, cache, kernel, or GPU semantics. Operator support and approximation/quantization remain explicit. |
| zkGPT, USENIX Security 2025 | Full cryptographic relation for quantized GPT-2 | Author reports 21.8s prover, 0.35s verifier, 101KB proof on a 32-thread CPU setup | Strong soundness for the encoded circuit, not hardware provenance or native float semantics. |
| NANOZK, arXiv:2603.18046v2 | Proposed layerwise Halo2/IPA proof chain | Measurements stop at small attention/block dimensions; GPT-2-scale values are projected | Code was not retained at the advertised location and tables conflict. Do not use its headline as deployment evidence. |
| TensorCommitments, arXiv:2602.12630v1 | Tensor-native position-binding commitments and openings | Reports 0.97% post-inference prover and 0.12% verifier overhead on LLaMA2-13B/A100; 96.02% empirical detection | Appendix F proves opening/position binding, but the written construction does not enforce `T_l=f_l(T_{l-1},W_l)`. The reported detection rate is empirical, not negligible cryptographic execution soundness. Quarantine as a data structure pending independent review. |
| Lightweight Cryptographic Proofs, arXiv:2603.19025 | Post-commit random path checking with local transition recomputation | Llama-2-7B; author reports ~12.44ms verifier and ~3.4MB proof for one path | Provides formal other-model soundness only under trace separation; worst-case concentrated corruption has weak single-path detection. Cleartext openings leak model/trace data. |
| IMMACULATE, arXiv:2602.22700 | Selective auditing against a trusted CPU-TEE reference | Dense/MoE models; <1% throughput loss by auditing a tiny request fraction | System overhead is amortized across mostly unaudited traffic; guarantees depend on cheating prevalence and a much slower reference path. Not a per-request proof. |
| Verde, ICML 2025 | Optimistic duplicate execution and bisection to a disputed operator | Deterministic FP32 reference kernels; single/multi-provider experiments | Sound only if at least one provider/challenger is honest and data remains available; requires duplicate compute and changes native execution semantics. |
| VeriLLM, arXiv:2509.24257 | One-honest-verifier decentralized checking with incentives | LLM inference/verification network | Conditional on an honest verifier and economic model. The paper's 0.78% headline is inconsistent with its cited 33ms/1278ms component ratio; do not repeat without reproduction. |
| Repeated-Game Security for Restaking-Based Verifiable Inference, arXiv:2608.09055v1 | Closed-form repeated-game analysis of bounded/proportional slashing, plus history-dependent challenges, reputation-weighted slashing, and stake vesting | Nine open-weight model pairs in the authors' calibration; author reports a 2.6× audit-rate reduction in one setting and lower deviation profits | Incentive compatibility is conditional on the game, detection response, discount factor, stake identity, and stationary-deviation model. It is not cryptographic execution soundness and directly warns against one-round economic analysis. |
| Proof of Demand Is Not Proof of Work, ePrint 2026/1492 | Separates work soundness, job binding, and demand exogeneity; gives conditional indistinguishability and cost results for endogenous demand receipts | Formal model with free pseudonyms, fungible payments, coalition-controlled requester/worker roles, and explicit realizability or indistinguishability premises | Independently supports Aeye's refusal to infer `DEMAND` from work or job binding. It is not an unconditional impossibility theorem, a Pearl bridge, or a construction for execution origin; exogenous authorities and costly provenance change the premise set. |
| DiFR, arXiv:2511.20621 | Empirical token/activation divergence tests under synchronized seed/reference | vLLM integration; high AUC reported for tested substitutions | Detection rather than cryptographic soundness; depends on trusted reference behavior and attack distribution. Useful as an audit signal, never sole execution authority. |
| Hollow-LLM, IEEE S&P 2026 / arXiv:2607.28884 | Attack separating proof of a relation from proof of computational effort | Ghost/structured private weights under a fixed public architecture | Direct evidence that correct ZK inference is not `WORK`. A canonical public weight digest blocks this specific private-weight substitution but not all shortcut structure. |
| Evidence-Bound Gateway-Path Provenance, arXiv:2606.22560v1 | TEE-bound request, policy, route, endpoint-observation, and encrypted-stream evidence | Rust prototype with mock and AWS Nitro attestation paths | Proves a gateway-mediated path only under TEE, release-key, verifier, and supply-chain assumptions. The paper explicitly does not prove that the upstream provider served the claimed model or executed it correctly, and it has no Pearl-native commitment bridge. |
| TEE.fail, IEEE S&P 2026 | Physical attack on current CVM attestation trust | Intel TDX/SGX, AMD SEV-SNP, and relayed NVIDIA CC consequences | Attestation is conditional evidence, not a mathematical proof. Physical trust and binding a GPU quote to the intended CVM/job must be explicit. |
| Kernel Contracts, arXiv:2604.22032 | Proposed schema for portable kernel correctness claims | Twelve contract classes and documented incidents | Useful vocabulary, not a verifier or retained multi-device conformance result. |

## What “sub-1%” means in current work

The retained literature contains at least four non-equivalent uses of low overhead:

1. Pearl amortizes low-rank noising into a large GEMM and amortizes a succinct proof over a
   rare winner. This is a `WORK` protocol, not full execution verification.
2. TensorCommitments measures post-inference commitment/opening work, but its published
   construction does not prove the layer-transition relation.
3. IMMACULATE audits fewer than one in 100,000 requests in one configuration; low fleet
   overhead does not mean each receipt is strongly checked.
4. Hawkeye adds no prover work if a verifier independently re-executes, but its reported
   4096×4096 CPU replay costs roughly 40–53 seconds and covers only an MMA relation.
5. Maverick leaves the server's linear operation close to native but moves preprocessing,
   verification, nonlinear operations, and optional privacy work to the client. This is a
   different system boundary from provider-only overhead.
6. Sound Debloating and zkComposer reduce the cost of an already specified proof relation;
   neither makes a missing request/output/operand binding true.

Therefore `<1%` remains a valid target only for Aeye's commitment-only fast path. Every
stronger lane must publish its own end-to-end cost.

## Derived design consequences

- No retained system proves all four Aeye coordinates.
- Aeye must compose *relations*, not brand names: Pearl is a `WORK` adapter; Hawkeye and
  MMA-Sim are arithmetic-profile adapters; DeepProve/zkGPT are strong-relation candidates;
  Verde is an optimistic candidate; TEEs are conditional provenance candidates.
- Maverick is the most interesting new low-server-overhead primitive for linear-transition
  verification, but a transferable Aeye result still needs public-input binding, complete
  nonlinear/cache/output coverage, and an independently appraised transcript.
- E-009 supplies that binding and complete denominator for one toy profile. It also shows
  why a scalable construction needs authenticated, amortized preprocessing: independently
  recomputing `Q=G^T M` restores correctness by touching the full matrices.
- PAB-1 identifies a narrower native bridge: prove origin for Pearl's exact selected
  activation-strip positions and open those bytes under the same keyed `hash_a`. This can
  compose two private witnesses without placing them in one circuit, but upgrades only the
  covered strip prefixes and still requires exact quantization/profile and model-root
  binding.
- Artemis means that generic witness-to-commitment consistency is prior art, not an Aeye
  novelty claim. The unresolved contribution is a typed translation or shared-opening
  relation at Pearl's keyed-BLAKE3 positions, including the exact runtime bytes and claim
  ceiling; replacing Pearl's commitment with a convenient polynomial commitment would
  change the native statement rather than bridge it.
- Sound Debloating can safely reduce a fixed circuit only after the Aeye relation is frozen;
  zkComposer can parallelize it only when shared boundary commitments preserve equality.
- A coupled Aeye–Pearl result is a strict claim-surface extension: it projects to the native
  Pearl `WORK` statement, while the reverse implication fails on replayed/garbage operands
  or output grafts. This is not a claim that Aeye is a superior PoUW algorithm.
- Public, canonical model roots are important twice: they support Pearl operand census and
  block the specific private ghost-weight ambiguity highlighted by Hollow-LLM.
- Full proof lanes target quantized circuit semantics. Native production semantics require
  a separate, explicitly covered arithmetic profile.
- Strong work, correct execution, faithful arithmetic, and authentic economic ordering are
  not substitutable resources.
- Under the explicit free-pseudonym and endogenous-observation premises of ePrint
  2026/1492, job binding cannot certify economically independent demand. Aeye may verify a
  named authorization policy and retained provenance, but must not expose a universal
  `demand_proved` bit.
- TEE-backed gateway provenance can bind request routing and the client-observed stream,
  but it ends at an observed provider endpoint. It is a conditional `T2` input, not
  evidence that the upstream model executed correctly and not a replacement for PAB-1.
- Economic verification must be modeled across repeated service, not one query at a time.
  Proportional slashing can reduce future penalty exposure after detected cheating; any
  Aeye incentive lane must retain its discount-factor, stake-ownership, collusion, and
  history assumptions and may not upgrade `EXECUTION` cryptographically.

## Unresolved evidence

- Pearl FB-4a has not yet been discharged with a non-self-mined mainnet block and a
  checkpoint revision predating that block. MC1 reaches real checkpoint bytes under a
  synthetic key but does not perform the native comparison.
- The September FP8 certificate-v4 proposal has not been independently reproduced against
  B200 vectors, and the retained PR was open/unmerged at the cutoff. It must not be mixed
  with E-000's certificate-v3 hypothesis.
- Pearl FB-4b has no preregistered census result.
- No retained Hawkeye/MMA-Sim run was independently executed by Aeye on the exact target
  hardware and binaries.
- TensorCommitments' execution-soundness gap requires author clarification or an amended
  protocol before it can enter any Aeye verification lane.
- DeepProve has not been evaluated here on Pearl models or native Pearl quantization.
- Artemis has not been adapted to Pearl's keyed BLAKE3 roots; no retained construction
  proves equality between an Artemis-compatible polynomial commitment and Pearl's native
  tree without explicitly paying for and reviewing that translation relation.
- E-009-R1 instantiates `R_X(subject,h_A,h_B)` over its complete 13-event toy DAG. No
  retained backend instantiates it for actual Pearl roots, ordinary transformer semantics,
  batched serving/cache reuse, private inference, or production scale.
