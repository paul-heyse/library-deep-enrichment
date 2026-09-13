"""Normalization budget failures retain exact owner membership and successful peers."""

from pathlib import Path

import pytest
from attrs import evolve

from library_deep_enrichment.analyses.behavior.contracts import BehaviorRequest, Limits
from library_deep_enrichment.analyses.behavior.coverage import BehaviorCoverage, State
from library_deep_enrichment.analyses.behavior.projection_budget import ProjectionBudgetError
from library_deep_enrichment.analyses.behavior.service import programs, validate
from library_deep_enrichment.analyses.characterization.contracts import (
    BehaviorCharacterization,
    CharacterizationRequest,
)
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.contracts import FactArtifact
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.workflows.behavior import build
from library_deep_enrichment.workflows.characterization import build as characterize
from tests import test_behavior_python as python_controls

source_case = python_controls.source_case


@pytest.mark.parametrize("term_limit", [1, 16])
def test_projection_exhaustion_replays_and_resumes_without_losing_denominator(
    source_case: tuple[Path, FactArtifact], tmp_path: Path, term_limit: int
) -> None:
    """One large function does not consume the projection budget of a small peer in its file."""
    root, artifact = source_case
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    names = {"final_override", "comprehension_nested"}
    owners = tuple(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact) and item.kind == "definition" and item.symbol in names
    )
    assert len(owners) == len(names)
    request = BehaviorRequest(
        logical_id="projection-budget",
        profile=artifact.profile,
        owners=tuple(sorted(map(revision_of, owners))),
        artifacts=(owners[0].artifact,),
        limits=Limits(terms=term_limit),
    )
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    reader = corpus.reader()
    outcomes = tuple(reader.records("behavior_coverage"))
    assert len(outcomes) == len(owners)
    exhausted = tuple(
        item
        for item in outcomes
        if isinstance(item, BehaviorCoverage) and item.phase == "normalization"
    )
    assert len(exhausted) == (len(owners) if term_limit == 1 else 1)
    for item in exhausted:
        assert item.state == State.EXHAUSTED
        assert not item.program
        assert not item.summary
        assert {metric.name: metric.value for metric in item.metrics} == {
            "projection_terms_attempted": term_limit + 1,
            "projection_terms_limit": term_limit,
        }
        with pytest.raises(CorpusError, match="retained-source replay"):
            validate(reader, (evolve(item, state=State.SUMMARIZED),))
    assert len(tuple(reader.records("behavior_programs"))) == len(owners) - len(exhausted)
    assert len(tuple(reader.records("behavior_summaries"))) == len(owners) - len(exhausted)
    with pytest.raises(ProjectionBudgetError):
        programs(reader, request)
    _restore_and_retry(corpus, request, tmp_path)


def _restore_and_retry(corpus: Corpus, request: BehaviorRequest, tmp_path: Path) -> None:
    characterize(
        corpus,
        CharacterizationRequest(
            logical_id="exhausted-owner-dimensions", behaviors=(revision_of(request),)
        ),
    )
    profiles = tuple(corpus.reader().records("behavior_characterizations"))
    assert len(profiles) == len(request.owners)
    for profile in profiles:
        assert isinstance(profile, BehaviorCharacterization)
        if not profile.program:
            assert not profile.costs
            assert profile.state == State.EXHAUSTED
            assert any(item.startswith("normalization_unavailable:") for item in profile.frontier)
    archive = tmp_path / "portable"
    exported = export_view(corpus.reader(), archive)
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, archive, head="analysis") == exported.manifest
    original = tuple(corpus.reader().records("behavior_coverage"))
    assert tuple(restored.reader().records("behavior_coverage")) == original
    assert tuple(restored.reader().records("behavior_characterizations")) == profiles
    assert not build(restored, evolve(request, limits=Limits())).reused
    assert not tuple(restored.reader().records("behavior_characterizations"))
    assert len(tuple(restored.reader().records("behavior_summaries"))) == len(request.owners)
    assert all(
        isinstance(item, BehaviorCoverage) and item.state == State.SUMMARIZED
        for item in restored.reader().records("behavior_coverage")
    )
    assert tuple(corpus.reader().records("behavior_coverage")) == original
