"""Immutable bundles with validation and compare-and-swap publication."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from attrs import asdict
from filelock import FileLock

from library_guides.artifact_cache import ArtifactCache
from library_guides.collection import CollectionError, confined, load
from library_guides.evidence_graph import EvidenceGraph
from library_guides.examples import environment
from library_guides.examples import run as run_example
from library_guides.examples import verify as verify_examples
from library_guides.knowledge import Knowledge
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.qualification import coverage, validate
from library_guides.reader import index, render
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import sync_directory, write_atomic


def current(store: Path) -> str | None:
    """Read a single generation pointer, or report that none is published.

    Returns:
        The current generation identity, or None before first publication.

    """
    pointer = store / "current.json"
    return json.loads(pointer.read_bytes())["generation"] if pointer.is_file() else None


def manifest(root: Path) -> dict[str, str]:
    """Hash the complete bundle write set, excluding the manifest itself.

    Returns:
        Relative artifact paths mapped to their actual byte digests.

    """
    return {
        path.relative_to(root).as_posix(): digest_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() != "bundle.json"
    }


def verify(root: Path) -> str:
    """Reject truncated, changed or undeclared generation content.

    Returns:
        The verified content-derived generation identity.

    Raises:
        CollectionError: If declared files, actual bytes or the generation identity disagree.

    """
    declared = json.loads((root / "bundle.json").read_bytes())
    actual = manifest(root)
    if actual != declared["files"]:
        message = f"bundle content changed: {root}"
        raise CollectionError(message)
    identifier = digest_bytes(canonical_bytes(actual))
    if identifier != declared["generation"]:
        message = f"bundle identity changed: {root}"
        raise CollectionError(message)
    return identifier


def build(root: Path, store: Path) -> Path:
    """Stage and verify a complete bundle; never modify the published pointer.

    Returns:
        The staged, validated candidate directory.

    Raises:
        CollectionError: If input validation fails or the source changes during staging.

    """
    knowledge = load(root)
    errors = validate(root, knowledge)
    if errors:
        message = "collection is not qualified:\n" + "\n".join(errors[:50])
        raise CollectionError(message)
    staging = store / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    candidate = Path(tempfile.mkdtemp(prefix="build-", dir=staging))
    paths = _portable_paths(knowledge)
    for relative in sorted(paths):
        write_atomic(confined(candidate, relative), confined(root, relative).read_bytes())
    # Validate the copied snapshot: concurrent authoring cannot create mixed inputs.
    snapshot = load(candidate)
    errors = validate(candidate, snapshot)
    if errors:
        message = "input changed while staging:\n" + "\n".join(errors[:50])
        raise CollectionError(message)
    cache = ArtifactCache(store / "artifact-cache")
    graph = EvidenceGraph(candidate, snapshot)
    # A build job can produce an executable consumed by later jobs. Keep the
    # complete sequence exclusive while using the documented shared cache.
    execution_lock = Path.home() / ".cache/library-guides/examples/execution.lock"
    execution_lock.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(execution_lock), timeout=60):
        for example in snapshot.examples:
            product = candidate / "verification" / f"{digest_bytes(example.id.encode())}.json"
            key = cache.key([graph.fingerprint(example.id), environment(example, root=candidate)])
            if not example.cacheable or not cache.restore("example", key, product):
                run_example(candidate, snapshot, example)
                cache.retain("example", key, product)
    verify_examples(candidate, snapshot)
    for record in (*snapshot.capabilities, *snapshot.decisions, *snapshot.integrations):
        product = candidate / "briefs" / f"{digest_bytes(record.id.encode())}.md"
        key = cache.key(
            [
                graph.fingerprint(record.id),
                [asdict(seed) for seed in snapshot.facet_seeds]
                if isinstance(snapshot, KnowledgeV3)
                else [],
            ]
        )
        if not cache.restore("render", key, product):
            write_atomic(product, render(candidate, snapshot, record.id).encode())
            cache.retain("render", key, product)
    write_atomic(candidate / "coverage.json", canonical_bytes(coverage(candidate, snapshot)))
    index_key = cache.key(asdict(snapshot))
    if not cache.restore("index", index_key, candidate / "index.sqlite"):
        index(candidate / "index.sqlite", snapshot, evidence_root=candidate)
        cache.retain("index", index_key, candidate / "index.sqlite")
    write_atomic(candidate / "stage-reuse.json", canonical_bytes(dict(cache.counts)))
    files = manifest(candidate)
    identity = digest_bytes(canonical_bytes(files))
    write_atomic(
        candidate / "bundle.json", canonical_bytes({"generation": identity, "files": files})
    )
    verify(candidate)
    return candidate


def publish(candidate: Path, store: Path, *, expected: str | None) -> str:
    """Commit one verified bundle only if the observed predecessor still exists.

    Returns:
        The atomically published generation identity.

    Raises:
        CollectionError: If another writer has advanced the publication pointer.

    """
    identity = verify(candidate)
    failures = validate(candidate, load(candidate))
    if failures:
        message = "publication requires a qualified collection: " + "; ".join(failures[:10])
        raise CollectionError(message)
    verify_examples(candidate, load(candidate))
    store.mkdir(parents=True, exist_ok=True)
    with FileLock(str(store / "publish.lock")):
        if current(store) != expected:
            message = "publication conflict: current generation changed"
            raise CollectionError(message)
        destination = store / "generations" / identity
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            verify(destination)
        else:
            temporary = Path(tempfile.mkdtemp(prefix="publish-", dir=destination.parent))
            for relative in (*manifest(candidate), "bundle.json"):
                write_atomic(
                    confined(temporary, relative), confined(candidate, relative).read_bytes()
                )
            verify(temporary)
            temporary.rename(destination)
            sync_directory(destination.parent)
        write_atomic(store / "current.json", canonical_bytes({"generation": identity}))
    return identity


def resolve(store: Path) -> Path:
    """Pin and verify the current immutable bundle for a reader.

    Returns:
        The verified immutable generation directory pinned by the pointer.

    Raises:
        CollectionError: If no generation exists or the pointer and bundle disagree.

    """
    identifier = current(store)
    if identifier is None:
        message = f"no published generation in {store}"
        raise CollectionError(message)
    root = confined(store / "generations", identifier)
    if verify(root) != identifier:
        message = "published pointer names a different bundle"
        raise CollectionError(message)
    return root


def _portable_paths(knowledge: Knowledge) -> set[str]:
    from library_guides.knowledge_v3 import KnowledgeV3

    paths = {source.path for source in knowledge.sources} | {"knowledge.yaml", "obligations.yaml"}
    paths.update(path for example in knowledge.examples for path in example.inputs)
    if isinstance(knowledge, KnowledgeV3):
        if knowledge.candidate_universes or knowledge.universe_dependencies:
            paths.add("candidate-universes.yaml")
        paths.update(
            proof.prior_knowledge.path
            for proof in knowledge.revalidations
            if proof.prior_knowledge is not None
        )
        paths.update(
            entry.path for proof in knowledge.revalidations for entry in proof.prior_inputs
        )
        paths.update(
            entry.path for snapshot in knowledge.source_snapshots for entry in snapshot.files
        )
        for artifact in knowledge.fact_artifacts:
            paths.update((artifact.input_path, artifact.header_path, artifact.receipt_path))
            paths.update(shard.path for shard in artifact.shards)
            paths.update(item.path for item in artifact.witnesses)
            if artifact.acquisition_path:
                paths.add(artifact.acquisition_path)
    return paths
