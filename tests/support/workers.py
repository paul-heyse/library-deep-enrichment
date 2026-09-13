"""Locate the standalone Rust worker binaries built by `just native-build`."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ASSETS = REPO / "src" / "library_deep_enrichment" / "assets"
SCHEMAS = ASSETS / "schemas"


def worker_binary(name: str) -> Path:
    """Resolve one worker executable, preferring an explicit ``LDE_WORKER_DIR``.

    Returns:
        The absolute path of ``lde-<name>``.

    Raises:
        pytest.fail: ``LDE_REQUIRE_WORKERS=1`` and the worker is not built.

    A missing worker is reported as *blocked* (a skip naming the prerequisite), never as a pass.
    ``just test-native`` sets ``LDE_REQUIRE_WORKERS=1`` so an unbuilt worker fails there.
    """
    override = os.environ.get("LDE_WORKER_DIR")
    candidates = (
        [Path(override) / f"lde-{name}"]
        if override
        else [
            REPO / ".dev-state" / "bin" / f"lde-{name}",
            REPO / "target" / "debug" / f"lde-{name}",
            REPO / "crates" / name / "target" / "debug" / f"lde-{name}",
        ]
    )
    path = next((c for c in candidates if c.is_file()), candidates[0])
    if not path.is_file():
        reason = f"blocked: build crates/{name} first (just native-build); missing {path}"
        if os.environ.get("LDE_REQUIRE_WORKERS") == "1":
            pytest.fail(reason)
        pytest.skip(reason)
    return path.resolve()
