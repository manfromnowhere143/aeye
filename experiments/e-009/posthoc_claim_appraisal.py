#!/usr/bin/env python3
"""Reproduce and correct E-009-R1's post-hoc claim-metadata appraisal gap.

The frozen R1 verifier is content-addressed by the preregistration and must not be
edited. This overlay first requires that frozen relation replay to accept, then
checks receipt claim metadata against a verifier-owned v1 policy and constructs
its result vector from that policy rather than copying issuer-authored fields.

This is an observed post-hoc correction. It is not part of the preregistered run,
does not upgrade R1, and is not independent human or institutional review.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
ARTIFACT_DIR = EXPERIMENT_DIR / "artifacts"
ARTIFACT = ARTIFACT_DIR / "posthoc-claim-appraisal.json"
FROZEN_VERIFIER = EXPERIMENT_DIR / "independent_verify.py"
FROZEN_VERIFIER_DIGEST = (
    "sha256:9c4f6f4eed0c490b8261214a694db133ba33575f0fbe34c318cb6a853de7cf31"
)


@dataclass(frozen=True, order=True)
class ClaimFinding:
    code: str
    location: str
    message: str


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def load_frozen_verifier() -> ModuleType:
    observed = file_digest(FROZEN_VERIFIER)
    if observed != FROZEN_VERIFIER_DIGEST:
        raise RuntimeError(
            "frozen E-009 verifier digest mismatch: "
            f"expected {FROZEN_VERIFIER_DIGEST}, observed {observed}"
        )
    name = "aeye_e009_frozen_verifier_for_claim_appraisal"
    specification = importlib.util.spec_from_file_location(name, FROZEN_VERIFIER)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load frozen verifier at {FROZEN_VERIFIER}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def coverage_contract(event_count: int) -> dict[str, dict[str, Any]]:
    return {
        "WORK": {
            "known": False,
            "scope": "No native Pearl statement or certificate exists in E-009.",
            "unit": "unknown",
            "numerator": None,
            "denominator": None,
        },
        "EXECUTION": {
            "known": True,
            "scope": (
                "Frozen E-009 event universe: five sampled coded-linear and eight "
                "exact relations."
            ),
            "unit": "event",
            "numerator": event_count,
            "denominator": event_count,
        },
        "SEMANTICS": {
            "known": True,
            "scope": (
                "Exact declared finite-field/hard-attention profile; no hardware mapping."
            ),
            "unit": "event",
            "numerator": event_count,
            "denominator": event_count,
        },
        "DEMAND": {
            "known": False,
            "scope": (
                "No qualifying signed independent authorization or economic event is "
                "represented."
            ),
            "unit": "unknown",
            "numerator": None,
            "denominator": None,
        },
    }


def result_contract(event_count: int) -> dict[str, dict[str, Any]]:
    coverage = coverage_contract(event_count)
    return {
        "WORK": {
            "status": "unknown",
            "assurance": "commitment_only",
            "coverage": coverage["WORK"],
            "assumptions": [
                "synthetic.pearl.no-certificate",
                "sha256.collision-resistance",
            ],
            "evidence_refs": ["e009:r1:synthetic-pearl-operands"],
            "diagnostics": [
                "Synthetic clean-operand roots do not establish Pearl WORK."
            ],
        },
        "EXECUTION": {
            "status": "satisfied",
            "assurance": "sampled",
            "coverage": coverage["EXECUTION"],
            "assumptions": [
                "e009.coded-mvm-mds-soundness",
                "e009.fiat-shamir-random-oracle-and-bounded-grinding",
                "e009.verifier-code-correctness",
                "sha256.collision-resistance",
            ],
            "evidence_refs": ["e009:r1:coded-execution-audit"],
            "diagnostics": [
                "Limited to E-009-R1 and conditional on the reported coded-audit "
                "bound and Fiat-Shamir assumptions."
            ],
        },
        "SEMANTICS": {
            "status": "satisfied",
            "assurance": "hybrid",
            "coverage": coverage["SEMANTICS"],
            "assumptions": [
                "e009.finite-field-profile-fidelity",
                "e009.verifier-code-correctness",
                "sha256.collision-resistance",
            ],
            "evidence_refs": ["e009:r1:declared-semantics-conformance"],
            "diagnostics": [
                "Only the declared prime-field, centered-decode, hard-attention "
                "semantics are in scope; this is not GPU or ordinary transformer "
                "semantics."
            ],
        },
        "DEMAND": {
            "status": "unsupported",
            "assurance": "none",
            "coverage": coverage["DEMAND"],
            "assumptions": [],
            "evidence_refs": [],
            "diagnostics": [
                "The operator's experiment instruction is provenance, not DEMAND evidence."
            ],
        },
    }


def evidence_contract(event_count: int) -> dict[str, dict[str, Any]]:
    coverage = coverage_contract(event_count)
    return {
        "e009:r1:synthetic-pearl-operands": {
            "coordinates": ["WORK"],
            "evidence_type": "pearl_pouw",
            "statement_id": "aeye:synthetic-pearl-clean-operands:v0",
            "assurance": "commitment_only",
            "coverage": coverage["WORK"],
            "assumptions": [
                {
                    "assumption_id": "synthetic.pearl.no-certificate",
                    "kind": "availability",
                    "status": "unsupported",
                    "version": "E-009-R1",
                },
                {
                    "assumption_id": "sha256.collision-resistance",
                    "kind": "standard",
                    "status": "reviewed",
                    "version": "FIPS-180-4",
                },
            ],
            "producer_id": "e009:provider-generator",
            "scope": {
                "kind": "job",
                "membership_proof_ref": None,
                "scope_id": "E-009-R1",
            },
        },
        "e009:r1:coded-execution-audit": {
            "coordinates": ["EXECUTION"],
            "evidence_type": "sampled_audit",
            "statement_id": "aeye:e009-complete-causal-block:v0",
            "assurance": "sampled",
            "coverage": coverage["EXECUTION"],
            "assumptions": [
                {
                    "assumption_id": "e009.coded-mvm-mds-soundness",
                    "kind": "computational",
                    "status": "declared",
                    "version": "v0",
                },
                {
                    "assumption_id": (
                        "e009.fiat-shamir-random-oracle-and-bounded-grinding"
                    ),
                    "kind": "computational",
                    "status": "declared",
                    "version": "v0",
                },
                {
                    "assumption_id": "e009.verifier-code-correctness",
                    "kind": "trust",
                    "status": "declared",
                    "version": "independent-code-path-v0",
                },
                {
                    "assumption_id": "sha256.collision-resistance",
                    "kind": "standard",
                    "status": "reviewed",
                    "version": "FIPS-180-4",
                },
            ],
            "producer_id": "e009:provider-generator",
            "scope": {
                "kind": "job",
                "membership_proof_ref": None,
                "scope_id": "E-009-R1",
            },
        },
        "e009:r1:declared-semantics-conformance": {
            "coordinates": ["SEMANTICS"],
            "evidence_type": "arithmetic_conformance",
            "statement_id": "aeye:finite-field-hard-attention:v0",
            "assurance": "hybrid",
            "coverage": coverage["SEMANTICS"],
            "assumptions": [
                {
                    "assumption_id": "e009.finite-field-profile-fidelity",
                    "kind": "trust",
                    "status": "declared",
                    "version": "aeye:finite-field-hard-attention:v0",
                },
                {
                    "assumption_id": "e009.verifier-code-correctness",
                    "kind": "trust",
                    "status": "declared",
                    "version": "independent-code-path-v0",
                },
                {
                    "assumption_id": "sha256.collision-resistance",
                    "kind": "standard",
                    "status": "reviewed",
                    "version": "FIPS-180-4",
                },
            ],
            "producer_id": "e009:provider-generator",
            "scope": {
                "kind": "job",
                "membership_proof_ref": None,
                "scope_id": "E-009-R1",
            },
        },
    }


def cross_binding_contract() -> list[dict[str, Any]]:
    return [
        {
            "binding_id": "e009:r1:synthetic-pearl-to-q-linear",
            "binding_type": "pearl_work_to_execution",
            "diagnostics": [
                "Equality is real for the frozen clean q_linear operands; the "
                "WORK-side relation is synthetic and does not establish Pearl WORK."
            ],
            "equal_fields": ["operand_root_a", "operand_root_b"],
            "execution_evidence_ref": "e009:r1:coded-execution-audit",
            "work_evidence_ref": "e009:r1:synthetic-pearl-operands",
        }
    ]


def policy_specification(event_count: int) -> dict[str, Any]:
    return {
        "policy_id": "aeye:e009-r1-claim-appraisal",
        "version": "v1-post-hoc",
        "receipt_profile": "aeye.research-json.v0",
        "receipt_schema_version": "aeye.receipt.v0",
        "issuer": {"principal_id": "e009:provider-generator"},
        "results": result_contract(event_count),
        "evidence_metadata": evidence_contract(event_count),
        "cross_evidence_bindings": cross_binding_contract(),
        "conflicts": [],
    }


def compare_field(
    findings: list[ClaimFinding],
    observed: object,
    expected: object,
    code: str,
    location: str,
) -> None:
    if observed != expected:
        findings.append(
            ClaimFinding(code, location, "issuer-authored metadata differs from v1 policy")
        )


def claim_contract_findings(
    documents: dict[str, Any], event_count: int
) -> list[ClaimFinding]:
    receipt = documents.get("receipt", {})
    policy = policy_specification(event_count)
    findings: list[ClaimFinding] = []

    compare_field(
        findings,
        receipt.get("receipt_profile"),
        policy["receipt_profile"],
        "RECEIPT_PROFILE_MISMATCH",
        "receipt/receipt_profile",
    )
    compare_field(
        findings,
        receipt.get("schema_version"),
        policy["receipt_schema_version"],
        "RECEIPT_SCHEMA_VERSION_MISMATCH",
        "receipt/schema_version",
    )
    compare_field(
        findings,
        receipt.get("issuer"),
        policy["issuer"],
        "RECEIPT_ISSUER_MISMATCH",
        "receipt/issuer",
    )

    observed_results = receipt.get("claimed_results", {})
    expected_results = policy["results"]
    compare_field(
        findings,
        set(observed_results) if isinstance(observed_results, dict) else None,
        set(expected_results),
        "CLAIM_COORDINATE_SET_MISMATCH",
        "receipt/claimed_results",
    )
    field_codes = {
        "status": "CLAIM_STATUS_MISMATCH",
        "assurance": "CLAIM_ASSURANCE_MISMATCH",
        "coverage": "CLAIM_COVERAGE_MISMATCH",
        "assumptions": "CLAIM_ASSUMPTION_MISMATCH",
        "evidence_refs": "CLAIM_EVIDENCE_REF_MISMATCH",
        "diagnostics": "CLAIM_DIAGNOSTIC_MISMATCH",
    }
    for coordinate, expected in expected_results.items():
        observed = (
            observed_results.get(coordinate, {})
            if isinstance(observed_results, dict)
            else {}
        )
        for field, code in field_codes.items():
            compare_field(
                findings,
                observed.get(field),
                expected[field],
                code,
                f"receipt/claimed_results/{coordinate}/{field}",
            )

    evidence = receipt.get("evidence", [])
    evidence_items = [item for item in evidence if isinstance(item, dict)]
    observed_ids = [item.get("evidence_id") for item in evidence_items]
    expected_evidence = policy["evidence_metadata"]
    compare_field(
        findings,
        sorted(observed_ids) if all(isinstance(item, str) for item in observed_ids) else None,
        sorted(expected_evidence),
        "EVIDENCE_ID_SET_MISMATCH",
        "receipt/evidence",
    )
    by_id = {item.get("evidence_id"): item for item in evidence_items}
    evidence_field_codes = {
        "coordinates": "EVIDENCE_COORDINATE_MISMATCH",
        "evidence_type": "EVIDENCE_TYPE_MISMATCH",
        "statement_id": "EVIDENCE_STATEMENT_MISMATCH",
        "assurance": "EVIDENCE_ASSURANCE_MISMATCH",
        "coverage": "EVIDENCE_COVERAGE_MISMATCH",
        "assumptions": "EVIDENCE_ASSUMPTION_MISMATCH",
        "producer_id": "EVIDENCE_PRODUCER_MISMATCH",
        "scope": "EVIDENCE_SCOPE_MISMATCH",
    }
    for evidence_id, expected in expected_evidence.items():
        observed = by_id.get(evidence_id, {})
        for field, code in evidence_field_codes.items():
            compare_field(
                findings,
                observed.get(field),
                expected[field],
                code,
                f"receipt/evidence/{evidence_id}/{field}",
            )

    compare_field(
        findings,
        receipt.get("cross_evidence_bindings"),
        policy["cross_evidence_bindings"],
        "CROSS_EVIDENCE_POLICY_MISMATCH",
        "receipt/cross_evidence_bindings",
    )
    compare_field(
        findings,
        receipt.get("conflicts"),
        policy["conflicts"],
        "CONFLICT_SET_MISMATCH",
        "receipt/conflicts",
    )
    return sorted(set(findings))


def corrected_results(event_count: int) -> dict[str, dict[str, Any]]:
    results = result_contract(event_count)
    results["WORK"]["diagnostics"].append(
        "The v1 post-hoc appraiser derives this result from its policy; no native "
        "Pearl verifier was executed."
    )
    results["EXECUTION"]["diagnostics"].append(
        "The v1 post-hoc appraiser derives the 13/13 denominator from the frozen "
        "event universe and does not copy receipt coverage."
    )
    results["SEMANTICS"]["diagnostics"].append(
        "The v1 post-hoc appraiser allowlists the declared finite-field statement "
        "and assumptions."
    )
    results["DEMAND"]["diagnostics"].append(
        "No demand relation was presented to either the frozen verifier or the v1 "
        "post-hoc appraiser."
    )
    return results


def mutation_cases() -> list[tuple[str, Callable[[dict[str, Any]], None]]]:
    def unchanged(_: dict[str, Any]) -> None:
        return

    def inflated_coverage(bundle: dict[str, Any]) -> None:
        for coordinate in ("EXECUTION", "SEMANTICS"):
            bundle["receipt"]["claimed_results"][coordinate]["coverage"] = {
                "known": True,
                "scope": "forged full coverage",
                "unit": "event",
                "numerator": 1300,
                "denominator": 1300,
            }

    def removed_assumptions(bundle: dict[str, Any]) -> None:
        for coordinate in ("EXECUTION", "SEMANTICS"):
            bundle["receipt"]["claimed_results"][coordinate]["assumptions"] = []
        for evidence in bundle["receipt"]["evidence"]:
            if evidence["coordinates"] in (["EXECUTION"], ["SEMANTICS"]):
                evidence["assumptions"] = []

    def unknown_statement_id(bundle: dict[str, Any]) -> None:
        for evidence in bundle["receipt"]["evidence"]:
            if evidence["coordinates"] in (["EXECUTION"], ["SEMANTICS"]):
                evidence["statement_id"] = "review:unimplemented-relation:v999"

    def wrong_output_control(bundle: dict[str, Any]) -> None:
        bundle["output"]["token_id"] = 4
        bundle["output"]["token"] = "jade"

    return [
        ("unchanged", unchanged),
        ("inflated_coverage", inflated_coverage),
        ("removed_assumptions", removed_assumptions),
        ("unknown_statement_id", unknown_statement_id),
        ("wrong_output_control", wrong_output_control),
    ]


def finding_codes(findings: list[Any]) -> list[str]:
    return sorted({finding.code for finding in findings})


def run_probes(
    verifier: ModuleType,
    documents: dict[str, Any],
    event_count: int,
) -> list[dict[str, Any]]:
    outcomes: list[dict[str, Any]] = []
    for case_id, mutate in mutation_cases():
        candidate = copy.deepcopy(documents)
        mutate(candidate)
        frozen_findings = verifier.verify_documents(candidate)
        corrected_findings = [
            *frozen_findings,
            *claim_contract_findings(candidate, event_count),
        ]
        frozen_codes = finding_codes(frozen_findings)
        corrected_codes = finding_codes(corrected_findings)
        outcomes.append(
            {
                "case_id": case_id,
                "frozen_accepted": not frozen_codes,
                "frozen_finding_codes": frozen_codes,
                "corrected_accepted": not corrected_codes,
                "corrected_finding_codes": corrected_codes,
            }
        )
    return outcomes


def run_appraisal() -> dict[str, Any]:
    verifier = load_frozen_verifier()
    paths = verifier.bundle_paths(ARTIFACT_DIR)
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing frozen E-009 artifacts: {missing}")
    documents = verifier.load_documents(paths)
    event_count = len(verifier.EXPECTED_EVENTS)

    base_findings = [
        *verifier.preregistration_findings(paths),
        *verifier.run_index_findings(paths),
        *verifier.verify_documents(documents, paths=paths),
    ]
    strict_findings = claim_contract_findings(documents, event_count)
    original_codes = finding_codes([*base_findings, *strict_findings])
    if original_codes:
        raise RuntimeError(
            "retained E-009 bundle does not satisfy the composed appraisal: "
            + ", ".join(original_codes)
        )

    policy = policy_specification(event_count)
    probes = run_probes(verifier, documents, event_count)
    expected_probe_outcomes = {
        "unchanged": (True, True),
        "inflated_coverage": (True, False),
        "removed_assumptions": (True, False),
        "unknown_statement_id": (True, False),
        "wrong_output_control": (False, False),
    }
    observed_probe_outcomes = {
        item["case_id"]: (item["frozen_accepted"], item["corrected_accepted"])
        for item in probes
    }
    if observed_probe_outcomes != expected_probe_outcomes:
        raise RuntimeError(
            "claim-appraisal controls do not have the required acceptance pattern: "
            f"{observed_probe_outcomes}"
        )

    return {
        "schema_version": "aeye.e009-posthoc-claim-appraisal.v0",
        "status": "observed-post-hoc",
        "experiment_id": documents["input"]["experiment_id"],
        "run_id": documents["input"]["run_id"],
        "provenance": {
            "review_input": (
                "Operator-supplied separate machine review; treated as untrusted input."
            ),
            "reproduction": (
                "Independently reproduced against the content-pinned frozen verifier "
                "with deterministic in-memory mutations."
            ),
            "relationship_to_r1": (
                "Post-hoc appraisal correction only; frozen R1 source and result bytes "
                "remain unchanged."
            ),
        },
        "defect": {
            "finding_id": "E009-POSTHOC-CLAIM-METADATA-TRUST",
            "frozen_verifier_path": "experiments/e-009/independent_verify.py",
            "frozen_verifier_digest": FROZEN_VERIFIER_DIGEST,
            "observed_behavior": (
                "The frozen verifier accepted valid-schema changes that inflated "
                "EXECUTION/SEMANTICS coverage, removed their assumptions, or replaced "
                "their statement identifiers, then copied claimed_results into its report."
            ),
            "preservation_rule": (
                "Do not edit the preregistered verifier; compose it with this versioned, "
                "fail-closed claim policy."
            ),
        },
        "corrected_appraisal": {
            "underlying_relation_replay": "accepted",
            "policy_id": policy["policy_id"],
            "policy_version": policy["version"],
            "policy_digest": canonical_digest(policy),
            "result_source": (
                "Verifier-owned v1 policy plus the frozen verifier's 13-event universe; "
                "no claimed_result field is copied from the receipt."
            ),
            "results": corrected_results(event_count),
        },
        "probes": probes,
        "interpretation": {
            "supported": (
                "The v1 overlay rejects each reproduced claim-metadata mutation while "
                "accepting the unchanged bundle and preserving the frozen relation replay."
            ),
            "limitation": (
                "The correction is post-hoc and policy-specific; it does not retroactively "
                "join the R1 preregistration or create independent review."
            ),
            "non_claim": (
                "This is not Pearl verification, production security, hardware fidelity, "
                "complete malicious-provider security, or evidence of DEMAND."
            ),
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
    result = run_appraisal()
    rendered = json.dumps(
        result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
    ) + "\n"
    if arguments.write:
        ARTIFACT.write_text(rendered, encoding="utf-8")
    if arguments.json:
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
