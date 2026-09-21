#!/usr/bin/env python3
"""Deterministic validation for the Aeye research packet.

This validator checks structure and architectural invariants. It does not verify a
Pearl proof, a signature, a ZK proof, hardware execution, or economic demand.
Passing is necessary for the research gate and deliberately insufficient for
scientific or security acceptance.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover - fail-closed environment guard
    raise SystemExit(
        "missing dependency: install jsonschema>=4.23,<5 before validation"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
FIXTURE_MANIFEST = ROOT / "fixtures" / "manifest.json"
LEDGER = ROOT / "evidence" / "ledger" / "sources.json"
E009_DIR = ROOT / "experiments" / "e-009"
E009_ARTIFACT_DIR = E009_DIR / "artifacts"

COORDINATES = ("WORK", "EXECUTION", "SEMANTICS", "DEMAND")
DIGEST_RE = re.compile(r"^sha256:([0-9a-f]{64})$")
FORBIDDEN_GLOBAL_KEYS = {
    "overall_verified",
    "overall_status",
    "global_verdict",
    "verified_inference",
}
LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def finding(code: str, path: Path | str, message: str) -> Finding:
    try:
        rendered = str(Path(path).resolve().relative_to(ROOT))
    except (ValueError, TypeError):
        rendered = str(path)
    return Finding(code, rendered, message)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def framed_digest(domain: str, parts: Iterable[bytes]) -> str:
    """Hash a domain and unambiguous sequence of byte strings."""
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(b"\x00")
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return f"sha256:{digest.hexdigest()}"


def digest_bytes(value: str) -> bytes:
    match = DIGEST_RE.fullmatch(value)
    if not match:
        raise ValueError(f"not an Aeye SHA-256 digest: {value!r}")
    return bytes.fromhex(match.group(1))


def expected_intent_id(subject: dict[str, Any]) -> str:
    return framed_digest(
        "aeye/intent/v0",
        (
            digest_bytes(subject["request_root"]),
            digest_bytes(subject["model_root"]),
            digest_bytes(subject["execution_root"]),
            bytes.fromhex(subject["client_nonce"]),
            subject["freshness_domain"].encode("utf-8"),
        ),
    )


def expected_job_id(subject: dict[str, Any]) -> str:
    return framed_digest(
        "aeye/job/v0",
        (
            digest_bytes(subject["intent_id"]),
            digest_bytes(subject["demand_root"]),
        ),
    )


def expected_subject_root(subject: dict[str, Any]) -> str:
    return framed_digest(
        "aeye/execution-subject/v0",
        (
            digest_bytes(subject["job_id"]),
            digest_bytes(subject["trace_root"]),
            digest_bytes(subject["output_root"]),
        ),
    )


def schema_findings(instance: Any, schema_path: Path, instance_path: Path) -> list[Finding]:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    results: list[Finding] = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path)):
        pointer = "/".join(str(part) for part in error.absolute_path)
        suffix = f"#{pointer}" if pointer else ""
        results.append(
            finding("SCHEMA_VIOLATION", instance_path, f"{suffix}: {error.message}")
        )
    return results


def walk_keys(value: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}/{key}"
            yield key, child_path
            yield from walk_keys(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_keys(child, f"{prefix}/{index}")


def forbidden_global_findings(data: Any, path: Path) -> list[Finding]:
    return [
        finding(
            "FORBIDDEN_GLOBAL_VERDICT",
            path,
            f"{pointer}: {key!r} collapses the four-coordinate result vector",
        )
        for key, pointer in walk_keys(data)
        if key.casefold() in FORBIDDEN_GLOBAL_KEYS
    ]


def coverage_findings(coverage: Any, path: Path, pointer: str) -> list[Finding]:
    if not isinstance(coverage, dict):
        return []
    results: list[Finding] = []
    known = coverage.get("known")
    numerator = coverage.get("numerator")
    denominator = coverage.get("denominator")
    if known is False and (numerator is not None or denominator is not None):
        results.append(
            finding(
                "UNKNOWN_COERCED_TO_ZERO",
                path,
                f"{pointer}: unknown coverage must preserve null numerator and denominator",
            )
        )
    if (
        known is True
        and isinstance(numerator, int)
        and isinstance(denominator, int)
        and numerator > denominator
    ):
        results.append(
            finding(
                "COVERAGE_EXCEEDS_SCOPE",
                path,
                f"{pointer}: numerator {numerator} exceeds denominator {denominator}",
            )
        )
    return results


def result_vector_findings(
    results: Any,
    evidence_by_id: dict[str, dict[str, Any]],
    path: Path,
    prefix: str,
) -> list[Finding]:
    if not isinstance(results, dict):
        return []
    output: list[Finding] = []
    for coordinate in COORDINATES:
        result = results.get(coordinate)
        if not isinstance(result, dict):
            continue
        pointer = f"{prefix}/{coordinate}"
        output.extend(coverage_findings(result.get("coverage"), path, f"{pointer}/coverage"))
        refs = result.get("evidence_refs")
        if not isinstance(refs, list):
            continue
        resolved: list[dict[str, Any]] = []
        for evidence_id in refs:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                output.append(
                    finding(
                        "EVIDENCE_REF_MISSING",
                        path,
                        f"{pointer}: evidence reference {evidence_id!r} does not resolve",
                    )
                )
                continue
            resolved.append(evidence)
            if coordinate not in evidence.get("coordinates", []):
                output.append(
                    finding(
                        "EVIDENCE_COORDINATE_LAUNDERING",
                        path,
                        f"{pointer}: {evidence_id!r} does not make a {coordinate} statement",
                    )
                )

        declared_assumptions = set(result.get("assumptions", []))
        required_assumptions = {
            assumption.get("assumption_id")
            for evidence in resolved
            for assumption in evidence.get("assumptions", [])
            if isinstance(assumption, dict) and assumption.get("assumption_id")
        }
        omitted = sorted(required_assumptions - declared_assumptions)
        if omitted:
            output.append(
                finding(
                    "ASSUMPTION_OMISSION",
                    path,
                    f"{pointer}: result omits evidence assumptions {omitted}",
                )
            )

        if result.get("status") != "satisfied":
            continue

        evidence_types = {item.get("evidence_type") for item in resolved}
        assurance = result.get("assurance")
        coverage = result.get("coverage", {})
        if coordinate == "WORK" and "pearl_pouw" not in evidence_types:
            output.append(
                finding("WORK_EVIDENCE_TYPE", path, f"{pointer}: satisfied WORK lacks a work relation")
            )
        elif coordinate == "EXECUTION":
            strong = {"execution_proof", "sampled_audit", "optimistic_dispute", "attestation"}
            if assurance in {"commitment_only", "none"} or not evidence_types.intersection(strong):
                output.append(
                    finding(
                        "EXECUTION_COMMITMENT_ONLY",
                        path,
                        f"{pointer}: commitments or registries cannot satisfy EXECUTION",
                    )
                )
        elif coordinate == "SEMANTICS":
            strong = {"arithmetic_conformance", "execution_proof", "attestation"}
            if not evidence_types.intersection(strong):
                output.append(
                    finding(
                        "SEMANTICS_EVIDENCE_TYPE",
                        path,
                        f"{pointer}: satisfied SEMANTICS lacks a semantics relation",
                    )
                )
        elif coordinate == "DEMAND" and not evidence_types.intersection({"authorization", "payment"}):
            output.append(
                finding(
                    "DEMAND_EVIDENCE_TYPE",
                    path,
                    f"{pointer}: satisfied DEMAND lacks an independent authorization or payment event",
                )
            )
        if isinstance(coverage, dict) and coverage.get("known") is not True:
            output.append(
                finding(
                    "SATISFIED_WITH_UNKNOWN_COVERAGE",
                    path,
                    f"{pointer}: satisfied claims require an explicit coverage denominator",
                )
            )
    return output


def result_native_binding_findings(
    results: Any,
    evidence_by_id: dict[str, dict[str, Any]],
    subject: Any,
    path: Path,
    prefix: str,
) -> list[Finding]:
    """Require satisfied claims to expose the native public inputs they authenticate."""
    if not isinstance(results, dict) or not isinstance(subject, dict):
        return []
    output: list[Finding] = []
    intent_id = subject.get("intent_id")
    job_id = subject.get("job_id")
    subject_root = subject.get("subject_root")

    def resolved(coordinate: str) -> list[dict[str, Any]]:
        result = results.get(coordinate)
        if not isinstance(result, dict) or result.get("status") != "satisfied":
            return []
        return [
            evidence_by_id[reference]
            for reference in result.get("evidence_refs", [])
            if reference in evidence_by_id
        ]

    execution = resolved("EXECUTION")
    if execution and not any(
        item.get("evidence_type")
        in {"execution_proof", "sampled_audit", "optimistic_dispute", "attestation"}
        and item.get("native_public_inputs", {}).get("aeye_job_id") == job_id
        and item.get("native_public_inputs", {}).get("aeye_subject_root") == subject_root
        for item in execution
    ):
        output.append(
            finding(
                "EXECUTION_SUBJECT_BINDING_MISSING",
                path,
                f"{prefix}/EXECUTION: no accepted execution relation natively binds both job_id and subject_root",
            )
        )

    semantics = resolved("SEMANTICS")
    if semantics and not any(
        item.get("evidence_type")
        in {"arithmetic_conformance", "execution_proof", "attestation"}
        and item.get("native_public_inputs", {}).get("aeye_subject_root") == subject_root
        for item in semantics
    ):
        output.append(
            finding(
                "SEMANTICS_SUBJECT_BINDING_MISSING",
                path,
                f"{prefix}/SEMANTICS: no accepted semantics relation natively binds subject_root",
            )
        )

    demand = resolved("DEMAND")
    if demand and not any(
        item.get("evidence_type") in {"authorization", "payment"}
        and item.get("native_public_inputs", {}).get("aeye_intent_id") == intent_id
        for item in demand
    ):
        output.append(
            finding(
                "DEMAND_INTENT_BINDING_MISSING",
                path,
                f"{prefix}/DEMAND: no accepted demand relation natively binds the pre-authorization intent_id",
            )
        )
    return output


def cross_evidence_binding_findings(
    bindings: Any,
    evidence_by_id: dict[str, dict[str, Any]],
    subject: Any,
    path: Path,
) -> list[Finding]:
    """Check equality witnesses; do not infer or upgrade coordinate results."""
    if not isinstance(bindings, list):
        return []
    output: list[Finding] = []
    seen: set[str] = set()
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            continue
        pointer = f"cross_evidence_bindings/{index}"
        binding_id = binding.get("binding_id")
        if isinstance(binding_id, str):
            if binding_id in seen:
                output.append(
                    finding(
                        "DUPLICATE_CROSS_BINDING_ID",
                        path,
                        f"{pointer}: duplicate binding_id {binding_id!r}",
                    )
                )
            seen.add(binding_id)
        work = evidence_by_id.get(binding.get("work_evidence_ref"))
        execution = evidence_by_id.get(binding.get("execution_evidence_ref"))
        if work is None or execution is None:
            output.append(
                finding(
                    "CROSS_EVIDENCE_REF_MISSING",
                    path,
                    f"{pointer}: both evidence references must resolve",
                )
            )
            continue
        if work.get("evidence_type") != "pearl_pouw" or "WORK" not in work.get("coordinates", []):
            output.append(
                finding(
                    "COUPLING_WORK_TYPE",
                    path,
                    f"{pointer}: work reference must be Pearl WORK evidence",
                )
            )
        if execution.get("evidence_type") not in {
            "execution_proof",
            "sampled_audit",
            "optimistic_dispute",
            "attestation",
        } or "EXECUTION" not in execution.get("coordinates", []):
            output.append(
                finding(
                    "COUPLING_EXECUTION_TYPE",
                    path,
                    f"{pointer}: execution reference must be an execution-verification relation",
                )
            )
        work_inputs = work.get("native_public_inputs", {})
        execution_inputs = execution.get("native_public_inputs", {})
        for field in ("operand_root_a", "operand_root_b"):
            left = work_inputs.get(field) if isinstance(work_inputs, dict) else None
            right = execution_inputs.get(field) if isinstance(execution_inputs, dict) else None
            if left is None or right is None:
                output.append(
                    finding(
                        "CROSS_EVIDENCE_BINDING_MISSING",
                        path,
                        f"{pointer}: {field} must be a native public input of both relations",
                    )
                )
            elif left != right:
                output.append(
                    finding(
                        "CROSS_EVIDENCE_BINDING_MISMATCH",
                        path,
                        f"{pointer}: {field} differs across WORK and EXECUTION evidence",
                    )
                )
        if isinstance(subject, dict) and (
            execution_inputs.get("aeye_job_id") != subject.get("job_id")
            or execution_inputs.get("aeye_subject_root") != subject.get("subject_root")
        ):
            output.append(
                finding(
                    "COUPLING_EXECUTION_SUBJECT_MISMATCH",
                    path,
                    f"{pointer}: execution relation must natively bind this receipt's job and subject",
                )
            )
    return output


def validate_receipt(data: Any, path: Path) -> list[Finding]:
    output = schema_findings(
        data, SCHEMA_DIR / "aeye-evidence-receipt-v0.schema.json", path
    )
    output.extend(forbidden_global_findings(data, path))
    if not isinstance(data, dict):
        return sorted(set(output))

    subject = data.get("subject")
    if isinstance(subject, dict):
        try:
            if subject.get("intent_id") != expected_intent_id(subject):
                output.append(
                    finding(
                        "INTENT_BINDING_MISMATCH",
                        path,
                        "subject/intent_id does not bind request, model, execution, nonce, and freshness domain",
                    )
                )
            if subject.get("job_id") != expected_job_id(subject):
                output.append(
                    finding(
                        "JOB_BINDING_MISMATCH",
                        path,
                        "subject/job_id does not bind intent_id and demand_root",
                    )
                )
            if subject.get("subject_root") != expected_subject_root(subject):
                output.append(
                    finding(
                        "SUBJECT_BINDING_MISMATCH",
                        path,
                        "subject/subject_root does not bind job_id, trace_root, and output_root",
                    )
                )
        except (KeyError, TypeError, ValueError):
            pass

    timeline = data.get("timeline")
    if isinstance(timeline, dict):
        intent_fixed = timeline.get("intent_fixed_sequence")
        authorization = timeline.get("authorization_fixed_sequence")
        job = timeline.get("job_fixed_sequence")
        subject_fixed = timeline.get("subject_fixed_sequence")
        challenge = timeline.get("challenge_sampled_sequence")
        sealed = timeline.get("receipt_sealed_sequence")
        ints = (intent_fixed, authorization, job, subject_fixed, sealed)
        if all(isinstance(value, int) for value in ints):
            if not intent_fixed < authorization:
                output.append(
                    finding(
                        "INTENT_AUTHORIZATION_ORDER",
                        path,
                        "intent must be fixed before its authorization event",
                    )
                )
            if not authorization < job:
                output.append(
                    finding("AUTHORIZATION_ORDER", path, "authorization must be fixed before the job")
                )
            if not job < subject_fixed:
                output.append(
                    finding("SUBJECT_ORDER", path, "job must be fixed before the final execution subject")
                )
            if isinstance(challenge, int):
                if not subject_fixed < challenge:
                    output.append(
                        finding(
                            "CHALLENGE_ORDER",
                            path,
                            "trace and output subject must be fixed before an audit challenge",
                        )
                    )
                if not challenge < sealed:
                    output.append(
                        finding("SEAL_ORDER", path, "challenged evidence must precede receipt sealing")
                    )
            elif not subject_fixed < sealed:
                output.append(
                    finding("SEAL_ORDER", path, "execution subject must precede receipt sealing")
                )

    evidence = data.get("evidence")
    evidence_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(evidence, list):
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                continue
            evidence_id = item.get("evidence_id")
            if isinstance(evidence_id, str):
                if evidence_id in evidence_by_id:
                    output.append(
                        finding(
                            "DUPLICATE_EVIDENCE_ID",
                            path,
                            f"evidence/{index}: duplicate evidence_id {evidence_id!r}",
                        )
                    )
                evidence_by_id[evidence_id] = item
            output.extend(coverage_findings(item.get("coverage"), path, f"evidence/{index}/coverage"))
            native_inputs = item.get("native_public_inputs")
            if isinstance(native_inputs, dict) and isinstance(subject, dict):
                native_intent = native_inputs.get("aeye_intent_id")
                native_job = native_inputs.get("aeye_job_id")
                native_subject = native_inputs.get("aeye_subject_root")
                if native_intent is not None and native_intent != subject.get("intent_id"):
                    output.append(
                        finding(
                            "EVIDENCE_INTENT_BINDING_MISMATCH",
                            path,
                            f"evidence/{index}: native intent public input differs from the receipt",
                        )
                    )
                if native_job is not None and native_job != subject.get("job_id"):
                    output.append(
                        finding(
                            "EVIDENCE_JOB_BINDING_MISMATCH",
                            path,
                            f"evidence/{index}: native job public input differs from the receipt",
                        )
                    )
                if native_subject is not None and native_subject != subject.get("subject_root"):
                    output.append(
                        finding(
                            "EVIDENCE_SUBJECT_BINDING_MISMATCH",
                            path,
                            f"evidence/{index}: native subject public input differs from the receipt",
                        )
                    )
            if item.get("evidence_type") == "pearl_pouw" and isinstance(native_inputs, dict):
                required = ("work_context_root", "operand_root_a", "operand_root_b")
                if any(native_inputs.get(field) is None for field in required):
                    output.append(
                        finding(
                            "PEARL_PUBLIC_INPUT_MISSING",
                            path,
                            f"evidence/{index}: Pearl evidence must expose its work context and both operand roots",
                        )
                    )
            if isinstance(subject, dict) and item.get("receipt_job_id") != subject.get("job_id"):
                scope = item.get("scope", {})
                if not (
                    isinstance(scope, dict)
                    and scope.get("kind") == "aggregate"
                    and scope.get("membership_proof_ref")
                ):
                    output.append(
                        finding(
                            "CROSS_JOB_EVIDENCE",
                            path,
                            f"evidence/{index}: foreign-job evidence lacks an aggregate membership proof",
                        )
                    )

    results = data.get("claimed_results")
    output.extend(result_vector_findings(results, evidence_by_id, path, "claimed_results"))
    output.extend(
        result_native_binding_findings(
            results, evidence_by_id, subject, path, "claimed_results"
        )
    )
    output.extend(
        cross_evidence_binding_findings(
            data.get("cross_evidence_bindings"), evidence_by_id, subject, path
        )
    )

    sampled = any(
        isinstance(item, dict) and item.get("assurance") == "sampled"
        for item in (evidence if isinstance(evidence, list) else [])
    ) or any(
        isinstance(item, dict) and item.get("assurance") == "sampled"
        for item in (results.values() if isinstance(results, dict) else [])
    )
    if sampled and isinstance(timeline, dict) and timeline.get("challenge_sampled_sequence") is None:
        output.append(
            finding("MISSING_AUDIT_CHALLENGE", path, "sampled assurance requires a post-subject challenge")
        )

    return sorted(set(output))


def safe_repo_path(raw_path: str, owner_path: Path) -> tuple[Path | None, list[Finding]]:
    candidate = (ROOT / raw_path).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None, [finding("PATH_ESCAPE", owner_path, f"path escapes repository: {raw_path!r}")]
    return candidate, []


def validate_report(data: Any, path: Path) -> list[Finding]:
    output = schema_findings(data, SCHEMA_DIR / "verification-report-v0.schema.json", path)
    output.extend(forbidden_global_findings(data, path))
    if not isinstance(data, dict) or not isinstance(data.get("receipt_path"), str):
        return sorted(set(output))

    receipt_path, path_findings = safe_repo_path(data["receipt_path"], path)
    output.extend(path_findings)
    if receipt_path is None or not receipt_path.is_file():
        output.append(finding("RECEIPT_MISSING", path, "referenced receipt does not exist"))
        return sorted(set(output))
    expected_digest = data.get("receipt_digest")
    if expected_digest != sha256_file(receipt_path):
        output.append(
            finding("RECEIPT_DIGEST_MISMATCH", path, "receipt_digest does not match referenced bytes")
        )

    try:
        receipt = load_json(receipt_path)
    except (OSError, json.JSONDecodeError) as exc:
        output.append(finding("RECEIPT_UNREADABLE", path, str(exc)))
        return sorted(set(output))
    if not isinstance(receipt, dict):
        return sorted(set(output))
    evidence_by_id = {
        item["evidence_id"]: item
        for item in receipt.get("evidence", [])
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    output.extend(result_vector_findings(data.get("results"), evidence_by_id, path, "results"))
    output.extend(
        result_native_binding_findings(
            data.get("results"), evidence_by_id, receipt.get("subject"), path, "results"
        )
    )

    verifier = data.get("verifier", {})
    issuer = receipt.get("issuer", {})
    results = data.get("results", {})
    has_satisfied = isinstance(results, dict) and any(
        isinstance(results.get(coordinate), dict)
        and results[coordinate].get("status") == "satisfied"
        for coordinate in COORDINATES
    )
    if (
        has_satisfied
        and isinstance(verifier, dict)
        and isinstance(issuer, dict)
        and verifier.get("principal_id") == issuer.get("principal_id")
    ):
        output.append(
            finding(
                "SELF_VERIFICATION",
                path,
                "receipt issuer cannot independently verify its own consequential claims",
            )
        )
    return sorted(set(output))


def run_git(path: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def validate_ledger(data: Any, path: Path = LEDGER) -> list[Finding]:
    output = schema_findings(data, SCHEMA_DIR / "source-ledger-v0.schema.json", path)
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return sorted(set(output))
    source_ids: set[str] = set()
    declared_files: set[str] = set()
    required_files: set[str] = set()
    retained_git_paths: set[str] = set()
    for index, entry in enumerate(data["entries"]):
        if not isinstance(entry, dict):
            continue
        source_id = entry.get("source_id")
        if isinstance(source_id, str):
            if source_id in source_ids:
                output.append(
                    finding("DUPLICATE_SOURCE_ID", path, f"entries/{index}: duplicate {source_id!r}")
                )
            source_ids.add(source_id)
        artifact = entry.get("artifact")
        if not isinstance(artifact, dict):
            continue
        artifact_type = artifact.get("type")
        if artifact_type == "file" and isinstance(artifact.get("path"), str):
            declared_files.add(artifact["path"])
            required_files.add(artifact["path"])
            artifact_path, path_findings = safe_repo_path(artifact["path"], path)
            output.extend(path_findings)
            if artifact_path is None or not artifact_path.is_file():
                output.append(
                    finding("SOURCE_ARTIFACT_MISSING", path, f"entries/{index}: {artifact['path']!r}")
                )
            elif sha256_file(artifact_path) != artifact.get("sha256"):
                output.append(
                    finding(
                        "SOURCE_DIGEST_MISMATCH",
                        path,
                        f"entries/{index}: retained bytes changed for {artifact['path']!r}",
                    )
                )
        elif artifact_type == "digest_only" and isinstance(artifact.get("path"), str):
            declared_files.add(artifact["path"])
            artifact_path, path_findings = safe_repo_path(artifact["path"], path)
            output.extend(path_findings)
            if artifact_path is not None and artifact_path.exists():
                if not artifact_path.is_file():
                    output.append(
                        finding(
                            "SOURCE_ARTIFACT_NOT_FILE",
                            path,
                            f"entries/{index}: {artifact['path']!r}",
                        )
                    )
                elif sha256_file(artifact_path) != artifact.get("sha256"):
                    output.append(
                        finding(
                            "SOURCE_DIGEST_MISMATCH",
                            path,
                            f"entries/{index}: digest-only bytes changed for {artifact['path']!r}",
                        )
                    )
        elif artifact_type == "git_tree" and isinstance(artifact.get("path"), str):
            retained_git_paths.add(artifact["path"])
            artifact_path, path_findings = safe_repo_path(artifact["path"], path)
            output.extend(path_findings)
            if artifact_path is None or not artifact_path.is_dir():
                output.append(
                    finding("SOURCE_ARTIFACT_MISSING", path, f"entries/{index}: {artifact['path']!r}")
                )
                continue
            try:
                if run_git(artifact_path, "rev-parse", "HEAD") != artifact.get("commit"):
                    output.append(
                        finding(
                            "SOURCE_COMMIT_MISMATCH",
                            path,
                            f"entries/{index}: Git HEAD changed for {artifact['path']!r}",
                        )
                    )
                if run_git(artifact_path, "remote", "get-url", "origin") != artifact.get("remote"):
                    output.append(
                        finding(
                            "SOURCE_REMOTE_MISMATCH",
                            path,
                            f"entries/{index}: origin changed for {artifact['path']!r}",
                        )
                    )
                if run_git(artifact_path, "status", "--porcelain"):
                    output.append(
                        finding(
                            "SOURCE_TREE_DIRTY",
                            path,
                            f"entries/{index}: retained Git tree is not clean: {artifact['path']!r}",
                        )
                    )
            except (subprocess.CalledProcessError, OSError) as exc:
                output.append(
                    finding("SOURCE_GIT_UNREADABLE", path, f"entries/{index}: {exc}")
                )

    discovered_files = {
        str(candidate.relative_to(ROOT))
        for directory, pattern in (
            (ROOT / "evidence" / "papers", "*.pdf"),
            (ROOT / "evidence" / "standards", "*.txt"),
            (ROOT / "evidence" / "changes", "*.patch"),
        )
        for candidate in directory.glob(pattern)
    }
    for missing in sorted(discovered_files - declared_files):
        output.append(
            finding("UNLEDGERED_RETAINED_FILE", path, f"retained evidence is absent from ledger: {missing}")
        )
    for stale in sorted(required_files - discovered_files):
        output.append(
            finding("LEDGER_FILE_OUTSIDE_RETENTION_SET", path, f"ledger file is outside retained sets: {stale}")
        )

    discovered_git = {
        str(candidate.relative_to(ROOT))
        for candidate in (ROOT / "evidence" / "external").iterdir()
        if candidate.is_dir() and (candidate / ".git").exists()
    }
    for missing in sorted(discovered_git - retained_git_paths):
        output.append(
            finding("UNLEDGERED_RETAINED_GIT", path, f"retained Git tree is absent from ledger: {missing}")
        )
    return sorted(set(output))


def experiment_findings(data: Any, path: Path) -> list[Finding]:
    output = schema_findings(data, SCHEMA_DIR / "experiment-manifest-v0.schema.json", path)
    if isinstance(data, dict):
        status = data.get("status")
        result = data.get("result")
        if status in {"proposed", "preregistered", "running", "blocked"} and result is not None:
            output.append(
                finding("PREMATURE_EXPERIMENT_RESULT", path, "unfinished experiment cannot carry a result")
            )
        if status == "blocked" and not data.get("blocking_conditions"):
            output.append(
                finding("UNEXPLAINED_BLOCK", path, "blocked status requires explicit blocking conditions")
            )
        frozen_inputs = data.get("frozen_inputs")
        if isinstance(frozen_inputs, list):
            values = {
                item.get("input_id"): item.get("value")
                for item in frozen_inputs
                if isinstance(item, dict) and isinstance(item.get("input_id"), str)
            }
            for input_id, expected in values.items():
                if not input_id.endswith("_sha256") or not isinstance(expected, str):
                    continue
                artifact_id = input_id[: -len("_sha256")]
                raw_path = values.get(artifact_id)
                if not isinstance(raw_path, str):
                    output.append(
                        finding(
                            "EXPERIMENT_DIGEST_TARGET_MISSING",
                            path,
                            f"{input_id!r} has no string path in {artifact_id!r}",
                        )
                    )
                    continue
                artifact_path, path_findings = safe_repo_path(raw_path, path)
                output.extend(path_findings)
                if artifact_path is None or not artifact_path.is_file():
                    output.append(
                        finding(
                            "EXPERIMENT_DIGEST_TARGET_MISSING",
                            path,
                            f"digest target does not exist: {raw_path!r}",
                        )
                    )
                    continue
                observed = sha256_file(artifact_path).removeprefix("sha256:")
                if observed != expected.removeprefix("sha256:"):
                    output.append(
                        finding(
                            "EXPERIMENT_INPUT_DIGEST_MISMATCH",
                            path,
                            f"{input_id!r} does not match retained bytes at {raw_path!r}",
                        )
                    )
    return sorted(set(output))


def validate_experiment(path: Path) -> list[Finding]:
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [finding("JSON_UNREADABLE", path, str(exc))]
    return experiment_findings(data, path)


def validate_e009_artifacts() -> list[Finding]:
    """Validate retained R1 packaging; mathematical replay remains verifier-owned."""
    manifest_path = E009_DIR / "manifest.json"
    if not manifest_path.is_file():
        return []
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [finding("E009_MANIFEST_UNREADABLE", manifest_path, str(exc))]
    if manifest.get("status") != "supported":
        return []

    output: list[Finding] = []
    paths = {
        "input": E009_DIR / "input.json",
        "trace": E009_ARTIFACT_DIR / "trace.json",
        "audit": E009_ARTIFACT_DIR / "audit.json",
        "receipt": E009_ARTIFACT_DIR / "receipt.json",
        "report": E009_ARTIFACT_DIR / "verification-report.json",
        "run": E009_ARTIFACT_DIR / "run.json",
        "result": E009_ARTIFACT_DIR / "result.json",
        "mutations": E009_ARTIFACT_DIR / "mutation-results.json",
        "cost_decomposition": E009_ARTIFACT_DIR / "posthoc-cost-decomposition.json",
        "adversarial_probe": E009_ARTIFACT_DIR / "posthoc-adversarial-probe.json",
        "claim_appraisal": E009_ARTIFACT_DIR / "posthoc-claim-appraisal.json",
    }
    for name, path in paths.items():
        if not path.is_file():
            output.append(finding("E009_ARTIFACT_MISSING", path, f"missing {name} artifact"))
    if output:
        return sorted(set(output))
    try:
        documents = {name: load_json(path) for name, path in paths.items()}
    except (OSError, json.JSONDecodeError) as exc:
        return [finding("E009_ARTIFACT_UNREADABLE", E009_ARTIFACT_DIR, str(exc))]

    for name, schema_name in (
        ("input", "e009-input-v0.schema.json"),
        ("trace", "e009-trace-v0.schema.json"),
        ("audit", "e009-audit-v0.schema.json"),
        ("run", "e009-run-v0.schema.json"),
        ("result", "e009-result-v0.schema.json"),
        ("mutations", "e009-mutation-results-v0.schema.json"),
        ("cost_decomposition", "e009-cost-decomposition-v0.schema.json"),
        ("adversarial_probe", "e009-posthoc-adversarial-probe-v0.schema.json"),
        ("claim_appraisal", "e009-posthoc-claim-appraisal-v0.schema.json"),
    ):
        output.extend(schema_findings(documents[name], SCHEMA_DIR / schema_name, paths[name]))
    output.extend(validate_receipt(documents["receipt"], paths["receipt"]))
    output.extend(validate_report(documents["report"], paths["report"]))

    run = documents["run"]
    if run.get("input", {}).get("sha256") != sha256_file(paths["input"]):
        output.append(finding("E009_RUN_INPUT_DIGEST_MISMATCH", paths["run"], "run index does not authenticate input.json"))
    indexed = run.get("artifacts", {})
    if isinstance(indexed, dict):
        for name, record in indexed.items():
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                output.append(finding("E009_RUN_INDEX_MALFORMED", paths["run"], f"artifact {name!r} is malformed"))
                continue
            artifact_path, path_findings = safe_repo_path(record["path"], paths["run"])
            output.extend(path_findings)
            if artifact_path is None or not artifact_path.is_file():
                output.append(finding("E009_INDEXED_ARTIFACT_MISSING", paths["run"], record["path"]))
                continue
            if record.get("sha256") != sha256_file(artifact_path):
                output.append(finding("E009_INDEXED_ARTIFACT_DIGEST_MISMATCH", artifact_path, "retained bytes differ from run index"))
            if record.get("bytes") != artifact_path.stat().st_size:
                output.append(finding("E009_INDEXED_ARTIFACT_SIZE_MISMATCH", artifact_path, "retained size differs from run index"))

    result = documents["result"]
    expected_coordinates = {
        "WORK": "unknown",
        "EXECUTION": "satisfied",
        "SEMANTICS": "satisfied",
        "DEMAND": "unsupported",
    }
    if result.get("status") != "supported" or result.get("unmodified_bundle_accepted") is not True:
        output.append(finding("E009_RESULT_NOT_SUPPORTED", paths["result"], "R1 result does not record accepted supported status"))
    if result.get("coordinate_results") != expected_coordinates:
        output.append(finding("E009_COORDINATE_VECTOR_MISMATCH", paths["result"], "R1 coordinate vector changed"))
    if result.get("event_coverage") != {"numerator": 13, "denominator": 13, "coded_linear": 5, "exact": 8}:
        output.append(finding("E009_COVERAGE_MISMATCH", paths["result"], "R1 event denominator changed"))
    mutations = documents["mutations"]
    if not (
        mutations.get("case_count") == 8
        and mutations.get("all_rejected") is True
        and mutations.get("all_expected_failures_observed") is True
        and len(mutations.get("outcomes", [])) == 8
    ):
        output.append(finding("E009_MUTATION_RESULT_MISMATCH", paths["mutations"], "not all eight controls rejected as preregistered"))

    artifact_refs = manifest.get("result", {}).get("artifact_refs", [])
    for index, reference in enumerate(artifact_refs):
        if not isinstance(reference, str) or "#sha256:" not in reference:
            output.append(finding("E009_RESULT_REF_MALFORMED", manifest_path, f"result artifact reference {index} is not content-addressed"))
            continue
        raw_path, expected_hex = reference.rsplit("#sha256:", 1)
        artifact_path, path_findings = safe_repo_path(raw_path, manifest_path)
        output.extend(path_findings)
        if artifact_path is None or not artifact_path.is_file():
            output.append(finding("E009_RESULT_REF_MISSING", manifest_path, raw_path))
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hex):
            output.append(finding("E009_RESULT_REF_MALFORMED", manifest_path, reference))
        elif sha256_file(artifact_path) != f"sha256:{expected_hex}":
            output.append(finding("E009_RESULT_REF_DIGEST_MISMATCH", artifact_path, "result artifact bytes differ from manifest"))
    return sorted(set(output))


def validate_markdown_links() -> list[Finding]:
    output: list[Finding] = []
    markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        for match in LOCAL_LINK_RE.finditer(text):
            target = match.group(1).split("#", 1)[0]
            if not target:
                continue
            candidate = (markdown.parent / target).resolve()
            try:
                candidate.relative_to(ROOT)
            except ValueError:
                output.append(finding("MARKDOWN_LINK_ESCAPE", markdown, target))
                continue
            if not candidate.exists():
                output.append(
                    finding("BROKEN_LOCAL_LINK", markdown, f"missing local link target: {target}")
                )
    return sorted(set(output))


def validate_fixture_manifest() -> tuple[list[Finding], dict[str, list[Finding]]]:
    harness_findings: list[Finding] = []
    outcomes: dict[str, list[Finding]] = {}
    try:
        manifest = load_json(FIXTURE_MANIFEST)
    except (OSError, json.JSONDecodeError) as exc:
        return [finding("FIXTURE_MANIFEST_UNREADABLE", FIXTURE_MANIFEST, str(exc))], outcomes

    for entry in manifest.get("valid", []):
        fixture_path = ROOT / entry["path"]
        try:
            data = load_json(fixture_path)
            kind = entry["kind"]
            result = validate_receipt(data, fixture_path) if kind == "receipt" else validate_report(data, fixture_path)
        except (OSError, json.JSONDecodeError) as exc:
            result = [finding("JSON_UNREADABLE", fixture_path, str(exc))]
        outcomes[entry["path"]] = result
        if result:
            harness_findings.append(
                finding(
                    "VALID_FIXTURE_REJECTED",
                    fixture_path,
                    f"expected valid; observed codes {sorted({item.code for item in result})}",
                )
            )

    for entry in manifest.get("invalid", []):
        fixture_path = ROOT / entry["path"]
        try:
            specification = load_json(fixture_path)
            specification_findings = schema_findings(
                specification,
                SCHEMA_DIR / "negative-fixture-v0.schema.json",
                fixture_path,
            )
            if specification_findings:
                result = specification_findings
                outcomes[entry["path"]] = result
                harness_findings.append(
                    finding(
                        "INVALID_FIXTURE_SPECIFICATION",
                        fixture_path,
                        f"mutation fixture is malformed: {sorted({item.code for item in result})}",
                    )
                )
                continue
            base_path, path_findings = safe_repo_path(specification["base_path"], fixture_path)
            if path_findings or base_path is None:
                result = path_findings
                outcomes[entry["path"]] = result
                harness_findings.extend(path_findings)
                continue
            data = apply_mutations(load_json(base_path), specification["mutations"])
            kind = specification["base_kind"]
            if kind == "receipt":
                result = validate_receipt(data, fixture_path)
            elif kind == "report":
                result = validate_report(data, fixture_path)
            else:
                result = experiment_findings(data, fixture_path)
        except (OSError, json.JSONDecodeError) as exc:
            result = [finding("JSON_UNREADABLE", fixture_path, str(exc))]
        outcomes[entry["path"]] = result
        observed_codes = {item.code for item in result}
        expected_codes = set(entry["expected_codes"])
        if not result:
            harness_findings.append(
                finding("INVALID_FIXTURE_ACCEPTED", fixture_path, "known-bad fixture passed")
            )
        missing = expected_codes - observed_codes
        if missing:
            harness_findings.append(
                finding(
                    "EXPECTED_FAILURE_NOT_OBSERVED",
                    fixture_path,
                    f"missing expected diagnostic codes {sorted(missing)}; observed {sorted(observed_codes)}",
                )
            )
    return sorted(set(harness_findings)), outcomes


def decode_json_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def apply_mutations(base: Any, mutations: list[dict[str, Any]]) -> Any:
    """Apply a narrow, deterministic subset of JSON Patch to a deep copy."""
    document = copy.deepcopy(base)
    for mutation in mutations:
        tokens = [decode_json_pointer_token(token) for token in mutation["pointer"].split("/")[1:]]
        if not tokens:
            raise ValueError("root mutation is not permitted")
        parent = document
        for token in tokens[:-1]:
            parent = parent[int(token)] if isinstance(parent, list) else parent[token]
        final = tokens[-1]
        if mutation["op"] == "set":
            if isinstance(parent, list):
                parent[int(final)] = copy.deepcopy(mutation["value"])
            else:
                parent[final] = copy.deepcopy(mutation["value"])
        elif isinstance(parent, list):
            del parent[int(final)]
        else:
            del parent[final]
    return document


def validate_repository() -> tuple[list[Finding], dict[str, list[Finding]]]:
    output: list[Finding] = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        try:
            Draft202012Validator.check_schema(load_json(schema_path))
        except Exception as exc:  # jsonschema raises several precise subclasses
            output.append(finding("INVALID_SCHEMA", schema_path, str(exc)))
    try:
        ledger = load_json(LEDGER)
        output.extend(validate_ledger(ledger))
    except (OSError, json.JSONDecodeError) as exc:
        output.append(finding("LEDGER_UNREADABLE", LEDGER, str(exc)))
    # Experiment directories may also retain typed inputs, transcripts, receipts,
    # reports, and measurements. Only explicit experiment-state documents use the
    # experiment-manifest schema; other contracts are validated by their own paths.
    experiment_paths = {
        *sorted((ROOT / "experiments").rglob("manifest.json")),
        *sorted((ROOT / "experiments").rglob("preregistration.json")),
    }
    for experiment_path in sorted(experiment_paths):
        output.extend(validate_experiment(experiment_path))
    output.extend(validate_e009_artifacts())
    output.extend(validate_markdown_links())
    harness_findings, outcomes = validate_fixture_manifest()
    output.extend(harness_findings)
    return sorted(set(output)), outcomes


def print_human(findings: list[Finding], outcomes: dict[str, list[Finding]]) -> None:
    invalid_count = sum(1 for result in outcomes.values() if result)
    print(
        f"Aeye validation: {len(findings)} repository error(s); "
        f"{len(outcomes)} fixture(s) exercised; {invalid_count} rejected as designed"
    )
    for item in findings:
        print(f"ERROR {item.code} {item.path}: {item.message}")
    if not findings:
        print("PASS schemas, retained-source/frozen-experiment integrity, protocol invariants, and fixture expectations")
        print("NON-CLAIM no cryptographic proof, signature, hardware origin, performance, or demand truth was established")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit a machine-readable summary")
    args = parser.parse_args(argv)
    findings, outcomes = validate_repository()
    if args.json:
        print(
            json.dumps(
                {
                    "ok": not findings,
                    "findings": [item.as_dict() for item in findings],
                    "fixtures": {
                        key: [item.as_dict() for item in value]
                        for key, value in sorted(outcomes.items())
                    },
                    "non_claim": "Structural validation is not scientific, cryptographic, hardware, performance, or economic verification.",
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print_human(findings, outcomes)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
