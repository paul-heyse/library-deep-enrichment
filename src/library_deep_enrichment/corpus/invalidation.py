"""Withdraw dependent current products when selected inputs or candidate populations change."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.contracts import Disposition, Job, Member
from library_deep_enrichment.corpus.direct_dependencies import withdraw as withdraw_direct
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.identities import references as identity_references
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.semantics.contracts import Comparison
from library_deep_enrichment.semantics.decision_contracts import Counterfactual
from library_deep_enrichment.workflows.contracts import InputReceipt, StageDefinition
from library_deep_enrichment.workflows.inputs import matches

if TYPE_CHECKING:
    from collections.abc import Mapping

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader

DECISION_INPUTS = frozenset(
    {
        "operations",
        "operation_shapes",
        "assertions",
        "qualifications",
        "capabilities",
        "tasks",
        "predicates",
        "expressions",
        "policies",
        "preference_policies",
        "invocation_contracts",
        "transfer_models",
        "transfer_mappings",
        "composition_goals",
    }
)


def _population_changed(
    reader: CorpusReader,
    job: Job,
    definition: Record | None,
    heads: Mapping[str, Member],
    families: set[str],
) -> bool:
    receipts = tuple(
        reader.get("stage_input_receipts", item.revision)
        for item in job.inputs
        if item.family == "stage_input_receipts"
    )
    if receipts:
        return any(
            isinstance(receipt, InputReceipt)
            and any(matches(receipt.selector, head) for head in heads.values())
            for receipt in receipts
        )
    populations = (
        {item.family for item in definition.inputs}
        if isinstance(definition, StageDefinition)
        else {item.family for item in job.inputs}
    )
    return bool(populations & families)


def _withdraw_identities(
    reader: CorpusReader, staged: Mapping[tuple[str, str, str], Member], removed: set[str]
) -> tuple[Member, ...]:
    result = []
    for family in ("contextual_identities", "identity_joins"):
        for record in reader.records(family):
            key = (family, record.logical_id, record.profile)
            if key not in staged and any(
                revision in removed for _, revision in identity_references(record)
            ):
                member = Member(
                    family=family,
                    logical_id=record.logical_id,
                    profile=record.profile,
                    revision=revision_of(record),
                )
                result.append(member)
                removed.add(member.revision)
    return tuple(result)


def _task_changed(reader: CorpusReader, member: Member, removed: set[str]) -> bool:
    record = reader.get(member.family, member.revision)
    if isinstance(record, Comparison):
        return record.task in removed
    if isinstance(record, Counterfactual):
        return bool({record.task, record.alternative_task} & removed)
    # Composition products can be rooted in another product instead of a task;
    # their existing conservative dependency contract remains in force.
    return True


def invalidate(
    reader: CorpusReader, staged: Mapping[tuple[str, str, str], Member], retired: tuple[Member, ...]
) -> tuple[tuple[Record, ...], tuple[Member, ...]]:
    """Calculate a finite dependency closure before the coordinator's final admission.

    Returns:
        New pending-currentness receipts and exact prior members to withdraw. Historical
        manifests and all release heads retain their original readable selections.

    """
    members = {(item.family, item.logical_id, item.profile): item for item in reader.members()}
    changed = {key for key, member in staged.items() if members.get(key) != member}
    effective = tuple(
        item for item in retired if staged.get((item.family, item.logical_id, item.profile)) != item
    )
    removed = {item.revision for item in effective}
    removed.update(members[key].revision for key in changed if key in members)
    families = {key[0] for key in changed} | {item.family for item in effective}
    old_jobs = [item for item in reader.records("jobs") if isinstance(item, Job) and item.outputs]
    withdrawn = {item.revision: item for item in retired}
    receipts: list[Record] = []
    invalidated: set[str] = set()
    changed_heads = {member.revision: member for key, member in staged.items() if key in changed}
    changed_heads.update((item.revision, item) for item in effective)
    changed_heads.update((members[key].revision, members[key]) for key in changed if key in members)
    pending = True
    while pending:
        pending = False
        for job in old_jobs:
            key = ("jobs", job.logical_id, job.profile)
            if key in staged or job.logical_id in invalidated:
                continue
            definition = reader.lookup("stage_definitions", job.stage, job.profile)
            dependencies = (
                set(definition.dependencies) if isinstance(definition, StageDefinition) else set()
            )
            if not (
                _population_changed(reader, job, definition, changed_heads, families)
                or any(item.revision in removed for item in job.inputs)
                or dependencies & invalidated
            ):
                continue
            invalidated.add(job.logical_id)
            owned = set(job.outputs)
            for member in members.values():
                if member.revision in owned and member.family not in {"blobs", "blob_chunks"}:
                    withdrawn[member.revision] = member
                    removed.add(member.revision)
                    families.add(member.family)
                    changed_heads[member.revision] = member
            receipts.append(
                Job(
                    logical_id=job.logical_id,
                    profile=job.profile,
                    stage=job.stage,
                    request=digest(
                        ["invalidated-inputs", job.request, sorted(changed), sorted(removed)]
                    ),
                    inputs=(),
                    universes=(),
                    outputs=(),
                    disposition=Disposition.PARTIAL,
                    reason="Selected input or independent candidate population changed; rebuild required",
                    previous_success=revision_of(job),
                )
            )
            pending = True
    direct = withdraw_direct(reader, staged, removed, tuple(old_jobs))
    withdrawn.update((member.revision, member) for member in direct)
    families.update(member.family for member in direct)
    if families & DECISION_INPUTS:
        for key, member in members.items():
            if (
                member.family
                in {
                    "comparisons",
                    "compositions",
                    "counterfactuals",
                    "composition_evaluations",
                    "composition_programs",
                    "composition_witnesses",
                    "state_transfers",
                }
                and key not in staged
                and (
                    families & DECISION_INPUTS != {"tasks"}
                    or _task_changed(reader, member, removed)
                )
            ):
                withdrawn[member.revision] = member
    # Source-identity records also have direct exact dependencies when authored
    # outside a bulk stage. A join must disappear with either of its endpoints.
    withdrawn.update(
        (member.revision, member) for member in _withdraw_identities(reader, staged, removed)
    )
    return tuple(receipts), tuple(withdrawn[key] for key in sorted(withdrawn))
