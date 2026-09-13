"""Read-only analytical workers use the existing supervised native transport."""

from __future__ import annotations

import base64
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import frozen

from library_deep_enrichment.corpus.backend import BudgetExceededError, CorpusError
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical, digest
from library_deep_enrichment.corpus.schemas import REGISTRY, revision_of
from library_deep_enrichment.corpus.validation import AdmissionReader
from library_deep_enrichment.discovery.contracts import DiscoveryScope
from library_deep_enrichment.facts.contracts import Budget
from library_deep_enrichment.worker_runtime import WorkerExecutionError, WorkerLimitError, WorkerRequest, run
from library_deep_enrichment.workflows.contracts import ExecutionReceipt, StageDefinition

BUDGET_EXIT = 75
MAX_WORKER_MEMORY = 64 * 1024**3

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader


def memory_budget(default: int) -> int:
    """Resolve an explicit canary setting before capturing the worker request.

    Returns:
        The selected positive RSS ceiling, retaining the supplied default when unset.

    Raises:
        CorpusError: An explicit resource setting is malformed or outside the supported range.

    """
    configured = os.environ.get("LDE_ANALYTICAL_MEMORY_BYTES")
    try:
        value = default if configured is None else int(configured)
    except ValueError as error:
        message = "LDE_ANALYTICAL_MEMORY_BYTES must be a positive integer"
        raise CorpusError(message) from error
    if not 0 < value <= MAX_WORKER_MEMORY:
        message = "analytical memory ceiling must be positive and at most 64 GiB"
        raise CorpusError(message)
    return value


@frozen(kw_only=True)
class AnalyticalRequest:
    """A pinned read view and finite producer route; no writer capability is supplied."""

    root: str
    manifest: str
    max_rows: int
    retired: tuple[tuple[str, str, str], ...]
    route: str
    scope: DiscoveryScope | None
    max_records: int
    max_bytes: int
    subject: str = ""
    memory_bytes: int = 4_000_000_000


def _binary_values(value: object) -> object:
    if isinstance(value, dict):
        if set(value) == {"$bytes"} and isinstance(value["$bytes"], str):
            return base64.b64decode(value["$bytes"], validate=True)
        return {key: _binary_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_binary_values(item) for item in value]
    return value


@frozen(kw_only=True)
class RemoteProducer:
    """Run an allowlisted producer with time, address-space, CPU, and output ceilings."""

    root: Path
    definition: StageDefinition
    route: str
    scope: DiscoveryScope | None = None
    subject: str = ""
    memory_bytes: int = 4_000_000_000

    def __call__(self, reader: CorpusReader) -> tuple[Record, ...]:
        """Return checked worker records for independent coordinator admission.

        Returns:
            Complete typed output, never a prefix from an interrupted process.

        Raises:
            CorpusError: The supervised entry point received an unsupported reader or row.
            BudgetExceededError: The worker or supervisor enforces a declared bound.

        """
        if not isinstance(reader, AdmissionReader) or reader.staged or reader.replace:
            message = "analytical worker requires the pinned stage input overlay"
            raise CorpusError(message)
        request = AnalyticalRequest(
            root=str(self.root.resolve()),
            manifest=reader.manifest_id,
            max_rows=reader.max_rows,
            retired=tuple(sorted(reader.keys)),
            route=self.route,
            scope=self.scope,
            max_records=self.definition.max_records,
            max_bytes=self.definition.max_bytes,
            subject=self.subject,
            memory_bytes=memory_budget(self.memory_bytes),
        )
        body = CONVERTER.unstructure(request)
        identity = digest(body)
        records: list[Record] = []

        def consume(frame: dict[str, object]) -> None:
            family, row = frame.get("family"), _binary_values(frame.get("row"))
            if (
                set(frame) != {"family", "row"}
                or not isinstance(family, str)
                or not isinstance(row, dict)
            ):
                message = "invalid analytical record envelope"
                raise CorpusError(message)
            if family not in self.definition.outputs:
                message = "analytical worker emitted an undeclared family"
                raise CorpusError(message)
            records.append(REGISTRY[family].decode(row))

        with tempfile.TemporaryDirectory(prefix="library-guides-analysis-") as directory:
            path = Path(directory) / "request.json"
            path.write_bytes(canonical(body))
            try:
                result = run(
                    WorkerRequest(
                        argv=(
                            "/usr/bin/env",
                            "MALLOC_ARENA_MAX=2",
                            "TOKIO_WORKER_THREADS=2",
                            "OPENBLAS_NUM_THREADS=1",
                            "OMP_NUM_THREADS=1",
                            "RAYON_NUM_THREADS=1",
                            sys.executable,
                            "-m",
                            "library_deep_enrichment.workflows.worker",
                            str(path),
                        ),
                        cwd=Path(directory),
                        request_id=identity,
                        input_digest=identity,
                        address_space_bytes=64 * 1024**3,
                        budget=Budget(
                            wall_seconds=math.ceil(self.definition.max_seconds),
                            cpu_seconds=math.ceil(self.definition.max_seconds),
                            output_bytes=self.definition.max_bytes + 64_000,
                            max_records=self.definition.max_records,
                            memory_bytes=request.memory_bytes,
                        ),
                    ),
                    consume,
                )
            except WorkerLimitError as error:
                raise BudgetExceededError(str(error)) from error
            except WorkerExecutionError as error:
                if error.returncode == BUDGET_EXIT:
                    raise BudgetExceededError(str(error)) from error
                raise CorpusError(str(error)) from error
        return (
            *records,
            ExecutionReceipt(
                logical_id=f"stage-execution:{self.definition.logical_id}",
                profile=self.definition.profile,
                definition=revision_of(self.definition),
                request=identity,
                input_manifest=reader.manifest_id,
                route=self.route,
                elapsed_seconds=float(str(result["elapsed_seconds"])),
                peak_sampled_tree_rss_bytes=int(str(result["peak_sampled_tree_rss_bytes"])),
                output_bytes=int(str(result["output_bytes"])),
                records=len(records),
                rss_limit_bytes=int(str(result["rss_limit_bytes"])),
                address_space_limit_bytes=int(str(result["address_space_limit_bytes"])),
            ),
        )
