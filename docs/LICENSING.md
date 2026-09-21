# Licensing and Distribution Boundary

Status: current repository policy  
Date: 2026-09-21

This document records which repository material Daniel Wahnich can license as Aeye work
and which retained material remains governed by third-party terms. It is a repository
scope record, not legal advice or a representation about rights held by another party.

## Aeye-authored work

Aeye-authored source code, schemas, fixtures, experiment programs, and documentation are
released under the unmodified [Apache License 2.0](../LICENSE). Copyright 2026 Daniel
Wahnich. The [NOTICE](../NOTICE) file carries project attribution and the third-party
boundary.

Apache-2.0 permits research and commercial reuse under its terms, includes a patent grant
limited to covered contributor claims, requires preservation of applicable notices and
identification of modified files, and grants no general trademark permission. These are
the standard license's provisions, not additional Aeye restrictions. The official
[license text](https://www.apache.org/licenses/LICENSE-2.0.txt) and
[application guidance](https://www.apache.org/foundation/license-faq.html) are controlling
references for the Apache license itself.

Contributions intentionally submitted for inclusion use Apache-2.0 under section 5 unless
the contributor explicitly states otherwise or a separate written agreement applies.

## Third-party evidence is not relicensed

| Repository surface | Custody purpose | License treatment |
|---|---|---|
| `evidence/papers/` | Ignored local copies hydrated from ledger-pinned public locators | Not distributed in Git; each work retains its publisher or author terms |
| `evidence/standards/` | Ignored local RFC text hydrated from RFC Editor locators | Not distributed in Git; IETF Trust notices and terms remain controlling |
| `evidence/changes/` | Ignored local upstream patch hydrated from its public locator | Not distributed in Git; upstream copyright and component licenses remain controlling |
| `evidence/external/` | Ignored, reproducible checkouts at source-ledger commits | Not part of the Aeye Git release; each checkout retains its upstream license |
| Installed Python packages and tools | Validation dependencies | Obtained separately under their upstream terms |

The source ledger records identity, version, retrieval, scope, limitation, and digest or
commit. `scripts/hydrate_external_evidence.py` retrieves public sources into ignored local
paths and rejects any byte or Git-identity mismatch. It does not grant redistribution
rights. Public availability is not itself a license.

One locally retained source archive uses evaluation-only terms and is intentionally absent
from the Aeye Git tree. Its presence in a local ignored evidence directory grants no right
to redistribute it.

## Public-source distribution decision

The public repository contains Aeye-authored work and metadata required to reproduce its
source custody. It does not contain third-party paper, RFC, patch, or external-repository
payloads. Publicly retrievable inputs are represented by an HTTPS locator and SHA-256
digest or by an exact Git remote and commit. One historical Pearl whitepaper whose public
locator was not retained is represented only by its digest and is not part of the public
replay authority.

This boundary permits publication of Aeye's work without asserting redistribution rights
over third-party material. A reviewer who runs hydration obtains those sources directly
from their publishers or upstream repositories and remains responsible for the applicable
terms. The accepted inventory is recorded in
[`PUBLIC_RELEASE_INVENTORY_2026-09-21.md`](PUBLIC_RELEASE_INVENTORY_2026-09-21.md).

## Scientific and trademark boundary

The Apache license permits use of covered work; it does not certify the protocol, establish
security or performance, confer scientific authority, or imply Pearl or any cited author's
endorsement. **Aeye** remains a working research-system name. Trademark availability and
ownership have not been established by this licensing decision.
