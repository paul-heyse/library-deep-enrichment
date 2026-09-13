"""Batched reads retain exact historical and proposed membership boundaries."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, Unpack

import pytest
from attrs import evolve
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import Backend, CorpusError
from library_guides.corpus.contracts import Disposition, Job, Member, Operation
from library_guides.corpus.evidence import select
from library_guides.corpus.schemas import REGISTRY, revision_of
from library_guides.corpus.sequence_pages import SequenceRequest
from library_guides.corpus.sequence_pages import read as read_sequence
from library_guides.corpus.store import Corpus
from library_guides.corpus.validation import AdmissionReader, validate_records
from library_guides.publication.closure import evidence_closure
from library_guides.semantics.contracts import Task
from library_guides.semantics.task_matching import compare

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader

QUERY_WINDOW_CEILING = 100


class ScanOptions(TypedDict, total=False):
    """Preserve the real scanner's keyword contract while counting physical reads."""

    version: int | None
    where: str
    columns: list[str] | None
    limit: int


def _job(name: str) -> Job:
    return Job(
        logical_id=name,
        stage="fixture",
        request="first",
        inputs=(),
        universes=(),
        outputs=(),
        disposition=Disposition.COMPLETE,
        reason="fixture",
    )


def test_batch_preserves_order_duplicates_and_pinned_history(tmp_path: Path) -> None:
    """A warmed historical reader cannot acquire the current replacement or an orphan."""
    corpus = Corpus(tmp_path)
    writer = Coordinator(corpus, WriterIdentity(principal="fixture"))
    first, other = _job("first"), _job("other")
    writer.commit((first, other), expected="")
    pinned = corpus.reader()
    requested = (revision_of(other), revision_of(first), revision_of(other))
    assert tuple(pinned.get_many("jobs", requested)) == (other, first, other)
    changed = evolve(first, request="second")
    writer.commit((changed,), expected=pinned.manifest_id)
    assert tuple(pinned.get_many("jobs", requested)) == (other, first, other)
    with pytest.raises(CorpusError, match="outside pinned membership"):
        tuple(pinned.get_many("jobs", (revision_of(changed),)))
    with pytest.raises(CorpusError, match="outside pinned membership"):
        tuple(corpus.reader().get_many("jobs", requested))
    assert tuple(pinned.filtered_records("jobs", (("logical_id", "first"),))) == (first,)
    assert tuple(corpus.reader().filtered_records("jobs", (("logical_id", "first"),))) == (changed,)
    assert tuple(corpus.reader().filtered_records("jobs", (("request", "first"),))) == (other,)
    assert tuple(corpus.reader().filtered_records("jobs", (("logical_id", "' OR true --"),))) == ()
    with pytest.raises(CorpusError, match="registered text columns"):
        tuple(pinned.filtered_records("jobs", (("unknown_column", "first"),)))


def test_validation_batches_evidence_selections_across_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Many independent source supports use bounded windows, not one read per output."""
    corpus = Corpus(tmp_path)
    sources = tuple(_job(str(index)) for index in range(260))
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit(sources, expected="")
    reader = corpus.reader()
    original = type(reader).get_many
    cold_reads = []

    def tracked(self: CorpusReader, family: str, revisions: Iterable[str]) -> Iterator[Record]:
        keys = tuple(revisions)
        if family == "jobs" and any(self._cache.get((family, key)) is None for key in keys):
            cold_reads.append(len(keys))
        yield from original(self, family, keys)

    monkeypatch.setattr(type(reader), "get_many", tracked)
    operations = tuple(
        Operation(
            logical_id=f"operation:{source.logical_id}",
            symbol=f"sample.{source.logical_id}",
            package="sample",
            version="1",
            language="python",
            kind="function",
            signature="()",
            parameters=(),
            returns="",
            routes=(),
            resolution="unresolved",
            evidence=(select(source, "/reason", "fixture"),),
        )
        for source in sources
    )
    validate_records(reader, operations)
    assert cold_reads == [128, 128, 4]


def test_wide_comparisons_do_not_issue_per_candidate_point_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A shared population larger than the cache remains exact and uses finite windows."""
    corpus = Corpus(tmp_path)
    operations = tuple(
        Operation(
            logical_id=f"operation:{index}",
            profile="wide",
            symbol=f"sample.{index}",
            package="sample",
            version="1",
            language="python",
            kind="function",
            signature="()",
            parameters=(),
            returns="",
            routes=(),
            resolution="unresolved",
            evidence=(),
        )
        for index in range(3000)
    )
    writer = Coordinator(corpus, WriterIdentity(principal="fixture"))
    writer.commit(operations, expected="")
    task = Task(
        logical_id="first",
        profile="wide",
        profiles=("wide",),
        goal="unmodeled",
        requirements=(),
        context=(),
        inputs=(),
        preferences=(),
        description="No suitability is established",
    )
    tasks = (task, evolve(task, logical_id="second"))
    comparisons = [compare(corpus.reader(), item) for item in tasks]
    calls = []
    original = Backend.scan

    def tracked(
        self: Backend,
        name: str,
        **options: Unpack[ScanOptions],
    ) -> Iterator[dict[str, object]]:
        if name == "operations":
            calls.append(options.get("limit", 250_000))
        yield from original(self, name, **options)

    monkeypatch.setattr(Backend, "scan", tracked)
    writer.commit(
        (*tasks, *(item for pair in comparisons for item in pair)),
        expected=corpus.reader().manifest_id,
    )
    assert len(calls) < QUERY_WINDOW_CEILING
    assert len(tuple(corpus.reader().records("comparisons"))) == len(tasks)
    calls.clear()
    closure = evidence_closure(
        corpus.reader(), tuple(("comparisons", revision_of(pair[1])) for pair in comparisons)
    )
    assert {revision_of(item) for item in closure if isinstance(item, Operation)} == {
        revision_of(item) for item in operations
    }
    assert len(calls) < QUERY_WINDOW_CEILING
    _check_candidate_pages(corpus, tuple(revision_of(pair[1]) for pair in comparisons))


def _check_candidate_pages(corpus: Corpus, comparisons: tuple[str, ...]) -> None:
    before = corpus.reader()
    request = SequenceRequest(
        family="comparisons", revision=comparisons[0], field="/candidates", max_rows=2
    )
    first = read_sequence(before, request)
    assert first.eligible == len(tuple(before.members("operations")))
    assert first.consumed == request.max_rows
    assert not first.complete
    assert first.continuation
    second_request = evolve(request, continuation=first.continuation)
    second = read_sequence(before, second_request)
    assert second.consumed == first.consumed + request.max_rows
    assert not {str(item) for item in first.values} & {str(item) for item in second.values}
    tiny = read_sequence(before, evolve(request, max_bytes=1))
    assert not tiny.values
    assert tiny.consumed == 0
    assert tiny.continuation
    with pytest.raises(CorpusError, match="another manifest, record or field"):
        read_sequence(before, evolve(second_request, revision=comparisons[1]))
    with pytest.raises(CorpusError, match="another manifest, record or field"):
        read_sequence(before, evolve(second_request, field="/preferred"))
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit(
        (_job("head-advance"),), expected=before.manifest_id
    )
    with pytest.raises(CorpusError, match="another manifest, record or field"):
        read_sequence(corpus.reader(), second_request)
    assert read_sequence(before, second_request) == second


@pytest.mark.parametrize("replace", [False, True])
def test_batch_overlay_rejects_superseded_and_retired_support(
    tmp_path: Path,
    *,
    replace: bool,
) -> None:
    """Prefetch cannot promote a cached predecessor through proposed selection changes."""
    corpus = Corpus(tmp_path)
    old, retired = _job("old"), _job("retired")
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit((old, retired), expected="")
    base = corpus.reader()
    base.prefetch(("jobs", revision_of(record)) for record in (old, retired))
    new = evolve(old, request="new")
    reader = AdmissionReader(
        base,
        {"jobs": [REGISTRY["jobs"].encode(new)]},
        replace=replace,
        retire=(
            Member(
                family="jobs",
                logical_id=retired.logical_id,
                profile=retired.profile,
                revision=revision_of(retired),
            ),
        ),
    )
    assert tuple(reader.get_many("jobs", (revision_of(new),))) == (new,)
    assert tuple(reader.filtered_records("jobs", (("stage", "fixture"),))) == (new,)
    for record in (old, retired):
        with pytest.raises(CorpusError, match="outside proposed membership"):
            reader.prefetch((("jobs", revision_of(record)),))
