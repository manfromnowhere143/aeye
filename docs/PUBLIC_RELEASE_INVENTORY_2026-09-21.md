# Public Release Inventory — 2026-09-21

Status: release gate; public visibility does not alter any scientific claim  
Scope: Aeye-authored source, specifications, schemas, fixtures, and retained experiment
outputs at the release commit

## Release decision

The public source repository contains the complete Aeye-authored research packet needed to
read, run, falsify, and cite the current result. It does not publish private correspondence,
agent prompts, credentials, model weights, live-chain data, or third-party evidence
payloads.

The prior private repository remains a private evidence archive. The public repository
starts from a reviewed source snapshot so earlier private Git objects containing
third-party payloads or internal workflow material cannot become public through history.
No scientific result is upgraded by that change of custody.

## Included

- the scientific charter, exact claims and non-claims, threat model, formal composition,
  protocol specification, architecture decisions, dated verdicts, and correction history;
- all Aeye-authored schemas, validators, known-good and known-bad fixtures, tests, and
  continuous-integration configuration;
- the complete E-009-R1 code, preregistration, transcript, result vector, measurements,
  post-hoc probes, and adversarial disposition;
- the blocked E-000 conformance instruments, manifest, reviewer-freeze record, checklist,
  and explicit pre-candidate gates;
- the source ledger with exact versions, public retrieval locators, SHA-256 digests, Git
  remotes, commits, scopes, limitations, and evidence labels;
- Apache-2.0 license, third-party boundary, citation metadata, contribution policy,
  security policy, and this release inventory.

## Excluded

| Material | Reason | Public substitute |
|---|---|---|
| Third-party PDFs, RFC text, and upstream patch bytes | Public access does not itself grant Aeye redistribution rights | Official HTTPS locator plus exact SHA-256 digest; fail-closed local hydration |
| Third-party repository checkouts | They are upstream work, not Aeye source | Exact anonymous HTTPS remote and 40-hex commit; fail-closed local hydration |
| One historical Pearl whitepaper with no retained public locator | Its identity and redistribution path are not reproducible | Digest-only metadata; excluded from public replay authority |
| Internal agent prompts | Operational scaffolding is not scientific evidence and contained machine-specific instructions | None; the resulting reviewed artifacts are included |
| Private correspondence and contact drafts | Not part of the scientific record | None |
| Model weights, private prompts, credentials, wallets, and live-chain state | Outside the authorized research boundary | None |

## Release checks

The release is blocked unless all of the following hold on the public candidate:

1. tracked-history secret scanning reports no leak;
2. author and committer metadata identify only Daniel Wahnich;
3. person-specific persuasion language and operational prompt files are absent;
4. every local Markdown link resolves and both README Mermaid diagrams parse;
5. evidence hydration retrieves only allowlisted public HTTPS or anonymous Git sources and
   rejects every digest, commit, remote, dirty-tree, path, or size mismatch;
6. repository validation reports zero errors, all 18 fixtures execute, and all 15 designed
   failures reject;
7. E-009 independent replay accepts only the retained toy relation and its mutation suite
   remains rejecting;
8. the source-only unit suite passes under the locked Python 3.12 and 3.14 environments;
   external-byte, checkout, and upstream-lock comparisons either verify the complete
   hydrated set or report an explicit skip when no external payload is present;
9. a fresh anonymous clone reproduces the documented commands without changing tracked
   bytes; and
10. unauthenticated GitHub and raw-content requests resolve the public repository and
    README.

## Scientific ceiling at release

The release contains one supported toy execution-interface result. It contains no native
Pearl opening, mainnet census, request-to-activation proof, ordinary-transformer proof,
GPU-fidelity result, authenticated preprocessing result, production benchmark, demand
proof, security certification, independent human review, or external endorsement.

The release is intended to make those limits inspectable, not to conceal them.

Required CI does not depend on third-party hosts. It validates the full Aeye source packet
and ledger contract without requiring external payloads. The separately replayed hydration
path remains fail-closed on URL, redirect, digest, commit, remote, cleanliness, size, and
path checks. This separation prevents an upstream CDN refusal from being reported as an
Aeye test failure.
