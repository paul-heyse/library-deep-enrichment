"""Exact compact dependency populations and admission-time denominator controls."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from attrs import evolve
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import Disposition, Gap, Job, Operation
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.workflows.contracts import FamilySelector, InputReceipt
from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import run_stage

if TYPE_CHECKING:
    from pathlib import Path


def _operation(profile: str) -> Operation:
    return Operation(
        logical_id="candidate",
        profile=profile,
        symbol="candidate",
        package="example",
        version="1",
        language="python",
        kind="function",
        signature="()",
        parameters=(),
        returns="str",
        routes=("candidate",),
        resolution="declared",
        evidence=(),
    )


def test_empty_population_and_other_profile_invalidation(tmp_path: Path) -> None:
    """The first matching candidate invalidates a previously empty scoped input."""
    corpus = Corpus(tmp_path / "corpus")
    stage = definition("sample", {"operations": ("/signature",)}, ("gaps",), ())
    selectors = (FamilySelector(family="operations", profiles=("selected",)),)
    gap = Gap(
        logical_id="empty",
        subject="",
        predicate="",
        reason="no selected input",
        next_evidence="acquire candidates",
    )
    run_stage(corpus, stage, lambda _: (gap,), selectors=selectors)
    before = corpus.reader()
    receipts = tuple(before.records("stage_input_receipts"))
    assert len(receipts) == 1
    assert isinstance(receipts[0], InputReceipt)
    assert receipts[0].count == 0
    writer = Coordinator(corpus, WriterIdentity(principal="fixture"))
    writer.commit((_operation("other"),), expected=before.manifest_id)
    assert run_stage(corpus, stage, lambda _: (), selectors=selectors).reused
    writer.commit((_operation("selected"),), expected=corpus.reader().manifest_id)
    job = corpus.reader().lookup("jobs", "sample")
    assert isinstance(job, Job)
    assert job.disposition == Disposition.PARTIAL
    assert not tuple(corpus.reader().records("gaps"))
    assert before.get("gaps", revision_of(gap)) == gap


def test_receipt_forgery_and_selected_source_replacement(tmp_path: Path) -> None:
    """Exact revisions matter even when the declared signature field did not change."""
    corpus = Corpus(tmp_path / "corpus")
    writer = Coordinator(corpus, WriterIdentity(principal="fixture"))
    operation = _operation("selected")
    writer.commit((operation,), expected="")
    stage = definition("sample", {"operations": ("/signature",)}, (), ())
    run_stage(corpus, stage, lambda _: ())
    receipt = next(corpus.reader().records("stage_input_receipts"))
    assert isinstance(receipt, InputReceipt)
    with pytest.raises(CorpusError):
        writer.commit((evolve(receipt, count=99),), expected=corpus.reader().manifest_id)
    writer.commit((evolve(operation, returns="bytes"),), expected=corpus.reader().manifest_id)
    assert not run_stage(corpus, stage, lambda _: ()).reused
    assert run_stage(corpus, stage, lambda _: ()).reused
