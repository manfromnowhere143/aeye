# Aeye Pre-Implementation Gate

Status: `blocking`  
Architecture acceptance: not granted

No product runtime, Pearl fork/PIP, mainnet transaction, public dashboard, production vLLM
patch, or security/performance claim may begin until the operator explicitly accepts an
architecture baseline and every blocking item below has retained evidence.

## Gate A — research contract

- [x] Independent Aeye root and repository charter exist.
- [x] Four claim coordinates and non-claims are written.
- [x] Evidence receipt does not expose a global verification bit.
- [x] Threat model covers provider/miner/requester/registry/verifier/vendor collusion.
- [ ] Independent reviewer verdict retained after this packet is frozen.
- [ ] Operator acceptance recorded with packet digest.

## Gate B — source authority

- [x] Source ledger validated against all retained bytes and commits.
- [ ] Pearl FB-1…FB-7 independently audited with exact file/line evidence.
- [x] FB-4 is split into runtime-slab recomputability, network match rate, and registry
      coverage; the original byte-for-byte checkpoint claim is marked contradicted.
- [ ] PIP-3/live-certificate version-3 collision is clarified with Pearl before any version
      proposal.
- [x] TensorCommitments is excluded from execution authority pending resolution of its
      transition-relation gap.
- [x] INT certificate-v3 and proposed FP8 certificate-v4 claims have separate parsers,
      arithmetic profiles, experiment paths, and assumption identifiers.

## Gate C — contracts and fixtures

- [x] Receipt, verification-report, source-ledger, experiment, negative-fixture, E-009
      input, trace, and audit schemas validate; retained source and frozen experiment
      artifact digests/commits validate.
- [x] Valid fixture demonstrates honest `unknown/unsupported` states.
- [x] Every claim coordinate has at least one known-bad fixture.
- [x] Registry-poison fixture demonstrates propagation while documentation states it cannot
      detect a malicious source in the wild.
- [x] Missing values never become false/zero.
- [ ] Conflict-retention behavior has an independent known-bad fixture and reviewer check.
- [x] Native relation inputs are distinct from receipt placement; mismatched Pearl and
      execution operand roots are rejected.
- [x] Two-stage intent/job binding removes the demand-event hash cycle and has a known-bad
      fixture.
- [x] A frozen experiment implementation digest has a known-bad mismatch fixture.

## Gate D — experiment authorization

- [ ] E-000 manifest and public data sources accepted.
- [x] E-008 manifest exists for proposed FP8 certificate-v4 parity, but required vectors,
      hardware, second implementation, and operator acceptance remain blocked.
- [x] E-009-R1 was preregistered and completed: the separate code path accepted 13/13
      events and rejected all eight frozen mutations. Its scope remains synthetic and toy.
- [x] E-010 proposed manifest records the authenticated-preprocessing successor, but its
      proof lane, workload, privacy policy, challenge model, comparators, verifiers, and
      operator acceptance remain blocked.
- [x] Proposed experiments require no private weights/prompts, credentials, spending, or
      live transactions.
- [x] Mainnet work, if any, is public and read-only.
- [ ] Hardware experiments name authorized machines and retain exact binaries/toolchains.
- [x] E-009 toy benchmark methodology was fixed before its measurements.
- [ ] Any hardware, native-Pearl, or production-serving benchmark methodology is fixed
      before those measurements.

## Gate E — scientific acceptance

- [ ] FB-4a narrowed hypothesis independently resolved.
- [x] Commitment-only lineage is rejected as satisfied `EXECUTION` by the validator.
- [x] Arithmetic conformance and physical hardware provenance remain separate in the
      schemas, claims, and experiment acceptance rules.
- [x] Every satisfied result requires a machine-readable coverage denominator and retains
      evidence assumptions.
- [x] Negative and null experiment statuses use the same manifest/result contract as
      positive results.
- [x] The execution side of the Pearl work-to-execution interface is instantiated by a
      claim-bearing E-009 toy backend rather than only a structural fixture.
- [ ] The complete conjunction is instantiated with a native version-pinned Pearl
      certificate/root relation and realistic execution semantics.

Passing the validator is necessary but never sufficient for architecture acceptance.
