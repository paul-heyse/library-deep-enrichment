"""Manifest-driven extraction wired to immutable V3 fact artifacts."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

import yaml
from attrs import asdict, field, frozen
from cattrs import Converter
from filelock import FileLock
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from library_guides.collection import CollectionError, confined
from library_guides.facts.context import observed
from library_guides.facts.context import verify as verify_context
from library_guides.facts.contracts import (
    Budget,
    FactArtifact,
    FactHead,
    FactShard,
    FileEntry,
    SemanticProfile,
)
from library_guides.facts.store import build_index, verify
from library_guides.schemas import schema_for
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import sync_directory, write_atomic
from library_guides.worker_runtime import WorkerRequest, run

_CONVERTER = Converter(forbid_extra_keys=True)
_LANE_SCHEMAS = {
    "declarations": "library-guides.declaration.v1",
    "cargo": "library-guides.cargo.v1",
    "cargo_messages": "library-guides.cargo-messages.v1",
    "syntax": "library-guides.source-facts.v1",
    "execution": "library-guides.source-execution.v1",
    "types": "library-guides.python-semantics.v1",
    "mir": "library-guides.mir.v1",
    "mir_execution": "library-guides.mir-execution.v1",
    "mir_instances": "library-guides.mir-instances.v1",
    "mir_callables": "library-guides.mir-callables.v1",
    "mir_lifecycle": "library-guides.mir-lifecycle.v1",
    "mir_memory": "library-guides.mir-memory.v1",
}


@frozen(kw_only=True)
class SourceJob:
    """One frozen input and pinned native producer under a named profile."""

    id: str
    kind: Literal[
        "declarations",
        "cargo",
        "cargo_messages",
        "syntax",
        "execution",
        "types",
        "mir",
        "mir_execution",
        "mir_instances",
        "mir_callables",
        "mir_lifecycle",
        "mir_memory",
    ]
    input: str
    helper: str
    profile: str
    schema: str
    context: str = ""
    inputs: tuple[tuple[str, str], ...] = ()
    isolate: bool = False
    snapshots: tuple[str, ...] = ()
    compression: Literal["none", "zstd", "gzip"] = "none"
    expected_input: str = ""
    semantic_profile: SemanticProfile | None = None
    witnesses: tuple[FileEntry, ...] = ()


@frozen(kw_only=True)
class SourceManifest:
    """Finite extraction universe and explicit resource policy."""

    schema_version: Literal["library-guides.source-manifest.v1"]
    jobs: tuple[SourceJob, ...]
    budget: Budget = field(factory=Budget)


def read_manifest(path: Path) -> SourceManifest:
    """Validate a source manifest before resolving paths or running commands.

    Returns:
        Strict typed source jobs.

    Raises:
        CollectionError: If identifiers or profiles are missing or repeated.

    """
    raw = yaml.safe_load(path.read_bytes())
    Draft202012Validator(schema_for(SourceManifest)).validate(raw)
    manifest = _CONVERTER.structure(raw, SourceManifest)
    if (
        not manifest.jobs
        or len({job.id for job in manifest.jobs}) != len(manifest.jobs)
        or any(not job.id or not job.profile for job in manifest.jobs)
    ):
        message = "source job identities/profiles must be nonempty and unique"
        raise CollectionError(message)
    return manifest


def job_key(job: SourceJob) -> str:
    """Fingerprint exact producer, input, owned schema and applicability.

    Returns:
        A content-derived extraction request key.

    Raises:
        CollectionError: If a declared semantic input has changed.

    """
    for path, expected in job.inputs:
        if digest_file(Path(path)) != expected:
            message = f"declared semantic input changed: {path}"
            raise CollectionError(message)
    for witness in job.witnesses:
        path = Path(witness.path)
        if path.stat().st_size != witness.size or digest_file(path) != witness.digest:
            message = f"declared provenance witness changed: {witness.path}"
            raise CollectionError(message)
    if job.expected_input and digest_file(Path(job.input)) != job.expected_input:
        message = "source input differs from its acquisition receipt"
        raise CollectionError(message)
    if job.semantic_profile is not None:
        verify_context(job.semantic_profile)
    if job.context and (job.semantic_profile is None or job.context != job.semantic_profile.id):
        message = "named context requires its verified semantic profile"
        raise CollectionError(message)
    return digest_bytes(
        canonical_bytes(
            {
                "job": asdict(job),
                "input": digest_file(Path(job.input)),
                "helper": digest_file(Path(job.helper)),
                "schema": digest_file(Path(job.schema)),
                "protocol": "library-guides.facts.v1",
                "ingestion": {
                    name: digest_file(Path(__file__).parent / name)
                    for name in (
                        "source_pipeline.py",
                        "worker_runtime.py",
                        "_worker_entry.py",
                        "facts/protocol.py",
                        "facts/contracts.py",
                        "facts/store.py",
                        "facts/witness_origins.py",
                        "facts/context.py",
                    )
                },
            }
        )
    )


def artifact_index(root: Path, artifact: FactArtifact) -> Path:
    """Locate a disposable index within the selected fact artifact.

    Returns:
        Collection-confined index path.

    """
    return confined(root, artifact.receipt_path).parent / "index.sqlite"


def cached(root: Path, key: str) -> FactArtifact | None:
    """Reuse only complete, byte-verified artifacts.

    Returns:
        Valid artifact or a cache miss when any component is corrupt or incomplete.

    """
    path = root / "facts" / key / "artifact.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_bytes())
        Draft202012Validator(schema_for(FactArtifact)).validate(raw)
        artifact = _CONVERTER.structure(raw, FactArtifact)
        verify(root, artifact)
        if artifact.outcome != "complete":
            return None
    except OSError, ValueError, CollectionError, ValidationError:
        return None
    return artifact


def extract(root: Path, job: SourceJob, budget: Budget) -> FactArtifact:
    """Normalize to private staging and commit after complete receipt validation.

    Returns:
        Verified artifact; unchanged inputs execute no worker.

    Raises:
        CollectionError: If the source exceeds budget or extraction is incomplete.

    """
    key = job_key(job)
    store = root / "facts"
    store.mkdir(parents=True, exist_ok=True)
    with FileLock(str(store / f"{key}.lock"), timeout=budget.wall_seconds):
        if artifact := cached(root, key):
            return artifact
        if Path(job.input).stat().st_size > budget.input_bytes:
            message = "source exceeds input budget"
            raise CollectionError(message)
        staging = Path(tempfile.mkdtemp(prefix="extract-", dir=store))
        try:
            artifact = _extract(staging, key, job, budget)
            _commit(root, staging, key, artifact)
        except BaseException:
            if staging.exists():
                shutil.rmtree(staging)
            raise
    return artifact


def _extract(staging: Path, key: str, job: SourceJob, budget: Budget) -> FactArtifact:
    source = staging / "input.json"
    acquisition = staging / "acquired.source"
    shutil.copyfile(job.input, acquisition)
    _materialize(acquisition, source, job.compression, budget.input_bytes)
    source_digest = digest_file(source)
    validator = Draft202012Validator(json.loads(Path(job.schema).read_bytes()))
    relative = f"facts/{key}"
    witnesses = _retain_witnesses(staging, relative, job.witnesses, budget.input_bytes)
    rows = staging / "records.jsonl"
    seen: set[str] = set()
    with rows.open("wb") as output:

        def consume(record: dict[str, object]) -> None:
            validator.validate(record)
            identifier = record.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in seen:
                message = "missing or duplicate fact identity"
                raise CollectionError(message)
            seen.add(identifier)
            output.write(canonical_bytes(record) + b"\n")

        mode = {"cargo": "cargo-normalize", "cargo_messages": "cargo-messages"}.get(
            job.kind, "normalize"
        )
        receipt = run(
            WorkerRequest(
                argv=(str(Path(job.helper).resolve()), mode, str(source.resolve()), key),
                cwd=staging.resolve(),
                request_id=key,
                input_digest=source_digest,
                budget=budget,
                isolate=job.isolate,
                read_roots=(
                    Path(job.helper).resolve().parent,
                    *(Path(path).resolve().parent for path, _ in job.inputs),
                ),
                write_roots=(staging.resolve(),),
            ),
            consume,
        )
        output.flush()
        os.fsync(output.fileno())
    if digest_file(Path(job.input)) != digest_file(acquisition) or job_key(job) != key:
        message = "input or producer changed during extraction"
        raise CollectionError(message)
    terminal = receipt["terminal"]
    if not isinstance(terminal, dict) or terminal["coverage"]["state"] != "complete":
        message = "incomplete extraction cannot commit as a complete artifact"
        raise CollectionError(message)
    receipt["request_key"] = key
    receipt["producer_digest"] = digest_file(Path(job.helper))
    receipt["schema_digest"] = digest_file(Path(job.schema))
    receipt["profile"] = job.profile
    header = receipt["header"]
    header = _verify_header(header, job)
    context = job.semantic_profile or observed(header, job.kind, source_digest)
    receipt["context"] = context.id
    receipt["semantic_profile"] = asdict(context)
    receipt["job"] = job.id
    receipt["snapshots"] = job.snapshots
    receipt["witnesses"] = [asdict(item) for item in witnesses]
    receipt["witness_origins"] = {
        "model": "library-guides.witness-origins.v1",
        "entries": [
            {"original_path": original.path, "retained": asdict(retained)}
            for original, retained in zip(job.witnesses, witnesses, strict=True)
        ],
    }
    write_atomic(staging / "header.json", canonical_bytes(receipt["header"]))
    write_atomic(staging / "receipt.json", canonical_bytes(receipt))
    artifact = FactArtifact(
        id=f"facts:{key}",
        schema=str(header["schema"]),
        profile=job.profile,
        producer=receipt["producer_digest"],
        input_path=f"{relative}/input.json",
        input_digest=source_digest,
        header_path=f"{relative}/header.json",
        receipt_path=f"{relative}/receipt.json",
        receipt_digest=digest_file(staging / "receipt.json"),
        shards=(
            FactShard(
                path=f"{relative}/records.jsonl", digest=digest_file(rows), records=len(seen)
            ),
        ),
        outcome="complete",
        artifact_kind="cargo" if job.kind == "cargo_messages" else job.kind,
        job=job.id,
        context=context.id,
        snapshots=job.snapshots,
        acquisition_path=f"{relative}/acquired.source",
        acquisition_digest=digest_file(acquisition),
        witnesses=witnesses,
    )
    write_atomic(staging / "artifact.json", canonical_bytes(asdict(artifact)))
    return artifact


def _retain_witnesses(
    staging: Path, relative: str, inputs: tuple[FileEntry, ...], limit: int
) -> tuple[FileEntry, ...]:
    from attrs import evolve

    if sum(item.size for item in inputs) > limit:
        message = "provenance witnesses exceed input budget"
        raise CollectionError(message)
    result = []
    for number, item in enumerate(inputs):
        path = staging / "witnesses" / f"{number}-{item.digest}"
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item.path, path)
        if path.stat().st_size != item.size or digest_file(path) != item.digest:
            message = "provenance witness changed during acquisition"
            raise CollectionError(message)
        result.append(evolve(item, path=f"{relative}/witnesses/{path.name}"))
    return tuple(result)


def _materialize(source: Path, destination: Path, compression: str, limit: int) -> None:
    import gzip
    from compression import zstd

    opener = {"none": open, "gzip": gzip.open, "zstd": zstd.open}[compression]
    count = 0
    with opener(source, "rb") as input_stream, destination.open("wb") as output:
        while chunk := input_stream.read(65536):
            count += len(chunk)
            if count > limit:
                message = "decompressed source exceeds input budget"
                raise CollectionError(message)
            output.write(chunk)


def plan(root: Path, path: Path) -> dict[str, object]:
    """Resolve manifest paths and report actual artifact reuse without mutation.

    Returns:
        Declared jobs and their verified cache state.

    """
    manifest = resolved_manifest(path)
    jobs = [
        {
            "job": asdict(job),
            "key": job_key(job),
            "state": "reused" if cached(root, job_key(job)) else "required",
        }
        for job in manifest.jobs
    ]
    return {"schema": manifest.schema_version, "jobs": jobs, "budget": asdict(manifest.budget)}


def resolved_manifest(path: Path) -> SourceManifest:
    """Resolve operator-owned paths relative to the source manifest.

    Returns:
        The same typed manifest with explicit absolute file locations.

    """
    from attrs import evolve

    manifest = read_manifest(path)
    return evolve(
        manifest,
        jobs=tuple(
            evolve(
                job,
                input=str((path.parent / job.input).resolve()),
                helper=str((path.parent / job.helper).resolve()),
                schema=str((path.parent / job.schema).resolve()),
                inputs=tuple(
                    (str((path.parent / input_path).resolve()), digest)
                    for input_path, digest in job.inputs
                ),
                witnesses=tuple(
                    evolve(item, path=str((path.parent / item.path).resolve()))
                    for item in job.witnesses
                ),
            )
            for job in manifest.jobs
        ),
    )


def _commit(root: Path, staging: Path, key: str, artifact: FactArtifact) -> None:
    store = root / "facts"
    destination = store / key
    if destination.exists():
        destination.rename(store / f"{key}.invalid-{staging.name}")
    staging.rename(destination)
    sync_directory(store)
    verify(root, artifact)
    build_index(root, artifact, artifact_index(root, artifact))


def build(root: Path, path: Path) -> dict[str, object]:
    """Execute declared jobs and attach verified products with explicit failed heads.

    Returns:
        Current artifact identities and per-job outcomes.

    Raises:
        CollectionError: If no V3 authority exists or the authoring view changed.

    """
    from attrs import evolve

    from library_guides.collection import load, save
    from library_guides.knowledge_v3 import KnowledgeV3

    knowledge = load(root)
    if not isinstance(knowledge, KnowledgeV3):
        message = "source extraction requires an explicitly migrated V3 collection"
        raise CollectionError(message)
    before = digest_file(root / "knowledge.yaml")
    manifest = resolved_manifest(path)
    artifacts = []
    contexts = {profile.id: profile for profile in knowledge.semantic_profiles}
    heads = []
    for job in manifest.jobs:
        request = "unavailable"
        try:
            request = job_key(job)
            artifact = extract(root, job, manifest.budget)
        except (OSError, ValueError, RuntimeError, ValidationError) as error:
            heads.append(
                FactHead(
                    job=job.id,
                    profile=job.profile,
                    request=request,
                    artifact=None,
                    outcome="failed",
                    reason=str(error),
                )
            )
        else:
            artifacts.append(artifact)
            receipt = json.loads(confined(root, artifact.receipt_path).read_bytes())
            context = _CONVERTER.structure(receipt["semantic_profile"], SemanticProfile)
            verify_context(context)
            contexts[context.id] = context
            heads.append(
                FactHead(
                    job=job.id,
                    profile=job.profile,
                    request=request,
                    artifact=artifact.id,
                    outcome="complete",
                )
            )
    if digest_file(root / "knowledge.yaml") != before:
        message = "authoring changed during extraction; artifacts retained, attachment refused"
        raise CollectionError(message)
    replaced = {(item.job, item.profile) for item in heads}
    retained_heads = tuple(
        item for item in knowledge.fact_heads if (item.job, item.profile) not in replaced
    )
    retained = tuple(
        item
        for item in knowledge.fact_artifacts
        if item.id not in {artifact.id for artifact in artifacts}
    )
    with FileLock(str(root / "knowledge.lock"), timeout=manifest.budget.wall_seconds):
        if digest_file(root / "knowledge.yaml") != before:
            message = "authoring changed before attachment; verified artifacts retained"
            raise CollectionError(message)
        save(
            root,
            evolve(
                knowledge,
                fact_artifacts=retained + tuple(artifacts),
                fact_heads=retained_heads + tuple(heads),
                semantic_profiles=tuple(contexts.values()),
            ),
        )
    report: dict[str, object] = {
        "state": "complete" if all(head.outcome == "complete" for head in heads) else "partial",
        "artifacts": [asdict(item) for item in artifacts],
        "jobs": [asdict(item) for item in heads],
    }
    write_atomic(root / "source-build-report.json", canonical_bytes(report))
    return report


def _verify_header(header: object, job: SourceJob) -> dict[str, object]:
    if not isinstance(header, dict) or header.get("profile", job.profile) != job.profile:
        message = "worker semantic profile mismatch"
        raise CollectionError(message)
    if header.get("schema") != _LANE_SCHEMAS[job.kind]:
        message = "worker schema does not match the requested evidence lane"
        raise CollectionError(message)
    return header
