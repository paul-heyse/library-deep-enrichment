"""Where generated evidence lives inside the content tree."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.content import CONTENT_ROOT

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "api_path",
    "coverage_path",
    "documentation_path",
    "library_root",
    "receipt_path",
    "sources_path",
    "surfaces_path",
]


def library_root(library_id: str, *, repository_root: Path) -> Path:
    """Return the content directory for one library.

    Returns:
        Path under the agent-reference content tree.

    """
    return repository_root / CONTENT_ROOT / "libraries" / library_id


def api_path(library_id: str, profile_id: str, *, repository_root: Path) -> Path:
    """Return the API inventory path for one profile.

    Returns:
        Path to the profile's JSONL inventory.

    """
    return library_root(library_id, repository_root=repository_root) / "api" / f"{profile_id}.jsonl"


def surfaces_path(library_id: str, profile_id: str, *, repository_root: Path) -> Path:
    """Return the non-symbol surface inventory path for one profile.

    Returns:
        Path to the profile's JSONL surface inventory.

    """
    root = library_root(library_id, repository_root=repository_root)
    return root / "surfaces" / f"{profile_id}.jsonl"


def receipt_path(library_id: str, stage_id: str, profile_id: str, *, repository_root: Path) -> Path:
    """Return the receipt path for one stage execution.

    Returns:
        Path to the receipt JSON file.

    """
    root = library_root(library_id, repository_root=repository_root)
    return root / "receipts" / f"{stage_id}.{profile_id}.json"


def documentation_path(library_id: str, profile_id: str, *, repository_root: Path) -> Path:
    """Return the upstream-documentation evidence path for one profile.

    Returns:
        Path to the profile's JSONL documentation observations.

    """
    root = library_root(library_id, repository_root=repository_root)
    return root / "documentation" / f"{profile_id}.jsonl"


def sources_path(*, repository_root: Path) -> Path:
    """Return the shared source ledger path.

    Returns:
        Path to ``evidence/sources.jsonl``.

    """
    return repository_root / CONTENT_ROOT / "evidence" / "sources.jsonl"


def coverage_path(*, repository_root: Path) -> Path:
    """Return the shared coverage report path.

    Returns:
        Path to ``evidence/coverage.json``.

    """
    return repository_root / CONTENT_ROOT / "evidence" / "coverage.json"
