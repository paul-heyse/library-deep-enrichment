"""Coordinator-owned historical checker receipts; archived views cannot become active writers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa

from library_deep_enrichment.corpus.backend import CorpusError, literal
from library_deep_enrichment.corpus.encoding import bytes_digest, digest

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.backend import Backend

CURRENT = "current"
HISTORICAL = "library-guides.realization.2026-09-12.pre-schema-approval.v1"
TABLE = "historical_views"
ARCHIVED_MANIFESTS = frozenset(
    {
        "93f1462edd7bbf5eeb8d51da30f3dfc434eb5fe638fa889dcd68b90b65a1c5f8",
        "c846a29508e67b5799ee2cf767fce0412cf6ba508faec72616a8d86750b6a299",
    }
)
SCHEMA = pa.schema(
    [
        pa.field(name, pa.string(), nullable=False)
        for name in ("manifest", "checker", "implementation")
    ]
)


def fingerprint(checker: str) -> str:
    """Resolve a built-in recovered checker; archives cannot provide executable code.

    Returns:
        Its exact implementation fingerprint, or the current-validation sentinel.

    Raises:
        CorpusError: No explicitly retained checker implements the requested identity.

    """
    if checker == CURRENT:
        return CURRENT
    if checker != HISTORICAL:
        message = "unsupported historical semantic checker"
        raise CorpusError(message)
    root = Path(__file__).parents[1]
    return digest(
        [
            (name, bytes_digest((root / name).read_bytes()))
            for name in (
                "semantics/historical_realization.py",
                "semantics/historical_task_matching.py",
                "semantics/historical_replay.py",
            )
        ]
    )


def check_manifest(manifest: str, checker: str) -> None:
    """Limit historical interpretation to inventoried original releases.

    Raises:
        CorpusError: New content tries to acquire obsolete historical semantics.

    """
    fingerprint(checker)
    if checker != CURRENT and manifest not in ARCHIVED_MANIFESTS:
        message = "historical checking is restricted to inventoried original release identities"
        raise CorpusError(message)


def selected(backend: Backend, manifest: str) -> str:
    """Read the immutable checker assignment of a selected logical view.

    Returns:
        The supported checker after validating its implementation identity.

    Raises:
        CorpusError: Historical checker metadata is conflicting or its code changed.

    """
    if not manifest or not backend.exists(TABLE):
        return CURRENT
    rows = tuple(backend.scan(TABLE, where=f"manifest = {literal(manifest)}", limit=1))
    if not rows:
        return CURRENT
    row = rows[0]
    checker = str(row["checker"])
    check_manifest(manifest, checker)
    if checker == CURRENT or row["implementation"] != fingerprint(checker):
        message = "historical checker assignment or implementation changed"
        raise CorpusError(message)
    return checker


def retain(backend: Backend, manifest: str, checker: str) -> None:
    """Record historical semantics before the final head commit, preserving logical identities.

    Raises:
        CorpusError: A retained assignment conflicts with this verified import.

    """
    if checker == CURRENT:
        return
    check_manifest(manifest, checker)
    old = selected(backend, manifest)
    if old == checker:
        return
    if old != CURRENT:
        message = "a logical manifest already has different historical checker semantics"
        raise CorpusError(message)
    backend.append(
        TABLE,
        SCHEMA,
        [{"manifest": manifest, "checker": checker, "implementation": fingerprint(checker)}],
    )
