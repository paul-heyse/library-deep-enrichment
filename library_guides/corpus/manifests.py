"""Logical manifest identity and physical bindings without self-reference."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa

from library_guides.corpus.backend import CorpusError, literal
from library_guides.corpus.contracts import Head, Manifest, Member
from library_guides.corpus.encoding import CONVERTER, digest
from library_guides.corpus.schemas import NUMBER, TEXT

if TYPE_CHECKING:
    from collections.abc import Iterable

    from library_guides.corpus.backend import Backend

HEAD_SCHEMA = pa.schema(
    [
        pa.field("name", TEXT, nullable=False),
        pa.field("sequence", NUMBER, nullable=False),
        pa.field("manifest", TEXT, nullable=False),
        pa.field("manifest_version", NUMBER, nullable=False),
        pa.field("predecessor", TEXT, nullable=False),
    ]
)
MEMBER_SCHEMA = pa.schema(
    [
        pa.field(name, TEXT, nullable=False)
        for name in ("manifest", "family", "logical_id", "profile", "revision")
    ]
)
MANIFEST_SCHEMA = pa.schema(
    [
        *[
            pa.field(name, TEXT, nullable=False)
            for name in ("digest", "predecessor", "members_digest")
        ],
        pa.field("membership_version", NUMBER, nullable=False),
        pa.field(
            "bindings",
            pa.list_(
                pa.struct(
                    [
                        pa.field("family", TEXT, nullable=False),
                        pa.field("version", NUMBER, nullable=False),
                    ]
                )
            ),
            nullable=False,
        ),
        pa.field("count", NUMBER, nullable=False),
    ]
)


def read_head(backend: Backend, name: str) -> Head | None:
    """Read the latest control commit through a fresh table handle.

    Returns:
        The highest committed sequence for the requested named view.

    """
    if not backend.exists("control_heads"):
        return None
    rows = backend.scan("control_heads", where=f"name = {literal(name)}")
    latest = max(rows, key=lambda row: int(str(row["sequence"])), default=None)
    return None if latest is None else CONVERTER.structure(latest, Head)


def read_manifest(backend: Backend, head: Head) -> Manifest:
    """Resolve the exact manifest table version named by a control commit.

    Returns:
        Resolve the exact manifest table version named by a control commit.

    Raises:
        CorpusError: The head does not name exactly one valid manifest.

    """
    rows = list(
        backend.scan(
            "manifests",
            version=head.manifest_version,
            where=f"digest = {literal(head.manifest)}",
            limit=1,
        )
    )
    if len(rows) != 1:
        message = f"missing manifest: {head.manifest}"
        raise CorpusError(message)
    manifest = CONVERTER.structure(rows[0], Manifest)
    if logical_digest(manifest.predecessor, manifest.members_digest) != manifest.digest:
        message = "manifest logical digest does not match its retained membership identity"
        raise CorpusError(message)
    return manifest


def membership_digest(members: Iterable[Member]) -> str:
    """Return portable identity for an unordered exact membership selection.

    Returns:
        Portable identity for an unordered exact membership selection.

    """
    return digest(sorted((m.family, m.logical_id, m.profile, m.revision) for m in members))


def logical_digest(predecessor: str, members_digest: str) -> str:
    """Return a manifest identity independent of physical storage versions.

    Returns:
        A manifest identity independent of physical storage versions.

    """
    return digest(["library-guides-corpus-v4", predecessor, members_digest])
