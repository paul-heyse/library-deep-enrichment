"""Observed prefixes survive worker faults without turning into admitted products."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest
from attrs import evolve
from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Gap, Job
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.contracts import Budget
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.worker_observations import failure_observations
from library_deep_enrichment.worker_runtime import WorkerRequest, run
from library_deep_enrichment.workflows.contracts import StageDefinition
from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import run_stage
from library_deep_enrichment.workflows.failure_records import FailureReceipt
from library_deep_enrichment.workflows.remote import BUDGET_EXIT

from tests.test_source_protocol import _stream

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader


def _worker(tmp_path: Path, fault: str) -> tuple[WorkerRequest, int]:
    header, body, terminal = _stream()
    stream = header + body + (terminal[:-1] if fault == "truncated" else b"")
    stream_path = tmp_path / "worker.frames"
    stream_path.write_bytes(stream)
    finish = "time.sleep(30)" if fault == "wall" else "sys.exit(75)"
    if fault == "truncated":
        finish = "sys.exit(0)"
    script = f"import pathlib,sys,time; sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes()); sys.stdout.buffer.flush(); {finish}"
    request = WorkerRequest(
        argv=(sys.executable, "-c", script, str(stream_path)),
        cwd=tmp_path,
        request_id="request",
        input_digest="input",
        budget=evolve(Budget(), wall_seconds=1),
    )
    return request, len(stream)


@pytest.mark.parametrize("fault", ["exit", "truncated", "wall", "callback", "interrupted"])
def test_worker_fault_records_transport_prefix_and_portable_recovery(
    tmp_path: Path, fault: str
) -> None:
    """The exact received denominator, original exception, and no-prefix admission survive."""
    corpus = Corpus(tmp_path / "corpus")
    stage = definition("observed-worker", {}, ("gaps",), ())
    request, output_bytes = _worker(tmp_path, fault)
    prefix = Gap(
        logical_id="prefix", subject="", predicate="", reason="private", next_evidence="none"
    )

    def produce(_: CorpusReader) -> Iterable[Record]:
        pending: list[Record] = []

        def consume(_: dict[str, object]) -> None:
            if fault in {"callback", "interrupted"}:
                message = "rejected by record consumer"
                if fault == "interrupted":
                    raise KeyboardInterrupt(message)
                raise CorpusError(message)
            pending.append(prefix)

        run(request, consume)
        return tuple(pending)

    with pytest.raises((CollectionError, CorpusError, KeyboardInterrupt)) as raised:
        run_stage(corpus, stage, produce)
    observations = failure_observations(raised.value)
    assert len(observations) == 1
    observation = observations[0]
    assert observation.expected_records == (1,)
    assert observation.delivered_records == 1
    assert observation.consumed_records == (0 if fault in {"callback", "interrupted"} else 1)
    assert observation.internal_progress == "unobserved"
    assert observation.output_bytes == output_bytes
    assert not observation.terminal_seen
    assert observation.elapsed_seconds > 0
    assert observation.rss_samples > 0
    if fault == "exit":
        assert observation.returncode == BUDGET_EXIT
    if fault == "truncated":
        assert observation.returncode == 0
    receipt = next(corpus.reader().records("stage_failures"))
    assert isinstance(receipt, FailureReceipt)
    assert receipt.worker == observations
    assert receipt.phase == "produce"
    assert receipt.collected_records == 0
    assert (
        receipt.coordinator_high_water_after_bytes
        >= receipt.coordinator_high_water_before_bytes
        > 0
    )
    assert not tuple(corpus.reader().records("gaps"))
    _reject_and_restore(corpus, receipt, prefix, tmp_path)


def _reject_and_restore(
    corpus: Corpus, receipt: FailureReceipt, prefix: Gap, tmp_path: Path
) -> None:
    observation = receipt.worker[0]
    writer = Coordinator(corpus, WriterIdentity(principal="negative-control"))
    mutations = (
        evolve(receipt, request="wrong-request"),
        evolve(receipt, worker=(evolve(observation, internal_progress="complete"),)),
        evolve(receipt, worker=(evolve(observation, consumed_records=2),)),
        evolve(receipt, collected_records=-1),
        evolve(receipt, phase="complete"),
    )
    for mutation in mutations:
        with pytest.raises(CorpusError):
            writer.commit((mutation,), expected=corpus.reader().manifest_id)
    archive = tmp_path / "failed-export"
    exported = export_view(corpus.reader(), archive)
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, archive, head="analysis") == exported.manifest
    assert restored.reader().get("stage_failures", revision_of(receipt)) == receipt
    failed = restored.reader().get("jobs", receipt.job)
    assert isinstance(failed, Job)
    assert not failed.outputs
    stage = restored.reader().get("stage_definitions", receipt.definition)
    assert isinstance(stage, StageDefinition)
    run_stage(restored, stage, lambda _: (prefix,))
    assert run_stage(restored, stage, lambda _: ()).reused
    assert not tuple(restored.reader().records("stage_failures"))
    assert tuple(restored.reader().records("gaps")) == (prefix,)


def test_unobserved_denominator_is_not_zero(tmp_path: Path) -> None:
    """A dead producer without a handshake supplies no internal or transport denominator."""
    request = WorkerRequest(
        argv=("/usr/bin/true",),
        cwd=tmp_path,
        request_id="request",
        input_digest="input",
        budget=Budget(),
    )
    with pytest.raises(CollectionError) as raised:
        run(request, lambda _: None)
    observation = failure_observations(raised.value)[0]
    assert observation.expected_records == ()
    assert observation.delivered_records == observation.consumed_records == 0
    assert observation.internal_progress == "unobserved"
