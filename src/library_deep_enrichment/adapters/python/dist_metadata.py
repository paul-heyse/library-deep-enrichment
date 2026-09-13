"""Version facts read from Python dependency declarations and lock files.

Declared intent, lock resolution, and the installed environment are three
different facts. A lock entry says what would be installed for this platform
set; it does not establish what the running interpreter actually imports.
"""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING

from attrs import field, frozen

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

__all__ = [
    "LockedDistribution",
    "read_declared_requirements",
    "read_locked_distributions",
]


@frozen(kw_only=True)
class LockedDistribution:
    """One distribution as resolved in a lock file."""

    name: str = field()
    version: str = field()
    source: str | None = field(default=None)


def read_locked_distributions(lock_path: Path) -> Mapping[str, LockedDistribution]:
    """Return every locked distribution keyed by its distribution name.

    Args:
        lock_path: Path to ``uv.lock``.

    Returns:
        Mapping of distribution name to its locked entry.

    """
    document = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = document.get("package")
    if not isinstance(packages, list):
        return {}
    resolved: dict[str, LockedDistribution] = {}
    for entry in packages:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        version = entry.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            continue
        source = entry.get("source")
        registry = source.get("registry") if isinstance(source, dict) else None
        resolved[name] = LockedDistribution(
            name=name,
            version=version,
            source=registry if isinstance(registry, str) else None,
        )
    return resolved


def read_declared_requirements(pyproject: Path) -> Mapping[str, str]:
    """Return the declared requirement specifier for each project dependency.

    A declaration states intent; the lock states what the resolver selected.
    Reporting only one of the two hides the distinction the guide must preserve.

    Args:
        pyproject: Path to ``pyproject.toml``.

    Returns:
        Mapping of distribution name to its full requirement specifier.

    """
    document = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = document.get("project")
    if not isinstance(project, dict):
        return {}
    dependencies = project.get("dependencies")
    if not isinstance(dependencies, list):
        return {}
    declared: dict[str, str] = {}
    for entry in dependencies:
        if not isinstance(entry, str):
            continue
        name = re.split(r"[<>=!~\[;\s]", entry, maxsplit=1)[0].strip()
        if name:
            declared.setdefault(name, entry.strip())
    return declared
