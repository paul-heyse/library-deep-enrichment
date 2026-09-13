"""Version facts read from Cargo manifests.

A workspace dependency declaration is *declared intent*. When the declaration is
an exact requirement it also fixes the resolved version, but the two remain
distinct facts and are reported as such.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from attrs import field, frozen

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

__all__ = ["CargoDependency", "read_locked_packages", "read_workspace_dependencies"]


@frozen(kw_only=True)
class CargoDependency:
    """One workspace dependency declaration."""

    name: str = field()
    requirement: str = field()
    features: tuple[str, ...] = field(default=())
    default_features: bool = field(default=True)
    source: str | None = field(default=None)

    def is_exact(self) -> bool:
        """Return whether the requirement pins a single version.

        Returns:
            ``True`` when the requirement begins with ``=``.

        """
        return self.requirement.startswith("=")

    def exact_version(self) -> str | None:
        """Return the pinned version when the requirement is exact.

        Returns:
            The version text, or ``None`` when the requirement is a range.

        """
        return self.requirement[1:] if self.is_exact() else None


def _dependency_from(name: str, value: object) -> CargoDependency | None:
    if isinstance(value, str):
        return CargoDependency(name=name, requirement=value)
    if not isinstance(value, dict):
        return None
    requirement = value.get("version")
    git = value.get("git")
    if not isinstance(requirement, str):
        if isinstance(git, str):
            revision = value.get("rev")
            suffix = f"@{revision}" if isinstance(revision, str) else ""
            return CargoDependency(name=name, requirement="git", source=f"{git}{suffix}")
        return None
    raw_features = value.get("features")
    features = (
        tuple(entry for entry in raw_features if isinstance(entry, str))
        if isinstance(raw_features, list)
        else ()
    )
    default_features = value.get("default-features")
    return CargoDependency(
        name=name,
        requirement=requirement,
        features=features,
        default_features=default_features if isinstance(default_features, bool) else True,
    )


def read_workspace_dependencies(cargo_toml: Path) -> Mapping[str, CargoDependency]:
    """Return every ``[workspace.dependencies]`` entry.

    Args:
        cargo_toml: Path to the workspace ``Cargo.toml``.

    Returns:
        Mapping of dependency name to its declaration.

    """
    document = tomllib.loads(cargo_toml.read_text(encoding="utf-8"))
    workspace = document.get("workspace")
    if not isinstance(workspace, dict):
        return {}
    dependencies = workspace.get("dependencies")
    if not isinstance(dependencies, dict):
        return {}
    resolved: dict[str, CargoDependency] = {}
    for name, value in dependencies.items():
        if not isinstance(name, str):
            continue
        dependency = _dependency_from(name, value)
        if dependency is not None:
            resolved[name] = dependency
    return resolved


def read_locked_packages(cargo_lock: Path) -> Mapping[str, str]:
    """Return the resolved version of every package in a Cargo lock file.

    A declaration is intent; a lock entry is what the resolver selected. The two
    coincide for an exact requirement and diverge for a range.

    Args:
        cargo_lock: Path to ``Cargo.lock``.

    Returns:
        Mapping of package name to resolved version.

    """
    document = tomllib.loads(cargo_lock.read_text(encoding="utf-8"))
    packages = document.get("package")
    if not isinstance(packages, list):
        return {}
    resolved: dict[str, str] = {}
    for entry in packages:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        version = entry.get("version")
        if isinstance(name, str) and isinstance(version, str):
            resolved.setdefault(name, version)
    return resolved
