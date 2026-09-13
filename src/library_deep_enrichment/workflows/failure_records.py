"""Typed failed-attempt observations, separate from current behavioral products."""

from __future__ import annotations

import math
import resource
import time
from typing import TYPE_CHECKING

from attrs import define, frozen

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Disposition, Job, Record
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.worker_observations import WorkerObservation, failure_observations
from library_deep_enrichment.workflows.contracts import StageDefinition

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader


@define(kw_only=True)
class StageProgress:
    """Coordinator counters; yielded records stay private until atomic admission."""

    started: float
    phase: str = "definition"
    collected_records: int = 0
    collected_payload_bytes: int = 0
    coordinator_high_water_before_bytes: int = 0


@frozen(kw_only=True)
class FailureReceipt(Record):
    """Exact failed job and observed work, without claiming internal completed owners."""

    definition: str
    job: str
    request: str
    input_manifest: str
    phase: str
    collected_records: int
    collected_payload_bytes: int
    elapsed_seconds: float
    coordinator_high_water_before_bytes: int
    coordinator_high_water_after_bytes: int
    worker: tuple[WorkerObservation, ...]
    interpretation: str = "uncommitted-observation.v1"


def coordinator_high_water_bytes() -> int:
    """Observe Linux coordinator process lifetime high-water RSS, excluding children.

    Returns:
        Process lifetime high-water RSS; this is not a per-stage peak estimate.

    """
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def observe(
    definition: StageDefinition,
    job: Job,
    manifest: str,
    progress: StageProgress,
    error: BaseException,
) -> FailureReceipt:
    """Freeze the private counters alongside an exact failed job.

    Returns:
        A diagnostic record referencing only the failed job and owning declaration.

    """
    return FailureReceipt(
        logical_id=f"stage-failure:{definition.logical_id}",
        profile=definition.profile,
        definition=revision_of(definition),
        job=revision_of(job),
        request=job.request,
        input_manifest=manifest,
        phase=progress.phase,
        collected_records=progress.collected_records,
        collected_payload_bytes=progress.collected_payload_bytes,
        elapsed_seconds=time.monotonic() - progress.started,
        coordinator_high_water_before_bytes=progress.coordinator_high_water_before_bytes,
        coordinator_high_water_after_bytes=coordinator_high_water_bytes(),
        worker=failure_observations(error),
    )


def validate(reader: CorpusReader, record: FailureReceipt) -> None:
    """Check provenance and counter semantics without certifying observed computation.

    Raises:
        CorpusError: The receipt changes its job, declaration or observational meaning.

    """
    definition = reader.get("stage_definitions", record.definition)
    job = reader.get("jobs", record.job)
    if not isinstance(definition, StageDefinition) or not isinstance(job, Job):
        message = "failed attempt does not identify a job and stage definition"
        raise CorpusError(message)
    expected = (Disposition.FAILED, (), definition.logical_id, record.request, definition.profile)
    actual = (job.disposition, job.outputs, job.stage, job.request, job.profile)
    provenance = any(
        item.family == "stage_definitions" and item.revision == record.definition
        for item in job.inputs
    )
    if actual != expected or not provenance or record.profile != definition.profile:
        message = "failed attempt does not retain its exact job and observational contract"
        raise CorpusError(message)
    valid = (
        record.logical_id == f"stage-failure:{definition.logical_id}",
        record.interpretation == "uncommitted-observation.v1",
        record.phase in {"definition", "produce", "collect", "admit"},
        min(record.collected_records, record.collected_payload_bytes) >= 0,
        math.isfinite(record.elapsed_seconds),
        record.elapsed_seconds >= 0,
        0
        <= record.coordinator_high_water_before_bytes
        <= record.coordinator_high_water_after_bytes,
        len(record.worker) <= 1,
    )
    if not all(valid):
        message = "failed attempt contains invalid observational counters"
        raise CorpusError(message)
    for item in record.worker:
        _validate_worker(item)


def _validate_worker(item: WorkerObservation) -> None:
    valid = (
        bool(item.request),
        bool(item.input_digest),
        math.isfinite(item.elapsed_seconds),
        item.elapsed_seconds >= 0,
        min(item.peak_sampled_tree_rss_bytes, item.rss_samples, item.output_bytes) >= 0,
        0 <= item.consumed_records <= item.delivered_records,
        len(item.expected_records) <= 1,
        all(value >= 0 for value in item.expected_records),
        0 < item.rss_limit_bytes <= item.address_space_limit_bytes,
        item.internal_progress == "unobserved",
        not item.terminal_seen or item.expected_records == (item.delivered_records,),
    )
    if not all(valid):
        message = "worker failure observation contains impossible or overstated counters"
        raise CorpusError(message)
