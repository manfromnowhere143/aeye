#!/usr/bin/env python3
"""Owner-side semantic audit of the E-000 reviewer amendments and binding repair.

This program checks that the retained manifest incorporates the twelve explicit reviewer
amendments, resolves the four defects found in the ADR-0012 delta readback, and keeps its
historical references content-addressed. It does not approve the experiment, replace
reviewer readback, create operator acceptance, or inspect a candidate.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST_PATH = HERE / "manifest.json"
FREEZE_PATH = HERE / "reviewer-freeze.json"
CHECKLIST_PATH = ROOT / "docs" / "E000_ACCEPTANCE_CHECKLIST_2026-09-21.md"
PAB_PATH = ROOT / "docs" / "PEARL_ACTIVATION_ORIGIN_BINDING_2026-09-21.md"


@dataclass(frozen=True)
class AmendmentCheck:
    amendment_id: str
    passed: bool
    detail: str


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = manifest["frozen_inputs"]
    identifiers = [item["input_id"] for item in values]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("manifest frozen_inputs contains duplicate input_id values")
    return {item["input_id"]: item for item in values}


def _contains_all(values: list[str], fragments: tuple[str, ...]) -> bool:
    joined = "\n".join(values)
    return all(fragment in joined for fragment in fragments)


def _control_contract(
    manifest: dict[str, Any], freeze: dict[str, Any]
) -> tuple[bool, str]:
    manifest_controls: dict[str, str] = {}
    for text in manifest["known_bad_controls"]:
        match = re.match(r"^(E000-KB-\d{2})\b", text)
        if match is None:
            return False, f"control lacks a stable leading ID: {text!r}"
        manifest_controls[match.group(1)] = text
    expected = {
        item["control_id"]: item["expected_diagnostic"]
        for item in freeze["known_bad_controls"]
    }
    if set(manifest_controls) != set(expected):
        missing = sorted(set(expected) - set(manifest_controls))
        extra = sorted(set(manifest_controls) - set(expected))
        return False, f"control ID mismatch; missing={missing}, extra={extra}"
    wrong = [
        control_id
        for control_id, diagnostic in expected.items()
        if diagnostic not in manifest_controls[control_id]
    ]
    if wrong:
        return False, f"controls omit frozen diagnostics: {wrong}"
    seed = manifest_controls["E000-KB-23"]
    if "noise-seed" not in seed or "does not test hash_b" not in seed:
        return False, "E000-KB-23 is not limited to the V3 noise-seed vector"
    return True, "all 30 IDs and diagnostics present; KB-23 is correctly scoped"


def audit(
    manifest: dict[str, Any],
    freeze: dict[str, Any],
    *,
    freeze_digest: str,
    checklist_digest: str,
    pab_text: str,
) -> list[AmendmentCheck]:
    inputs = _inputs(manifest)
    procedures = manifest["procedure"]
    acceptance = manifest["acceptance"]
    failure = manifest["failure"]
    blockers = manifest["blocking_conditions"]

    def fixed(input_id: str, predicate: Callable[[Any], bool]) -> bool:
        item = inputs.get(input_id, {})
        return item.get("status") == "fixed" and predicate(item.get("value"))

    def historical(input_id: str, predicate: Callable[[Any], bool]) -> bool:
        item = inputs.get(input_id, {})
        return item.get("status") == "historical" and predicate(item.get("value"))

    selection = inputs.get("candidate_selection_rule", {}).get("value")
    import_scope = inputs.get("predecessor_import_scope", {}).get("value")
    observation_policy = inputs.get("fresh_reviewer_observation_policy", {}).get("value")

    control_ok, control_detail = _control_contract(manifest, freeze)
    checks = [
        AmendmentCheck(
            "A1",
            fixed(
                "certificate_code_route",
                lambda value: isinstance(value, str)
                and "zk-pow/src/api" in value
                and "SeedDerivation::Salted" in value
                and "src/v1 excluded" in value,
            ),
            "V3 api/circuit/ffi route, Salted derivation, and V1 exclusion are fixed",
        ),
        AmendmentCheck(
            "A2",
            fixed(
                "mainnet_fork_heights_at_pin",
                lambda value: value
                == {
                    "moe": 71935,
                    "dense_only": 91630,
                    "rank_penalty": 96251,
                    "salted_seed_v3": 99000,
                },
            )
            and fixed("candidate_min_height", lambda value: value == 99000),
            "four pinned fork heights and minimum V3 height are fixed",
        ),
        AmendmentCheck(
            "A3",
            fixed("public_data_length", lambda value: value == 164)
            and fixed(
                "moe_scope",
                lambda value: isinstance(value, str) and "excluded" in value,
            )
            and fixed(
                "expert_parallel_degree",
                lambda value: isinstance(value, str)
                and "not applicable" in value
                and "dense-only" in value,
            ),
            "dense 164-byte scope is fixed and EP is not applicable",
        ),
        AmendmentCheck(
            "A4",
            fixed(
                "candidate_selection_rule",
                lambda value: isinstance(value, dict)
                and value.get("steps") == freeze["candidate_selection_rule"]["steps"],
            )
            and historical(
                "predecessor_reviewer_freeze",
                lambda value: value == "experiments/e-000/reviewer-freeze.json",
            )
            and historical(
                "predecessor_reviewer_freeze_sha256",
                lambda value: value == freeze_digest,
            ),
            "selection steps are embedded and the predecessor freeze remains historical",
        ),
        AmendmentCheck(
            "A5",
            fixed(
                "finality_rule",
                lambda value: isinstance(value, str)
                and ">=100 confirmations" in value
                and "two independent public sources" in value,
            ),
            "two-source 100-confirmation rule is fixed",
        ),
        AmendmentCheck(
            "A6",
            len(procedures) == 9
            and all(text.startswith(f"Phase {index} ") for index, text in enumerate(procedures, 1))
            and _contains_all(procedures, ("sealed", "reveal", "exactly one comparison")),
            "nine ordered phases include sealing, reveal, and exactly one comparison",
        ),
        AmendmentCheck("A7", control_ok, control_detail),
        AmendmentCheck(
            "A8",
            _contains_all(
                acceptance,
                (
                    "zk-pow/src/api",
                    "sealed",
                    "intermediate",
                    "Pearl oracle",
                    "non-self-mining",
                ),
            ),
            "acceptance contains route, sealing, intermediate, oracle, and attestation gates",
        ),
        AmendmentCheck(
            "A9",
            _contains_all(
                failure,
                (
                    "version-route mismatch",
                    "unresolved runtime transform parameter",
                    "registry retrieval before T_accept",
                    "BLOCKED",
                    "Phase 8",
                    "INVALID",
                ),
            ),
            "blocking and pre-reveal invalidation rules are explicit",
        ),
        AmendmentCheck(
            "A10",
            "zk-pow/src/v1/" not in pab_text
            and "SeedDerivation::Salted" in pab_text
            and _contains_all(blockers, ("At freeze creation", "independently checked")),
            "PAB V3 citations are corrected and the historical reviewer blocker is preserved",
        ),
        AmendmentCheck(
            "A11",
            fixed(
                "terminal_states",
                lambda value: isinstance(value, dict)
                and value.get("precedence") == freeze["terminal_states"]["precedence"],
            )
            and _contains_all(acceptance + failure, ("IN_COVERAGE_NO_MATCH", "exhaustive")),
            "all six terminal states retain frozen precedence and exhaustive no-match semantics",
        ),
        AmendmentCheck(
            "A12",
            _contains_all(
                acceptance,
                (
                    "E000-BLK-SECURITY-STOP",
                    "minimal local reproduction",
                    "SECURITY.md",
                ),
            ),
            "security-disclosure stop is explicit",
        ),
        AmendmentCheck(
            "D1",
            all(
                field not in inputs
                for field in (
                    "reviewer_freeze",
                    "reviewer_freeze_sha256",
                    "reviewer_checklist",
                    "reviewer_checklist_sha256",
                )
            )
            and fixed(
                "acceptance_binding_model",
                lambda value: isinstance(value, str)
                and "immutable manifest" in value
                and "contains no fresh-review or operator-record digest" in value
                and "fresh reviewer freeze cites this manifest digest" in value
                and "No accepted-manifest rewrite" in "\n".join(acceptance),
            ),
            "fresh review binds the immutable manifest externally; no self-referential fields exist",
        ),
        AmendmentCheck(
            "D2",
            isinstance(selection, dict)
            and selection.get("steps") == freeze["candidate_selection_rule"]["steps"]
            and len(selection.get("inputs", [])) == 2
            and "fresh reviewer-freeze digest" in selection["inputs"][0]
            and "exact immutable manifest digest" in selection["inputs"][0]
            and "this file's SHA-256" not in "\n".join(selection["inputs"]),
            "embedded S1-S8 use the fresh Phase 6 binding graph to define T_accept",
        ),
        AmendmentCheck(
            "D3",
            all(
                historical(input_id, lambda _value: True)
                for input_id in (
                    "predecessor_reviewer_freeze",
                    "predecessor_reviewer_freeze_sha256",
                    "predecessor_reviewer_checklist",
                    "predecessor_reviewer_checklist_sha256",
                )
            )
            and isinstance(import_scope, dict)
            and set(import_scope.get("imported", []))
            == {
                "reviewer-freeze.json#terminal_states",
                "reviewer-freeze.json#known_bad_controls control_id and expected_diagnostic values",
            }
            and _contains_all(
                import_scope.get("superseded", []),
                (
                    "ordered_phase_gates",
                    "acceptance_predicate",
                    "invalidation_predicate",
                    "prohibited_observations_before_freeze.reviewer",
                    "phase-numbered gates",
                ),
            ),
            "historical artifacts have an explicit section-level import and supersession boundary",
        ),
        AmendmentCheck(
            "D4",
            isinstance(observation_policy, dict)
            and _contains_all(
                observation_policy.get("permitted_for_phase_2_readback", []),
                (
                    "checkpoint repository identities",
                    "immutable revision identifiers",
                    "cryptographic digests",
                    "retrieval receipts",
                    "tensor inventory",
                ),
            )
            and _contains_all(
                observation_policy.get("prohibited_until_candidate_selection", []),
                (
                    "mainnet queries",
                    "candidate heights",
                    "hash_b",
                    "model-weight bytes",
                    "miner-captured",
                ),
            ),
            "fresh reviewer may inspect registry metadata and digests but not outcomes or weight bytes",
        ),
    ]

    # The checklist digest was not a numbered reviewer amendment, but it is a manifest
    # integrity invariant once the owner elected to bind the companion document.
    checklist_ok = historical(
        "predecessor_reviewer_checklist",
        lambda value: value == "docs/E000_ACCEPTANCE_CHECKLIST_2026-09-21.md",
    ) and historical(
        "predecessor_reviewer_checklist_sha256", lambda value: value == checklist_digest
    )
    checks.append(
        AmendmentCheck(
            "OWNER-CHECKLIST-DIGEST",
            checklist_ok,
            "predecessor checklist path and retained digest are preserved",
        )
    )
    return checks


def _protocol_correction_state(manifest: dict[str, Any]) -> tuple[bool, bool, str]:
    inputs = _inputs(manifest)
    correction = inputs.get("sequence_correction", {})
    procedures = manifest.get("procedure", [])
    expected_phase_fragments = (
        "raw-source retention",
        "checkpoint/registry freeze",
        "transformation-recipe freeze",
        "implementation/version freeze",
        "known-bad tests",
        "reviewer readback and operator acceptance",
        "candidate selection and sealed computation",
        "reveal",
        "exactly one comparison",
    )
    ordered = (
        len(procedures) == len(expected_phase_fragments)
        and all(
            procedure.startswith(f"Phase {index} ") and fragment in procedure
            for index, (procedure, fragment) in enumerate(
                zip(procedures, expected_phase_fragments, strict=True), 1
            )
        )
        and "T_accept" in procedures[5]
        and all("T_accept" not in procedure for procedure in procedures[:5])
    )
    correction_fixed = (
        manifest.get("status") == "blocked"
        and correction.get("status") == "fixed"
        and correction.get("value")
        == "docs/decisions/0012-pre-candidate-freezes-precede-operator-acceptance.md"
    )
    binding = inputs.get("binding_correction", {})
    binding_fixed = (
        binding.get("status") == "fixed"
        and binding.get("value")
        == "docs/decisions/0013-immutable-manifest-and-external-acceptance-bindings.md"
    )
    reviewer_fields = (
        "reviewer_freeze",
        "reviewer_freeze_sha256",
        "reviewer_checklist",
        "reviewer_checklist_sha256",
    )
    reviewer_pending = all(field not in inputs for field in reviewer_fields)
    detail = (
        "Phases 1-5 precede fresh reviewer readback and T_accept; fresh review and "
        "acceptance bind the immutable manifest externally"
    )
    return correction_fixed and binding_fixed and ordered, reviewer_pending, detail


# Retained for callers of the pre-ADR-0013 owner audit. The semantics are stricter now.
def _sequence_correction_state(manifest: dict[str, Any]) -> tuple[bool, bool, str]:
    return _protocol_correction_state(manifest)


def build_report() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    freeze_digest = sha256(FREEZE_PATH)
    checklist_digest = sha256(CHECKLIST_PATH)
    checks = audit(
        manifest,
        freeze,
        freeze_digest=freeze_digest,
        checklist_digest=checklist_digest,
        pab_text=PAB_PATH.read_text(encoding="utf-8"),
    )
    failed = [item.amendment_id for item in checks if not item.passed]
    protocol_corrected, reviewer_pending, sequence_detail = _protocol_correction_state(manifest)
    checks.append(
        AmendmentCheck(
            "OWNER-SEQUENCE-CORRECTION",
            protocol_corrected and reviewer_pending,
            sequence_detail,
        )
    )
    failed = [item.amendment_id for item in checks if not item.passed]
    return {
        "schema_version": "aeye.e000-owner-freeze-audit.v2",
        "status": (
            "historical_amendments_confirmed_binding_corrected_review_pending"
            if not failed and protocol_corrected and reviewer_pending
            else "owner_amendments_incomplete"
        ),
        "reviewer_verdict": freeze["reviewer_verdict"],
        "digests": {
            "predecessor_reviewer_freeze": freeze_digest,
            "predecessor_reviewer_checklist": checklist_digest,
            "amended_manifest": sha256(MANIFEST_PATH),
        },
        "checks": [asdict(item) for item in checks],
        "failed": failed,
        "candidate_input_read_by_this_program": False,
        "operator_acceptance_created": False,
        "protocol_correction_blocked": not protocol_corrected,
        "protocol_sequence_blocked": not protocol_corrected,
        "sequence_correction_implemented": protocol_corrected,
        "binding_correction_implemented": protocol_corrected,
        "fresh_reviewer_readback_blocked": reviewer_pending,
        "claim_ceiling": (
            "owner self-check of manifest incorporation only; not reviewer validation, "
            "operator acceptance, cryptographic review, or E-000 execution"
        ),
        "remaining_before_candidate": [
            "finite T1-or-better registry",
            "fully source-fixed runtime transformation recipe",
            "two frozen code-path-independent implementations",
            "all 30 controls in both implementations and oracle where applicable",
            "fresh reviewer freeze and source-bound readback of every preceding artifact",
            "exact digest-citing operator acceptance after every preceding artifact is frozen",
        ],
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return (
        0
        if not report["failed"]
        and report["sequence_correction_implemented"]
        and report["binding_correction_implemented"]
        and report["fresh_reviewer_readback_blocked"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
