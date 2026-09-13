"""Adversarial discovery, positive-support closure, and real analytical runtime controls."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from attrs import evolve

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Disposition, Job, Operation
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.discovery.contracts import (
    Attribute,
    Concept,
    EmbeddingRecipe,
    GraphNode,
)
from library_deep_enrichment.discovery.embeddings import validate_vector
from library_deep_enrichment.discovery.fca import SupportContext
from library_deep_enrichment.discovery.graphs import project_graphs
from library_deep_enrichment.discovery.search import search
from library_deep_enrichment.semantics.relational import evaluate
from library_deep_enrichment.workflows.discovery import build_retrieval
from library_deep_enrichment.workflows.engine import run_stage

if TYPE_CHECKING:
    from pathlib import Path


def _source(name: str) -> Operation:
    return Operation(
        logical_id=f"op:{name}",
        profile="context",
        symbol=name,
        package="sample",
        version="1",
        language="python",
        kind="function",
        signature="(value)",
        parameters=(),
        returns="Object",
        routes=(name,),
        resolution="declared",
        evidence=(),
    )


def _corpus(tmp_path: Path) -> Corpus:
    corpus = Corpus(tmp_path / "corpus")
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit(
        (_source("decode"), _source("unrelated")), expected=""
    )
    return corpus


def test_real_souffle_positive_join_and_recursive_cycle() -> None:
    """The installed rule worker preserves recursion and never fills a missing owner relation."""
    reachable = evaluate("reachability", {"Edge": [(0, 1), (1, 2), (2, 1)]}, "Reach")
    assert (0, 2) in reachable
    assert (2, 2) in reachable
    assert (2, 0) not in reachable
    facts = {
        "Source": [(0, 0, 1, 0), (1, 0, 2, 0)],
        "Model": [(0, 0)],
        "Operation": [(1, 0), (2, 1)],
    }
    assert evaluate("owner_rules", facts, "Candidate") == ((0, 0, 1),)


def test_fca_closure_records_support_not_negative_truth() -> None:
    """Closure is exact for a positive incidence relation with an unknown-only isolate."""
    attributes = tuple(
        Attribute(
            logical_id=name,
            predicate=name,
            value_digest=digest("yes"),
            condition="",
            interpretation="upstream_contract",
            quantifier="contract",
            domain="selected",
            phase="declared",
        )
        for name in ("a", "b")
    )
    context = SupportContext(
        objects=("first", "both", "unknown"),
        attributes=attributes,
        support=(),
        matrix=((True, False), (True, True), (False, False)),
    )
    first = (revision_of(attributes[0]),)
    extent, intent = context.closure(first)
    assert extent == ("first", "both")
    assert intent == first
    assert context.closure(intent) == (extent, intent)
    assert context.closure(())[0] == context.objects


def test_graph_projection_retains_isolates_and_discovery_sources(tmp_path: Path) -> None:
    """Real graph algorithms retain disconnected operations in every projection."""
    corpus = _corpus(tmp_path)
    assert not build_retrieval(corpus).reused
    assert build_retrieval(corpus).reused
    products = tuple(project_graphs(corpus.reader()))
    nodes = [item for item in products if isinstance(item, GraphNode)]
    communities = [item for item in products if isinstance(item, Concept)]
    assert len(nodes) == len({"structural", "semantic", "fused"}) * len({"decode", "unrelated"})
    assert all(len(item.members) == 1 for item in communities)
    result = search(corpus.reader(), "decode")
    assert result.eligible == len({"decode", "unrelated"})
    assert result.hits[0].subject == revision_of(_source("decode"))
    assert result.hits[0].channels == ("lexical",)
    assert result.hits[0].support


def test_new_competitor_invalidates_stage_but_pinned_view_survives(tmp_path: Path) -> None:
    """A source population addition invalidates outputs even when previously cited rows do not change."""
    corpus = _corpus(tmp_path)
    build_retrieval(corpus)
    before = corpus.reader()
    Coordinator(corpus, WriterIdentity(principal="new-competitor")).commit(
        (_source("decode_incremental"),), expected=before.manifest_id
    )
    assert len(tuple(before.records("retrieval_units"))) == len({"decode", "unrelated"})
    assert not tuple(corpus.reader().records("retrieval_units"))
    stale = corpus.reader().lookup("jobs", "retrieval-units.v1")
    assert isinstance(stale, Job)
    assert stale.disposition == Disposition.PARTIAL
    assert not build_retrieval(corpus).reused
    assert len(tuple(corpus.reader().records("retrieval_units"))) == len(
        {"decode", "unrelated", "decode_incremental"}
    )


def test_failed_changed_stage_cannot_reuse_previous_success(tmp_path: Path) -> None:
    """A new producer failure becomes current and atomically withdraws prior owned outputs."""
    corpus = _corpus(tmp_path)
    build_retrieval(corpus)
    definition = corpus.reader().lookup("stage_definitions", "retrieval-units.v1")
    from library_deep_enrichment.workflows.contracts import StageDefinition

    assert isinstance(definition, StageDefinition)
    changed = evolve(definition, implementation="changed-producer")

    def fail(_reader: object) -> tuple:
        message = "intentional finite worker failure"
        raise CorpusError(message)

    with pytest.raises(CorpusError, match="intentional"):
        run_stage(corpus, changed, fail)
    assert not tuple(corpus.reader().records("retrieval_units"))
    job = corpus.reader().lookup("jobs", "retrieval-units.v1")
    assert isinstance(job, Job)
    assert job.disposition == Disposition.FAILED


def test_embedding_recipe_roundtrip_and_numerical_rejection(tmp_path: Path) -> None:
    """Model identity survives Arrow admission; malformed and wrong-space vectors are rejected."""
    corpus = _corpus(tmp_path)
    recipe = EmbeddingRecipe(
        logical_id="numerical-test",
        model="test",
        model_revision="commit",
        tokenizer="test",
        tokenizer_revision="commit",
        dimension=2,
        dtype="float32",
        pooling="last",
        normalization="l2",
        max_tokens=32,
        document_prefix="",
        query_template="{query}",
        runtime="test-validation-only",
    )
    Coordinator(corpus, WriterIdentity(principal="recipe")).commit(
        (recipe,), expected=corpus.reader().manifest_id
    )
    assert corpus.reader().get("embedding_recipes", revision_of(recipe)) == recipe
    assert validate_vector([1.0, 0.0], recipe) == (1.0, 0.0)
    for invalid in ([0.0, 0.0], [1.0], [float("nan"), 0.0], [True, 0.0]):
        with pytest.raises(CorpusError):
            validate_vector(invalid, recipe)


def test_cli_retains_lexical_results_when_runtime_initialization_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable local snapshot must not block the independently usable corpus."""
    import json

    from typer.testing import CliRunner

    from library_deep_enrichment.cli import app

    corpus = _corpus(tmp_path)
    build_retrieval(corpus)

    def unavailable(_config: object) -> None:
        message = "missing tokenizer snapshot"
        raise OSError(message)

    monkeypatch.setattr("library_deep_enrichment.runtime.embedding_client", unavailable)
    result = CliRunner().invoke(
        app,
        [
            "--corpus",
            str(corpus.root),
            "--runtime-root",
            str(tmp_path),
            "discover",
            "decode",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["hits"][0]["subject"] == revision_of(_source("decode"))
    assert "initialization failed: OSError" in data["frontier"][0]
