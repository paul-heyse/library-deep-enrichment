"""Exact prerequisite withdrawal for current products restored without producer jobs."""

from __future__ import annotations

from itertools import batched
from typing import TYPE_CHECKING

from library_guides.corpus import contracts as c
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from collections.abc import Mapping

    from library_guides.corpus.store import CorpusReader

# These are retained authority/run observations, not assertions of current success.
# Their exact subjects may intentionally be historical. Blob identities are immutable.
HISTORY = frozenset(
    {
        "jobs",
        "stage_definitions",
        "stage_input_receipts",
        "stage_executions",
        "policies",
        "reviews",
        "blobs",
        "blob_chunks",
    }
)


def _links(record: c.Record) -> set[str]:
    from library_guides.corpus.validation import _supports, references

    result = {revision for _, revision in references(record)}
    for support in _supports(record):
        result.add(support.revision if isinstance(support, c.Selection) else support.blob)
    if isinstance(record, c.Qualification):
        result.update((record.subject, *record.support))
    if isinstance(record, c.Scope):
        result.update(record.members)
    if isinstance(record, c.Release):
        result.update(
            (*record.subjects, *record.qualifications, *record.universes, record.guide_blob)
        )
    if isinstance(record, c.Gap):
        result.update((record.subject, record.predicate))
    if isinstance(record, c.TypeNode):
        result.add(record.owner)
    if isinstance(record, c.Relation):
        result.update((record.source, record.target))
    return result - {""}


def withdraw(
    reader: CorpusReader,
    staged: Mapping[tuple[str, str, str], c.Member],
    removed: set[str],
    jobs: tuple[c.Job, ...],
) -> tuple[c.Member, ...]:
    """Propagate exact premise loss independently of retained bulk-job ownership.

    Returns:
        Unstaged current products that no longer have their exact prerequisites.
        Historical views and original byte objects remain selected by their old heads.

    """
    if not removed:
        return ()
    members = {item.revision: item for item in reader.members()}
    # Bulk outputs have already been checked against their declared exact populations
    # by job invalidation. Portable closures have no jobs and take this direct path.
    excluded = {revision for job in jobs for revision in job.outputs} | removed
    candidates: dict[str, tuple[c.Member, set[str]]] = {}
    removed_families = {members[key].family for key in removed if key in members}
    for family in {member.family for member in members.values()} - HISTORY:
        # NativeFact's only links are its artifact and original blob. This avoids
        # reading the full compiler corpus for a semantic-only premise change.
        if family == "native_facts" and not removed_families & {
            "native_artifacts",
            "blobs",
            "contexts",
            "source_files",
        }:
            continue
        selected = tuple(
            member.revision
            for member in members.values()
            if member.family == family
            and member.revision not in excluded
            and (family, member.logical_id, member.profile) not in staged
        )
        for keys in batched(selected, 128, strict=False):
            for record in reader.get_many(family, keys):
                key = revision_of(record)
                links = _links(record)
                if links:
                    candidates[key] = members[key], links
    result = {}
    pending = True
    while pending:
        pending = False
        for key, (member, links) in candidates.items():
            if key not in removed and links & removed:
                result[key] = member
                removed.add(key)
                pending = True
    return tuple(result[key] for key in sorted(result))
