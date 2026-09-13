"""Pagination never substitutes a changed head, skips a limited row, or promotes orphans."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Disposition, Job
from library_deep_enrichment.corpus.store import Corpus

if TYPE_CHECKING:
    from pathlib import Path


def _job(name: str, profile: str = "a") -> Job:
    return Job(
        logical_id=name,
        profile=profile,
        stage="fixture",
        request=name,
        inputs=(),
        universes=(),
        outputs=(),
        disposition=Disposition.COMPLETE,
        reason="fixture",
    )


def test_pinned_ordered_pages_survive_an_advance_and_reject_cross_head_cursor(
    tmp_path: Path,
) -> None:
    """Each row occurs once even with duplicate names across profiles and new competitors."""
    corpus = Corpus(tmp_path)
    writer = Coordinator(corpus, WriterIdentity(principal="fixture"))
    original = (_job("z"), _job("a", "b"), _job("a"))
    first = writer.commit(original, expected="")
    reader = corpus.reader()
    page = reader.page("jobs", max_rows=1)
    assert page.eligible == len(original)
    assert page.consumed == 1
    assert not page.complete
    writer.commit((_job("b"),), expected=first)
    with pytest.raises(CorpusError, match="different pinned"):
        corpus.reader().page("jobs", continuation=page.continuation)
    with pytest.raises(CorpusError, match="different pinned"):
        reader.page("jobs", profile="a", continuation=page.continuation)
    records = list(page.records)
    while page.continuation:
        page = reader.page("jobs", continuation=page.continuation, max_rows=1)
        records.extend(page.records)
    assert [(row.logical_id, row.profile) for row in records] == [
        ("a", "a"),
        ("a", "b"),
        ("z", "a"),
    ]
    assert page.complete
    assert page.consumed == page.eligible == len(original)


def test_byte_limit_retains_the_unconsumed_row_and_empty_populations_complete(
    tmp_path: Path,
) -> None:
    """A packet that cannot fit its first record returns a usable unchanged cursor."""
    corpus = Corpus(tmp_path)
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit((_job("only"),), expected="")
    reader = corpus.reader()
    page = reader.page("jobs", max_bytes=1)
    assert not page.records
    assert page.consumed == 0
    assert page.eligible == 1
    assert not page.complete
    assert page.continuation
    assert "byte limit" in page.limit_reason
    resumed = reader.page("jobs", continuation=page.continuation)
    assert resumed.records == (_job("only"),)
    assert resumed.complete
    empty = reader.page("jobs", profile="empty")
    assert empty.complete
    assert empty.eligible == 0
    assert not empty.continuation
