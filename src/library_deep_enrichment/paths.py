"""Service-owned state locations.

Corpora, acquired sources, model snapshots and tool runtimes live outside every working
repository. The single root is ``LDE_HOME``; every other location derives from it so a
development session can redirect all state with one variable.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "acquired_root",
    "default_corpus",
    "examples_root",
    "foundational_root",
    "home",
    "implementation_root",
    "intelligence_root",
    "runtime_root",
]


def home() -> Path:
    """Resolve the service state root.

    Returns:
        ``LDE_HOME`` when set, else ``$XDG_CACHE_HOME/library-deep-enrichment``.

    """
    configured = os.environ.get("LDE_HOME")
    if configured:
        return Path(configured).expanduser()
    cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache).expanduser() if cache else Path.home() / ".cache"
    return base / "library-deep-enrichment"


def intelligence_root() -> Path:
    """Return the root holding admitted corpora and qualification pilots.

    Returns:
        ``intelligence`` under the state root.

    """
    return home() / "intelligence"


def default_corpus() -> Path:
    """Return the corpus the CLI binds when ``--corpus`` is omitted.

    Returns:
        ``LDE_CORPUS`` when set, else the current pilot corpus under the intelligence root.

    """
    configured = os.environ.get("LDE_CORPUS")
    if configured:
        return Path(configured).expanduser()
    return intelligence_root() / "pilot-v4" / "corpus"


def runtime_root() -> Path:
    """Return the managed embedding runtime root (model snapshots, tools, lifecycle receipts).

    Returns:
        ``LDE_RUNTIME_ROOT`` when set, else ``runtime`` under the state root.

    """
    configured = os.environ.get("LDE_RUNTIME_ROOT")
    if configured:
        return Path(configured).expanduser()
    return home() / "runtime"


def implementation_root() -> Path:
    """Return the root of retained implementation qualification runs.

    Returns:
        ``implementation`` under the state root.

    """
    return home() / "implementation"


def foundational_root() -> Path:
    """Return the root of retained foundational-characterization runs.

    Returns:
        ``foundational`` under the state root.

    """
    return home() / "foundational"


def acquired_root() -> Path:
    """Return the cache of acquired upstream source and documentation payloads.

    Returns:
        ``acquired`` under the state root.

    """
    return home() / "acquired"


def examples_root() -> Path:
    """Return the cache used by declared verification examples.

    Returns:
        ``examples`` under the state root.

    """
    return home() / "examples"
