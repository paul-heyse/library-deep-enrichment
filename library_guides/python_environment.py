"""Import-free installed-distribution acquisition and ordered frozen type environments."""

from __future__ import annotations

import base64
import importlib.metadata
import tempfile
from pathlib import Path

from attrs import asdict, frozen
from filelock import FileLock

from library_guides.collection import CollectionError, confined, load, save
from library_guides.facts.context import identify
from library_guides.facts.contracts import SemanticProfile, Setting, SourceSnapshot
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.source_pipeline import SourceJob, SourceManifest
from library_guides.source_snapshots import Acquisition, freeze, snapshot_root, verify
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import write_atomic


@frozen(kw_only=True)
class Distribution:
    """Exact installed package requested for static acquisition, without importing it."""

    name: str
    version: str


@frozen(kw_only=True)
class Environment:
    """Finite ordered module universe and target Python semantics."""

    id: str
    distributions: tuple[Distribution, ...]
    python_version: str = "3.14"
    platform: str = "linux"
    view: str = "interface"


def acquire(root: Path, request: Distribution) -> SourceSnapshot:
    """Copy the distribution's recorded files, checking available RECORD hashes.

    Returns:
        Exact bytes including metadata, opaque native files and external-script inventory.

    Raises:
        CollectionError: If version, RECORD inventory or content checks fail.

    """
    dist = importlib.metadata.distribution(request.name)
    if dist.version != request.version or not dist.files:
        message = f"installed distribution does not match exact source request: {request.name} {request.version}"
        raise CollectionError(message)
    with tempfile.TemporaryDirectory(prefix="library-guides-distribution-") as temporary:
        staging = Path(temporary)
        records = [_copy_distribution_file(dist, item, staging) for item in dist.files]
        write_atomic(
            staging / "library-guides-acquisition.json",
            canonical_bytes(
                {
                    "distribution": asdict(request),
                    "method": "importlib.metadata without importing target",
                    "files": records,
                    "requires_dist": dist.requires or [],
                }
            ),
        )
        return freeze(
            root,
            staging,
            Acquisition(
                package=request.name,
                version=request.version,
                origin=f"installed-distribution:{request.name}=={request.version}",
                attribution=dist.metadata.get("License-Expression")
                or dist.metadata.get("License")
                or "Distribution authors; license files retained in inventory",
            ),
        )


def _copy_distribution_file(
    dist: importlib.metadata.Distribution, item: importlib.metadata.PackagePath, staging: Path
) -> dict[str, object]:
    located = dist.locate_file(item)
    if not isinstance(located, Path):
        message = "installed distribution must expose actual filesystem paths"
        raise CollectionError(message)
    source = located
    if not source.is_file():
        message = f"distribution RECORD input is absent: {item}"
        raise CollectionError(message)
    body = source.read_bytes()
    hashed = digest_bytes(body)
    if item.hash is not None:
        expected = base64.urlsafe_b64encode(bytes.fromhex(hashed)).decode().rstrip("=")
        if item.hash.mode != "sha256" or expected != item.hash.value:
            message = f"unsupported or mismatched distribution RECORD checksum: {item}"
            raise CollectionError(message)
    external = item.is_absolute() or ".." in item.parts
    relative = f".distribution-external/{hashed}/{item.name}" if external else str(item)
    target = confined(staging, relative)
    if target.exists() and digest_file(target) != hashed:
        message = f"conflicting installed files: {relative}"
        raise CollectionError(message)
    write_atomic(target, body)
    if digest_file(source) != hashed:
        message = "distribution changed during copying"
        raise CollectionError(message)
    return {
        "record_path": str(item),
        "path": relative,
        "digest": hashed,
        "external_script": external,
        "record_checksum": "verified" if item.hash is not None else "not_recorded",
    }


def materialize(
    root: Path, request: Environment
) -> tuple[dict[str, object], SemanticProfile, tuple[SourceSnapshot, ...]]:
    """Build explicit ordered roots, stub precedence and a retained source-file universe.

    Returns:
        Worker request, effective context and acquired distribution snapshots.

    Raises:
        CollectionError: If module selection is ambiguous or the source view is unsupported.

    """
    if request.view not in {"interface", "source"} or not request.distributions:
        message = "Python environment requires a finite interface/source view"
        raise CollectionError(message)
    snapshots = tuple(acquire(root, distribution) for distribution in request.distributions)
    files = []
    paths = []
    selected: dict[str, tuple[int, int]] = {}
    for position, snapshot in enumerate(snapshots):
        verify(root, snapshot)
        source = snapshot_root(root, snapshot)
        paths.append(source.relative_to(root).as_posix())
        for entry in snapshot.files:
            logical = Path(entry.path).relative_to(source.relative_to(root))
            module = _module(logical, confined(root, entry.path))
            priority = (
                0 if logical.suffix == (".pyi" if request.view == "interface" else ".py") else 1
            )
            file: dict[str, str | None] = {
                "path": entry.path,
                "digest": entry.digest,
                "module": None,
            }
            files.append(file)
            if module is not None:
                rank = position * 2 + priority
                existing = selected.get(module)
                if existing is None or rank < existing[0]:
                    if existing is not None:
                        files[existing[1]]["module"] = None
                    file["module"] = module
                    selected[module] = (rank, len(files) - 1)
                elif rank == existing[0]:
                    message = f"ambiguous selected Python module: {module}"
                    raise CollectionError(message)
    context = identify(
        SemanticProfile(
            id="",
            purpose="python",
            package="environment:" + request.id,
            version="exact-distribution-catalog",
            source_digest=digest_bytes(canonical_bytes([s.source_digest for s in snapshots])),
            toolchain="pyrefly-1.2.0; exact binary pinned by each extraction",
            target=request.platform,
            dependency_digests=tuple(s.source_digest for s in snapshots),
            settings=(
                Setting(
                    name="ordered_search_roots",
                    value=canonical_bytes(paths).decode(),
                    origin="observed",
                ),
                Setting(name="python_version", value=request.python_version, origin="requested"),
                Setting(name="source_view", value=request.view, origin="requested"),
                Setting(
                    name="module_selection",
                    value=canonical_bytes(selected).decode(),
                    origin="observed",
                ),
            ),
            limitations=(
                "Only explicitly acquired distributions are supplied; missing imports remain diagnostics and unknown targets.",
                "Unselected native and Cython bodies remain opaque; bundled stdlib stubs follow the pinned Pyrefly producer.",
                "Source view selects .py definitions where a same-root .pyi also exists; import resolution still follows the pinned solver and retains uncertainty.",
            ),
        )
    )
    worker: dict[str, object] = {
        "profile": request.id,
        "root": str(root.resolve()),
        "files": files,
        "search_paths": paths,
        "python_version": request.python_version,
        "python_platform": request.platform,
    }
    return worker, context, snapshots


def _module(path: Path, source: Path) -> str | None:
    if path.suffix not in {".py", ".pyi"} or any(
        part.startswith(".") or ".dist-info" in part or ".data" in part for part in path.parts
    ):
        return None
    try:
        source.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts and all(part.isidentifier() for part in parts) else None


def prepare(root: Path, request: Environment, helper: Path, destination: Path) -> SourceManifest:
    """Acquire static inputs and write a reviewable source manifest without running workers.

    Returns:
        A strict extraction manifest for the same active V3 authority.

    Raises:
        CollectionError: If the selected authoring authority is not V3.

    """
    import yaml
    from attrs import evolve

    worker, context, snapshots = materialize(root, request)
    with FileLock(str(root / "knowledge.lock"), timeout=60):
        knowledge = load(root)
        if not isinstance(knowledge, KnowledgeV3):
            message = "Python environments require a V3 authority"
            raise CollectionError(message)
        save(
            root,
            evolve(
                knowledge,
                source_snapshots=tuple(
                    {s.id: s for s in (*knowledge.source_snapshots, *snapshots)}.values()
                ),
            ),
        )
    path = root / "requests" / (digest_bytes(canonical_bytes(worker)) + ".json")
    write_atomic(path, canonical_bytes(worker))
    manifest = SourceManifest(
        schema_version="library-guides.source-manifest.v1",
        jobs=(
            SourceJob(
                id=request.id,
                kind="types",
                input=str(path.resolve()),
                helper=str(helper.resolve()),
                schema=str(
                    Path(__file__).parent / "assets/schemas/python-semantics.v1.schema.json"
                ),
                profile=request.id,
                isolate=True,
                semantic_profile=context,
                snapshots=tuple(s.id for s in snapshots),
                inputs=tuple(
                    (str(confined(root, f.path)), f.digest) for s in snapshots for f in s.files
                ),
            ),
        ),
    )
    write_atomic(destination, yaml.safe_dump(asdict(manifest), sort_keys=False).encode())
    return manifest
