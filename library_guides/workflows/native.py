"""Supervised source extraction that publishes only through the unified coordinator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import asdict
from cattrs import Converter

from library_guides.corpus.encoding import bytes_digest, digest
from library_guides.facts.contracts import SemanticProfile, SourceSnapshot
from library_guides.native_admission import NativeBuilder, stage_artifact
from library_guides.source_pipeline import extract, resolved_manifest
from library_guides.store.digests import digest_file
from library_guides.workflows.contracts import StageDefinition
from library_guides.workflows.engine import run_stage

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import Corpus, CorpusReader
    from library_guides.workflows.engine import StageResult


def build(
    corpus: Corpus, source: Path, transport: Path, *, catalog: Path | None = None
) -> StageResult:
    """Execute a finite source manifest with tracked failures and immutable corpus outputs.

    Returns:
        A current stage receipt. Disposable worker transport files never serve queries.

    """
    manifest = resolved_manifest(source)
    converter = Converter(forbid_extra_keys=True)
    snapshots = (
        {}
        if catalog is None
        else {
            item.id: item
            for item in converter.structure(
                json.loads(catalog.read_bytes()), tuple[SourceSnapshot, ...]
            )
        }
    )
    paths = {
        path
        for job in manifest.jobs
        for path in (
            job.input,
            job.helper,
            job.schema,
            *(item[0] for item in job.inputs),
            *(item.path for item in job.witnesses),
        )
    }
    paths.update(
        str(transport / item.path) for snapshot in snapshots.values() for item in snapshot.files
    )
    observed_inputs = {}
    for path in sorted(paths):
        try:
            observed_inputs[path] = digest_file(Path(path))
        except OSError:
            observed_inputs[path] = "unavailable"
    implementation = digest(
        {
            "manifest": asdict(manifest),
            "observed_inputs": observed_inputs,
            "catalog": [asdict(item) for item in snapshots.values()],
            "code": {
                name: bytes_digest((Path(__file__).parents[1] / name).read_bytes())
                for name in (
                    "workflows/native.py",
                    "native_admission.py",
                    "source_pipeline.py",
                    "worker_runtime.py",
                    "corpus/declarations.py",
                )
            },
        }
    )
    definition = StageDefinition(
        logical_id=f"source-build:{source.name}",
        inputs=(),
        dependencies=(),
        implementation=implementation,
        outputs=(
            "native_artifacts",
            "native_facts",
            "contexts",
            "source_files",
            "raw_observations",
            "operations",
            "entities",
            "type_nodes",
            "type_uses",
            "relations",
            "passages",
            "blobs",
            "blob_chunks",
        ),
        max_records=1_500_000,
        max_bytes=4 * 1024**3,
        max_seconds=3600.0,
    )

    def produce(_reader: CorpusReader) -> Iterator[Record]:
        builder = NativeBuilder(implementation, max_records=definition.max_records)
        for job in manifest.jobs:
            artifact = extract(transport, job, manifest.budget)
            receipt = json.loads((transport / artifact.receipt_path).read_bytes())
            profile = converter.structure(receipt["semantic_profile"], SemanticProfile)
            stage_artifact(builder, transport, artifact, profile, snapshots)
        yield from builder.records.values()

    return run_stage(corpus, definition, produce)
