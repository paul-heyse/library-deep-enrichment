"""Separately qualify current decisions from verified historical source closures."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from attrs import asdict, evolve

from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.checker_epochs import HISTORICAL
from library_guides.corpus.schemas import revision_of
from library_guides.publication.releases import publish
from library_guides.semantics.contracts import Predicate, Task
from library_guides.semantics.task_matching import compare
from library_guides.semantics.vocabulary import approve_rules, foundation
from library_guides.workflows import semantics, shapes

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus, CorpusReader

SOURCE_FAMILIES = frozenset(
    {
        "blobs",
        "blob_chunks",
        "contexts",
        "source_files",
        "legacy_records",
        "legacy_selections",
        "raw_observations",
        "native_artifacts",
        "native_facts",
        "entities",
        "operations",
        "passages",
        "relations",
        "type_nodes",
        "type_uses",
        "registry_entries",
        "registry_properties",
        "registry_kernels",
    }
)


def _task(current: CorpusReader, archived: CorpusReader, task: Task) -> Task:
    for requirement in task.requirements:
        old = archived.get("predicates", requirement.predicate)
        if (
            not isinstance(old, Predicate)
            or current.lookup("predicates", old.logical_id, old.profile) != old
        ):
            message = "historical task needs an explicit semantic migration for a changed predicate"
            raise CorpusError(message)
    if task.preferences:
        message = "historical preference policies require separate current qualification"
        raise CorpusError(message)
    return evolve(task, logical_id=task.logical_id + ":current-successor")


def create(
    corpus: Corpus, archived: CorpusReader, *, authority: str, rationale: str
) -> dict[str, object]:
    """Import identical source evidence and recompute current rules, schemas and task outcomes.

    Returns:
        Source/semantic accounting and exact new release identities. Historical assertions,
        approvals, reviews and generated products remain in their immutable original archive.

    Raises:
        CorpusError: The input is not verified historical evidence or the destination is occupied.

    """
    if corpus.reader().manifest_id or archived.semantic_checker != HISTORICAL:
        message = "current successor creation requires verified history and an empty destination"
        raise CorpusError(message)
    counts = Counter(item.family for item in archived.members())
    records = (
        record
        for family in sorted(SOURCE_FAMILIES & counts.keys())
        for record in archived.records(family)
    )
    source_manifest = Coordinator(
        corpus, WriterIdentity(principal="historical-source-equivalence", role="migration")
    ).commit(records, expected="")
    definitions = foundation()
    approvals = approve_rules(definitions, authority=authority, rationale=rationale)
    Coordinator(corpus, WriterIdentity(principal=authority, role="policy")).commit(
        (*definitions, *approvals), expected=source_manifest
    )
    shape_result = shapes.build(corpus)
    semantic_result = semantics.build(corpus)
    releases = []
    for index, original in enumerate(archived.records("tasks")):
        if not isinstance(original, Task):
            continue
        task = _task(corpus.reader(), archived, original)
        scope, comparison = compare(corpus.reader(), task)
        Coordinator(corpus, WriterIdentity(principal="current-task-comparison")).commit(
            (task, scope, comparison), expected=corpus.reader().manifest_id
        )
        head = f"release-{index}"
        release = publish(corpus, comparison, expected="", head=head)
        releases.append(
            {
                "old_task": revision_of(original),
                "current_task": revision_of(task),
                "comparison": revision_of(comparison),
                "head": head,
                "manifest": release,
                "candidates": len(comparison.candidates),
                "dispositions": dict(Counter(item.disposition for item in comparison.candidates)),
            }
        )
    return {
        "historical_manifest": archived.manifest_id,
        "historical_checker": archived.semantic_checker,
        "source_manifest": source_manifest,
        "current_manifest": corpus.reader().manifest_id,
        "current_checker": corpus.reader().semantic_checker,
        "identical_source_records": {
            family: count for family, count in sorted(counts.items()) if family in SOURCE_FAMILIES
        },
        "retained_only_in_immutable_history": {
            family: count
            for family, count in sorted(counts.items())
            if family not in SOURCE_FAMILIES
        },
        "shape_stage": asdict(shape_result),
        "semantic_stage": asdict(semantic_result),
        "releases": releases,
        "policy_authority": authority,
        "policy_rationale": rationale,
    }
