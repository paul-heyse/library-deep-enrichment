"""Derived behaviors must be supported, classified, and honestly counted."""

from __future__ import annotations

from pathlib import Path

import pytest
from library_guides.derivation import (
    Agreement,
    DerivationBatch,
    evidence_is_known,
    load_derived_behaviors,
    validate_proposal,
)
from library_guides.divergence import compare
from library_guides.manifest import load_library_manifest
from library_guides.stages.packet_io import evidence_reference_ids, packets_for_library
from library_guides.validate.authored import AuthoredRecordError

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_LIBRARY = "datafusion-rust"


def _proposal(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "behavior_id": "demo.behavior",
        "library_id": "demo",
        "profile_id": "demo-p",
        "packet_id": "demo:group",
        "claim": "Something the evidence establishes.",
        "mechanism": "Because the upstream documentation says so.",
        "conditions": ["Applies under a stated condition."],
        "evidence_refs": ["api:demo::Thing"],
        "prior_refs": [],
        "agreement": "novel",
        "verification_level": "documented",
        "review_state": "accepted",
    }
    base.update(overrides)
    return base


def test_a_proposal_citing_no_evidence_is_rejected() -> None:
    """An unsupported claim is exactly what this system exists to prevent."""
    with pytest.raises(AuthoredRecordError, match="at least one evidence reference"):
        validate_proposal(_proposal(evidence_refs=[]), context="test")


def test_claiming_a_relationship_to_a_prior_requires_naming_it() -> None:
    """'Contradicts the docs' is unreviewable without saying which claim."""
    with pytest.raises(AuthoredRecordError, match="names none in prior_refs"):
        validate_proposal(_proposal(agreement="contradicts_prior"), context="test")


def test_an_unknown_agreement_value_is_rejected() -> None:
    """The four buckets are the vocabulary; a fifth would not be counted."""
    with pytest.raises(AuthoredRecordError, match="is not one of"):
        validate_proposal(_proposal(agreement="probably_fine"), context="test")


def test_a_well_formed_novel_proposal_validates() -> None:
    """The ordinary case must pass, or the guards above prove nothing."""
    behavior = validate_proposal(_proposal(), context="test")
    assert behavior.agreement is Agreement.NOVEL
    assert not behavior.is_publishable()
    assert behavior.is_finding()


def test_an_agreed_behavior_is_not_counted_as_a_finding() -> None:
    """Confirming the prior document is a result, but it is not a discovery."""
    behavior = validate_proposal(
        _proposal(agreement="agreed", prior_refs=["df-rust:1.1"]), context="test"
    )
    assert not behavior.is_finding()


def _derived() -> tuple[str, DerivationBatch]:
    profile_id = load_library_manifest(_LIBRARY).profiles[0].profile_id
    return profile_id, load_derived_behaviors(_LIBRARY, profile_id, repository_root=REPOSITORY_ROOT)


def test_the_pilot_actually_derived_behaviors() -> None:
    """A vacuous pass over an empty derivation would prove nothing."""
    _, batch = _derived()
    minimum_expected = 5
    assert len(batch.behaviors) >= minimum_expected


def test_every_derived_behavior_cites_evidence_a_packet_offered() -> None:
    """A citation that no packet contained would be fabricated, not derived."""
    _, batch = _derived()
    packets = packets_for_library(
        _LIBRARY, repository_root=REPOSITORY_ROOT, stack_id="datafusion-arrow-rust"
    )
    known = evidence_reference_ids(packets)
    unknown = evidence_is_known(batch.behaviors, known)
    assert not unknown, f"evidence references no packet offered: {unknown}"


def test_every_derived_behavior_names_the_packet_it_came_from() -> None:
    """Provenance back to the evidence group has to survive into the record."""
    _, batch = _derived()
    packets = {
        packet.packet_id
        for packet in packets_for_library(
            _LIBRARY, repository_root=REPOSITORY_ROOT, stack_id="datafusion-arrow-rust"
        )
    }
    unknown = {b.packet_id for b in batch.behaviors} - packets
    assert not unknown, f"derived from packets that do not exist: {sorted(unknown)}"


def test_a_non_novel_behavior_names_the_prior_it_relates_to() -> None:
    """Agreement and refinement are only auditable against a named prior."""
    _, batch = _derived()
    for behavior in batch.behaviors:
        if behavior.agreement is not Agreement.NOVEL:
            assert behavior.prior_refs, f"{behavior.behavior_id} names no prior"


def test_divergence_reports_partial_runs_as_partial() -> None:
    """A subset run must not read as though the whole library were derived."""
    profile_id, batch = _derived()
    packets = packets_for_library(
        _LIBRARY, repository_root=REPOSITORY_ROOT, stack_id="datafusion-arrow-rust"
    )
    report = compare(
        batch.behaviors,
        [],
        library_id=_LIBRARY,
        profile_id=profile_id,
        packets_available=len(packets),
    )
    assert report.packets_derived < report.packets_available
    assert report.behaviors_per_packet > 0
    assert "of packets" in report.describe()


def test_the_novel_rate_is_measured_against_derived_behaviors() -> None:
    """The rate must not be inflated by counting packets nobody derived from."""
    profile_id, batch = _derived()
    report = compare(
        batch.behaviors,
        [],
        library_id=_LIBRARY,
        profile_id=profile_id,
        packets_available=1000,
    )
    novel = report.buckets[str(Agreement.NOVEL)]
    assert report.novel_rate == pytest.approx(novel / report.derived_total)
