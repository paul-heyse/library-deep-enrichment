"""Reader for authored decision briefs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import yaml
from attrs import field, frozen

from library_guides.content import CONTENT_ROOT
from library_guides.models.enums import ReviewState
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

__all__ = ["Candidate", "DecisionBrief", "load_decisions"]

_SCHEMA_VERSION: Final = "library-guides.decisions.v1"


@frozen(kw_only=True)
class Candidate:
    """One option in a decision, with the exact API that exposes it."""

    candidate_id: str = field()
    summary: str = field()
    api: str = field()
    fits_when: str = field()


@frozen(kw_only=True)
class DecisionBrief:
    """The retrieval unit for a non-trivial choice."""

    decision_id: str = field()
    stack_id: str = field()
    use_case: str = field()
    family_kind: str = field()
    decisive_requirements: tuple[str, ...] = field()
    candidates: tuple[Candidate, ...] = field()
    comparison: str = field()
    principles: tuple[str, ...] = field()
    reversing_conditions: tuple[str, ...] = field()
    next_step: str = field()
    evidence_refs: tuple[str, ...] = field()
    review_state: ReviewState = field(default=ReviewState.NEEDS_REVIEW)

    @staticmethod
    def is_publishable() -> bool:
        """Return whether this brief may be rendered as accepted guidance.

        Legacy file citations do not carry v2 evidence selections or review digests.

        Returns:
            False; legacy records must be re-derived and reviewed in v2.

        """
        return False


def _candidates(raw: Sequence[object], *, context: str) -> tuple[Candidate, ...]:
    result: list[Candidate] = []
    for index, item in enumerate(raw):
        where = f"{context}.candidates[{index}]"
        mapping = require_mapping(item, context=where)
        result.append(
            Candidate(
                candidate_id=require_str(mapping, "id", context=where),
                summary=require_str(mapping, "summary", context=where),
                api=require_str(mapping, "api", context=where),
                fits_when=require_str(mapping, "fits_when", context=where),
            )
        )
    return tuple(result)


def load_decisions(stack_id: str, *, repository_root: Path) -> Mapping[str, DecisionBrief]:
    """Return every decision brief authored for one stack.

    Returns:
        Mapping of decision identifier to brief; empty when none are authored.

    Raises:
        AuthoredRecordError: When the file declares an unexpected schema.

    """
    path = repository_root / CONTENT_ROOT / "stacks" / stack_id / "decisions" / "decisions.yaml"
    if not path.is_file():
        return {}
    context = f"decisions {path}"
    document = require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), context=context)
    declared = require_str(document, "schema_version", context=context)
    if declared != _SCHEMA_VERSION:
        message = f"{context}: schema_version {declared!r} is not {_SCHEMA_VERSION!r}"
        raise AuthoredRecordError(message)
    briefs: dict[str, DecisionBrief] = {}
    for index, raw in enumerate(require_sequence(document, "decisions", context=context)):
        where = f"{context}.decisions[{index}]"
        mapping = require_mapping(raw, context=where)
        decision_id = require_str(mapping, "id", context=where)
        briefs[decision_id] = DecisionBrief(
            decision_id=decision_id,
            stack_id=stack_id,
            use_case=require_str(mapping, "use_case", context=where),
            family_kind=require_str(mapping, "family_kind", context=where),
            decisive_requirements=require_str_sequence(
                mapping, "decisive_requirements", context=where
            ),
            candidates=_candidates(
                require_sequence(mapping, "candidates", context=where), context=where
            ),
            comparison=require_str(mapping, "comparison", context=where),
            principles=require_str_sequence(mapping, "principles", context=where),
            reversing_conditions=require_str_sequence(
                mapping, "reversing_conditions", context=where
            ),
            next_step=require_str(mapping, "next_step", context=where),
            evidence_refs=require_str_sequence(mapping, "evidence_refs", context=where),
            review_state=ReviewState(require_str(mapping, "review_state", context=where)),
        )
    return briefs
