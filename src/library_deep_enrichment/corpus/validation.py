"""Admission-time support closure and consequence validation against a staged view."""

from __future__ import annotations

import ast
import json
from collections import defaultdict
from itertools import batched, chain, islice
from typing import TYPE_CHECKING, cast

from attrs import fields, has

from library_deep_enrichment.analyses.fabric import references as analysis_references
from library_deep_enrichment.analyses.fabric import validate as validate_analysis
from library_deep_enrichment.corpus import contracts as c
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.cache import RecordCache
from library_deep_enrichment.corpus.encoding import bytes_digest, digest, payload
from library_deep_enrichment.corpus.evidence import field_value, iter_blob, resolve, resolve_bytes
from library_deep_enrichment.corpus.identities import references as identity_references
from library_deep_enrichment.corpus.identities import validate as validate_identity
from library_deep_enrichment.corpus.native_validation import references as native_references
from library_deep_enrichment.corpus.native_validation import validate as validate_native
from library_deep_enrichment.corpus.normalization import validate as validate_normalization
from library_deep_enrichment.corpus.schemas import REGISTRY, revision_of
from library_deep_enrichment.corpus.store import CorpusReader
from library_deep_enrichment.discovery.validation import references as discovery_references
from library_deep_enrichment.discovery.validation import validate as validate_discovery
from library_deep_enrichment.semantics import contracts as s
from library_deep_enrichment.semantics.decision_validation import references as decision_references
from library_deep_enrichment.semantics.decision_validation import validate as validate_decision
from library_deep_enrichment.semantics.enrichment_validation import (
    references as enrichment_references,
)
from library_deep_enrichment.semantics.enrichment_validation import validate as validate_enrichment
from library_deep_enrichment.semantics.proofs import check_consequence
from library_deep_enrichment.semantics.realization import realize
from library_deep_enrichment.semantics.shape_validation import validate_shapes
from library_deep_enrichment.semantics.type_shapes import OperationShape
from library_deep_enrichment.workflows.contracts import InputReceipt
from library_deep_enrichment.workflows.failure_records import FailureReceipt
from library_deep_enrichment.workflows.failure_records import validate as validate_failure_receipt
from library_deep_enrichment.workflows.inputs import references as workflow_references
from library_deep_enrichment.workflows.inputs import validate as validate_input_receipt

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from attrs import AttrsInstance


class AdmissionReader(CorpusReader):
    """Read a proposed selected view without granting producer write access."""

    def __init__(
        self,
        base: CorpusReader,
        staged: Mapping[str, list[dict[str, object]]],
        *,
        replace: bool,
        retire: tuple[c.Member, ...] = (),
    ) -> None:
        """Overlay exact staged revisions on a pinned predecessor."""
        self.base = base
        self.staged = staged
        self.replace = replace
        self.manifest = base.manifest
        self.max_rows = base.max_rows
        self._cache = RecordCache()
        self.index = {
            (family, str(row["revision"])): row for family, rows in staged.items() for row in rows
        }
        self.keys = {
            (family, str(row["logical_id"]), str(row["profile"]))
            for family, rows in staged.items()
            for row in rows
        }
        self.keys.update((item.family, item.logical_id, item.profile) for item in retire)

    def _raw_row(self, family: str, revision: str) -> dict[str, object]:
        """Resolve only a revision in the proposed exact selection.

        Returns:
            A validated staged or retained row.

        Raises:
            CorpusError: The proposed view excludes the requested support revision.

        """
        row = self.index.get((family, revision))
        if row is not None:
            return row
        if not self.replace:
            original = self.base.row(family, revision)
            if (family, str(original["logical_id"]), str(original["profile"])) not in self.keys:
                return original
        message = f"support outside proposed membership: {family}/{revision}"
        raise CorpusError(message)

    def records(self, family: str) -> Iterator[c.Record]:
        """Enumerate a family at the proposed selection.

        Yields:
            Exact staged and unchanged predecessor records.

        """
        codec = REGISTRY[family]
        if not self.replace:
            for record in self.base.records(family):
                if (family, record.logical_id, record.profile) not in self.keys:
                    yield record
        seen: set[str] = set()
        for row in self.staged.get(family, []):
            revision = str(row["revision"])
            if revision not in seen:
                seen.add(revision)
                yield codec.decode(row)

    def members(self, family: str = "") -> Iterator[c.Member]:
        """Yield proposed metadata without reading family payloads.

        Yields:
            Exact retained and staged logical heads, with replacements and retirements applied.

        """
        if not self.replace:
            for member in self.base.members(family):
                if (member.family, member.logical_id, member.profile) not in self.keys:
                    yield member
        for selected_family, rows in self.staged.items():
            if family and family != selected_family:
                continue
            seen: set[str] = set()
            for row in rows:
                revision = str(row["revision"])
                if revision in seen:
                    continue
                seen.add(revision)
                yield c.Member(
                    family=selected_family,
                    logical_id=str(row["logical_id"]),
                    profile=str(row["profile"]),
                    revision=revision,
                )

    def filtered_records(
        self, family: str, equals: tuple[tuple[str, str], ...]
    ) -> Iterator[c.Record]:
        """Apply the same typed equality query to the exact proposed selection.

        Yields:
            Matching unretired predecessor and staged records.

        """
        from library_deep_enrichment.corpus.queries import predicate

        predicate(family, equals)
        if not self.replace:
            for record in self.base.filtered_records(family, equals):
                if (family, record.logical_id, record.profile) not in self.keys:
                    yield record
        for row in self.staged.get(family, ()):
            if all(row.get(name) == value for name, value in equals):
                yield REGISTRY[family].decode(row)

    def lookup(self, family: str, logical_id: str, profile: str = "") -> c.Record | None:
        """Resolve an exact staged key before consulting the pinned base.

        Returns:
            The proposed current record, or no record for a retired/missing key.

        """
        for row in self.staged.get(family, ()):
            if row["logical_id"] == logical_id and row["profile"] == profile:
                return self.get(family, str(row["revision"]))
        if self.replace or (family, logical_id, profile) in self.keys:
            return None
        return self.base.lookup(family, logical_id, profile)

    def get_many(self, family: str, revisions: Iterable[str]) -> Iterator[c.Record]:
        """Batch retained inputs while enforcing staged replacement and retirement.

        Yields:
            Only records selected by this proposed view, in request order.

        Raises:
            CorpusError: A requested predecessor revision was replaced or retired.

        """
        for batch in batched(revisions, 128, strict=False):
            staged = {revision for revision in batch if (family, revision) in self.index}
            if not self.replace:
                for record in self.base.get_many(family, (r for r in batch if r not in staged)):
                    if (family, record.logical_id, record.profile) in self.keys:
                        message = (
                            f"support outside proposed membership: {family}/{revision_of(record)}"
                        )
                        raise CorpusError(message)
                    self._cache.put((family, revision_of(record)), record)
            yield from (self.get(family, revision) for revision in batch)

    def previous(self) -> CorpusReader | None:
        """Expose committed input ancestry while keeping proposed outputs out of cache authority.

        Returns:
            A retained historical view of the pinned base.

        """
        return self.base


def _supports(value: object) -> Iterator[c.Selection | c.ByteRange]:
    if isinstance(value, (c.Selection, c.ByteRange)):
        yield value
    elif isinstance(value, tuple):
        for child in value:
            yield from _supports(child)
    elif has(type(value)):
        for descriptor in fields(cast("type[AttrsInstance]", type(value))):
            yield from _supports(getattr(value, descriptor.name))


def _acquisition_references(record: c.Record) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if isinstance(record, c.Blob):
        pairs.extend(("blob_chunks", item) for item in record.chunks)
    if isinstance(record, c.SourceFile):
        pairs.append(("blobs", record.blob))
    if isinstance(record, c.LegacySelection):
        pairs.append(("blobs", record.source_blob))
    if isinstance(record, c.Passage):
        pairs.append((record.owner_family, record.owner))
    if isinstance(record, c.RegistryProperty):
        pairs.append((record.owner_family, record.owner))
    if isinstance(record, c.RawObservation) and record.context:
        pairs.append(("contexts", record.context))
    if isinstance(record, (c.RegistryEntry, c.RegistryKernel)):
        pairs.append(("operations", record.operation))
    if isinstance(record, c.RegistryKernel):
        pairs.append(("registry_entries", record.registry_entry))
    if isinstance(record, c.TypeUse):
        pairs.append(("operations", record.owner))
    return pairs


def references(record: c.Record) -> tuple[tuple[str, str], ...]:
    """Enumerate typed revision references; display names never act as foreign keys.

    Returns:
        Family/revision pairs whose selected membership is required.

    """
    pairs = [
        *_acquisition_references(record),
        *discovery_references(record),
        *enrichment_references(record),
        *native_references(record),
        *decision_references(record),
        *analysis_references(record),
        *workflow_references(record),
        *identity_references(record),
    ]
    if isinstance(record, s.Rule):
        pairs.extend((("predicates", record.predicate), ("expressions", record.condition)))
    if isinstance(record, OperationShape):
        pairs.append(("operations", record.operation))
    if isinstance(record, s.Assertion):
        pairs.extend(
            (
                ("operations", record.subject),
                ("predicates", record.predicate),
                ("rules", record.rule),
                ("expressions", record.condition),
                ("scopes", record.scope),
            )
        )
    if isinstance(record, s.Proof):
        pairs.extend((("assertions", record.conclusion), ("rules", record.rule)))
        pairs.extend(("scopes", item) for item in record.scopes)
    if isinstance(record, (s.Mode, s.Capability)):
        pairs.extend((("operations", record.operation), ("expressions", record.condition)))
        pairs.extend(("assertions", item) for item in record.assertions)
    if isinstance(record, s.Capability):
        pairs.append(("modes", record.mode))
    if isinstance(record, s.Expression):
        pairs.extend(("expressions", item) for item in record.arguments)
    if isinstance(record, (s.Task, s.CapabilitySchema)):
        pairs.extend(("predicates", item.predicate) for item in record.requirements)
    if isinstance(record, s.Comparison):
        pairs.extend((("tasks", record.task), ("scopes", record.universe)))
        pairs.extend(("operations", item.operation) for item in record.candidates)
    return tuple(pair for pair in pairs if pair[1])


def _check_passage(reader: CorpusReader, passage: c.Passage) -> None:
    original = resolve_bytes(reader, passage.source)
    decoded = original.decode("utf-8")
    if passage.text == decoded:
        return
    if passage.role == "python-source-docstring":
        expression = ast.parse(decoded, mode="eval").body
        if (
            isinstance(expression, ast.Constant)
            and isinstance(expression.value, str)
            and expression.value == passage.text
        ):
            return
    try:
        value = json.loads(decoded)
    except json.JSONDecodeError:
        value = None
    if passage.text != value:
        message = "passage text does not match its original or JSON-string source bytes"
        raise CorpusError(message)


def _check_byte_object(reader: CorpusReader, record: c.Record) -> None:
    if isinstance(record, c.Blob):
        for _ in iter_blob(reader, revision_of(record)):
            pass
    if isinstance(record, c.BlobChunk) and bytes_digest(record.data) != record.digest:
        message = "source chunk digest does not match its bytes"
        raise CorpusError(message)


def _validate_job_inputs(reader: CorpusReader, job: c.Job) -> None:
    grouped: dict[str, dict[str, list[c.Selection]]] = defaultdict(lambda: defaultdict(list))
    for selection in job.inputs:
        grouped[selection.family][selection.revision].append(selection)
    for family, requested in grouped.items():
        for record in reader.records(family):
            selections = requested.pop(revision_of(record), ())
            if not selections:
                continue
            body = payload(record)
            for selection in selections:
                if digest(field_value(body, selection.field)) != selection.digest:
                    message = "stage input field differs from its pinned selection"
                    raise CorpusError(message)
        if requested:
            message = f"stage input revisions are outside selected membership: {family}"
            raise CorpusError(message)


def _validate_realizations(
    reader: CorpusReader, records: tuple[c.Record, ...], checker: str
) -> None:
    proposed_realizations = [
        record for record in records if isinstance(record, (s.Mode, s.Capability))
    ]
    if proposed_realizations:
        from library_deep_enrichment.corpus.checker_epochs import CURRENT, HISTORICAL, fingerprint
        from library_deep_enrichment.semantics.historical_realization import (
            realize as historical_realize,
        )

        fingerprint(checker)
        produce = historical_realize if checker == HISTORICAL else realize
        assert checker in {CURRENT, HISTORICAL}
        expected = {revision_of(record) for record in produce(reader)}
        if any(revision_of(record) not in expected for record in proposed_realizations):
            message = "mode or capability does not follow from its approved schema, qualified assertions, and exact interface"
            raise CorpusError(message)


def validate_records(
    reader: CorpusReader, records: tuple[c.Record, ...], *, checker: str = "current"
) -> None:
    """Validate exact support, source normalization, and generated assurance receipts."""
    from library_deep_enrichment.corpus.python_documents import (
        validate as validate_python_documents,
    )

    validate_python_documents(reader, records)
    _validate_realizations(reader, records, checker)
    validate_shapes(reader, records)
    validate_analysis(reader, records)
    verified: set[c.Selection | c.ByteRange | tuple[str, str]] = set()
    for batch in batched(records, 128, strict=False):
        reader.prefetch(_small_prerequisites(batch, verified))
        _validate_record_batch(reader, batch, verified, checker=checker)


MAX_VERIFIED_PREREQUISITES = 200_000
PREFETCH_WINDOW = 128


def _small_prerequisites(
    records: tuple[c.Record, ...],
    verified: set[c.Selection | c.ByteRange | tuple[str, str]],
) -> Iterator[tuple[str, str]]:
    for record in records:
        supports = (
            (item.family, item.revision) if isinstance(item, c.Selection) else ("blobs", item.blob)
            for item in _supports(record)
            if not isinstance(record, c.Job) and item not in verified
        )
        window = tuple(islice(chain(references(record), supports), PREFETCH_WINDOW + 1))
        if len(window) <= PREFETCH_WINDOW:
            yield from (pair for pair in window if pair not in verified)


def _remember(
    verified: set[c.Selection | c.ByteRange | tuple[str, str]],
    item: c.Selection | c.ByteRange | tuple[str, str],
) -> None:
    if len(verified) < MAX_VERIFIED_PREREQUISITES:
        verified.add(item)


def _validate_supports(
    reader: CorpusReader,
    record: c.Record,
    verified: set[c.Selection | c.ByteRange | tuple[str, str]],
) -> None:
    # Consume each prefetched window before loading another. A large finite
    # evidence packet must not evict its entire read set before verification begins.
    for batch in batched(
        (item for item in _supports(record) if item not in verified), 128, strict=False
    ):
        reader.prefetch(
            (item.family, item.revision) for item in batch if isinstance(item, c.Selection)
        )
        for support in batch:
            if isinstance(support, c.Selection):
                resolve(reader, support)
            else:
                reader.get("blobs", support.blob)
            _remember(verified, support)


def _validate_references(
    reader: CorpusReader,
    record: c.Record,
    verified: set[c.Selection | c.ByteRange | tuple[str, str]],
) -> None:
    for batch in batched(
        (pair for pair in references(record) if pair not in verified), 128, strict=False
    ):
        reader.prefetch(batch)
        for pair in batch:
            reader.get(*pair)
            _remember(verified, pair)


def _validate_record_batch(
    reader: CorpusReader,
    records: tuple[c.Record, ...],
    verified: set[c.Selection | c.ByteRange | tuple[str, str]],
    *,
    checker: str = "current",
) -> None:
    """Validate a prefetched batch.

    Raises:
        CorpusError: A proposed qualification is forged.

    """
    for record in records:
        _check_byte_object(reader, record)
        validate_discovery(reader, record)
        if isinstance(record, FailureReceipt):
            validate_failure_receipt(reader, record)
        if isinstance(record, InputReceipt):
            validate_input_receipt(reader, record)
        validate_normalization(reader, record)
        validate_enrichment(reader, record)
        validate_native(reader, record)
        validate_identity(reader, record)
        validate_decision(reader, record, checker=checker)
        _validate_references(reader, record, verified)
        if isinstance(record, c.Job):
            _validate_job_inputs(reader, record)
        if not isinstance(record, c.Job):
            _validate_supports(reader, record, verified)
        if isinstance(record, c.Passage):
            _check_passage(reader, record)
        if isinstance(record, c.Qualification) and record.method == "checked-rule-consequence":
            proof = reader.get("proofs", record.support[0])
            if not isinstance(proof, s.Proof) or check_consequence(reader, proof) != record:
                message = f"forged consequence qualification: {revision_of(record)}"
                raise CorpusError(message)


def validate_staged(reader: AdmissionReader, *, checker: str = "current") -> None:
    """Validate the proposed records before any authoritative table writes.

    Raises:
        CorpusError: A qualification claims a method without an admitted checker.

    """
    records = tuple(
        REGISTRY[family].decode(row) for family, rows in reader.staged.items() for row in rows
    )
    validate_records(reader, records, checker=checker)
    for record in records:
        if isinstance(record, c.Qualification) and record.method != "checked-rule-consequence":
            message = f"qualification method has no admitted checker: {record.method}"
            raise CorpusError(message)
