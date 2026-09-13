"""Portable decision evidence closure without copying unrelated analytical populations."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING, cast

from attrs import fields, has

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import (
    Blob,
    ByteRange,
    Context,
    Operation,
    Policy,
    Qualification,
    Record,
    Scope,
    Selection,
    SourceFile,
)
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.validation import references
from library_deep_enrichment.publication.objectives import links as objective_links
from library_deep_enrichment.semantics.contracts import Capability, CapabilitySchema, Comparison
from library_deep_enrichment.semantics.enrichment_contracts import (
    InvocationContract,
    TransferMapping,
    TransferModel,
    WitnessRecipe,
)
from library_deep_enrichment.semantics.type_shapes import OperationShape

if TYPE_CHECKING:
    from collections.abc import Iterator

    from attrs import AttrsInstance

    from library_deep_enrichment.corpus.store import CorpusReader

READ_WINDOW = 128


def _next_records(
    reader: CorpusReader, pending: deque[tuple[str, str]], retained: dict[str, Record]
) -> tuple[tuple[str, Record], ...]:
    """Resolve one exact frontier window without unbounded speculative prefetch.

    Returns:
        Distinct selected prerequisites in their first-observed traversal order.

    """
    window: dict[str, str] = {}
    while pending and len(window) < READ_WINDOW:
        family, revision = pending.popleft()
        if revision not in retained and revision not in window:
            window[revision] = family
    groups: dict[str, list[str]] = defaultdict(list)
    for revision, family in window.items():
        groups[family].append(revision)
    records: dict[str, Record] = {}
    for family, revisions in groups.items():
        records.update(zip(revisions, reader.get_many(family, revisions), strict=True))
    return tuple((revision, records[revision]) for revision in window)


def _source_links(value: object) -> Iterator[tuple[str, str]]:
    if isinstance(value, Selection):
        yield value.family, value.revision
    elif isinstance(value, ByteRange):
        yield "blobs", value.blob
    elif isinstance(value, tuple):
        for item in value:
            yield from _source_links(item)
    elif has(type(value)):
        for field in fields(cast("type[AttrsInstance]", type(value))):
            yield from _source_links(getattr(value, field.name))


def _decision_links(reader: CorpusReader, record: Record) -> Iterator[tuple[str, str]]:
    if isinstance(record, Qualification) and record.method == "checked-rule-consequence":
        yield "assertions", record.subject
        yield "proofs", record.support[0]
        yield "rules", record.support[1]
        for policy in record.support[2:]:
            yield "policies", policy
    if isinstance(record, Comparison):
        yield from objective_links(reader, record)
        for candidate in record.candidates:
            if candidate.capability:
                yield "capabilities", candidate.capability
            for requirement in candidate.requirements:
                for assertion in requirement.assertions:
                    yield "assertions", assertion


def _schema_links(reader: CorpusReader, record: Record) -> Iterator[tuple[str, str]]:
    approval_kinds: dict[type[Record], str] = {
        WitnessRecipe: "witness-recipe-approval",
        TransferModel: "transfer-model-approval",
        TransferMapping: "transfer-mapping-approval",
        InvocationContract: "invocation-approval",
    }
    approval_kind = approval_kinds.get(type(record))
    if approval_kind:
        for policy in reader.records("policies"):
            if (
                isinstance(policy, Policy)
                and policy.kind == approval_kind
                and policy.subject == revision_of(record)
            ):
                yield "policies", revision_of(policy)
    if not isinstance(record, Capability):
        return
    operation = reader.get("operations", record.operation)
    if isinstance(operation, Operation):
        shape = reader.lookup(
            "operation_shapes", f"shape:{operation.logical_id}", operation.profile
        )
        if isinstance(shape, OperationShape):
            yield "operation_shapes", revision_of(shape)
    schema = reader.lookup("capability_schemas", f"capability-schema:{record.schema}")
    if isinstance(schema, CapabilitySchema):
        schema_revision = revision_of(schema)
        yield "capability_schemas", schema_revision
        for policy in reader.records("policies"):
            if (
                isinstance(policy, Policy)
                and policy.kind == "schema-approval"
                and policy.subject == schema_revision
            ):
                yield "policies", revision_of(policy)


def decision_closure(reader: CorpusReader, comparison: Comparison) -> tuple[Record, ...]:
    """Resolve every decision prerequisite and source object through the pinned manifest.

    Returns:
        A complete selected closure, retaining source attribution and contextual records.

    """
    return evidence_closure(reader, (("comparisons", revision_of(comparison)),))


def evidence_closure(
    reader: CorpusReader, roots: tuple[tuple[str, str], ...]
) -> tuple[Record, ...]:
    """Resolve typed publication roots through the shared evidence and authority graph.

    Returns:
        All exact prerequisites, including source bytes and required policy authority.

    Raises:
        CorpusError: A purported finite scope names an unadmitted revision.

    """
    families = {member.revision: member.family for member in reader.members()}
    qualifications: dict[str, list[str]] = {}
    for item in reader.records("qualifications"):
        if isinstance(item, Qualification):
            qualifications.setdefault(item.subject, []).append(revision_of(item))
    pending = deque(roots)
    retained: dict[str, Record] = {}
    attributions = [item for item in reader.records("source_files") if isinstance(item, SourceFile)]
    contexts = [item for item in reader.records("contexts") if isinstance(item, Context)]
    while pending:
        for revision, record in _next_records(reader, pending, retained):
            retained[revision] = record
            pending.extend(
                (*references(record), *_source_links(record), *_decision_links(reader, record))
            )
            pending.extend(("qualifications", key) for key in qualifications.get(revision, []))
            pending.extend(_schema_links(reader, record))
            if isinstance(record, Scope):
                for member in record.members:
                    if member not in families:
                        message = "release scope refers to an unadmitted candidate"
                        raise CorpusError(message)
                    pending.append((families[member], member))
            if isinstance(record, Blob):
                pending.extend(
                    ("source_files", revision_of(item))
                    for item in attributions
                    if item.blob == revision
                )
            if record.profile:
                pending.extend(
                    ("contexts", revision_of(item))
                    for item in contexts
                    if item.profile == record.profile
                )
    return tuple(retained[key] for key in sorted(retained))
