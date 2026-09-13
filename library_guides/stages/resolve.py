"""Join documented behaviors to the extracted functionality inventory.

This is the stage the coverage matrix rests on. Without it the deep-dives
contribute nothing measurable: there is an API inventory on one side and an
authored guide on the other, with the documented behavior surface connected to
neither.

Resolution runs in ordered passes of decreasing certainty. The earlier passes
establish identity deterministically; the later ones only nominate candidates.
Every observation records which pass produced it, and a name that matches more
than one identity stays ambiguous rather than being silently collapsed - an
English sentence about "a table" must not become a binding to a class that
happens to be named ``Table``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from attrs import field, frozen

from library_guides.models.enums import (
    Ecosystem,
    EvidenceOrigin,
    ResolutionState,
)
from library_guides.models.records import Observation
from library_guides.models.spans import EvidenceSpan, LineRange

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from library_guides.adapters.docs.behaviors import Behavior, BehaviorIndex
    from library_guides.retrieve.index_build import LookupIndex

__all__ = [
    "PASS_ORDER",
    "ResolutionPass",
    "ResolveResult",
    "resolve_behaviors",
]


class ResolutionPass:
    """Named passes, in the order section 6.2 prescribes."""

    QUALIFIED_PATH = "qualified_path"
    QUALIFIED_ALIAS = "qualified_alias"
    REGISTERED_SURFACE = "registered_surface"
    SHORT_NAME_IN_SCOPE = "short_name_in_scope"
    SHORT_NAME_AMBIGUOUS = "short_name_ambiguous"


PASS_ORDER: Final = (
    ResolutionPass.QUALIFIED_PATH,
    ResolutionPass.QUALIFIED_ALIAS,
    ResolutionPass.REGISTERED_SURFACE,
    ResolutionPass.SHORT_NAME_IN_SCOPE,
    ResolutionPass.SHORT_NAME_AMBIGUOUS,
)

_ECOSYSTEM_SEPARATOR: Final = {Ecosystem.RUST: "::", Ecosystem.PYTHON: "."}


@frozen(kw_only=True)
class ResolveResult:
    """Observations joining behaviors to functionality, plus what stayed open."""

    observations: tuple[Observation, ...] = field()
    behaviors_total: int = field()
    behaviors_with_citation: int = field()
    behaviors_resolved: int = field()
    unresolved_identifiers: tuple[str, ...] = field(default=())

    def pass_counts(self) -> dict[str, int]:
        """Return how many observations each pass produced.

        Returns:
            Mapping of pass name to observation count.

        """
        counts: dict[str, int] = dict.fromkeys(PASS_ORDER, 0)
        for observation in self.observations:
            counts[observation.extractor_id] = counts.get(observation.extractor_id, 0) + 1
        return counts

    def summary(self) -> str:
        """Describe the join in one line.

        Returns:
            A short human-readable summary.

        """
        return (
            f"{len(self.observations):,} observations from "
            f"{self.behaviors_resolved:,}/{self.behaviors_with_citation:,} citing behaviors "
            f"({self.behaviors_total:,} total); "
            f"{len(self.unresolved_identifiers):,} identifiers unresolved"
        )


def _span_for(behavior: Behavior) -> EvidenceSpan:
    return EvidenceSpan(
        artifact_id=behavior.document_path,
        byte_start=behavior.byte_start,
        byte_end=behavior.byte_end,
        line_range=LineRange(start_line=behavior.start_line, end_line=behavior.end_line),
        enclosing_symbol=behavior.behavior_id,
        extraction_method="documentation_behavior_index",
    )


def _is_qualified(identifier: str, ecosystem: Ecosystem) -> bool:
    return _ECOSYSTEM_SEPARATOR[ecosystem] in identifier


def _leaf(identifier: str) -> str:
    return identifier.rsplit("::", 1)[-1].rsplit(".", 1)[-1]


def _classify(
    identifier: str,
    index: LookupIndex,
    ecosystem: Ecosystem,
) -> tuple[str, ResolutionState, tuple[str, ...]]:
    """Resolve one cited identifier through the ordered passes.

    Returns:
        The pass that matched, the resulting state, and the matched targets.

    """
    bindings, surfaces = index.lookup(identifier)
    if bindings:
        matched = tuple(sorted({binding.identity.public_path for binding in bindings}))
        pass_name = (
            ResolutionPass.QUALIFIED_PATH
            if _is_qualified(identifier, ecosystem)
            else ResolutionPass.QUALIFIED_ALIAS
        )
        return pass_name, ResolutionState.RESOLVED, matched
    if surfaces:
        matched = tuple(sorted({surface.identity.name for surface in surfaces}))
        return ResolutionPass.REGISTERED_SURFACE, ResolutionState.RESOLVED, matched

    near = index.suffix_matches(_leaf(identifier), limit=24)
    if not near:
        return ResolutionPass.SHORT_NAME_AMBIGUOUS, ResolutionState.UNRESOLVED, ()

    separator = _ECOSYSTEM_SEPARATOR[ecosystem]
    in_scope = tuple(
        candidate
        for candidate in near
        if separator in candidate or separator not in candidate.replace("::", ".")
    )
    scoped = (
        tuple(candidate for candidate in near if _matches_ecosystem(candidate, ecosystem))
        or in_scope
    )
    if len(scoped) == 1:
        return ResolutionPass.SHORT_NAME_IN_SCOPE, ResolutionState.CANDIDATE, scoped
    return ResolutionPass.SHORT_NAME_AMBIGUOUS, ResolutionState.AMBIGUOUS, tuple(near)


def _matches_ecosystem(candidate: str, ecosystem: Ecosystem) -> bool:
    if ecosystem is Ecosystem.RUST:
        return "::" in candidate
    return "::" not in candidate


def resolve_behaviors(
    indexes: Sequence[BehaviorIndex],
    index: LookupIndex,
    *,
    ecosystem_by_doc: Mapping[str, Ecosystem],
) -> ResolveResult:
    """Join every cited identifier in every behavior to the inventory.

    Args:
        indexes: Behavior indexes for the documents in scope.
        index: Exact-lookup index over the extracted inventories.
        ecosystem_by_doc: Which ecosystem each document's identifiers belong to,
            taken from the owning stack rather than guessed from the text.

    Returns:
        The join result.

    """
    observations: list[Observation] = []
    unresolved: set[str] = set()
    total = citing = resolved_behaviors = 0

    for behavior_index in indexes:
        ecosystem = ecosystem_by_doc.get(behavior_index.doc_id, Ecosystem.RUST)
        for behavior in behavior_index.behaviors:
            total += 1
            if not behavior.api_shaped_identifiers:
                continue
            citing += 1
            behavior_resolved = False
            for identifier in behavior.api_shaped_identifiers:
                pass_name, state, matched = _classify(identifier, index, ecosystem)
                if state is ResolutionState.RESOLVED:
                    behavior_resolved = True
                else:
                    unresolved.add(identifier)
                observations.append(
                    Observation(
                        observation_id=f"{behavior.behavior_id}#{identifier}",
                        library_id=behavior_index.doc_id,
                        subject=behavior.behavior_id,
                        predicate="documents_api",
                        object_value=matched[0] if matched else identifier,
                        evidence_origin=EvidenceOrigin.DOCUMENTATION_STATEMENT,
                        resolution_state=state,
                        extractor_id=pass_name,
                        scope=(behavior_index.document_path,),
                        competing_subjects=matched[1:] if len(matched) > 1 else (),
                        span=_span_for(behavior),
                    )
                )
            if behavior_resolved:
                resolved_behaviors += 1

    return ResolveResult(
        observations=tuple(observations),
        behaviors_total=total,
        behaviors_with_citation=citing,
        behaviors_resolved=resolved_behaviors,
        unresolved_identifiers=tuple(sorted(unresolved)),
    )
