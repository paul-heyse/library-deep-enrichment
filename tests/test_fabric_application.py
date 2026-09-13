"""The active CLI and application service cannot fall back to predecessor publication state."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from attrs import evolve
from typer.testing import CliRunner

from library_deep_enrichment.application import admit, page
from library_deep_enrichment.cli import app
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError, PredecessorConflictError
from library_deep_enrichment.corpus.contracts import Gap, Operation
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import run_stage

if TYPE_CHECKING:
    from pathlib import Path


def _operation(name: str) -> Operation:
    return Operation(
        logical_id=f"operation:{name}",
        profile="fixture",
        symbol=name,
        package="fixture",
        version="1",
        language="python",
        kind="function",
        signature="()",
        parameters=(),
        returns="",
        routes=(name,),
        resolution="fixture",
        evidence=(),
    )


def test_active_cli_uses_only_the_pinned_corpus_even_when_legacy_files_change(
    tmp_path: Path,
) -> None:
    """Changing YAML and SQLite generation files cannot change active inventory results."""
    corpus = Corpus(tmp_path)
    Coordinator(corpus, WriterIdentity(principal="test")).commit(
        (_operation("built_in"),), expected=""
    )
    runner = CliRunner()
    command = ["--corpus", str(tmp_path), "records", "operations"]
    first = runner.invoke(app, command)
    assert first.exit_code == 0, first.output
    (tmp_path / "knowledge.yaml").write_text("corrupt: [legacy\n")
    (tmp_path / "index.sqlite").write_bytes(b"not a database")
    (tmp_path / "build").mkdir()
    (tmp_path / "build/current.json").write_text('{"generation": "unrelated"}')
    second = runner.invoke(app, command)
    assert second.exit_code == 0
    assert json.loads(first.output) == json.loads(second.output)
    removed = runner.invoke(
        app, ["--corpus", str(tmp_path), "index-draft", str(tmp_path / "other.sqlite")]
    )
    assert removed.exit_code != 0
    assert "No such command" in removed.output


def test_authoring_predecessor_and_stage_output_ownership_are_enforced(tmp_path: Path) -> None:
    """A direct producer edit cannot leave an unchanged successful stage receipt behind."""
    corpus = Corpus(tmp_path)
    operation = _operation("built_in")
    first = admit(corpus, (operation,), authority="test-author", role="producer", expected="")
    stage = definition(
        "gap-projection", {"operations": ("/signature",)}, ("gaps",), ("application.py",)
    )
    gap = Gap(
        logical_id="gap:built_in",
        subject="built_in",
        predicate="metadata",
        reason="Unknown",
        next_evidence="witness",
        evidence=(),
    )
    run_stage(corpus, stage, lambda _: (gap,))
    with pytest.raises(PredecessorConflictError):
        admit(
            corpus, (_operation("new"),), authority="test-author", role="producer", expected=first
        )
    with pytest.raises(CorpusError, match="stage owner"):
        admit(
            corpus,
            (evolve(gap, reason="invented replacement"),),
            authority="test-author",
            role="producer",
            expected=corpus.reader().manifest_id,
        )


def test_family_page_reports_continuation_instead_of_claiming_a_complete_inventory(
    tmp_path: Path,
) -> None:
    """A page boundary is distinguishable from an exhausted selected family."""
    corpus = Corpus(tmp_path)
    admit(
        corpus,
        (_operation("one"), _operation("two")),
        authority="test",
        role="producer",
        expected="",
    )
    first = page(corpus.reader(), "operations", limit=1)
    second = page(corpus.reader(), "operations", limit=1, offset=1)
    assert first.next_offset == 1
    assert second.next_offset is None
    assert first.records[0] != second.records[0]
