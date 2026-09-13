"""Locate the standalone Rust worker binaries built by `just native-build`."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ASSETS = REPO / "src" / "library_deep_enrichment" / "assets"
SCHEMAS = ASSETS / "schemas"


def worker_binary(name: str) -> Path:
    """Resolve one worker executable, preferring an explicit ``LDE_WORKER_DIR``.

    Returns:
        The absolute path of ``lde-<name>``.

    Raises:
        AssertionError: The worker has not been built; the native lanes are `blocked`.

    """
    override = os.environ.get("LDE_WORKER_DIR")
    path = (
        Path(override) / f"lde-{name}"
        if override
        else REPO / "crates" / name / "target" / "debug" / f"lde-{name}"
    )
    assert path.is_file(), f"Build crates/{name} first (just native-build); missing {path}"
    return path.resolve()
