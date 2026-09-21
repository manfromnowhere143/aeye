# Security Policy

## Supported status

Aeye is a pre-deployment research system. No version is supported for production inference,
asset custody, public-chain operation, secret handling, or safety-critical use. Passing the
repository validator establishes only the bounded checks it names.

## Reporting a vulnerability

Use GitHub's private vulnerability-reporting form for implementation defects. Relevant
defects include acceptance of an invalid receipt, bypass of evidence binding, unexpected
data exposure, or misstatement of a retained result. Do not open a public issue containing
live credentials, private model data, personal data, or exploit material against an
external network.

If the issue concerns Pearl or another upstream project rather than Aeye, follow that
project's security policy. Do not publish a suspected upstream vulnerability through an
Aeye issue or research document before the affected maintainer has had a reasonable chance
to assess it.

## Scientific corrections

A false claim, invalid comparator, missing denominator, or irreproducible result may be a
scientific-integrity defect rather than a software vulnerability. Report it with the exact
artifact, commit, expected relation, observed contradiction, and smallest replay. Valid
corrections remain visible; history is not rewritten to make a prior result look correct.

## Pinned upstream lock advisories

The E-000 Pearl oracle intentionally retains dependency identities from the pinned Pearl
source. GitHub currently identifies two transitive entries in that lock:

- `GHSA-7gcf-g7xr-8hxj` affects `serde_with::KeyValueMap` serialization. Neither the
  oracle nor the pinned source path it invokes references `KeyValueMap`; the oracle accepts
  only local byte files and fixed command-line fields.
- `GHSA-g98v-hv3f-hcfr` concerns `atty` on Windows with a potentially unaligned pointer,
  principally when a custom global allocator is used. The oracle defines no custom
  allocator and does not invoke the `structopt` or `env_logger` paths that introduce
  `atty` transitively.

The repository records both alerts as unused by this narrow offline executable path. That
is not a claim that the upstream dependency graph is generally safe. Expanding the oracle,
changing supported hosts, enabling the affected APIs, or using the lock outside this
conformance role invalidates the disposition and requires a new review. Updating the lock
without a new Pearl pin would also invalidate the current dependency-identity comparison.
