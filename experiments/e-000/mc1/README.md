# MC1: real-byte matrix-commitment calibration

Status: `owner_result_awaiting_adversarial_readback`  
Candidate inspected: **no**  
Model-weight bytes in this repository: **no**

MC1 tests the pre-candidate byte path that E-000 would eventually use. It does not compare
against a certificate or `hash_b`.

The selection rule was fixed before any MC1 keyed root was computed: choose the
lexicographically first slab in each distinct `(family, n, k)` class of the reviewed
8B registry. This produced 15 classes: six `gate_up_proj`, three `o_proj`, and six
`qkv_proj`.

For those classes:

- the Python and Rust reconstruction paths processed 311,427,072 raw bytes each;
- all 15 reconstructed slab SHA-256 identities agreed;
- Python keyed BLAKE3, Rust keyed BLAKE3, and Pearl's pinned tree implementation agreed
  on all 15 roots under one frozen synthetic key;
- the signed-I8 byte mapping control passed; and
- one preregistered bit mutation changed both the raw-byte identity and keyed root.

The synthetic key is deterministic and public. It is not a Pearl `job_key`. All selected
slabs happened to be 1,024-byte aligned, so MC1 did not exercise nonzero final-chunk
padding on real bytes. The repository's synthetic conformance vectors cover that separate
case.

The result is retained in [mc1-agreement-v1.json](artifacts/mc1-agreement-v1.json), with
the two lane outputs, replay receipt, source, locks, content index, and a closed
[input-provenance projection](input-provenance-v0.json) beside it. The post-hoc harness
rejected nine transcript mutations. Those mutations test the comparator; they are not a
proof of cryptographic soundness.

The retained result bytes keep their original `aeye.private.*` schema identifiers because
renaming them would invalidate the replayed digests. The identifiers describe the packet's
origin, not its current visibility: the source-only packet listed by
`publication-manifest-v0.json` is public and contains no private paths, correspondence, or
model-weight payloads.

## Exact claim ceiling

For one deterministically selected real slab in each of 15 reviewed 8B family/shape
classes, two owner implementations reconstructed equal raw byte identities, and Python,
Rust, and Pearl's pinned implementation computed equal keyed BLAKE3 roots under one frozen
synthetic non-candidate key.

This does not establish source independence, live-runtime equivalence, a candidate
opening, `hash_b` equality, E-000, model identity, inference, `WORK`, `EXECUTION`,
`SEMANTICS`, `DEMAND`, security, performance, or independent validation.

## Replay boundary

The source-only repository preserves both implementations and every result byte, but it
does not redistribute the public checkpoint payload. A full replay therefore requires the
exact external tensor-extraction bundles and receipts named by digest in
[`publication-manifest-v0.json`](publication-manifest-v0.json), plus the pinned Pearl
oracle. `replay_mc1.py` takes every path explicitly and refuses to reuse its output
directory. No replay command queries a chain candidate.

Those external tensor bundles and exact extraction receipts are not in the public
repository. The public packet records their checkpoint revision, stream lengths, stream
digests, receipt digests, and registry digest, but a fresh clone alone cannot reproduce
the real-byte run. The retained clean replay is owner reproducibility, not public or
independent reproduction.

The comparator and post-hoc controls can be replayed from repository bytes alone through
the unit suite.
