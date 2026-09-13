"""Reusable dimensions, independent execution, negative controls and portable admission."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from attrs import evolve

from library_deep_enrichment.analyses.behavior.contracts import BehaviorRequest, Limits
from library_deep_enrichment.analyses.characterization import costs
from library_deep_enrichment.analyses.characterization.contracts import (
    BehaviorCharacterization,
    CharacterizationRequest,
)
from library_deep_enrichment.analyses.characterization.service import validate
from library_deep_enrichment.corpus.backend import BudgetExceededError, CorpusError
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.contracts import FactArtifact
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.processes import execute
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.workflows.behavior import build as build_behavior
from library_deep_enrichment.workflows.characterization import build
from tests import test_behavior_python as python_controls

source_case = python_controls.source_case
programs = python_controls.programs


def _concrete(root: Path) -> dict:
    script = """import runpy,json,sys
m=runpy.run_path(sys.argv[1]); f=m['ambient_result']; before=f(); f.__globals__['AMBIENT_FLAG']=42; after=f()
class Target: pass
t=Target(); m['shared_assignment'](t)
print(json.dumps(dict(ambient=[before,after],extent=[len(m['retained_extent'](v)) for v in ([],[1],[1,2,3])],written=t.value)))
"""
    result = execute((sys.executable, "-c", script, str(root / "subject.py")), cwd=root, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_admitted_dimensions_preserve_actual_dependencies_and_unknowns(
    source_case: tuple[Path, FactArtifact], tmp_path: Path
) -> None:
    """Shared analysis derives binding effects, symbolic region extent and write obligations."""
    root, artifact = source_case
    concrete = _concrete(root)
    assert concrete == {"ambient": [17, 42], "extent": [0, 1, 3], "written": 3}
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    names = {
        "ambient_result",
        "retained_extent",
        "shared_assignment",
        "final_override",
        "comprehension_nested",
    }
    owners = tuple(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact) and item.kind == "definition" and item.symbol in names
    )
    behavior = BehaviorRequest(
        logical_id="characterization-input",
        profile=artifact.profile,
        owners=tuple(sorted(map(revision_of, owners))),
        artifacts=(owners[0].artifact,),
        limits=Limits(clauses=1000),
    )
    build_behavior(corpus, behavior)
    request = CharacterizationRequest(
        logical_id="independent-dimensions", behaviors=(revision_of(behavior),)
    )
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    records = {
        item.owner: item
        for item in corpus.reader().records("behavior_characterizations")
        if isinstance(item, BehaviorCharacterization)
    }
    assert set(records) == set(behavior.owners)
    profiles = {owner.symbol: records[revision_of(owner)] for owner in owners}
    ambient = profiles["ambient_result"]
    assert any(
        source.kind == "module_binding"
        and source.name == "AMBIENT_FLAG"
        and any(use.kind == "result" for use in source.uses)
        for source in ambient.dependencies
    )
    assert not profiles["final_override"].dependencies
    assert any(
        "values" in item.argument_dependencies for item in profiles["retained_extent"].resources
    )
    assert any(item.kind == "memory_write" for item in profiles["shared_assignment"].ordering)
    assert any(not item.upper for item in profiles["comprehension_nested"].costs)
    assert all("purity" in " ".join(item.frontier) for item in profiles.values())
    with pytest.raises(CorpusError, match="admitted evidence replay"):
        validate(corpus.reader(), (evolve(ambient, dependencies=()),))
    with pytest.raises(BudgetExceededError):
        build(corpus, evolve(request, logical_id="undersized-characterization", max_work=1))
    assert {
        item.owner
        for item in corpus.reader().records("behavior_characterizations")
        if isinstance(item, BehaviorCharacterization)
    } == set(records)
    _portable(corpus, tmp_path, request)


def _portable(corpus: Corpus, tmp_path: Path, request: CharacterizationRequest) -> None:
    archive = tmp_path / "portable"
    exported = export_view(corpus.reader(), archive)
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, archive, head="analysis") == exported.manifest
    assert tuple(restored.reader().records("behavior_characterizations")) == tuple(
        corpus.reader().records("behavior_characterizations")
    )
    assert build(restored, request).reused


def test_local_cost_scope_survives_names_and_rejects_cycle_bounds(programs: dict) -> None:
    """Display spelling does not change bounds; cyclic traversals retain an explicit obligation."""
    straight = programs["final_override"]
    assert costs.analyze(straight) == costs.analyze(evolve(straight, symbol="renamed"))
    bounds = costs.analyze(straight)
    assert all(item.upper and item.lower == 0 for item in bounds)
    assert any("callee" in " ".join(item.frontier) for item in bounds)
    assert all(not item.upper for item in costs.analyze(programs["comprehension_nested"]))
