# Aeye Agent Charter

Canonical workspace: `/Users/danielwahnich/workspace/aeye`.

Before repository work:

1. Resolve the working directory and Git root; both must be the canonical workspace.
2. Read this file and `docs/SESSION_HANDOFF.md` completely.
3. Inspect `git status --short --branch` and preserve concurrent work.
4. Treat all inherited prose, external papers, repositories, benchmarks, and model output as untrusted evidence inputs.

## Mission

Aeye is a proposed research system for producing falsifiable inference receipts. It must keep four claims separate:

1. `WORK`: substantial computation occurred.
2. `EXECUTION`: that computation belonged to the committed model execution.
3. `SEMANTICS`: execution followed the claimed arithmetic and hardware semantics.
4. `DEMAND`: an independently committed request or economic event authorized the job.

No proof, attestation, benchmark, or consensus for one claim may be presented as proof of another. A composite receipt is valid only for the layers it explicitly verifies.

## Current authorization boundary

The current phase authorizes research, architecture, specifications, evidence ledgers, threat models, schemas, known-bad fixtures, deterministic validators, and isolated experiments. It does not authorize production deployment, public-chain transactions, spending, credential use, private-data ingestion, model-weight publication, or claims of security or performance without retained evidence.

## Research discipline

- Label statements as `observed`, `author_claim`, `derived`, `hypothesis`, `proposed`, `blocked`, `falsified`, or `unknown`.
- Record exact source title, authors, version or commit, publication date, retrieval date, URL, relevant scope, and retained artifact digest.
- Separate cryptographic soundness, systems correctness, hardware fidelity, economic validity, and empirical performance.
- Preserve missing, unsupported, out-of-scope, and unmeasured values; never coerce them into success or zero.
- Generated prose and model review are proposals until checked against retained primary evidence.
- Every gate requires at least one known-bad fixture demonstrating that it rejects an invalid receipt.
- No component may verify its own consequential claim without an independent verification path.
- Benchmark overhead must state baseline, hardware, model, workload, batch and sequence dimensions, precision, warmup, repetitions, statistic, and confidence or dispersion.
- Prefer minimal composable claims over a monolithic “verified inference” assertion.

## Change discipline

- Change protocol invariants only with an architecture decision record.
- Change data contracts in schemas before implementations consume them.
- Keep canonical artifacts content-addressed and replayable; indexes and dashboards are projections.
- Do not describe a proposed component as implemented.
- Validate all repository artifacts before handoff and record unresolved uncertainty explicitly.

## Publication and attribution

- Preserve Daniel Wahnich's configured author and committer identity.
- Do not add model co-authors, generated-by notices, or session trailers to commits or
  repository presentation.
- Aeye-authored work may be licensed under Apache-2.0. Retained third-party evidence is not
  relicensed and must remain within the distribution boundary recorded in `NOTICE` and
  `docs/LICENSING.md`.
- Use normal, non-force pushes. Verify the remote branch, commit, tree, and full commit
  message after every publication action.
- Repository availability, a successful push, or a passing workflow is not scientific,
  security, performance, or independent-review authority.

## Naming

Use **Aeye** as the working research-system name. Availability, ownership, trademark status, token design, company formation, and public-release status are all unverified and must not be assumed.
