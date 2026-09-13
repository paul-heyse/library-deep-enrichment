"""A generated product can change only with its owning stage receipt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Job

if TYPE_CHECKING:
    from collections.abc import Mapping

    from library_deep_enrichment.corpus.contracts import AdmissionBatch, Member
    from library_deep_enrichment.corpus.store import CorpusReader


def validate_ownership(
    reader: CorpusReader, batch: AdmissionBatch, staged: Mapping[tuple[str, str, str], Member]
) -> None:
    """Reject direct replacement of a stage-owned product without its currentness transition.

    Raises:
        CorpusError: A transaction bypasses the declared output owner.

    """
    members = {(item.family, item.logical_id, item.profile): item for item in reader.members()}
    changes = {
        members[key].revision
        for key, item in staged.items()
        if key in members and members[key] != item
    }
    changes.update(
        item.revision for item in batch.retire if item.family not in {"blobs", "blob_chunks"}
    )
    for job in reader.records("jobs"):
        if not isinstance(job, Job) or not changes.intersection(job.outputs):
            continue
        if ("jobs", job.logical_id, job.profile) not in staged:
            message = f"generated output cannot bypass its stage owner: {job.stage}"
            raise CorpusError(message)
