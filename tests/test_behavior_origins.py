"""Source-point lineage, equal values, exact replay, and bounded origin acquisition."""

from pathlib import Path

import pytest
from attrs import evolve
from library_guides.analyses.behavior.contracts import BehaviorProgram, BehaviorRequest, Limits
from library_guides.analyses.behavior.coverage import BehaviorCoverage, State, analyze
from library_guides.analyses.behavior.engine import Interpreter
from library_guides.analyses.behavior.origins import BehaviorOrigins
from library_guides.analyses.behavior.service import validate
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.native_contracts import NativeFact
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.facts.contracts import FactArtifact
from library_guides.native_admission import NativeInputs, admit_artifacts
from library_guides.publication.export import export_view, import_view
from library_guides.workflows.behavior import build

from tests import test_behavior_python as python_controls
from tests.test_behavior_comprehensions import execute_script
from tests.test_behavior_engine import builder

source_case = python_controls.source_case
programs = python_controls.programs


def test_source_subscriptions_retain_distinct_evaluated_operands(
    programs: dict[str, BehaviorProgram], source_case: tuple[Path, FactArtifact]
) -> None:
    """Two protocol operations keep their exact source points and pre-operation operands."""
    actual = execute_script(
        "log=[]\nclass Subject:\n"
        " def __getitem__(self,key):\n  log.append(key)\n  return ('first','second')[key]\n"
        "result=m['two_subscriptions'](Subject())\nprint(json.dumps([log,result]))"
    )
    assert actual == [[0, 1], ["first", "second"]]
    program = programs["two_subscriptions"]
    interpreter = Interpreter(Limits())
    summary = interpreter.summarize(program)
    origins = interpreter.origins.record(summary)
    points = {item.index: item for item in program.instructions}
    source = (source_case[0] / "subject.py").read_bytes()
    observed = set()
    for entry in origins.entries:
        if entry.operation == "index" and entry.mode == "ordinary_evaluation":
            point = points[entry.instruction]
            assert entry.program == revision_of(program)
            key = summary.terms[entry.arguments[1]]
            assert key.op == "literal"
            observed.add((source[point.start : point.end].decode(), key.value))
    assert observed == {("container[0]", "0"), ("container[1]", "1")}
    assert summary.frontier  # Origins do not close protocol dispatch or effects.


def test_value_interning_does_not_erase_distinct_assignment_origins(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Identical scalar values can have multiple independently retained source origins."""
    program = programs["two_equal_assignments"]
    interpreter = Interpreter(Limits())
    summary = interpreter.summarize(program)
    entries = [
        item
        for item in interpreter.origins.record(summary).entries
        if item.mode == "assignment" and item.operation == "literal"
    ]
    expected = 2
    assert len({item.instruction for item in entries}) == expected
    assert len({item.result for item in entries}) == 1
    assert execute_script("print(json.dumps(m['two_equal_assignments']()))") == [1, 1]


def test_origin_forgery_is_rejected_and_portable_closure_preserves_contexts(
    source_case: tuple[Path, FactArtifact], tmp_path: Path
) -> None:
    """Origins remain checked analysis consequences tied to the exact source and summary."""
    root, artifact = source_case
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    names = {"two_subscriptions", "two_equal_assignments"}
    owners = tuple(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact) and item.kind == "definition" and item.symbol in names
    )
    assert len(owners) == len(names)
    request = BehaviorRequest(
        logical_id="origin-controls",
        profile=artifact.profile,
        owners=tuple(sorted(map(revision_of, owners))),
        artifacts=(owners[0].artifact,),
    )
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    reader = corpus.reader()
    origins = tuple(reader.records("behavior_origins"))
    assert len(origins) == len(names)
    original = origins[0]
    assert isinstance(original, BehaviorOrigins)
    assert original.entries
    forged = evolve(
        original, entries=(evolve(original.entries[0], result=-1), *original.entries[1:])
    )
    with pytest.raises(CorpusError, match="retained-source replay"):
        validate(reader, (forged,))
    exported = export_view(reader, tmp_path / "portable")
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, tmp_path / "portable") == exported.manifest
    assert tuple(restored.reader("release").records("behavior_origins")) == origins


def test_origin_budget_failure_does_not_publish_incomplete_provenance() -> None:
    """A small value domain with many source points still has a bounded provenance cost."""
    graph = builder("repeated-value-sites")
    value = graph.term("literal", value="1", ty="python:int")
    for index in range(10):
        graph.emit("assign", destination="local:" + str(index), value=value)
    graph.emit("return", value=value)
    records = analyze((graph.finish(()),), {}, Limits(terms=1))
    assert len(records) == 1
    outcome = records[0]
    assert isinstance(outcome, BehaviorCoverage)
    assert outcome.state == State.EXHAUSTED
    assert outcome.phase == "interpretation"
    assert "value origin budget" in outcome.detail
    assert not outcome.summary
