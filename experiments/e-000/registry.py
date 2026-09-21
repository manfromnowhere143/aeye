#!/usr/bin/env python3
"""Fail-closed checkpoint-registry prequalification for Aeye E-000.

This module evaluates retained metadata and transport receipts.  It never downloads a
checkpoint, reads model-weight bytes, selects a block, or computes a Pearl commitment.
Its strongest positive output is structural eligibility for external T1 adjudication.
The owner-side program cannot assign T1, authenticate the publisher, or independently
reproduce the checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover - fail-closed environment guard
    raise SystemExit("missing dependency: install the hash-locked development requirements") from exc


SCHEMA_VERSION = "aeye.e000-checkpoint-registry.v0"
REPORT_SCHEMA_VERSION = "aeye.e000-registry-prequalification.v0"
EXPERIMENT_ID = "E-000"
EXPECTED_MANIFEST_SHA256 = (
    "sha256:011d3c232ce9638fc265730f01b13dd3e11d87c225d19ad17842a44d7a78ddc5"
)
POLICY_ID = "ADR-0014"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
ASN_RE = re.compile(r"^AS[1-9][0-9]*$")
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "e000-checkpoint-registry-v0.schema.json"
MANIFEST_PATH = Path(__file__).resolve().parent / "manifest.json"

FORBIDDEN_PAYLOAD_KEYS = {
    "candidate_block_hash",
    "candidate_block_height",
    "candidate_certificate",
    "candidate_public_certificate_bytes",
    "hash_b",
    "model_weight_bytes",
    "payload_bytes",
    "tensor_bytes",
    "weight_bytes",
}
FORBIDDEN_T1_LANGUAGE = (
    "authentic checkpoint",
    "independent publication",
    "publisher-independent",
    "source-authenticated",
    "verified weights",
)

RECEIPT_FIELDS = (
    "retrieval_id",
    "route_role",
    "route_evidence_kind",
    "network_path_label",
    "raw_receipt_sha256",
    "source_url",
    "effective_url_without_query",
    "final_delivery_host",
    "resolved_ip",
    "dns_names",
    "asn",
    "operator_organization",
    "tls_session_sha256",
    "started_at_utc",
    "completed_at_utc",
    "http_status",
    "complete_get",
    "range_requested",
    "resumed",
    "derived_from_local_bytes",
    "redirect_chain",
    "redirect_chain_raw_sha256",
    "server_declared_upstream_urls",
    "server_declared_upstream_raw_sha256",
    "response_headers",
    "bytes_received",
    "sha256",
    "elapsed_seconds",
    "wrapper_source_sha256",
    "extractor_source_sha256",
    "toolchain",
    "same_stream_manifest_sha256",
    "tensor_transcript_sha256",
)
HEADER_FIELDS = (
    "etag",
    "x_linked_etag",
    "x_repo_commit",
    "content_length",
    "content_range",
    "server",
    "via",
    "location_chain",
    "location_chain_raw_sha256",
)
T0_RECEIPT_FIELDS = (
    "retrieval_id",
    "route_role",
    "route_evidence_kind",
    "raw_receipt_sha256",
    "source_url",
    "effective_url_without_query",
    "final_delivery_host",
    "started_at_utc",
    "completed_at_utc",
    "http_status",
    "complete_get",
    "range_requested",
    "resumed",
    "derived_from_local_bytes",
    "bytes_received",
    "sha256",
)
T1_NON_NULL_RECEIPT_FIELDS = (
    "network_path_label",
    "resolved_ip",
    "dns_names",
    "asn",
    "operator_organization",
    "tls_session_sha256",
    "redirect_chain_raw_sha256",
    "server_declared_upstream_raw_sha256",
    "elapsed_seconds",
    "wrapper_source_sha256",
    "extractor_source_sha256",
    "toolchain",
    "same_stream_manifest_sha256",
    "tensor_transcript_sha256",
)


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _finding(code: str, path: str, message: str) -> Finding:
    return Finding(code=code, path=path, message=message)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate JSON object member: {key}")
        output[key] = value
    return output


def _reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def _load_strict_json(value: bytes) -> Any:
    return json.loads(
        value.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_members,
        parse_constant=_reject_nonfinite_constant,
    )


def _schema_findings(document: Any) -> list[Finding]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    output: list[Finding] = []
    for error in sorted(
        validator.iter_errors(document),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    ):
        pointer = "/" + "/".join(str(part) for part in error.absolute_path)
        output.append(
            _finding(
                "E000-REG-REJ-SCHEMA",
                pointer.rstrip("/"),
                error.message,
            )
        )
    return output


def _walk(value: Any, path: str = "") -> Iterable[tuple[str, Any, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            yield key, child, child_path
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}/{index}")


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None


def _url_host(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    if parsed.query or parsed.fragment:
        return None
    return parsed.hostname.casefold().rstrip(".")


def _normal(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).casefold().split())


def _missing_receipt_fields(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict):
        return list(RECEIPT_FIELDS)
    missing = [field for field in RECEIPT_FIELDS if field not in receipt]
    missing.extend(
        field
        for field in T1_NON_NULL_RECEIPT_FIELDS
        if field in receipt and receipt[field] in (None, "", [], {})
    )
    headers = receipt.get("response_headers")
    if not isinstance(headers, dict):
        missing.extend(f"response_headers/{field}" for field in HEADER_FIELDS)
    else:
        missing.extend(
            f"response_headers/{field}" for field in HEADER_FIELDS if field not in headers
        )
        if headers.get("location_chain_raw_sha256") in (None, ""):
            missing.append("response_headers/location_chain_raw_sha256")
    return missing


def _receipt_shape_findings(receipt: Any, path: str) -> list[Finding]:
    if not isinstance(receipt, dict):
        return [_finding("E000-REG-REJ-RECEIPT-TYPE", path, "receipt must be an object")]

    output: list[Finding] = []
    for field in ("source_url", "effective_url_without_query"):
        if _url_host(receipt.get(field)) is None:
            output.append(
                _finding(
                    "E000-REG-REJ-UNSAFE-URL",
                    f"{path}/{field}",
                    "URL must be sanitized HTTPS without credentials, query, or fragment",
                )
            )
    effective_host = _url_host(receipt.get("effective_url_without_query"))
    final_host = _normal(receipt.get("final_delivery_host"))
    if effective_host is not None and final_host != effective_host:
        output.append(
            _finding(
                "E000-REG-REJ-FINAL-HOST",
                f"{path}/final_delivery_host",
                "final_delivery_host must equal the sanitized effective URL host",
            )
        )
    resolved_ip = receipt.get("resolved_ip")
    try:
        if resolved_ip is not None:
            ipaddress.ip_address(resolved_ip)
    except ValueError:
        output.append(
            _finding(
                "E000-REG-REJ-IP",
                f"{path}/resolved_ip",
                "resolved_ip must be an IPv4 or IPv6 address retained at retrieval time",
            )
        )
    if not ASN_RE.fullmatch(str(receipt.get("asn", ""))):
        output.append(
            _finding("T1-BLK-ASN-UNRESOLVED", f"{path}/asn", "a concrete AS number is required")
        )
    for field in ("started_at_utc", "completed_at_utc"):
        if _parse_utc(receipt.get(field)) is None:
            output.append(
                _finding(
                    "E000-REG-REJ-TIMESTAMP",
                    f"{path}/{field}",
                    "timestamp must be a valid UTC value ending in Z",
                )
            )
    started = _parse_utc(receipt.get("started_at_utc"))
    completed = _parse_utc(receipt.get("completed_at_utc"))
    if started is not None and completed is not None and completed <= started:
        output.append(
            _finding(
                "E000-REG-REJ-TIMESTAMP-ORDER",
                path,
                "completed_at_utc must be strictly later than started_at_utc",
            )
        )
    return output


def _primary_receipt_valid(receipt: Any, shard: dict[str, Any]) -> bool:
    if not isinstance(receipt, dict) or any(field not in receipt for field in T0_RECEIPT_FIELDS):
        return False
    return bool(
        receipt.get("route_role") == "primary"
        and receipt.get("route_evidence_kind") == "observed_transport"
        and receipt.get("http_status") == 200
        and receipt.get("complete_get") is True
        and receipt.get("range_requested") is False
        and receipt.get("resumed") is False
        and receipt.get("derived_from_local_bytes") is False
        and receipt.get("bytes_received") == shard.get("bytes")
        and receipt.get("sha256") == shard.get("lfs_sha256")
    )


def _redirect_targets(receipt: dict[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for field in ("redirect_chain", "server_declared_upstream_urls"):
        raw = receipt.get(field)
        if isinstance(raw, list):
            values.extend(item for item in raw if isinstance(item, str))
    headers = receipt.get("response_headers")
    if isinstance(headers, dict) and isinstance(headers.get("location_chain"), list):
        values.extend(item for item in headers["location_chain"] if isinstance(item, str))
    return tuple(values)


def _first_pair_failure(
    primary: Any,
    secondary: Any,
    shard: dict[str, Any],
    disclosure: Any,
    claims: Any,
    path: str,
) -> Finding | None:
    """Apply the frozen T1 rejection order to one shard."""
    if isinstance(primary, dict) and isinstance(secondary, dict):
        primary_host = _normal(primary.get("final_delivery_host"))
        secondary_host = _normal(secondary.get("final_delivery_host"))
        primary_ip = _normal(primary.get("resolved_ip"))
        secondary_ip = _normal(secondary.get("resolved_ip"))
        primary_dns = primary.get("dns_names")
        secondary_dns = secondary.get("dns_names")
        primary_aliases = {
            _normal(item) for item in primary_dns if isinstance(item, str)
        } if isinstance(primary_dns, list) else set()
        secondary_aliases = {
            _normal(item) for item in secondary_dns if isinstance(item, str)
        } if isinstance(secondary_dns, list) else set()
        if (
            primary_host
            and primary_host == secondary_host
            or primary_ip
            and primary_ip == secondary_ip
            or primary_aliases.intersection(secondary_aliases)
        ):
            return _finding(
                "T1-REJ-RELABEL",
                path,
                "the two routes share a final host, resolved IP, or retained DNS alias",
            )

        primary_effective = primary.get("effective_url_without_query")
        primary_effective_host = _url_host(primary_effective)
        for target in _redirect_targets(secondary):
            target_host = _url_host(target)
            sanitized_target = target.split("?", 1)[0].split("#", 1)[0]
            if (
                target_host is not None
                and target_host in {primary_host, primary_effective_host}
                or isinstance(primary_effective, str)
                and sanitized_target == primary_effective
            ):
                return _finding(
                    "T1-REJ-REDIRECT-SAME-PAYLOAD-HOST",
                    path,
                    "the second route redirects to the primary payload host or object URL",
                )

        same_timestamps = (
            primary.get("started_at_utc") == secondary.get("started_at_utc")
            and primary.get("completed_at_utc") == secondary.get("completed_at_utc")
        )
        primary_tls = _normal(primary.get("tls_session_sha256"))
        secondary_tls = _normal(secondary.get("tls_session_sha256"))
        if (
            primary_tls
            and primary_tls == secondary_tls
            or secondary.get("derived_from_local_bytes") is True
            or primary.get("derived_from_local_bytes") is True
            or same_timestamps
        ):
            return _finding(
                "T1-REJ-SINGLE-STREAM",
                path,
                "receipts do not establish two separately initiated network byte streams",
            )

    for receipt in (primary, secondary):
        headers = receipt.get("response_headers") if isinstance(receipt, dict) else None
        if not isinstance(receipt, dict) or (
            receipt.get("http_status") != 200
            or receipt.get("complete_get") is not True
            or receipt.get("range_requested") is not False
            or receipt.get("resumed") is not False
            or not isinstance(headers, dict)
            or headers.get("content_range") is not None
        ):
            return _finding(
                "T1-REJ-INCOMPLETE-GET",
                path,
                "both routes must retain independent, non-range HTTP 200 complete transfers",
            )

    for receipt in (primary, secondary):
        if isinstance(receipt, dict) and (
            receipt.get("sha256") is not None
            and receipt.get("sha256") != shard.get("lfs_sha256")
            or receipt.get("bytes_received") is not None
            and receipt.get("bytes_received") != shard.get("bytes")
        ):
            return _finding(
                "T1-REJ-DIGEST-OR-LENGTH",
                path,
                "a full-stream digest or byte length differs from the frozen LFS object",
            )

    missing = sorted(
        {
            item
            for receipt in (primary, secondary)
            for item in _missing_receipt_fields(receipt)
        }
    )
    if not isinstance(disclosure, dict):
        missing.append("transport_disclosure")
    else:
        for field in (
            "same_workstation",
            "same_client_implementation",
            "effective_origin_shared",
            "effective_origin_evidence",
            "independent_publication",
            "proxy_revision_header_status",
        ):
            if field not in disclosure:
                missing.append(f"transport_disclosure/{field}")
    if missing:
        return _finding(
            "T1-REJ-MISSING-RETAINED-ARTIFACT",
            path,
            "missing required receipt material: " + ", ".join(sorted(set(missing))),
        )

    if primary.get("route_evidence_kind") != "observed_transport" or secondary.get(
        "route_evidence_kind"
    ) != "observed_transport":
        return _finding(
            "T1-REJ-LABEL-ONLY",
            path,
            "route names and narratives do not establish independent transport",
        )

    if (
        not isinstance(disclosure.get("same_workstation"), bool)
        or not isinstance(disclosure.get("same_client_implementation"), bool)
        or not isinstance(disclosure.get("effective_origin_shared"), bool)
        or not isinstance(disclosure.get("effective_origin_evidence"), str)
        or not disclosure.get("effective_origin_evidence")
        or not isinstance(disclosure.get("proxy_revision_header_status"), str)
        or not disclosure.get("proxy_revision_header_status")
    ):
        return _finding(
            "T1-REJ-MISSING-RETAINED-ARTIFACT",
            path,
            "transport disclosures must be typed and non-empty",
        )

    source_hosts = {_url_host(primary.get("source_url")), _url_host(secondary.get("source_url"))}
    if None in source_hosts or len(source_hosts) != 2:
        return _finding(
            "T1-REJ-LABEL-ONLY",
            path,
            "the two receipts do not establish separate HTTPS source origins",
        )

    primary_asn = _normal(primary.get("asn"))
    secondary_asn = _normal(secondary.get("asn"))
    primary_org = _normal(primary.get("operator_organization"))
    secondary_org = _normal(secondary.get("operator_organization"))
    if (
        not primary_asn
        or not secondary_asn
        or not primary_org
        or not secondary_org
        or primary_asn == secondary_asn
        or primary_org == secondary_org
    ):
        return _finding(
            "T1-REJ-OPERATOR-IDENTITY",
            path,
            "the final-delivery operators must have distinct retained ASN and organisation",
        )

    rendered_claims = "\n".join(item for item in claims if isinstance(item, str)).casefold()
    if (
        disclosure.get("independent_publication") is not False
        or any(phrase in rendered_claims for phrase in FORBIDDEN_T1_LANGUAGE)
        or re.search(r"\bt2\b", rendered_claims)
    ):
        return _finding(
            "T1-REJ-TIER-LANGUAGE",
            path,
            "T1 evidence is described with source-authentication or T2 language",
        )
    return None


def _entry_qualification(entry: Any, index: int) -> dict[str, Any]:
    base = f"/entries/{index}"
    findings: list[Finding] = []
    if not isinstance(entry, dict):
        finding = _finding("E000-REG-REJ-ENTRY-TYPE", base, "entry must be an object")
        return {
            "entry_id": None,
            "prequalification_status": "invalid_input",
            "observed_tier": None,
            "candidate_tier": None,
            "candidate_tier_statement": None,
            "reviewer_adjudication_required": True,
            "t2_evaluated": False,
            "t2_non_claim": "T2 requires an independent reproduction contract and is not inferred here",
            "findings": [finding.as_dict()],
        }

    revision = entry.get("revision")
    if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
        findings.append(
            _finding(
                "E000-REG-REJ-REVISION",
                f"{base}/revision",
                "checkpoint revision must be an immutable lowercase 40-hex Git commit",
            )
        )
    if _url_host(entry.get("repository")) is None:
        findings.append(
            _finding(
                "E000-REG-REJ-REPOSITORY",
                f"{base}/repository",
                "repository must be a sanitized HTTPS URL",
            )
        )
    if _parse_utc(entry.get("metadata_retrieved_at_utc")) is None:
        findings.append(
            _finding(
                "E000-REG-REJ-TIMESTAMP",
                f"{base}/metadata_retrieved_at_utc",
                "metadata retrieval time must be a valid UTC value ending in Z",
            )
        )

    tp_degrees = entry.get("tensor_parallel_degrees")
    tp_values_valid = bool(
        isinstance(tp_degrees, list)
        and tp_degrees
        and all(type(item) is int and item >= 1 for item in tp_degrees)
    )
    if not tp_values_valid or tp_degrees != sorted(set(tp_degrees)):
        findings.append(
            _finding(
                "E000-REG-REJ-TP-DEGREES",
                f"{base}/tensor_parallel_degrees",
                "TP degrees must be a non-empty sorted unique list of positive integers",
            )
        )

    weight_index = entry.get("weight_index")
    expected_paths = (
        weight_index.get("declared_weight_shards", [])
        if isinstance(weight_index, dict)
        else []
    )
    shards = entry.get("weight_shards")
    if not isinstance(expected_paths, list) or not isinstance(shards, list):
        expected_paths = []
        shards = []
        findings.append(
            _finding(
                "T1-REJ-SHARD-COVERAGE",
                base,
                "weight index and retained shard set must both be present",
            )
        )
    actual_paths = [
        item.get("path")
        for item in shards
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    expected_paths_valid = bool(
        isinstance(expected_paths, list)
        and expected_paths
        and all(isinstance(item, str) for item in expected_paths)
    )
    coverage_complete = bool(
        expected_paths_valid
        and len(expected_paths) == len(set(expected_paths))
        and sorted(expected_paths) == sorted(actual_paths)
    )
    if (
        not expected_paths_valid
        or len(expected_paths) != len(set(expected_paths))
        or sorted(expected_paths) != sorted(actual_paths)
    ):
        findings.append(
            _finding(
                "T1-REJ-SHARD-COVERAGE",
                f"{base}/weight_shards",
                "retained shards must equal the complete shard set declared by the pinned index",
            )
        )

    disclosure = entry.get("transport_disclosure")
    claims_value = entry.get("claims")
    claims = claims_value if isinstance(claims_value, list) else []
    recipe = entry.get("transform_recipe")
    recipe_digest_values = (
        (
            recipe.get("artifact_sha256"),
            recipe.get("source_verification_sha256"),
            recipe.get("semantic_entailment_review_sha256"),
        )
        if isinstance(recipe, dict)
        else ()
    )
    recipe_digests_distinct = bool(
        len(recipe_digest_values) == 3
        and all(isinstance(value, str) for value in recipe_digest_values)
        and len(set(recipe_digest_values)) == 3
    )
    recipe_ready = bool(
        isinstance(recipe, dict)
        and recipe.get("status") == "frozen"
        and recipe.get("unresolved_parameters") == []
        and recipe.get("semantic_entailment_review") == "accepted"
        and SHA256_RE.fullmatch(str(recipe.get("artifact_sha256", "")))
        and SHA256_RE.fullmatch(str(recipe.get("source_verification_sha256", "")))
        and SHA256_RE.fullmatch(
            str(recipe.get("semantic_entailment_review_sha256", ""))
        )
        and recipe_digests_distinct
    )
    if not recipe_ready:
        findings.append(
            _finding(
                "E000-BLK-UNRESOLVED-TRANSFORM",
                f"{base}/transform_recipe",
                "T1 review requires distinct recipe, source-verification, and accepted semantic-entailment-review artifacts with no unresolved parameter",
            )
        )
    all_primary_valid = bool(shards) and coverage_complete and not any(
        finding.code.startswith("E000-REG-REJ") for finding in findings
    )
    all_t1_valid = (
        all_primary_valid
        and recipe_ready
        and not any(finding.code == "T1-REJ-SHARD-COVERAGE" for finding in findings)
    )

    for shard_index, shard in enumerate(shards):
        path = f"{base}/weight_shards/{shard_index}"
        if not isinstance(shard, dict):
            findings.append(_finding("E000-REG-REJ-SHARD-TYPE", path, "shard must be an object"))
            all_primary_valid = False
            all_t1_valid = False
            continue
        if (
            not SHA256_RE.fullmatch(str(shard.get("lfs_sha256", "")))
            or type(shard.get("bytes")) is not int
            or shard.get("bytes", 0) < 1
        ):
            findings.append(
                _finding(
                    "E000-REG-REJ-LFS-IDENTITY",
                    path,
                    "each shard requires a positive byte length and sha256-prefixed LFS object id",
                )
            )
            all_primary_valid = False
            all_t1_valid = False

        retrievals = shard.get("retrievals")
        if not isinstance(retrievals, list):
            retrievals = []
        roles: dict[str, dict[str, Any]] = {}
        for receipt in retrievals:
            role = receipt.get("route_role") if isinstance(receipt, dict) else None
            if isinstance(role, str) and role in {"primary", "secondary"}:
                roles[role] = receipt
        primary = roles.get("primary")
        secondary = roles.get("secondary")
        if len(retrievals) != 2 or sorted(roles) != ["primary", "secondary"]:
            findings.append(
                _finding(
                    "T1-REJ-MISSING-RETAINED-ARTIFACT",
                    f"{path}/retrievals",
                    "exactly one primary and one secondary receipt are required",
                )
            )
            all_t1_valid = False
        for receipt_index, receipt in enumerate(retrievals):
            receipt_findings = _receipt_shape_findings(
                receipt, f"{path}/retrievals/{receipt_index}"
            )
            findings.extend(receipt_findings)
            if receipt_findings:
                all_t1_valid = False
            if any(item.code.startswith("E000-REG-REJ") for item in receipt_findings):
                all_primary_valid = False

        if not _primary_receipt_valid(primary, shard):
            all_primary_valid = False
        pair_failure = _first_pair_failure(primary, secondary, shard, disclosure, claims, path)
        if pair_failure is not None:
            findings.append(pair_failure)
            all_t1_valid = False

    has_input_error = any(item.code.startswith("E000-REG-REJ") for item in findings)
    if has_input_error:
        observed_tier = None
        candidate_tier = None
        candidate_tier_statement = None
        status = "invalid_input"
    elif all_t1_valid:
        observed_tier = "T0"
        candidate_tier = "T1"
        shared = isinstance(disclosure, dict) and disclosure.get("effective_origin_shared") is True
        same_workstation = (
            isinstance(disclosure, dict) and disclosure.get("same_workstation") is True
        )
        qualifiers = ["transport corroboration"]
        if shared:
            qualifiers[0] += " via a shared-effective-origin proxy"
        qualifiers.extend(
            [
                "single-publisher trust",
                "same-workstation retrieval" if same_workstation else "separate-workstation retrieval",
            ]
        )
        candidate_tier_statement = (
            f"T1 ({qualifiers[0]}); {qualifiers[1]}; {qualifiers[2]}"
        )
        status = "eligible_for_review"
    elif all_primary_valid:
        observed_tier = "T0"
        candidate_tier = None
        candidate_tier_statement = None
        status = "below_minimum"
    else:
        observed_tier = None
        candidate_tier = None
        candidate_tier_statement = None
        status = "below_minimum"

    return {
        "entry_id": entry.get("entry_id"),
        "prequalification_status": status,
        "observed_tier": observed_tier,
        "candidate_tier": candidate_tier,
        "candidate_tier_statement": candidate_tier_statement,
        "reviewer_adjudication_required": True,
        "t2_evaluated": False,
        "t2_non_claim": "T2 requires an independent reproduction contract and is not inferred here",
        "findings": [item.as_dict() for item in sorted(set(findings))],
    }


def prequalify_registry(
    document: Any, *, registry_artifact_sha256: str | None = None
) -> dict[str, Any]:
    """Return an owner-side report requiring external T1 adjudication."""
    global_findings: list[Finding] = _schema_findings(document)
    if registry_artifact_sha256 is not None and not SHA256_RE.fullmatch(
        registry_artifact_sha256
    ):
        global_findings.append(
            _finding(
                "E000-REG-REJ-ARTIFACT-DIGEST",
                "/registry_artifact_sha256",
                "registry artifact digest must be sha256-prefixed lowercase hex",
            )
        )
        registry_artifact_sha256 = None
    try:
        registry_canonical_sha256 = _canonical_sha256(document)
    except (TypeError, ValueError):
        registry_canonical_sha256 = None
        global_findings.append(
            _finding(
                "E000-REG-REJ-NONCANONICAL-JSON",
                "",
                "registry must contain only finite, canonicalizable JSON values",
            )
        )
    observed_manifest_digest = _sha256_file(MANIFEST_PATH)
    if observed_manifest_digest != EXPECTED_MANIFEST_SHA256:
        global_findings.append(
            _finding(
                "E000-REG-REJ-IMPLEMENTATION-MANIFEST-DRIFT",
                str(MANIFEST_PATH),
                "the qualifier's manifest binding no longer matches the repository manifest",
            )
        )
    if not isinstance(document, dict):
        global_findings.append(
            _finding("E000-REG-REJ-DOCUMENT-TYPE", "", "registry must be a JSON object")
        )
        entries: list[Any] = []
    else:
        entries = document.get("entries") if isinstance(document.get("entries"), list) else []
        if document.get("schema_version") != SCHEMA_VERSION:
            global_findings.append(
                _finding(
                    "E000-REG-REJ-SCHEMA-VERSION",
                    "/schema_version",
                    f"expected {SCHEMA_VERSION}",
                )
            )
        if document.get("experiment_id") != EXPERIMENT_ID:
            global_findings.append(
                _finding("E000-REG-REJ-EXPERIMENT", "/experiment_id", "expected E-000")
            )
        if document.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256:
            global_findings.append(
                _finding(
                    "E000-REG-REJ-MANIFEST-BINDING",
                    "/manifest_sha256",
                    "registry must bind the current immutable E-000 manifest",
                )
            )
        if document.get("candidate_inspected") is not False:
            global_findings.append(
                _finding(
                    "E000-REG-REJ-CANDIDATE-MATERIAL",
                    "/candidate_inspected",
                    "pre-candidate registry work must retain candidate_inspected=false",
                )
            )
        if document.get("contains_model_weight_bytes") is not False:
            global_findings.append(
                _finding(
                    "E000-REG-REJ-MODEL-BYTES",
                    "/contains_model_weight_bytes",
                    "registry artifacts may contain metadata and digests, never model-weight bytes",
                )
            )
        if not entries:
            global_findings.append(
                _finding("E000-REG-REJ-EMPTY", "/entries", "registry must contain at least one entry")
            )
        for key, _value, path in _walk(document):
            if key in FORBIDDEN_PAYLOAD_KEYS:
                code = (
                    "E000-REG-REJ-CANDIDATE-MATERIAL"
                    if key.startswith("candidate_") or key == "hash_b"
                    else "E000-REG-REJ-MODEL-BYTES"
                )
                global_findings.append(
                    _finding(code, path, f"forbidden pre-candidate payload field: {key}")
                )

    entry_results = [_entry_qualification(entry, index) for index, entry in enumerate(entries)]
    entry_ids = [
        item.get("entry_id")
        for item in entries
        if isinstance(item, dict) and isinstance(item.get("entry_id"), str)
    ]
    if len(entry_ids) != len(entries) or len(entry_ids) != len(set(entry_ids)):
        global_findings.append(
            _finding("E000-REG-REJ-DUPLICATE-ENTRY", "/entries", "entry_id values must be unique")
        )

    invalid_entry_present = any(
        item["prequalification_status"] == "invalid_input" for item in entry_results
    )
    if invalid_entry_present:
        global_findings.append(
            _finding(
                "E000-REG-REJ-ENTRY-SET",
                "/entries",
                "one invalid entry invalidates the registry as an atomic prequalification set",
            )
        )

    if global_findings:
        for result in entry_results:
            result.update(
                prequalification_status="invalid_input",
                observed_tier=None,
                candidate_tier=None,
                candidate_tier_statement=None,
            )

    if global_findings:
        prequalification_status = "invalid_input"
    elif entry_results and all(
        item["prequalification_status"] == "eligible_for_review" for item in entry_results
    ):
        prequalification_status = "eligible_for_review"
    else:
        prequalification_status = "below_minimum"

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "policy_id": POLICY_ID,
        "registry_artifact_sha256": registry_artifact_sha256,
        "registry_canonical_sha256": registry_canonical_sha256,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "prequalification_status": prequalification_status,
        "required_minimum_tier": "T1",
        "candidate_inspected": False,
        "reviewer_adjudication_required": True,
        "t2_evaluated": False,
        "entry_results": entry_results,
        "findings": [item.as_dict() for item in sorted(set(global_findings))],
        "claim_ceiling": (
            "This owner-side report can establish structural eligibility for T1 review, not "
            "assign T1. An external reviewer must adjudicate the retained receipts and bind its "
            "decision to their exact digests. Even adjudicated T1 would not authenticate the "
            "publisher, reproduce the checkpoint, identify a Pearl model, or establish WORK, "
            "EXECUTION, SEMANTICS, or DEMAND."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()

    registry_bytes = args.registry.read_bytes()
    try:
        document = _load_strict_json(registry_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "code": "E000-REG-REJ-JSON-PARSE",
                    "message": str(exc),
                    "registry": str(args.registry),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    report = prequalify_registry(
        document,
        registry_artifact_sha256=_sha256_bytes(registry_bytes),
    )
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write is not None:
        args.write.write_text(encoded, encoding="utf-8")
        print(json.dumps({"report": str(args.write), "sha256": _sha256_file(args.write)}))
    else:
        print(encoded, end="")
    return 0 if report["prequalification_status"] == "eligible_for_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
