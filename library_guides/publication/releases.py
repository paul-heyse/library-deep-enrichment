"""Named release heads select one qualified corpus view without copying directories."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import Disposition, Qualification, Release
from library_guides.corpus.evidence import iter_blob, stage_blob
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.validation import validate_records
from library_guides.publication.closure import decision_closure
from library_guides.publication.render import RENDERER, render_comparison
from library_guides.semantics.contracts import Comparison, Task
from library_guides.semantics.task_matching import replay

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus, CorpusReader


def publish(corpus: Corpus, comparison: Comparison, *, expected: str, head: str = "release") -> str:
    """Publish a supported/partial decision and its complete retained evidence view.

    Returns:
        The release manifest. Analysis may subsequently advance independently.

    Raises:
        CorpusError: The proposed comparison is stale or does not follow from current inputs.

    """
    reader = corpus.reader()
    reader.get("comparisons", revision_of(comparison))
    task = reader.get("tasks", comparison.task)
    if not isinstance(task, Task) or replay(reader, task, comparison) != comparison:
        message = (
            "comparison is stale or differs from the admitted task, models, and candidate universe"
        )
        raise CorpusError(message)
    records = decision_closure(reader, comparison)
    validate_records(reader, tuple(records))
    guide = render_comparison(reader, comparison).encode()
    blob, chunks = stage_blob(io.BytesIO(guide), media_type="text/markdown")
    release = Release(
        logical_id=f"release:{comparison.logical_id}",
        profile=comparison.profile,
        source_manifest=reader.manifest_id,
        subjects=(revision_of(comparison),),
        qualifications=tuple(
            revision_of(item)
            for item in records
            if isinstance(item, Qualification) and item.disposition == Disposition.COMPLETE
        ),
        universes=(comparison.universe,),
        renderer=RENDERER,
        guide_blob=revision_of(blob),
    )
    # Migration authority here copies already verified immutable records into a
    # named view of this same corpus. It never loads legacy authoring files.
    return Coordinator(
        corpus, WriterIdentity(principal="release-coordinator", role="migration")
    ).commit(
        [*records, *chunks, blob, release],
        expected=expected,
        head=head,
        replace=True,
    )


def read_guide(reader: CorpusReader, release: Release) -> str:
    """Read the retained rendered guide using only the pinned release corpus.

    Returns:
        Verified Markdown, requiring no extractor or embedding service.

    """
    reader.get("releases", revision_of(release))
    return b"".join(iter_blob(reader, release.guide_blob)).decode("utf-8")
