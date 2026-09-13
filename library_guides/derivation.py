"""Behaviors derived from evidence by the authoring process.

A derived behavior is a claim this process makes, not a passage copied from a
document. It must cite the evidence it stands on, and it records how it relates
to any prior claim so that agreement, contradiction and novelty are all visible
rather than blended into a single revision.

``agreement`` is the field that earns the system its keep. A behavior the
evidence supports that no prior document contains is the whole reason for
deriving rather than summarizing.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Final

import yaml
from attrs import field, frozen

from library_guides.content import CONTENT_ROOT
from library_guides.models.enums import ReviewState, VerificationLevel
from library_guides.validate.authored import (
    AuthoredRecordError,
    require_mapping,
    require_sequence,
    require_str,
    require_str_sequence,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

__all__ = [
    "Agreement",
    "DerivationBatch",
    "DerivedBehavior",
    "derived_path",
    "evidence_is_known",
    "load_derived_behaviors",
    "validate_proposal",
]

_SCHEMA_VERSION: Final = "library-guides.derived_behaviors.v1"


class Agreement(StrEnum):
    """How a derived behavior relates to the prior document, if any."""

    AGREED = "agreed"
    """Evidence supports it and a prior claim says the same thing."""

    REFINED = "refined"
    """A prior claim is broadly right but missing a condition the evidence shows."""

    CONTRADICTS_PRIOR = "contradicts_prior"
    """Evidence contradicts what the prior claim asserts."""

    NOVEL = "novel"
    """Evidence supports it and no prior claim covers it."""


@frozen(kw_only=True)
class DerivedBehavior:
    """One behavior this process asserts, with the evidence it rests on."""

    behavior_id: str = field()
    library_id: str = field()
    profile_id: str = field()
    packet_id: str = field()
    claim: str = field()
    mechanism: str = field()
    conditions: tuple[str, ...] = field(default=())
    evidence_refs: tuple[str, ...] = field(default=())
    prior_refs: tuple[str, ...] = field(default=())
    agreement: Agreement = field(default=Agreement.NOVEL)
    verification_level: VerificationLevel = field(default=VerificationLevel.DOCUMENTED)
    review_state: ReviewState = field(default=ReviewState.NEEDS_REVIEW)
    open_question: str = field(default="")

    @staticmethod
    def is_publishable() -> bool:
        """Return whether this behavior may be rendered as guidance.

        Returns:
            False; the legacy review lacks an exact semantic dependency digest.

        """
        return False

    def is_finding(self) -> bool:
        """Return whether this behavior is a result the prior document lacks.

        Returns:
            ``True`` for novel behaviors and for contradictions of a prior claim.

        """
        return self.agreement in {Agreement.NOVEL, Agreement.CONTRADICTS_PRIOR}


@frozen(kw_only=True)
class DerivationBatch:
    """Every behavior derived for one library profile."""

    library_id: str = field()
    profile_id: str = field()
    behaviors: tuple[DerivedBehavior, ...] = field()

    def by_agreement(self) -> dict[str, int]:
        """Return how many behaviors fall in each agreement bucket.

        Returns:
            Mapping of agreement value to count.

        """
        counts: dict[str, int] = dict.fromkeys((item.value for item in Agreement), 0)
        for behavior in self.behaviors:
            counts[str(behavior.agreement)] += 1
        return counts

    def packets_covered(self) -> int:
        """Return how many distinct packets produced these behaviors.

        Returns:
            Distinct packet count.

        """
        return len({behavior.packet_id for behavior in self.behaviors})

    def summary(self) -> str:
        """Describe the batch in one line.

        Returns:
            A short human-readable summary.

        """
        packets = self.packets_covered()
        per_packet = len(self.behaviors) / packets if packets else 0.0
        findings = sum(1 for behavior in self.behaviors if behavior.is_finding())
        return (
            f"{self.library_id}/{self.profile_id}: {len(self.behaviors):,} behaviors "
            f"from {packets} packets ({per_packet:.1f}/packet), "
            f"{findings} findings, buckets={self.by_agreement()}"
        )


def derived_path(library_id: str, profile_id: str, *, repository_root: Path) -> Path:
    """Return where one profile's derived behaviors live.

    Returns:
        Path to the profile's derived-behaviour file.

    """
    return (
        repository_root
        / CONTENT_ROOT
        / "libraries"
        / library_id
        / "behaviors"
        / f"{profile_id}.yaml"
    )


def validate_proposal(raw: Mapping[str, object], *, context: str) -> DerivedBehavior:
    """Return one validated derived behavior.

    A proposal that cites no evidence is rejected outright rather than stored
    with a warning: an unsupported claim is exactly what this system exists to
    prevent, and storing it makes it indistinguishable from a supported one.

    Returns:
        The validated behavior.

    Raises:
        AuthoredRecordError: When the proposal is malformed or unsupported.

    """
    evidence = require_str_sequence(raw, "evidence_refs", context=context)
    if not evidence:
        message = f"{context}: a derived behavior must cite at least one evidence reference"
        raise AuthoredRecordError(message)
    agreement_value = require_str(raw, "agreement", context=context)
    try:
        agreement = Agreement(agreement_value)
    except ValueError as error:
        allowed = ", ".join(item.value for item in Agreement)
        message = f"{context}: agreement {agreement_value!r} is not one of: {allowed}"
        raise AuthoredRecordError(message) from error
    if agreement is not Agreement.NOVEL and not raw.get("prior_refs"):
        message = (
            f"{context}: agreement {agreement_value!r} claims a relationship to a prior "
            f"claim but names none in prior_refs"
        )
        raise AuthoredRecordError(message)
    return DerivedBehavior(
        behavior_id=require_str(raw, "behavior_id", context=context),
        library_id=require_str(raw, "library_id", context=context),
        profile_id=require_str(raw, "profile_id", context=context),
        packet_id=require_str(raw, "packet_id", context=context),
        claim=require_str(raw, "claim", context=context),
        mechanism=require_str(raw, "mechanism", context=context),
        conditions=_optional_strings(raw, "conditions", context=context),
        evidence_refs=evidence,
        prior_refs=_optional_strings(raw, "prior_refs", context=context),
        agreement=agreement,
        verification_level=VerificationLevel(
            require_str(raw, "verification_level", context=context)
        ),
        review_state=ReviewState(require_str(raw, "review_state", context=context)),
        open_question=str(raw.get("open_question") or ""),
    )


def load_derived_behaviors(
    library_id: str,
    profile_id: str,
    *,
    repository_root: Path,
) -> DerivationBatch:
    """Return the derived behaviors stored for one profile.

    Returns:
        The batch; empty when nothing has been derived yet.

    Raises:
        AuthoredRecordError: When the file declares an unexpected schema.

    """
    path = derived_path(library_id, profile_id, repository_root=repository_root)
    if not path.is_file():
        return DerivationBatch(library_id=library_id, profile_id=profile_id, behaviors=())
    context = f"derived behaviors {path}"
    document = require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), context=context)
    declared = require_str(document, "schema_version", context=context)
    if declared != _SCHEMA_VERSION:
        message = f"{context}: schema_version {declared!r} is not {_SCHEMA_VERSION!r}"
        raise AuthoredRecordError(message)
    behaviors = tuple(
        validate_proposal(
            require_mapping(item, context=f"{context}.behaviors[{position}]"),
            context=f"{context}.behaviors[{position}]",
        )
        for position, item in enumerate(require_sequence(document, "behaviors", context=context))
    )
    return DerivationBatch(
        library_id=library_id,
        profile_id=profile_id,
        behaviors=behaviors,
    )


def _optional_strings(
    raw: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> tuple[str, ...]:
    if key not in raw or raw[key] is None:
        return ()
    return require_str_sequence(raw, key, context=context)


def evidence_is_known(
    behaviors: Sequence[DerivedBehavior],
    known: frozenset[str],
) -> tuple[str, ...]:
    """Return evidence references that no packet actually offered.

    Returns:
        Unknown references, so a fabricated citation cannot pass review.

    """
    unknown: set[str] = set()
    for behavior in behaviors:
        unknown.update(ref for ref in behavior.evidence_refs if ref not in known)
    return tuple(sorted(unknown))
