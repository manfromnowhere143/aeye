#!/usr/bin/env python3
"""Replay the post-hoc self-consistent forged-transcript probe for E-009-R1.

The probe changes one q_linear output, regenerates every downstream event and
commitment, then falsifies the retained coded-check transcript. It asks which
independent-verifier checks still reject. It is not part of the frozen R1
preregistration and cannot upgrade or replace any preregistered result.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
ARTIFACT = EXPERIMENT_DIR / "artifacts" / "posthoc-adversarial-probe.json"


def load_module(name: str, path: Path) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load module at {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def build_bundle(provider: ModuleType, data: dict[str, Any]) -> dict[str, Any]:
    roots = provider.roots_from_input(data)
    trace, output = provider.build_trace(data, roots)
    subject = provider.complete_subject(data, roots, trace, output)
    preprocessing = provider.build_preprocessing(data)
    audit = provider.build_audit(data, subject, trace, preprocessing)
    work = provider.build_synthetic_work(data, subject, trace)
    receipt = provider.build_receipt(
        data,
        subject,
        work,
        provider.canonical_digest(work),
        provider.canonical_digest(audit),
        provider.canonical_digest(trace),
    )
    return {
        "input": data,
        "trace": trace,
        "output": output,
        "synthetic_pearl_work": work,
        "audit": audit,
        "receipt": receipt,
    }


def multiplication_counts(provider: ModuleType, data: dict[str, Any]) -> dict[str, Any]:
    field = data["arithmetic_profile"]["field_prime"]
    matrices = [
        provider.encode_matrix(matrix, field)
        for matrix in data["model"]["matrices"].values()
    ]
    preprocessing = sum(
        (2 * len(matrix)) * len(matrix[0]) * len(matrix) for matrix in matrices
    )
    exact_mvm = sum(len(matrix) * len(matrix[0]) for matrix in matrices)
    return {
        "preprocessing_authentication": preprocessing,
        "exact_matrix_vector_replay": exact_mvm,
        "ratio_numerator": preprocessing,
        "ratio_denominator": exact_mvm,
        "ratio_decimal": round(preprocessing / exact_mvm, 6),
        "scope": "field multiplications only; excludes additions, hashing, parsing, and all other verifier work",
    }


def run_probe() -> dict[str, Any]:
    provider = load_module("aeye_e009_probe_provider", EXPERIMENT_DIR / "generate.py")
    verifier = load_module(
        "aeye_e009_probe_verifier", EXPERIMENT_DIR / "independent_verify.py"
    )
    data = json.loads((EXPERIMENT_DIR / "input.json").read_text(encoding="utf-8"))
    field = data["arithmetic_profile"]["field_prime"]

    honest_compute = provider.compute_values
    honest_values = honest_compute(data)

    def forged_compute(candidate: dict[str, Any]) -> dict[str, Any]:
        values = honest_compute(candidate)
        q = list(values["q"])
        q[0] = (q[0] + 1) % field
        scores = [provider.dot(q, key, field) for key in values["cache_keys"]]
        selected_index = provider.centered_argmax(scores, field)
        selected_value = values["cache_values"][selected_index]
        residual = provider.vector_add(selected_value, values["x"], field)
        mlp = provider.matrix_vector(values["matrices"]["W1"], residual, field)
        relu = [
            provider.encode_scalar(max(0, provider.signed_decode(value, field)), field)
            for value in mlp
        ]
        logits = provider.matrix_vector(values["matrices"]["W2"], relu, field)
        token_id = provider.centered_argmax(logits, field)
        values.update(
            q=q,
            scores=scores,
            selected_index=selected_index,
            selected_value=selected_value,
            residual=residual,
            mlp=mlp,
            relu=relu,
            logits=logits,
            token_id=token_id,
            token=candidate["model"]["vocabulary"][token_id],
        )
        return values

    provider.compute_values = forged_compute
    try:
        forged = build_bundle(provider, data)
    finally:
        provider.compute_values = honest_compute

    naturally_rejected = [
        (relation["event_id"], check["repetition"])
        for relation in forged["audit"]["relations"]
        for check in relation["checks"]
        if not check["accepted"]
    ]

    # Model a dishonest issuer who changes the retained verdict fields as well as
    # regenerating all roots and downstream events. The independent verifier must
    # recompute rather than trust these values.
    for relation in forged["audit"]["relations"]:
        for check in relation["checks"]:
            check["accepted"] = True
            check["right"] = check["left"]
        relation["accepted"] = True
    forged["audit"]["all_relations_accept"] = True

    forged_codes = sorted(
        {finding.code for finding in verifier.verify_documents(forged)}
    )
    honest = build_bundle(provider, data)
    honest_codes = sorted(
        {finding.code for finding in verifier.verify_documents(honest)}
    )
    coded_rejection_codes = {
        "AUDIT_ACCEPTANCE_MISMATCH",
        "CODED_CHECK_TRANSCRIPT_MISMATCH",
        "CODED_LINEAR_REJECT",
        "RELATION_ACCEPTANCE_MISMATCH",
    }

    return {
        "schema_version": "aeye.e009-posthoc-adversarial-probe.v0",
        "status": "observed-post-hoc",
        "experiment_id": data["experiment_id"],
        "run_id": data["run_id"],
        "provenance": {
            "origin": "separate same-workstation machine-review scratch probe",
            "appraisal": "untrusted machine review independently replayed by the Aeye implementation owner",
            "relationship_to_r1": "not preregistered; does not change the frozen R1 result",
        },
        "attack": {
            "target_event": "q_linear",
            "changed_coordinate": 0,
            "honest_value": honest_values["q"][0],
            "forged_value": forged["trace"]["events"][1]["outputs"]["y"][0],
            "downstream_regenerated": True,
            "roots_and_challenges_regenerated": True,
            "retained_acceptance_fields_falsified": True,
        },
        "observation": {
            "naturally_rejected_coded_checks": len(naturally_rejected),
            "total_coded_checks": sum(
                len(relation["checks"])
                for relation in forged["audit"]["relations"]
            ),
            "finding_codes": forged_codes,
            "only_coded_relation_findings": set(forged_codes) == coded_rejection_codes,
            "honest_regeneration_finding_codes": honest_codes,
            "honest_output_token": honest["output"]["token"],
            "forged_output_token": forged["output"]["token"],
        },
        "field_multiplication_counts": multiplication_counts(provider, data),
        "interpretation": {
            "supported": "The independent verifier rejects the self-consistent forged transcript by recomputing the coded q_linear relation rather than trusting issuer acceptance fields.",
            "limitation": "Binding, ordering, and exact downstream-event checks add no separate rejection after the dishonest issuer regenerates a causally self-consistent downstream trace.",
            "non_claim": "This probe is not an exhaustive malicious-provider proof, independent peer review, a native Pearl test, or a production security result.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit compact machine output")
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace the retained post-hoc artifact with the reproduced result",
    )
    arguments = parser.parse_args()
    result = run_probe()
    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if arguments.write:
        ARTIFACT.write_text(rendered, encoding="utf-8")
    if arguments.json:
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
