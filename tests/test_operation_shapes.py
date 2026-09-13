"""Contextual Rust call shapes preserve wrapper obligations through portable releases."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from attrs import evolve
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import LegacyRecord, Operation, TypeUse
from library_guides.corpus.declarations import normalize_declaration
from library_guides.corpus.encoding import canonical
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.native_admission import NativeBuilder
from library_guides.publication.export import export_view, import_view
from library_guides.publication.releases import publish
from library_guides.semantics.contracts import Task
from library_guides.semantics.shape_validation import validate_shapes
from library_guides.semantics.task_matching import compare
from library_guides.semantics.type_shapes import OperationShape, operation_shape
from library_guides.semantics.vocabulary import approve_rules, foundation
from library_guides.workflows import semantics, shapes

if TYPE_CHECKING:
    from pathlib import Path


def _fixture(root: Path) -> tuple[Corpus, Operation, tuple[TypeUse, ...]]:
    builder = NativeBuilder("shape-fixture")
    raw: dict[str, object] = {
        "symbol": "fixture::Object::project",
        "kind": "function",
        "signature": "fn project(self: &Self) -> Result<Self, Error>",
        "item": {
            "docs": "Returns a stream.",
            "inner": {
                "function": {
                    "sig": {
                        "inputs": [["self", {"borrowed_ref": {"type": {"generic": "Self"}}}]],
                        "output": {
                            "resolved_path": {
                                "path": "Result",
                                "id": 77,
                                "args": {
                                    "angle_bracketed": {
                                        "args": [
                                            {"type": {"generic": "Self"}},
                                            {"type": {"generic": "E"}},
                                        ]
                                    }
                                },
                            }
                        },
                    }
                }
            },
        },
        "type_occurrences": [
            {
                "path": "Self",
                "resolved_symbol": "fixture::Object",
                "role": "input",
                "position": 0,
                "direct": False,
                "selector": "json:/item/inner/function/sig/inputs/0/1/borrowed_ref/type",
            },
            {
                "path": "Result",
                "resolved_symbol": "core::result::Result",
                "role": "output",
                "position": 0,
                "direct": True,
                "selector": "json:/item/inner/function/sig/output",
            },
        ],
    }
    alias = LegacyRecord(
        logical_id="fixture-source",
        profile="fixture",
        artifact="artifact-A",
        legacy_id="fixture-project",
        kind="declaration",
        original=builder.blob(canonical(raw), "application/json"),
        normalized_family="",
        normalized_revision="",
    )
    builder.add(alias)
    normalize_declaration(builder, alias, raw, version="1")
    models = foundation()
    corpus = Corpus(root)
    Coordinator(corpus, WriterIdentity(principal="fixture-import", role="migration")).commit(
        (*builder.records.values(), *models), expected=""
    )
    Coordinator(corpus, WriterIdentity(principal="fixture-review", role="policy")).commit(
        approve_rules(models, authority="fixture-review", rationale="Controlled fixture grammar"),
        expected=corpus.reader().manifest_id,
    )
    operation = next(item for item in builder.records.values() if isinstance(item, Operation))
    uses = tuple(item for item in builder.records.values() if isinstance(item, TypeUse))
    return corpus, operation, uses


def test_self_keeps_borrow_result_and_artifact_scope(tmp_path: Path) -> None:
    """Substitution resolves the nominal, without deleting borrowing or Result obligations."""
    corpus, operation, uses = _fixture(tmp_path / "corpus")
    shape = operation_shape(corpus.reader(), operation, uses)
    borrowed = json.loads(shape.inputs[0].type_expression)["borrowed_ref"]["type"]["nominal"]
    assert borrowed["name"] == "fixture::Object"
    assert borrowed["scope"] == "artifact-A"
    result = json.loads(shape.outputs[0].type_expression)["nominal"]
    assert result["name"] == "core::result::Result"
    assert result["arguments"]["angle_bracketed"]["args"] == [
        {"type": {"generic": {"owner": revision_of(operation), "name": "Self"}}},
        {"type": {"generic": {"owner": revision_of(operation), "name": "E"}}},
    ]
    assert "77" not in shape.outputs[0].type_expression
    assert shape == operation_shape(corpus.reader(), operation, tuple(reversed(uses)))
    flattened = evolve(shape, inputs=(evolve(shape.inputs[0], type_expression="fixture::Object"),))
    with pytest.raises(CorpusError, match="differs from its exact declared types"):
        validate_shapes(corpus.reader(), (flattened,))


def test_conflicting_contexts_remain_unresolved(tmp_path: Path) -> None:
    """Identical names from two artifacts cannot win by producer iteration order."""
    corpus, operation, uses = _fixture(tmp_path / "corpus")
    conflict = evolve(uses[0], logical_id="conflicting-use", nominal_scope="artifact-B")
    candidates = (*uses, conflict)
    shape = operation_shape(corpus.reader(), operation, candidates)
    assert shape == operation_shape(corpus.reader(), operation, tuple(reversed(candidates)))
    assert any("Conflicting nominal resolutions" in item for item in shape.frontier)
    assert "nominal" not in json.loads(shape.inputs[0].type_expression)["borrowed_ref"]["type"]


def test_shaped_capability_release_replays_without_source_transport(tmp_path: Path) -> None:
    """Export must retain call shapes and their exact nominal/source prerequisites."""
    corpus, _, _ = _fixture(tmp_path / "corpus")
    assert not shapes.build(corpus).reused
    assert shapes.build(corpus).reused
    from library_guides.workflows.contracts import ExecutionReceipt

    execution = corpus.reader().lookup("stage_executions", "stage-execution:operation-shapes.v1")
    assert isinstance(execution, ExecutionReceipt)
    assert execution.rss_limit_bytes == 8 * 1024**3
    assert 0 < execution.peak_sampled_tree_rss_bytes <= execution.rss_limit_bytes
    semantics.build(corpus)
    task = Task(
        logical_id="shape-task",
        profile="fixture",
        profiles=("fixture",),
        goal="consume-results",
        requirements=(),
        context=(),
        inputs=(),
        preferences=(),
        description="Fixture",
    )
    universe, comparison = compare(corpus.reader(), task)
    Coordinator(corpus, WriterIdentity(principal="fixture-task")).commit(
        (task, universe, comparison), expected=corpus.reader().manifest_id
    )
    manifest = publish(corpus, comparison, expected="")
    export_view(corpus.reader("release"), tmp_path / "export")
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, tmp_path / "export") == manifest
    retained = tuple(restored.reader("release").records("operation_shapes"))
    assert len(retained) == 1
    assert isinstance(retained[0], OperationShape)
    assert retained[0].operation == revision_of(
        next(restored.reader("release").records("operations"))
    )
