"""Executable multi-table, authority, and byte-evidence counterexamples."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pytest
from attrs import evolve
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError, PredecessorConflictError
from library_deep_enrichment.corpus.contracts import ByteRange, Disposition, Job, Policy
from library_deep_enrichment.corpus.encoding import bytes_digest
from library_deep_enrichment.corpus.evidence import resolve, resolve_bytes, select, stage_blob
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus

if TYPE_CHECKING:
    from pathlib import Path


def _job(request: str, outcome: Disposition = Disposition.COMPLETE) -> Job:
    return Job(
        logical_id="extract:demo",
        profile="demo-1",
        stage="D0",
        request=request,
        inputs=(),
        universes=(),
        outputs=(),
        disposition=outcome,
        reason="observed outcome",
    )


def test_fresh_head_and_pinned_reader_do_not_mix_jobs(tmp_path: Path) -> None:
    """A failed new request replaces current success while old readers stay pinned."""
    corpus = Corpus(tmp_path / "fabric")
    writer = Coordinator(corpus, WriterIdentity(principal="extractor"))
    old = _job("old")
    first = writer.commit([old], expected="")
    pinned = corpus.reader()
    assert list(pinned.records("jobs")) == [old]
    assert pinned.get("jobs", revision_of(old)) == old
    failed = _job("new", Disposition.FAILED)
    second = writer.commit([failed], expected=first)
    assert first != second
    assert list(pinned.records("jobs")) == [old]
    assert list(corpus.reader().records("jobs")) == [failed]
    with pytest.raises(CorpusError, match="outside pinned membership"):
        corpus.reader().get("jobs", revision_of(old))
    with pytest.raises(PredecessorConflictError, match="stale"):
        writer.commit([old], expected=first)


def test_unchanged_small_transaction_does_not_scan_the_population(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reasserting a current request uses bounded point reads and performs no family writes."""
    from library_deep_enrichment.corpus.store import CorpusReader

    corpus = Corpus(tmp_path)
    writer = Coordinator(corpus, WriterIdentity(principal="test"))
    record = _job("same")
    first = writer.commit((record,), expected="")

    def unexpected_population_scan(_reader: CorpusReader, _family: str = "") -> None:
        pytest.fail("unchanged transaction enumerated the full population")

    monkeypatch.setattr(CorpusReader, "members", unexpected_population_scan)
    checkpoints = []
    assert writer.commit((record,), expected=first, checkpoint=checkpoints.append) == first
    assert checkpoints == []


def test_index_maintenance_retains_exact_membership_and_pinned_history(tmp_path: Path) -> None:
    """Fresh physical indexes do not promote unselected rows or change logical facts."""
    from library_deep_enrichment.corpus.backend import Backend

    corpus = Corpus(tmp_path / "fabric")
    writer = Coordinator(corpus, WriterIdentity(principal="index-maintainer"))
    first = writer.commit((_job("old"),), expected="")
    pinned = corpus.reader()
    current = _job("new")
    second = writer.commit((current,), expected=first)
    before = tuple(corpus.reader().members())
    maintained = writer.refresh_indexes(expected=second)
    assert maintained != second
    assert tuple(corpus.reader().members()) == before
    assert tuple(pinned.records("jobs")) == (_job("old"),)
    backend = Backend(corpus.root)
    for name in ("jobs", "memberships"):
        table = backend.table(name)
        statistics = [table.index_stats(index.name) for index in table.list_indices()]
        assert all(item is not None and item.num_unindexed_rows == 0 for item in statistics)
    with pytest.raises(CorpusError, match="outside pinned membership"):
        corpus.reader().get("jobs", revision_of(_job("old")))


def test_append_updates_index_deltas_without_rebuilding_existing_indexes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An append retains old versions and covers new rows without recreating an index."""
    from lancedb.table import LanceTable
    from library_deep_enrichment.corpus.backend import Backend

    corpus = Corpus(tmp_path / "fabric")
    writer = Coordinator(corpus, WriterIdentity(principal="index-maintainer"))
    first = writer.commit((_job("old"),), expected="")
    backend = Backend(corpus.root)
    versions = {name: backend.table(name).version for name in ("jobs", "memberships")}
    tags = {name: backend.table(name).tags.list() for name in versions}

    def unexpected_rebuild(_table: LanceTable, *_args: object, **_kwargs: object) -> None:
        pytest.fail("append recreated an existing scalar index")

    monkeypatch.setattr(LanceTable, "create_index", unexpected_rebuild)
    second = writer.commit((_job("new"),), expected=first)
    assert second != first
    assert tuple(corpus.reader().records("jobs")) == (_job("new"),)
    for name, version in versions.items():
        table = backend.table(name)
        assert set(tags[name]).issubset(table.tags.list())
        assert version in {entry["version"] for entry in table.list_versions()}
        for index in table.list_indices():
            statistics = table.index_stats(index.name)
            assert statistics is not None
            assert statistics.num_unindexed_rows == 0
        assert backend.table(name, version).count_rows() > 0


@pytest.mark.parametrize("crash_at", ["jobs", "memberships", "manifests"])
def test_crash_cannot_admit_orphan_rows(tmp_path: Path, crash_at: str) -> None:
    """Each durable write boundary leaves a coherent previous head after failure."""
    corpus = Corpus(tmp_path / "fabric")
    writer = Coordinator(corpus, WriterIdentity(principal="extractor"))
    first = writer.commit([_job("old")], expected="")

    def crash(stage: str) -> None:
        if stage == crash_at:
            message = "simulated coordinator death"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="simulated"):
        writer.commit([_job("new")], expected=first, checkpoint=crash)
    assert corpus.reader().manifest_id == first
    assert list(corpus.reader().records("jobs")) == [_job("old")]
    writer.commit([_job("new")], expected=first)
    assert list(corpus.reader().records("jobs")) == [_job("new")]


def test_exact_fields_and_original_bytes_are_inside_the_corpus(tmp_path: Path) -> None:
    """Original Unicode/CRLF evidence survives without a source file."""
    corpus = Corpus(tmp_path / "fabric")
    data = "\u03b1\r\nreturn value\r\n".encode()
    blob, chunks = stage_blob(io.BytesIO(data), media_type="text/plain")
    job = _job("x")
    Coordinator(corpus, WriterIdentity(principal="extractor")).commit(
        [*chunks, blob, job],
        expected="",
    )
    selection = select(job, "/request", "request")
    assert resolve(corpus.reader(), selection) == "x"
    with pytest.raises(CorpusError, match="digest mismatch"):
        resolve(corpus.reader(), evolve(selection, digest="forged"))
    byte_selection = ByteRange(
        blob=revision_of(blob),
        start=0,
        end=len(data),
        digest=bytes_digest(data),
    )
    assert resolve_bytes(corpus.reader(), byte_selection) == data


def test_producers_cannot_rewrite_policy(tmp_path: Path) -> None:
    """Coverage and approval authority are separate from extraction authority."""
    policy = Policy(
        logical_id="coverage",
        kind="coverage",
        subject="all-operations",
        authority="owner",
        rationale="independent scope",
        allowed_predicates=(),
        required_scopes=("all",),
    )
    corpus = Corpus(tmp_path / "fabric")
    with pytest.raises(CorpusError, match="independent policy"):
        Coordinator(corpus, WriterIdentity(principal="extractor")).commit([policy], expected="")
    Coordinator(corpus, WriterIdentity(principal="owner", role="policy")).commit(
        [policy], expected=""
    )
    assert list(corpus.reader().records("policies")) == [policy]
