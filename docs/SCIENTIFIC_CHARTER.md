# Aeye Scientific Charter

Status: `proposed`  
Date: 2026-08-30; updated 2026-09-20

## Research question

Can one inference event carry a replayable receipt whose `WORK`, `EXECUTION`, `SEMANTICS`,
and `DEMAND` coordinates are independently testable, composable, and honest about their
coverage and trust assumptions—without destroying the low incremental overhead that makes
Pearl interesting?

The target is not a universal “AI was verified” badge. The target is a protocol in which a
third party can identify exactly what was established, by which verifier, over what portion
of the execution, under which assumptions, and what remains unknown.

## Hypotheses and falsifiers

| ID | Hypothesis | Minimal falsifier |
|---|---|---|
| `H1` | A version-pinned Pearl certificate supplies meaningful `WORK` evidence for its committed operands under that lineage's stated assumption. | A cheaper strategy with materially greater win probability per unit cost, failure of the stated assumption in the selected parameter regime, or ambiguity about which parser/fork relation accepted the bytes. |
| `H2` | A public Pearl checkpoint slab can independently reproduce the weight-side commitment in at least one non-self-mined mainnet certificate. | Exhaustive, version-correct reconstruction from a preregistered block and checkpoint revision fails after cross-language serialization is resolved. |
| `H3` | An execution-event DAG can bind request, model, cache inputs, operations, and output without depending on one vLLM release. | A normal serving behavior—continuous batching, cache reuse, speculative decoding, retry, or parallel migration—admits two materially different executions with the same receipt. |
| `H4` | A low-cost audit profile can detect economically relevant execution substitution with quantified probability. | A preregistered attack concentrates corruption outside the sampled surface at acceptable cost and beats the stated soundness bound. |
| `H5` | Instruction-level arithmetic profiles can make covered GPU operations reproducible. | Retained real-GPU conformance vectors disagree under the fully pinned profile, or required production kernels cannot be decomposed into covered instructions. |
| `H6` | The commitment-only fast path can remain below 1% incremental serving overhead on a named workload. | A reproducible benchmark against the identical inference baseline exceeds the target after confidence intervals and receipt storage are included. |
| `H7` | Stronger verification can be selected per job without changing claim meanings. | Two backends accept different semantic relations while advertising the same claim/profile identifier. |

`H6` is a target, not a forecast. Nothing in the retained literature establishes sub-1%
overhead for a full, adversarially sound, native-float, end-to-end receipt.

## Required separations

- A hash commitment establishes binding under an assumption; it does not establish that
  committed bytes are true, correctly labelled, causally related, or economically useful.
- Correct execution of a mathematical relation does not establish that a particular
  physical device performed it or that a large amount of work was expended.
- Arithmetic conformance does not establish request/model/output lineage.
- A signed or paid request establishes an event under a policy; it does not establish human
  intent, non-collusion, social value, or intrinsic usefulness.
- A sampled result is never described as full coverage.
- A mainnet block witnesses one accepted winning PoUW instance, not every GEMM attempted
  during an inference and not every request sharing a serving batch.

## Evidence status

Research statements use only `observed`, `author_claim`, `derived`, `hypothesis`,
`proposed`, `blocked`, `falsified`, or `unknown`. Receipt verification uses a different,
machine-readable vocabulary defined in `CLAIMS_AND_NON_CLAIMS.md`; prose must not collapse
the two.

## Success criteria

Aeye advances beyond architecture only if:

1. source claims are pinned to exact artifacts and independently replayable;
2. every receipt coordinate has a formal relation, non-claim, assurance class, coverage,
   and known-bad fixture;
3. a cycle-free `intent_id` is authenticated before execution, and the final job plus
   trace/output subject is bound before any unpredictable audit challenge;
4. an adversarial harness demonstrates claim-local failure rather than one global bit;
5. measurement uses the identical serving stack with and without Aeye;
6. an independent reviewer can reproduce rejections without trusting the authoring agent.

## Stop or pivot conditions

- Pivot away from Pearl as the `WORK` adapter if its conjecture, deployment parameters, or
  certificate availability cannot support the stated lower-bound claim.
- Kill public model-census claims if checkpoint-to-registered-weight-byte reconstruction
  is not reproducible independently or registry revision history is unavailable.
- Kill any `EXECUTION=satisfied` mode that has only self-authored commitments and no proof,
  challenge, honest replica, or attestation assumption.
- Kill any `SEMANTICS=satisfied` mode that names only a GPU architecture rather than the
  effective instruction/kernel profile and conformance evidence.
- Kill any “economic demand” claim whose policy permits the same economic principal to pay
  itself without disclosure.

## Authorization boundary

This phase permits architecture, evidence retention, schemas, validators, known-bad
fixtures, and isolated/read-only experiments. It does not permit a Pearl consensus change,
live transaction, spending, private prompt or weight ingestion, production serving,
publication, or a public security claim.
