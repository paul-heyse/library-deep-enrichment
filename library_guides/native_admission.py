"""One admission path for verified native workers and finite archival lane migration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import asdict, frozen

from library_guides.collection import confined
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import ByteRange, Context, Disposition, SourceFile
from library_guides.corpus.declarations import normalize_native_declaration
from library_guides.corpus.encoding import bytes_digest, digest
from library_guides.corpus.native_contracts import NativeArtifact, NativeFact
from library_guides.corpus.staging import ObservationBuilder
from library_guides.facts.context import observed
from library_guides.facts.context import verify as verify_context
from library_guides.facts.store import verify
from library_guides.source_snapshots import verify as verify_snapshot
from library_guides.store.digests import digest_file
from library_guides.workflows.contracts import StageDefinition
from library_guides.workflows.engine import run_stage

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import Corpus, CorpusReader
    from library_guides.facts.contracts import FactArtifact, SemanticProfile, SourceSnapshot
    from library_guides.workflows.engine import StageResult

MAX_NATIVE_RECORDS = 1_500_000


@frozen(kw_only=True)
class NativeInputs:
    """An explicit frozen native scope, usable without any legacy knowledge file."""

    root: Path
    artifacts: tuple[FactArtifact, ...]
    profiles: tuple[SemanticProfile, ...] = ()
    snapshots: tuple[SourceSnapshot, ...] = ()
    stage: str = "native-scope"


@frozen(kw_only=True)
class SourceOrigin:
    """Attribution and applicability for one acquired file population."""

    profile: str
    package: str
    locator: str
    attribution: str


class NativeBuilder(ObservationBuilder):
    """Bounded native staging and the shared declaration-normalization sink."""

    def blob(self, data: bytes, media_type: str) -> ByteRange:
        """Retain original source bytes for declaration normalization.

        Returns:
            A managed original-byte range.

        """
        return self.own_bytes(data, media_type=media_type)

    def source(self, root: Path, path: str, origin: SourceOrigin, *, expected: str = "") -> str:
        """Stage exact source bytes and their independently verified acquisition identity.

        Returns:
            The attributed source revision.

        Raises:
            CorpusError: A source file differs from its frozen acquisition.

        """
        data = confined(root, path).read_bytes()
        if expected and bytes_digest(data) != expected:
            msg = "native source content differs from acquisition manifest"
            raise CorpusError(msg)
        selection = self.blob(data, "application/octet-stream")
        return self.add(
            SourceFile(
                logical_id=f"native-source:{origin.locator}:{path}",
                profile=origin.profile,
                blob=selection.blob,
                package=origin.package,
                path=path,
                locator=origin.locator,
                license=origin.attribution,
                acquisition=f"sha256:{selection.digest}",
            )
        )


def _context(
    builder: NativeBuilder, artifact: FactArtifact, profile: SemanticProfile | None
) -> tuple[str, str]:
    observed = builder.observe(
        f"native-context-source:{artifact.context or artifact.id}",
        asdict(profile) if profile else {"unknown": artifact.context},
        profile=artifact.profile,
        kind="native-context",
    )
    context = Context(
        logical_id=f"native-context:{artifact.context or artifact.id}",
        profile=artifact.profile,
        language="python"
        if artifact.artifact_kind in {"types", "lexical", "execution"}
        else "mixed"
        if artifact.artifact_kind == "syntax"
        else "rust",
        package=profile.package if profile else "",
        version=profile.version if profile else "",
        toolchain=profile.toolchain if profile else "unknown",
        target=(profile.target or "") if profile else "",
        features=(),
        components=profile.dependency_digests if profile else (),
        evidence=(
            builder.select(observed, "/package", "context")
            if profile
            else builder.select(observed, "/unknown", "unresolved-context"),
        ),
    )
    return builder.add(context), context.version


def _sources(
    builder: NativeBuilder,
    root: Path,
    artifact: FactArtifact,
    profile: SemanticProfile | None,
    snapshots: dict[str, SourceSnapshot],
) -> tuple[str, ...]:
    sources: list[str] = []
    for identifier in artifact.snapshots:
        snapshot = snapshots.get(identifier)
        if snapshot is None:
            msg = "native artifact requires a missing frozen source snapshot"
            raise CorpusError(msg)
        verify_snapshot(root, snapshot)
        sources.extend(
            builder.source(
                root,
                item.path,
                SourceOrigin(
                    profile=artifact.profile,
                    package=snapshot.package,
                    locator=snapshot.id,
                    attribution=snapshot.attribution,
                ),
                expected=item.digest,
            )
            for item in snapshot.files
        )
    sources.extend(
        builder.source(
            root,
            item.path,
            SourceOrigin(
                profile=artifact.profile,
                package=profile.package if profile else "",
                locator=artifact.id,
                attribution="retained provenance witness",
            ),
            expected=item.digest,
        )
        for item in artifact.witnesses
    )
    if artifact.acquisition_path:
        sources.append(
            builder.source(
                root,
                artifact.acquisition_path,
                SourceOrigin(
                    profile=artifact.profile,
                    package=profile.package if profile else "",
                    locator=artifact.id,
                    attribution="upstream acquisition receipt",
                ),
                expected=artifact.acquisition_digest,
            )
        )
    return tuple(sorted(set(sources)))


def stage_artifact(
    builder: NativeBuilder,
    root: Path,
    artifact: FactArtifact,
    profile: SemanticProfile | None,
    snapshots: dict[str, SourceSnapshot],
) -> None:
    """Stage all verified native rows, their original bytes, and exact context.

    Raises:
        CorpusError: The native stream has duplicate identities or an invalid count.

    """
    verify(root, artifact)
    if profile is None:
        profile = observed(
            json.loads(confined(root, artifact.header_path).read_bytes()),
            artifact.artifact_kind,
            artifact.input_digest,
        )
    verify_context(profile)
    context, version = _context(builder, artifact, profile)
    sources = _sources(builder, root, artifact, profile, snapshots)

    def own(path: str, media_type: str) -> ByteRange:
        return builder.blob(confined(root, path).read_bytes(), media_type)

    shards = tuple(own(item.path, "application/x-ndjson") for item in artifact.shards)
    native = NativeArtifact(
        logical_id=f"native-artifact:{artifact.id}",
        profile=artifact.profile,
        external_id=artifact.id,
        lane=artifact.artifact_kind,
        schema=artifact.schema,
        context=context,
        input=own(artifact.input_path, "application/octet-stream"),
        header=own(artifact.header_path, "application/json"),
        receipt=own(artifact.receipt_path, "application/json"),
        shards=shards,
        shard_counts=tuple(item.records for item in artifact.shards),
        sources=sources,
        record_count=sum(item.records for item in artifact.shards),
        disposition=Disposition.COMPLETE,
        frontier=(
            "Transport completeness does not establish semantic or dispatch completeness",
            *(profile.limitations if profile else ("Original semantic context unavailable",)),
        ),
    )
    revision = builder.add(native)
    seen: set[str] = set()
    for shard, selection in zip(artifact.shards, shards, strict=True):
        offset, count = 0, 0
        with confined(root, shard.path).open("rb") as stream:
            for line in stream:
                raw = json.loads(line)
                identifier = str(raw["id"])
                if identifier in seen:
                    msg = "duplicate native fact identity within one artifact"
                    raise CorpusError(msg)
                seen.add(identifier)
                payload = raw.get("payload", {})
                fact = NativeFact(
                    logical_id=f"native-fact:{artifact.id}:{identifier}",
                    profile=artifact.profile,
                    artifact=revision,
                    native_id=identifier,
                    kind=str(raw.get("kind", payload.get("kind", "unknown"))),
                    symbol=str(raw.get("symbol", "")),
                    file=str(raw.get("file", "")),
                    owner=str(payload.get("owner") or raw.get("owner") or ""),
                    original=ByteRange(
                        blob=selection.blob,
                        start=offset,
                        end=offset + len(line),
                        digest=bytes_digest(line),
                    ),
                )
                builder.add(fact)
                if artifact.artifact_kind == "declarations":
                    normalize_native_declaration(builder, fact, raw, version=version)
                offset += len(line)
                count += 1
        if count != shard.records:
            msg = "native shard count differs from its terminal receipt"
            raise CorpusError(msg)


def admit_artifacts(corpus: Corpus, inputs: NativeInputs) -> StageResult:
    """Verify selected worker bytes and admit native facts through one tracked stage.

    Source dependencies are checked even for warm reuse. The transport cache or
    archival knowledge file is an acquisition input, never a serving authority.

    Returns:
        The durable stage result or an exact warm reuse receipt.

    """
    root, selected = inputs.root, inputs.artifacts
    profile_map = {item.id: item for item in inputs.profiles}
    snapshot_map = {item.id: item for item in inputs.snapshots}
    paths = {
        path
        for artifact in selected
        for path in (
            artifact.input_path,
            artifact.header_path,
            artifact.receipt_path,
            *(item.path for item in artifact.shards),
            *(item.path for item in artifact.witnesses),
            *((artifact.acquisition_path,) if artifact.acquisition_path else ()),
        )
    }
    paths.update(item.path for snapshot in snapshot_map.values() for item in snapshot.files)
    observed_inputs = {}
    for path in sorted(paths):
        try:
            observed_inputs[path] = digest_file(confined(root, path))
        except OSError:
            observed_inputs[path] = "unavailable"
    implementation = digest(
        {
            "artifacts": [asdict(item) for item in selected],
            "observed_inputs": observed_inputs,
            "profiles": [asdict(item) for item in profile_map.values()],
            "snapshots": [asdict(item) for item in snapshot_map.values()],
            "code": {
                name: bytes_digest((Path(__file__).parent / name).read_bytes())
                for name in (
                    "native_admission.py",
                    "corpus/declarations.py",
                    "corpus/native_validation.py",
                    "corpus/signature_syntax.py",
                    "facts/store.py",
                    "facts/context.py",
                    "facts/witness_origins.py",
                )
            },
        }
    )
    definition = StageDefinition(
        logical_id=f"native:{inputs.stage}",
        inputs=(),
        dependencies=(),
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
        implementation=implementation,
        max_records=MAX_NATIVE_RECORDS,
        max_bytes=4 * 1024**3,
        max_seconds=3600.0,
    )

    def produce(_reader: CorpusReader) -> Iterator[Record]:
        builder = NativeBuilder(implementation, max_records=MAX_NATIVE_RECORDS)
        for artifact in selected:
            stage_artifact(builder, root, artifact, profile_map.get(artifact.context), snapshot_map)
        yield from builder.records.values()

    return run_stage(corpus, definition, produce)
