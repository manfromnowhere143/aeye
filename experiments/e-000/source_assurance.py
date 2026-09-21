"""Candidate-blind source-assurance classifier proposed for an E-000 successor.

The module is deliberately separate from the active ADR-0014 registry prequalifier. It
cannot assign an active E-000 tier or authorize candidate selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SourceClass(StrEnum):
    BLOCKED = "BLOCKED"
    S0_PUBLISHER_ASSOCIATED = "S0_PUBLISHER_ASSOCIATED"
    S1_INDEPENDENTLY_DERIVED = "S1_INDEPENDENTLY_DERIVED"


@dataclass(frozen=True)
class SourceFacts:
    candidate_inspected: bool = False
    publisher_revision_frozen: bool = False
    metadata_digests_retained: bool = False
    all_shards_complete: bool = False
    all_lengths_match: bool = False
    all_sha256_match: bool = False
    same_stream_transcripts_retained: bool = False
    independent_parser_replay_passed: bool = False
    single_publisher_trust_disclosed: bool = False
    independent_derivation_complete: bool = False
    independent_derivation_exact: bool = False
    derivation_recipe_frozen: bool = False
    derivation_implementation_independent: bool = False
    upstream_source_trust_disclosed: bool = False
    second_transport_complete: bool = False
    second_transport_path_distinct: bool = False


@dataclass(frozen=True)
class Decision:
    source_class: SourceClass
    code: str
    transport_observation: str


def classify(facts: SourceFacts) -> Decision:
    """Classify source evidence without treating route diversity as provenance."""

    transport = (
        "SECOND_PATH_OBSERVED"
        if facts.second_transport_complete and facts.second_transport_path_distinct
        else "NO_SECOND_PATH_OBSERVATION"
    )
    if facts.candidate_inspected:
        return Decision(SourceClass.BLOCKED, "S-INV-CANDIDATE-LEAKAGE", transport)

    publisher_association = (
        facts.publisher_revision_frozen
        and facts.metadata_digests_retained
        and facts.all_shards_complete
        and facts.all_lengths_match
        and facts.all_sha256_match
        and facts.same_stream_transcripts_retained
        and facts.independent_parser_replay_passed
        and facts.single_publisher_trust_disclosed
    )
    if not publisher_association:
        return Decision(SourceClass.BLOCKED, "S-BLK-PUBLISHER-ASSOCIATION", transport)

    independently_derived = (
        facts.independent_derivation_complete
        and facts.independent_derivation_exact
        and facts.derivation_recipe_frozen
        and facts.derivation_implementation_independent
        and facts.upstream_source_trust_disclosed
    )
    if independently_derived:
        return Decision(
            SourceClass.S1_INDEPENDENTLY_DERIVED,
            "S1-INDEPENDENT-DERIVATION-EXACT",
            transport,
        )

    return Decision(
        SourceClass.S0_PUBLISHER_ASSOCIATED,
        "S0-PUBLISHER-BYTES-ASSOCIATED",
        transport,
    )


__all__ = ["Decision", "SourceClass", "SourceFacts", "classify"]
