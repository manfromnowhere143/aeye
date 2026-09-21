# Aeye Session Handoff

Status: public research packet with one `supported` toy result, a corrected post-hoc appraisal boundary, and an unaccepted E-000 pilot whose phase order is corrected but awaiting fresh review and pre-candidate artifacts; architecture acceptance not granted  
Date: 2026-09-21  
Canonical root: `/Users/danielwahnich/workspace/aeye`

## Active mission

Determine whether a technically defensible Aeye protocol can compose four independently testable receipt claims—`WORK`, `EXECUTION`, `SEMANTICS`, and `DEMAND`—using Pearl PoUW, Hawkeye or equivalent arithmetic reproduction, modern verifiable-inference systems, cryptographic commitments, and externally anchored request evidence.

The required outcome is an evidence-backed architecture verdict, not a promotional concept document. The investigation must identify:

- the strongest construction defensible with current techniques;
- exact trust assumptions and non-claims for every layer;
- attacks that pass one layer while violating another;
- realistic cost and latency envelopes;
- the smallest experiments capable of falsifying the design;
- go, conditional-go, pivot, and stop criteria.

## Immutable working decomposition

Until amended by an accepted architecture decision, the investigation treats these as distinct predicates:

- `WORK(receipt)`: the claimed lower bound or class of computation is evidenced.
- `EXECUTION(receipt, request, model, graph, output)`: evidenced work is bound to the committed inference transcript.
- `SEMANTICS(receipt, arithmetic_profile)`: checked operations conform to the named arithmetic semantics within an explicit coverage boundary.
- `DEMAND(receipt, authorization_event)`: the request preceded execution and was authorized by an independently committed principal or mechanism.

The conjunction is not implied by any single predicate.

## Initial research tracks

1. Pearl PoUW assumptions, protocol mechanics, code maturity, and substitution attacks.
2. Hawkeye identity, arithmetic coverage, reproducibility claim, and hardware-generation limits.
3. 2025–2026 verifiable-inference, zkML, optimistic verification, fraud proofs, TEEs, and proof-of-learning/useful-work literature.
4. Commitment graph for request, model/version, weights, execution DAG, intermediate activations, output, arithmetic profile, and demand event.
5. Adversarial harness: replay, precomputation, model substitution, output grafting, layer omission, arithmetic substitution, equivocation, requester collusion, and fake-demand attacks.
6. Measurement protocol for incremental prover overhead and verifier cost.

## Current repository state

The architecture packet has moved from prose-only bootstrap to a replayable research
contract and one successful claim-bearing toy experiment. No architecture has been
accepted, no production protocol or native Pearl proof backend has been implemented, and
no production performance or end-to-end security claim has been validated.

Implemented structural controls:

- retained primary papers, standards, pinned repositories, and Pearl PR material in a
  schema-checked, content-addressed source ledger;
- research schemas for evidence receipts, independent verification reports, source
  ledgers, experiment manifests, and negative fixtures;
- deterministic checks for intent/job/subject binding, ordering, coordinate laundering,
  assumptions, coverage, native evidence inputs, Pearl→execution operand equality,
  reviewer independence, local links, and retained-source integrity;
- a deterministic finite-field coded-MVM interface demonstrator with transparent
  Reed–Solomon/Vandermonde preprocessing, subject-bound sparse challenges, an exact
  soundness bound, and altered-output rejection; it is explicitly not E-009;
- three valid structural fixtures and 15 known-bad fixtures;
- formal no-laundering, demand-separation, projection, strictness, and conditional coupling
  arguments;
- a standards crosswalk that maps Aeye onto RATS/CMW/CBOR/COSE/EAT/SCITT without claiming
  conformance;
- separate experiment manifests for historical INT certificate-v3 reconstruction (E-000)
  proposed FP8 certificate-v4 verifier/B200 parity (E-008), and the first toy coded-linear
  coupling relation (E-009), plus the proposed authenticated-preprocessing successor
  (E-010).

E-000 pre-candidate state:

- the separate review lane retained `experiments/e-000/reviewer-freeze.json` and
  `docs/E000_ACCEPTANCE_CHECKLIST_2026-09-21.md` with verdict
  `ACCEPT_WITH_AMENDMENTS`; this is same-workstation machine review, not operator
  acceptance or independent human review;
- the owner amended all twelve manifest items and added an executable semantic audit.
  The readback's retained digests were reviewer freeze
  `d37acfa1de34fec048af058bdcabbfb40a3dbf977feddc7d03f259895cb2d419`, checklist
  `5d2f613f35fae2e46903b67356f493aafcb108326f2d12bc9e33d381e82dd43c`, and amended
  manifest `39fd3256068adc9471f538e1ec094d591b5a14f38341542c37a0bdff6ea5845e`;
- the adversarial readback at commit `8ed1498e` returned `AMENDMENTS_CONFIRMED` and
  demonstrated that `89085d...` was a superseded unretained serialization. The exact
  retained freeze digest is `d37acfa1...`; neither value currently authorizes acceptance;
- the same readback exposed that the owner audit is semantic-light and that most of the
  fixed controls and full implementation-independence boundary remain unimplemented;
- a subsequent owner check found an internal phase-order contradiction: Phase 2 created
  `T_accept` before the registry, recipe, implementations, and controls are frozen, while
  other retained rules require registry retrieval before `T_accept` and require the
  candidate not to exist when those artifacts are accepted;
- ADR-0012 now orders sources, registry, recipe, two implementations, and all controls
  before fresh review and `T_accept`. ADR-0013 makes the manifest immutable, embeds the
  corrected candidate-selection rule, and moves fresh-review and operator bindings into
  separate content-addressed records;
- the predecessor review artifacts are explicitly historical. Only their terminal-state
  semantics and named control contracts remain imported; their phase numbering,
  acceptance predicates, and reviewer-observation rule are superseded;
- the corrected fail-closed manifest hashes to
  `011d3c232ce9638fc265730f01b13dd3e11d87c225d19ad17842a44d7a78ddc5`.
  It is an owner correction awaiting fresh reviewer readback, not operator acceptance;
- target-agnostic V3 parsing, an explicit int8 slab-transform engine, an independently
  written BLAKE3 reference lane, and pinned Pearl root parity are implemented and tested.
  They are conformance instruments, not the two frozen independent E-000 implementations;
- no candidate height, block hash, certificate, `hash_b`, or real opening has been
  selected or inspected. E-000 remains `blocked` before execution by the fresh-review,
  registry, recipe, implementation, and control gates.

Implemented experimental result:

- E-009-R1 was frozen by preregistration digest before execution;
- one 13-event finite-field causal block binds request, model, job, trace, output, and
  synthetic clean Pearl-side operand roots;
- five linear events use authenticated Reed–Solomon/Vandermonde preprocessing and 16
  post-subject checks each; eight state/nonlinear/decode/output events replay exactly;
- a separately implemented verifier with no provider-module imports accepted the
  unmodified bundle and rejected 8/8 preregistered mutations with the expected codes;
- the conditional five-relation coded-audit union bound is approximately `4.99e-25`
  (`2^-80.73`) before hash, Fiat–Shamir/grinding, parser, implementation, and Pearl terms;
- the retained vector is `WORK=unknown`, `EXECUTION=satisfied/sampled`,
  `SEMANTICS=satisfied/hybrid` only for the exact toy profile, and
  `DEMAND=unsupported`;
- toy timings and bytes are retained. They reveal high relative cost and are explicitly
  not production predictions. A later `exploratory-post-hoc` artifact separates local
  client challenge derivation from provider response construction without changing or
  upgrading R1.

Post-result adversarial disposition:

- a separate same-workstation machine-review session reproduced R1 and supplied a scratch probe; this is
  retained as untrusted machine review on the same workstation, not independent human or
  institutional review;
- the implementation owner independently replayed that probe and retained a deterministic
  post-hoc version without changing any frozen R1 input, implementation, or artifact;
- the probe changes one `q_linear` coordinate, regenerates every downstream event, root,
  subject, and challenge, then falsifies issuer acceptance fields. Sixteen coded equations
  naturally reject, and the verifier rejects through four coded-relation diagnostics;
- no binding, ordering, or exact downstream-event check separately rejects that fully
  regenerated trace. This narrows the interpretation of the eight targeted mutations but
  does not falsify the sampled coded relation;
- an operation count confirms 832 field multiplications to authenticate all five
  `Q=G^T M` objects versus 90 for exact replay of all five `Mx` products. At R1 scale the
  coded audit has negative system value and serves only as interface rehearsal;
- the accepted disposition and role split are in
  `docs/ADVERSARIAL_REVIEW_RESPONSE_2026-09-21.md`. The reviewer should own its review and
  the frozen E-000 checklist; the implementation owner should not ghostwrite either.
- `docs/PEARL_ACTIVATION_ORIGIN_BINDING_2026-09-21.md` now supplies the source-pinned
  Pearl-native analysis. It distinguishes the six layer-0 256-bit fields from the complete
  certificate input, identifies the exact selected strip-prefix witness under `hash_a`,
  specifies PAB-1 as an external companion relation, prices its BLAKE3 surface, and retains
  the quantization/model/profile costs as unresolved rather than inventing a constraint
  count.

Public-source release published on 2026-09-21:

- the README now leads with the exact claim vector, complete ceilings, adverse cost result,
  post-hoc probe, evidence-ranked next moves, and accessible Mermaid semantics;
- Apache-2.0 applies only to Aeye-authored work. Third-party paper, RFC, patch, and source
  payloads are absent from the public Git tree and remain under their own terms;
- `scripts/hydrate_external_evidence.py` materializes 33 digest-pinned files and six
  commit-pinned anonymous HTTPS Git checkouts from allowlisted public sources, fails closed
  on any existing mismatch, and never replaces a path;
- the public repository is `https://github.com/manfromnowhere143/aeye`. It begins from a
  reviewed source snapshot and does not expose earlier private Git objects. The full prior
  history remains in the private `manfromnowhere143/aeye-private-archive` repository;
- GitHub Actions uses pinned actions, uv 0.11.28, a universal hash-locked dependency set,
  Python 3.12/3.14 replay, and an unchanged-worktree gate. Required CI is independent of
  third-party network availability and labels absent external inputs explicitly;
- `docs/PUBLIC_RELEASE_INVENTORY_2026-09-21.md` defines the exact public surface. Internal
  agent prompts, private correspondence, and third-party payloads are excluded; all
  Aeye-authored reproducible results remain included;
- the corrected public `main` run passed every required GitHub Actions gate on Python 3.12
  and 3.14. The initial public run remains visible and failed before Aeye validation because
  arXiv returned HTTP 406 to both runners;
- a separate anonymous clone hydrated all 33 digest-pinned files and six commit-pinned Git
  trees, then passed the full retained-evidence validator. This does not make network
  hydration part of required CI;
- secret scanning, push protection, Dependabot alerts, private vulnerability reporting,
  and human-only commit attribution are enabled;
- public visibility is a distribution decision only. It does not upgrade a result,
  establish independent review, or authorize deployment, contact, or live-chain work.

Same-workstation machine-review disposition on 2026-09-21:

- a private source-bound review of commit `873efb5` reproduced the E-009 arithmetic and
  exposed that the frozen verifier copied issuer-authored claim metadata into its report;
- a versioned post-hoc appraisal overlay now derives statement IDs, assumptions, and the
  13-event coverage denominator from verifier-owned policy and rejects inflated coverage,
  removed assumptions, and unknown statement identifiers while preserving the frozen
  verifier bytes;
- the review also corrected direct `Q=G^T M` preprocessing to `Theta(mNn)` arithmetic and
  separated PAB-1 activation-origin controls from stronger output and demand controls;
- Artemis `2409.12055v2` is now retained as relevant commit-and-prove prior art. It narrows
  the possible novelty to Pearl's exact keyed-BLAKE3 translation/composition boundary;
  Artemis is not a drop-in adapter for that native commitment.

Load-bearing corrections:

1. The 2026-08-30 `hash_b = checkpoint tensor verbatim` conclusion is contradicted by
   runtime fusion/slicing/packing. Public reconstruction remains E-000, status `proposed`
   and blocked.
2. Pearl certificate-v3 INT and proposed certificate-v4 FP8 are different protocol
   lineages. Never combine their parser, arithmetic, wire, or assumption claims.
3. A demand event cannot sign a final identifier that hashes the same event. The schema now
   uses pre-authorization `intent_id`, then `job_id = H(intent_id,demand_root)`.
4. Receipt placement is not a native proof input. Pearl work and execution evidence couple
   only through byte-identical operand roots exposed by both native relations.
5. The block header's transaction Merkle root enters Pearl's `job_key`. This is job-domain
   binding, not request inclusion, authorization, chronology, demand, or proof that the
   committed activations derive from a transaction.

Current validator result at handoff:

```text
Aeye validation: 0 repository error(s); 18 fixture(s) exercised; 15 rejected as designed
47 unit tests: PASS
E-000 owner amendment audit: historical self-check only; never an acceptance gate
E-000 synthetic Pearl parity: structured header/config, job_key, matrix root, and Salted seed vector agree
```

The repository validator explicitly does not verify a Pearl certificate, signature, ZK
proof, hardware origin, production benchmark, or real demand event. E-009's separate
verifier checks only the frozen toy relation and carries its assumptions and non-claims.

## Next safe actions

1. Before any operator acceptance or candidate selection, freeze a finite T1-or-better registry, exact source-cited
   runtime recipe, two code-path-independent implementations, and the complete 30-control
   result matrix.
2. Give the separate reviewer ADR-0012, ADR-0013, manifest digest
   `011d3c232ce9638fc265730f01b13dd3e11d87c225d19ad17842a44d7a78ddc5`, and every
   Phase 1 through 5 artifact. Require a source-bound readback and new reviewer-owned
   freeze for those exact bytes. The reviewer may inspect registry metadata and digests,
   but must not read weight bytes, query mainnet, inspect a candidate, edit owner code, or
   convert its verdict into operator acceptance.
3. Only after those gates and the fresh readback, obtain an exact digest-citing
   operator acceptance record, apply the future-block rule, and attempt one E-000 opening. Let
   availability and coverage decide whether a separately frozen E-001 census is warranted;
   do not make the census a prerequisite for PAB-0.
4. Retain immutable certificate-v4 vectors, an authorized B200 path, and a second independent
   verifier before running E-008.
5. Obtain independent review of the PAB-1 relation and freeze its byte-level bridge and
   required negative fixtures before implementation. Then build only the disclosed-input
   PAB-0 fixture against Pearl's pinned parser/tree; do not call it zero knowledge or full
   execution.
6. Design the successor around authenticated and amortized `Q=G^T M` preprocessing, an
   explicit anti-grinding challenge model, batched request membership, realistic quantized
   attention/cache/decode semantics, and an adapter consuming actual Pearl roots. Do not
   simply scale R1's matrix dimensions. The proposed contract is E-010 and the construction
   note is `docs/AUTHENTICATED_PREPROCESSING_CAPSULE.md`; neither is accepted or running.
7. Measure provider, client/challenger, prover/setup, verifier, network, storage, privacy,
   and recovery separately against a named complete baseline before making an overhead
   statement. R1's preregistered timing combines challenge and response; the later local
   party split is exploratory and remains insufficient for a production claim.
8. Do not attribute views or endorsement to any external person, institution, or upstream
   project. External correspondence requires a separately reviewed, evidence-bound brief
   and the operator's explicit send decision.

The authoritative R1 account is `docs/E009_RESULT_2026-09-20.md`. The expert-review brief
is `docs/EXPERT_REVIEW_BRIEF_DRAFT.md`; it remains unsent and conveys no endorsement.
