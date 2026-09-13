"""Immutable source acquisition with explicit inventories and containment checks."""

from __future__ import annotations

import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from attrs import asdict, frozen
from filelock import FileLock

from library_guides.collection import CollectionError, confined
from library_guides.facts.contracts import FileEntry, SourceSnapshot
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import write_atomic

if TYPE_CHECKING:
    from collections.abc import Iterable

_MAX_FILES = 100_000
_MAX_BYTES = 2_000_000_000
_EXCLUDED_PARTS = frozenset({".git", "target", "__pycache__", ".venv"})


@frozen(kw_only=True)
class Acquisition:
    """Package identity and attribution supplied by a verified acquisition job."""

    package: str
    version: str
    origin: str
    attribution: str


def language(path: Path) -> str:
    """Classify source roles while retaining opaque and unsupported files.

    Returns:
        A stable language or acquisition-only role.

    """
    suffix = path.suffix.lower()
    return {
        ".rs": "rust",
        ".py": "python",
        ".pyi": "python",
        ".pyx": "cython",
        ".pxd": "cython",
        ".md": "markdown",
        ".rst": "rst",
        ".so": "native",
        ".dll": "native",
        ".pyd": "native",
        ".dylib": "native",
    }.get(suffix, "other")


def inventory(source: Path) -> tuple[FileEntry, ...]:
    """Enumerate exact source bytes, rejecting symlinks and unexplained empty inputs.

    Returns:
        All regular files outside the explicit observation/build exclusions.

    Raises:
        CollectionError: If containment, inventory or size limits fail.

    """
    entries = []
    total = 0
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if _EXCLUDED_PARTS.intersection(relative.parts):
            continue
        if path.is_symlink():
            message = f"source symlink requires explicit materialization: {relative}"
            raise CollectionError(message)
        if not path.is_file():
            continue
        size = path.stat().st_size
        total += size
        if total > _MAX_BYTES or len(entries) >= _MAX_FILES:
            message = "source snapshot exceeds acquisition budget"
            raise CollectionError(message)
        entries.append(
            FileEntry(
                path=relative.as_posix(), digest=digest_file(path), size=size, kind=language(path)
            )
        )
    if not entries:
        message = "source snapshot is empty"
        raise CollectionError(message)
    return tuple(entries)


def verify(root: Path, snapshot: SourceSnapshot) -> None:
    """Check every file and the retained finite source manifest.

    Raises:
        CollectionError: If bytes, paths or manifest identity changed.

    """
    prefix = f"snapshots/{snapshot.source_digest}/source/"
    logical = []
    for entry in snapshot.files:
        path = confined(root, entry.path)
        if (
            not entry.path.startswith(prefix)
            or path.stat().st_size != entry.size
            or digest_file(path) != entry.digest
        ):
            message = f"frozen source changed: {entry.path}"
            raise CollectionError(message)
        logical.append({**asdict(entry), "path": entry.path.removeprefix(prefix)})
    material = {
        "package": snapshot.package,
        "version": snapshot.version,
        "origin": snapshot.origin,
        "files": logical,
        "exclusions": sorted(_EXCLUDED_PARTS),
    }
    if digest_bytes(canonical_bytes(material)) != snapshot.source_digest:
        message = "frozen source manifest identity mismatch"
        raise CollectionError(message)
    observed = inventory(root / prefix)
    if canonical_bytes([asdict(item) for item in observed]) != canonical_bytes(logical):
        message = "frozen source has undeclared files"
        raise CollectionError(message)


def freeze(root: Path, source: Path, identity: Acquisition) -> SourceSnapshot:
    """Copy a bounded exact inventory to immutable private staging.

    Returns:
        The verified snapshot reusable by each source lane.

    Raises:
        CollectionError: If source provenance is missing or inputs change while copying.

    """
    package, version, origin, attribution = (
        identity.package,
        identity.version,
        identity.origin,
        identity.attribution,
    )
    if not all((package, version, origin, attribution)):
        message = "frozen source requires package, version, origin and attribution"
        raise CollectionError(message)
    entries = inventory(source)
    material = {
        "package": package,
        "version": version,
        "origin": origin,
        "files": [asdict(item) for item in entries],
        "exclusions": sorted(_EXCLUDED_PARTS),
    }
    key = digest_bytes(canonical_bytes(material))
    prefix = f"snapshots/{key}/source/"
    snapshot = SourceSnapshot(
        id=f"snapshot:{key}",
        package=package,
        version=version,
        origin=origin,
        attribution=attribution,
        source_digest=key,
        files=tuple(
            FileEntry(path=prefix + item.path, digest=item.digest, size=item.size, kind=item.kind)
            for item in entries
        ),
    )
    destination = root / "snapshots" / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(destination) + ".lock", timeout=60):
        if destination.exists():
            verify(root, snapshot)
            return snapshot
        _copy_snapshot(root, source, destination, snapshot, entries)
    return snapshot


def _copy_snapshot(
    root: Path,
    source: Path,
    destination: Path,
    snapshot: SourceSnapshot,
    entries: tuple[FileEntry, ...],
) -> None:
    staging = Path(tempfile.mkdtemp(prefix="snapshot-", dir=destination.parent))
    try:
        for entry in entries:
            target = confined(staging / "source", entry.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(confined(source, entry.path), target)
            if digest_file(target) != entry.digest:
                message = f"source changed during acquisition: {entry.path}"
                raise CollectionError(message)
        if inventory(source) != entries:
            message = "source inventory changed during acquisition"
            raise CollectionError(message)
        write_atomic(staging / "manifest.json", canonical_bytes(asdict(snapshot)))
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    verify(root, snapshot)


def extract_archive(archive: Path, destination: Path) -> None:
    """Extract a bounded crate/sdist tar without links, traversal or device entries.

    Raises:
        CollectionError: If the archive contains unsafe or oversized members.

    """
    total = 0
    count = 0
    seen: set[str] = set()
    with tarfile.open(archive, mode="r|*") as stream:
        for member in stream:
            count += 1
            total += member.size
            path = PurePosixPath(member.name)
            unsafe = path.is_absolute() or ".." in path.parts or member.name in seen
            if (
                unsafe
                or count > _MAX_FILES
                or total > _MAX_BYTES
                or not (member.isdir() or member.isfile())
            ):
                message = f"unsupported archive entry: {member.name}"
                raise CollectionError(message)
            seen.add(member.name)
            target = confined(destination, path.as_posix())
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                body = stream.extractfile(member)
                if body is None:
                    message = f"archive member has no bytes: {member.name}"
                    raise CollectionError(message)
                with body, target.open("xb") as output:
                    shutil.copyfileobj(body, output, length=65536)


def snapshot_root(root: Path, snapshot: SourceSnapshot) -> Path:
    """Locate the exact source universe for a worker request.

    Returns:
        Collection-contained frozen source root.

    """
    return confined(root, f"snapshots/{snapshot.source_digest}/source")


def source_request(
    root: Path,
    snapshot: SourceSnapshot,
    *,
    profile: str,
    python_minor: int = 14,
    lexical: bool = True,
) -> dict[str, object]:
    """Create a structural request covering every acquired source role.

    Returns:
        Exact source paths, digests and context for the native worker.

    """
    verify(root, snapshot)
    source = snapshot_root(root, snapshot)
    return {
        "profile": profile,
        "root": str(source.resolve()),
        "python_minor": python_minor,
        "lexical": lexical,
        "files": [
            {
                "path": str(confined(root, entry.path).relative_to(source)),
                "digest": entry.digest,
                "language": entry.kind,
            }
            for entry in snapshot.files
        ],
    }


def retain_snapshots(root: Path, snapshots: Iterable[SourceSnapshot]) -> None:
    """Attach verified frozen sources to the same V3 authoring authority.

    Raises:
        CollectionError: If the collection was not explicitly migrated.

    """
    from attrs import evolve

    from library_guides.collection import load, save
    from library_guides.knowledge_v3 import KnowledgeV3

    with FileLock(str(root / "knowledge.lock"), timeout=60):
        knowledge = load(root)
        if not isinstance(knowledge, KnowledgeV3):
            message = "frozen sources require knowledge.v3"
            raise CollectionError(message)
        selected = tuple(snapshots)
        for snapshot in selected:
            verify(root, snapshot)
        ids = {item.id for item in selected}
        save(
            root,
            evolve(
                knowledge,
                source_snapshots=tuple(
                    item for item in knowledge.source_snapshots if item.id not in ids
                )
                + selected,
            ),
        )
