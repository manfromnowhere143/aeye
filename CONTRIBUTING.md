# Contributing to Aeye

Aeye accepts contributions that sharpen a falsifiable claim, expose a counterexample,
improve replayability, or reduce a stated cost without changing the relation being claimed.
The project is pre-deployment research; a contribution is not an authorization to deploy,
transact, ingest private data, or contact an external party.

## Evidence standard

- Label statements as `observed`, `author_claim`, `derived`, `hypothesis`, `proposed`,
  `blocked`, `falsified`, or `unknown`.
- State the exact relation, public inputs, coverage denominator, assurance, trust model,
  comparator, environment, and unresolved assumptions.
- Preserve missing, invalid, null, unsupported, and out-of-scope values. Never turn them
  into zero or success.
- Add at least one known-bad control for every consequential gate.
- Do not let a producer verify its own consequential claim without a distinct replay path.
- Pin external sources by version or commit and retain their scope, limitations, and
  applicable license boundary.

## Change order

1. Amend schemas before changing a consumed data contract.
2. Record protocol-invariant changes in an architecture decision.
3. Add or update known-good and known-bad fixtures.
4. Run the repository validator, E-009 replay when affected, and the full test suite.
5. Explain any remaining uncertainty in the same change.

```bash
python3 scripts/hydrate_external_evidence.py
python3 scripts/validate.py
python3 experiments/e-009/independent_verify.py
python3 -m unittest discover -s tests -v
```

## Authorship and licensing

Submit only material you have the right to contribute. Contributions intentionally
submitted for inclusion are licensed under Apache-2.0 pursuant to section 5 unless clearly
marked otherwise or governed by a separate written agreement. Preserve all applicable
third-party notices; Aeye's license does not relicense retained evidence.

Commits must retain the configured human author and committer identity. Do not add model
co-authors, generated-by notices, or session trailers. Real tool provenance remains in
scientific records when it is necessary to interpret evidence.
