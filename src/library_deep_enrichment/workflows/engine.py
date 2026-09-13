"""Coherent stage execution, content reuse, explicit failure currentness, and ownership."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

from attrs import frozen

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import (
    BudgetExceededError,
    CorpusError,
    PredecessorConflictError,
)
from library_deep_enrichment.corpus.contracts import AdmissionBatch, Disposition, Job, Member
from library_deep_enrichment.corpus.encoding import canonical, digest, payload
from library_deep_enrichment.corpus.evidence import select
from library_deep_enrichment.corpus.schemas import codec_for, revision_of
from library_deep_enrichment.corpus.validation import AdmissionReader
from library_deep_enrichment.workflows.contracts import (
    FamilySelector,
    InputReceipt,
    StageDefinition,
)
from library_deep_enrichment.workflows.failure_records import (
    StageProgress,
    coordinator_high_water_bytes,
    observe,
)
from library_deep_enrichment.workflows.inputs import capture

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from library_deep_enrichment.corpus.contracts import Record, Selection
    from library_deep_enrichment.corpus.store import Corpus, CorpusReader


@frozen(kw_only=True)
class StageResult:
    """The durable outcome of one exact requested stage generation."""

    manifest: str
    request: str
    reused: bool
    outputs: tuple[tuple[str, int], ...]
    elapsed_seconds: float


def overlay(reader: CorpusReader, records: Iterable[Record]) -> AdmissionReader:
    """Create a producer-only staged view for dependent projections in the same commit.

    Returns:
        An immutable-input view without persistent writer access.

    """
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        codec = codec_for(record)
        groups[codec.family].append(codec.encode(record))
    return AdmissionReader(reader, groups, replace=False)


def _check_definition(reader: CorpusReader, definition: StageDefinition) -> None:
    if definition.max_records <= 0 or definition.max_bytes <= 0 or definition.max_seconds <= 0:
        message = "stage resource limits must be positive"
        raise CorpusError(message)
    if {item.family for item in definition.inputs} & set(definition.outputs):
        message = "a stage cannot read its own output family as proof input"
        raise CorpusError(message)
    for dependency in definition.dependencies:
        receipt = reader.lookup("jobs", dependency)
        if not isinstance(receipt, Job) or receipt.disposition != Disposition.COMPLETE:
            message = f"required stage is not current and complete: {dependency}"
            raise CorpusError(message)


def _collect(
    definition: StageDefinition, outputs: Iterable[Record], started: float, progress: StageProgress
) -> tuple[Record, ...]:
    result: list[Record] = []
    total_bytes = 0
    for record in outputs:
        family = codec_for(record).family
        if family not in definition.outputs or family in {
            "policies",
            "reviews",
            "stage_definitions",
            "jobs",
        }:
            message = f"stage attempted an undeclared or independently owned family: {family}"
            raise CorpusError(message)
        total_bytes += len(canonical(payload(record)))
        result.append(record)
        progress.collected_records = len(result)
        progress.collected_payload_bytes = total_bytes
        if (
            len(result) > definition.max_records
            or total_bytes > definition.max_bytes
            or time.monotonic() - started > definition.max_seconds
        ):
            message = f"stage exceeded its record/byte/time boundary: {definition.logical_id}"
            raise BudgetExceededError(message)
    return tuple(result)


def _retire(reader: CorpusReader, previous: Job | None) -> tuple[Member, ...]:
    owned = set(previous.outputs) if previous else set()
    # Managed byte objects are shared immutable acquisition inputs. Withdrawing
    # a derived view never deletes bytes selected by another current record.
    return (
        tuple(
            member
            for member in reader.members()
            if member.revision in owned and member.family not in {"blobs", "blob_chunks"}
        )
        if owned
        else ()
    )


def run_stage(
    corpus: Corpus,
    definition: StageDefinition,
    produce: Callable[[CorpusReader], Iterable[Record]],
    *,
    selectors: tuple[FamilySelector, ...] = (),
) -> StageResult:
    """Run a finite trusted stage and admit all outputs together, or record failure.

    Returns:
        A durable exact-input result, including zero-producer warm reuse.

    """
    reader = corpus.reader()
    previous_record = reader.lookup("jobs", definition.logical_id, definition.profile)
    previous = previous_record if isinstance(previous_record, Job) else None
    receipts = capture(reader, definition, selectors)
    inputs = tuple(select(record, "/membership", "stage-input") for record in receipts)
    inputs = tuple(
        sorted(
            (*inputs, select(definition, "/implementation", "producer-contract")),
            key=lambda item: (item.family, item.revision, item.field, item.digest),
        )
    )
    request = digest(
        [
            revision_of(definition),
            [(item.family, item.revision, item.field, item.digest) for item in inputs],
        ]
    )
    if previous and previous.request == request and previous.disposition == Disposition.COMPLETE:
        return StageResult(
            manifest=reader.manifest_id,
            request=request,
            reused=True,
            outputs=(),
            elapsed_seconds=0.0,
        )
    return _execute_stage(
        corpus,
        StageRun(
            definition=definition,
            reader=reader,
            previous=previous,
            inputs=inputs,
            receipts=receipts,
            request=request,
            started=time.monotonic(),
        ),
        produce,
    )


@frozen(kw_only=True)
class StageRun:
    """One pinned stage request passed through execution and admission as a unit."""

    definition: StageDefinition
    reader: CorpusReader
    previous: Job | None
    inputs: tuple[Selection, ...]
    receipts: tuple[InputReceipt, ...]
    request: str
    started: float


def _previous_success(previous: Job | None) -> str:
    if previous is None:
        return ""
    return (
        revision_of(previous)
        if previous.disposition == Disposition.COMPLETE
        else previous.previous_success
    )


def _failure(corpus: Corpus, run: StageRun, error: BaseException, progress: StageProgress) -> None:
    failed = Job(
        logical_id=run.definition.logical_id,
        profile=run.definition.profile,
        stage=run.definition.logical_id,
        request=run.request,
        inputs=run.inputs,
        universes=(),
        outputs=(),
        disposition=Disposition.FAILED,
        reason=f"{type(error).__name__}: {str(error)[:4000]}",
        previous_success=_previous_success(run.previous),
    )
    Coordinator(corpus, WriterIdentity(principal="stage-failure")).commit(
        AdmissionBatch(
            records=(
                *run.receipts,
                run.definition,
                failed,
                observe(run.definition, failed, run.reader.manifest_id, progress, error),
            ),
            retire=_retire(run.reader, run.previous),
        ),
        expected=run.reader.manifest_id,
    )


def _execute_stage(
    corpus: Corpus, run: StageRun, produce: Callable[[CorpusReader], Iterable[Record]]
) -> StageResult:
    progress = StageProgress(
        started=run.started,
        coordinator_high_water_before_bytes=coordinator_high_water_bytes(),
    )
    try:
        manifest, records = _produce_and_commit(corpus, run, produce, progress)
    except PredecessorConflictError:
        raise
    except BaseException as error:
        _failure(corpus, run, error, progress)
        raise
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts[codec_for(record).family] += 1
    return StageResult(
        manifest=manifest,
        request=run.request,
        reused=False,
        outputs=tuple(sorted(counts.items())),
        elapsed_seconds=time.monotonic() - run.started,
    )


def _produce_and_commit(
    corpus: Corpus,
    run: StageRun,
    produce: Callable[[CorpusReader], Iterable[Record]],
    progress: StageProgress,
) -> tuple[str, tuple[Record, ...]]:
    _check_definition(run.reader, run.definition)
    source = AdmissionReader(
        run.reader, {}, replace=False, retire=_retire(run.reader, run.previous)
    )
    progress.phase = "produce"
    outputs = produce(source)
    progress.phase = "collect"
    records = _collect(run.definition, outputs, run.started, progress)
    job = Job(
        logical_id=run.definition.logical_id,
        profile=run.definition.profile,
        stage=run.definition.logical_id,
        request=run.request,
        inputs=run.inputs,
        universes=(),
        outputs=tuple(revision_of(item) for item in (*records, *run.receipts)),
        disposition=Disposition.COMPLETE,
        reason="Declared finite stage completed; product-specific frontiers remain explicit",
        previous_success=_previous_success(run.previous),
    )
    progress.phase = "admit"
    manifest = Coordinator(corpus, WriterIdentity(principal="stage-runner")).commit(
        AdmissionBatch(
            records=(*records, *run.receipts, run.definition, job),
            retire=_retire(run.reader, run.previous),
        ),
        expected=run.reader.manifest_id,
    )
    return manifest, records
