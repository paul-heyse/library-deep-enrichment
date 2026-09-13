"""Failed producers retain their exact selected denominator without admitting any prefix."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from attrs import evolve
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import BudgetExceededError, CorpusError
from library_deep_enrichment.corpus.contracts import Disposition, Gap, Job
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.workflows.contracts import FamilySelector, InputReceipt
from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import run_stage
from library_deep_enrichment.workflows.failure_records import FailureReceipt

from tests.test_stage_inputs import _operation

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader


def _portable_failure(
    corpus: Corpus, destination: Path, failed: Job, receipt: InputReceipt
) -> None:
    archive = destination / "failed-portable"
    exported = export_view(corpus.reader(), archive)
    restored = Corpus(destination / "restored")
    assert import_view(restored, archive) == exported.manifest
    reader = restored.reader("release")
    assert reader.get("jobs", revision_of(failed)) == failed
    assert reader.get("stage_input_receipts", revision_of(receipt)) == receipt
    observation = next(corpus.reader().records("stage_failures"))
    assert isinstance(observation, FailureReceipt)
    assert observation.phase == "collect"
    assert observation.collected_records == 1
    assert observation.collected_payload_bytes > 0
    assert observation.job == revision_of(failed)
    assert not observation.worker
    assert reader.get("stage_failures", revision_of(observation)) == observation


def _portable_resumed(corpus: Corpus, destination: Path) -> None:
    assert not tuple(corpus.reader().records("stage_failures"))
    archive = destination / "resumed-portable"
    exported = export_view(corpus.reader(), archive)
    assert import_view(Corpus(destination / "resumed-restored"), archive) == exported.manifest


@pytest.mark.parametrize("error", [CorpusError, BudgetExceededError, KeyboardInterrupt])
def test_failed_prefix_retains_inputs_and_resumes_without_duplicate_admission(
    tmp_path: Path, error: type[BaseException]
) -> None:
    """Normal failures, budget rejection and interruption preserve exact recovery evidence."""
    corpus = Corpus(tmp_path / "corpus")
    operations = (_operation("selected"), evolve(_operation("other"), logical_id="unrelated"))
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit(operations, expected="")
    stage = definition("failure-input-control", {"operations": ("/signature",)}, ("gaps",), ())
    selectors = (FamilySelector(family="operations", profiles=("selected",)),)
    original = Gap(
        logical_id="original",
        subject="",
        predicate="",
        reason="first result",
        next_evidence="collect",
    )
    success = run_stage(corpus, stage, lambda _: (original,), selectors=selectors)
    previous = corpus.reader()
    prior_job = previous.lookup("jobs", stage.logical_id)
    assert isinstance(prior_job, Job)
    Coordinator(corpus, WriterIdentity(principal="fixture-change")).commit(
        (evolve(operations[0], signature="(changed_argument)"),), expected=previous.manifest_id
    )
    changed = evolve(stage, implementation="different-producer-context")
    prefix = evolve(original, logical_id="unadmitted-prefix")

    def failing(_: CorpusReader) -> Iterable[Record]:
        yield prefix
        message = "controlled failure after an emitted prefix"
        raise error(message)

    with pytest.raises(error, match="controlled failure"):
        run_stage(corpus, changed, failing, selectors=selectors)
    failed = corpus.reader().lookup("jobs", stage.logical_id)
    assert isinstance(failed, Job)
    assert failed.disposition == Disposition.FAILED
    assert failed.previous_success == revision_of(prior_job)
    assert not failed.outputs
    assert {item.family for item in failed.inputs} == {"stage_definitions", "stage_input_receipts"}
    receipt = corpus.reader().get(
        "stage_input_receipts",
        next(item.revision for item in failed.inputs if item.family == "stage_input_receipts"),
    )
    assert isinstance(receipt, InputReceipt)
    assert receipt.selector == selectors[0]
    assert receipt.count == 1
    assert receipt.definition == revision_of(changed)
    assert not tuple(corpus.reader().records("gaps"))
    assert previous.manifest_id == success.manifest
    assert previous.get("gaps", revision_of(original)) == original
    _portable_failure(corpus, tmp_path, failed, receipt)
    with pytest.raises(error, match="controlled failure"):
        run_stage(corpus, changed, failing, selectors=selectors)
    retried = corpus.reader().lookup("jobs", stage.logical_id)
    assert isinstance(retried, Job)
    assert retried.previous_success == revision_of(prior_job)
    resumed = run_stage(corpus, changed, lambda _: (original,), selectors=selectors)
    assert not resumed.reused
    assert run_stage(corpus, changed, lambda _: (), selectors=selectors).reused
    assert tuple(corpus.reader().records("gaps")) == (original,)
    _portable_resumed(corpus, tmp_path)


def test_first_failure_retains_an_empty_candidate_catalog(tmp_path: Path) -> None:
    """A failed first run preserves the exact zero denominator; no success stage is required."""
    corpus = Corpus(tmp_path / "corpus")
    stage = definition("first-failure", {"operations": ("/signature",)}, (), ())

    def failing(_: CorpusReader) -> Iterable[Record]:
        message = "first attempt failed"
        raise CorpusError(message)

    with pytest.raises(CorpusError, match="first attempt"):
        run_stage(corpus, stage, failing)
    failed = corpus.reader().lookup("jobs", stage.logical_id)
    assert isinstance(failed, Job)
    assert failed.disposition == Disposition.FAILED
    receipt = corpus.reader().get(
        "stage_input_receipts",
        next(item.revision for item in failed.inputs if item.family == "stage_input_receipts"),
    )
    assert isinstance(receipt, InputReceipt)
    assert receipt.count == 0
    assert not failed.previous_success
