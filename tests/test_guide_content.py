"""Authored guidance must be supported, comparative, and reversible."""

from __future__ import annotations

from pathlib import Path

import pytest
from library_deep_enrichment.decisions import DecisionBrief, load_decisions
from library_deep_enrichment.manifest import known_stack_ids
from library_deep_enrichment.models.enums import ReviewState
from library_deep_enrichment.obligations import load_obligations
from library_deep_enrichment.principles import load_principles
from library_deep_enrichment.retrieve.index_build import build_index

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _all_briefs() -> list[tuple[str, DecisionBrief]]:
    briefs: list[tuple[str, DecisionBrief]] = []
    for stack_id in known_stack_ids():
        briefs.extend(
            (stack_id, brief)
            for brief in load_decisions(stack_id, repository_root=REPOSITORY_ROOT).values()
        )
    return briefs


def test_the_pilot_authored_decision_briefs() -> None:
    """A vacuous pass over an empty brief set would prove nothing."""
    minimum_expected = 6
    assert len(_all_briefs()) >= minimum_expected


@pytest.mark.parametrize(("stack_id", "brief"), _all_briefs())
def test_an_accepted_brief_cites_evidence(stack_id: str, brief: DecisionBrief) -> None:
    """Acceptance without evidence is an opinion, however well written."""
    if brief.review_state is not ReviewState.ACCEPTED:
        return
    assert brief.evidence_refs, f"{stack_id}/{brief.decision_id} is accepted with no evidence"
    assert brief.is_publishable()


@pytest.mark.parametrize(("stack_id", "brief"), _all_briefs())
def test_a_brief_compares_at_least_two_candidates(stack_id: str, brief: DecisionBrief) -> None:
    """A brief with one option is a recommendation, not a decision."""
    minimum_candidates = 2
    assert len(brief.candidates) >= minimum_candidates, f"{stack_id}/{brief.decision_id}"


@pytest.mark.parametrize(("stack_id", "brief"), _all_briefs())
def test_a_brief_names_a_condition_that_would_reverse_it(
    stack_id: str, brief: DecisionBrief
) -> None:
    """Guidance that cannot be wrong cannot be checked."""
    assert brief.reversing_conditions, (
        f"{stack_id}/{brief.decision_id} names no reversing condition"
    )


@pytest.mark.parametrize(("stack_id", "brief"), _all_briefs())
def test_a_brief_only_cites_declared_principles(stack_id: str, brief: DecisionBrief) -> None:
    """A principle reference must resolve to a defined mechanism, not a tag."""
    principles = load_principles(repository_root=REPOSITORY_ROOT)
    unknown = [name for name in brief.principles if name not in principles]
    assert not unknown, f"{stack_id}/{brief.decision_id} cites undefined principles: {unknown}"


@pytest.mark.parametrize(("stack_id", "brief"), _all_briefs())
def test_a_brief_declares_a_known_family_kind(stack_id: str, brief: DecisionBrief) -> None:
    """Coverage obligations are resolved through the family kind."""
    obligations = load_obligations()
    assert brief.family_kind in obligations, f"{stack_id}/{brief.decision_id}"


def test_every_principle_states_a_limit() -> None:
    """A principle with no competing consideration is a slogan."""
    principles = load_principles(repository_root=REPOSITORY_ROOT)
    assert principles
    missing = [name for name, principle in principles.items() if not principle.limits]
    assert not missing, f"principles with no stated limit: {missing}"


def test_every_principle_states_its_mechanism() -> None:
    """'Why it works' is what makes a principle usable in a comparison."""
    principles = load_principles(repository_root=REPOSITORY_ROOT)
    missing = [name for name, principle in principles.items() if not principle.mechanism.strip()]
    assert not missing, f"principles with no mechanism: {missing}"


def test_candidate_apis_resolve_against_the_extracted_inventory() -> None:
    """A brief must not route an agent at an API the inventory has never seen."""
    index = build_index(known_stack_ids(), repository_root=REPOSITORY_ROOT)
    unresolved: list[str] = []
    for stack_id, brief in _all_briefs():
        for candidate in brief.candidates:
            bindings, surfaces = index.lookup(candidate.api)
            if bindings or surfaces:
                continue
            if index.suffix_matches(candidate.api.rsplit("::", 1)[-1].rsplit(".", 1)[-1]):
                continue
            unresolved.append(f"{stack_id}/{brief.decision_id} -> {candidate.api}")
    assert not unresolved, "brief candidates with no inventory match:\n" + "\n".join(unresolved)


def test_lookup_reports_absence_as_scoped_to_the_searched_inventory() -> None:
    """'Not found here' and 'does not exist' are different claims."""
    index = build_index(known_stack_ids(), repository_root=REPOSITORY_ROOT)
    bindings, surfaces = index.lookup("definitely::not::a::real::symbol")
    assert not bindings
    assert not surfaces
    total_bindings, _ = index.size()
    assert total_bindings > 0, "the index is empty, so absence would be meaningless"
