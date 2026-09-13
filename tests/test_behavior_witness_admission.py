"""Actual Python execution through witness admission, warm reuse, and portable restoration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from attrs import evolve

from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorRequest,
    BehaviorSummary,
    Outcome,
)
from library_deep_enrichment.analyses.behavior.witness_contracts import (
    BehaviorWitnessCheck,
    BehaviorWitnessRequest,
    Cell,
    Input,
    Observation,
    ObservationSet,
)
from library_deep_enrichment.analyses.behavior.witness_service import validate
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import CONVERTER
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.staging import ObservationBuilder
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.contracts import FactArtifact
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.processes import execute
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.workflows.behavior import build as summarize
from library_deep_enrichment.workflows.behavior_witnesses import build as compare
from tests import test_behavior_python as python_controls

source_case = python_controls.source_case


def test_real_execution_checks_survive_warm_reuse_and_portable_restore(
    source_case: tuple[Path, FactArtifact], tmp_path: Path
) -> None:
    """A finite observed relation stays tied to its source, summary and exact output bytes."""
    root, artifact = source_case
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    reader = corpus.reader()
    owners = tuple(
        item
        for item in reader.records("native_facts")
        if isinstance(item, NativeFact)
        and item.kind == "definition"
        and item.symbol == "guarded_cleanup"
    )
    assert len(owners) == 1
    request = BehaviorRequest(
        logical_id="witness-control",
        profile=artifact.profile,
        owners=tuple(map(revision_of, owners)),
        artifacts=(owners[0].artifact,),
    )
    summarize(corpus, request)
    summary = next(
        item
        for item in corpus.reader().records("behavior_summaries")
        if isinstance(item, BehaviorSummary)
    )
    builder, witness = _observe(root, summary)
    Coordinator(corpus, WriterIdentity(principal="witness-control")).commit(
        tuple(builder.records.values()), expected=corpus.reader().manifest_id
    )
    assert summarize(corpus, request).reused
    first = compare(corpus, witness)
    assert not first.reused
    assert compare(corpus, witness).reused
    reader = corpus.reader()
    checks = tuple(reader.records("behavior_witness_checks"))
    assert len(checks) == 1
    checked = checks[0]
    assert isinstance(checked, BehaviorWitnessCheck)
    expected_count = 2
    assert checked.matched == expected_count
    assert checked.inconclusive == checked.disagreements == 0
    with pytest.raises(CorpusError, match="observation replay"):
        validate(reader, (evolve(checked, matched=0),))
    with pytest.raises(CorpusError, match="cannot bypass its stage owner"):
        Coordinator(corpus, WriterIdentity(principal="forged-check")).commit(
            (evolve(checked, matched=0),), expected=reader.manifest_id
        )
    exported = export_view(reader, tmp_path / "portable")
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, tmp_path / "portable") == exported.manifest
    assert tuple(restored.reader("release").records("behavior_witness_checks")) == checks


def _observe(
    root: Path, summary: BehaviorSummary
) -> tuple[ObservationBuilder, BehaviorWitnessRequest]:
    adapter = "import runpy,json,sys; f=runpy.run_path(sys.argv[1])['guarded_cleanup']; print(json.dumps([f(enabled=False),f(enabled=True)]))"
    result = execute(
        (sys.executable, "-c", adapter, str(root / "subject.py")), cwd=root, timeout=10
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    cases = tuple(
        Observation(
            case=str(index),
            summary=revision_of(summary),
            values=(
                Cell(kind="bool", scalar=str(bool(index)).lower()),
                Cell(kind="int", scalar=str(value)),
            ),
            inputs=(Input(parameter="enabled", value=0),),
            outcome=Outcome.RETURN,
            result=1,
            # This harness passes builtin False/True, whose truth operation cannot dispatch.
            assumptions=("python:ordinary_primitive:truth",),
        )
        for index, value in enumerate(observed)
    )
    builder = ObservationBuilder("ordinary-python-witness-control.v1")
    raw = builder.observe(
        "execution",
        {
            "observations": CONVERTER.unstructure(
                ObservationSet(
                    version="library-guides.behavior-observations.v1",
                    observations=cases,
                    seed=0,
                    generation="exhaustive boolean domain",
                )
            ),
            "execution": {
                "adapter": adapter,
                "stdout": result.stdout.decode(),
                "stderr": result.stderr.decode(),
                "returncode": result.returncode,
            },
        },
        profile=summary.profile,
        kind="concrete-witness",
    )
    witness = BehaviorWitnessRequest(
        logical_id="witness-check",
        profile=summary.profile,
        summaries=(revision_of(summary),),
        observations=builder.select(raw, "/observations", "finite-observations"),
        evidence=(builder.select(raw, "/execution", "actual-execution"),),
    )
    return builder, witness
