"""Manifest authoring for frozen structural extraction, shared across libraries."""

from __future__ import annotations

from pathlib import Path

import yaml
from attrs import asdict

from library_guides.collection import CollectionError, confined, load
from library_guides.facts.context import identify
from library_guides.facts.contracts import SemanticProfile, Setting
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.source_pipeline import SourceJob, SourceManifest
from library_guides.source_snapshots import source_request
from library_guides.store.digests import canonical_bytes, digest_bytes
from library_guides.store.staging import write_atomic


def syntax_manifest(
    root: Path, snapshots: tuple[str, ...], helper: Path, destination: Path, profile: str
) -> SourceManifest:
    """Materialize exact source requests without executing the producer.

    Returns:
        Jobs enumerating every frozen file, including opaque/native source roles.

    Raises:
        CollectionError: If a snapshot or declared profile is absent or repeated.

    """
    knowledge = load(root)
    if not isinstance(knowledge, KnowledgeV3) or profile not in {p.id for p in knowledge.profiles}:
        message = "syntax manifest requires V3 and a declared profile"
        raise CollectionError(message)
    selected = tuple(s for s in knowledge.source_snapshots if s.id in snapshots)
    if not snapshots or len(selected) != len(snapshots):
        message = "syntax selection contains an absent or duplicate snapshot"
        raise CollectionError(message)
    jobs = []
    for snapshot in selected:
        request = source_request(root, snapshot, profile=profile)
        path = root / "requests" / (digest_bytes(canonical_bytes(request)) + ".json")
        write_atomic(path, canonical_bytes(request))
        context = identify(
            SemanticProfile(
                id="",
                purpose="source",
                package=snapshot.package,
                version=snapshot.version,
                source_digest=snapshot.source_digest,
                toolchain="tree-sitter+ruff; exact binary recorded by extraction",
                target=None,
                settings=(
                    Setting(name="python_minor", value="14", origin="requested"),
                    Setting(name="rust_configuration", value=None, origin="unknown"),
                ),
                limitations=(
                    "Lexical identity and syntax do not establish runtime dispatch or compiler-active Rust configuration.",
                ),
            )
        )
        jobs.append(
            SourceJob(
                id="syntax:" + snapshot.package + ":" + snapshot.version,
                kind="syntax",
                input=str(path.resolve()),
                helper=str(helper.resolve()),
                profile=profile,
                schema=str(Path(__file__).parent / "assets/schemas/source-facts.v1.schema.json"),
                isolate=True,
                semantic_profile=context,
                snapshots=(snapshot.id,),
                inputs=tuple((str(confined(root, e.path)), e.digest) for e in snapshot.files),
            )
        )
    manifest = SourceManifest(schema_version="library-guides.source-manifest.v1", jobs=tuple(jobs))
    write_atomic(destination, yaml.safe_dump(asdict(manifest), sort_keys=False).encode())
    return manifest
