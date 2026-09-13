"""Build the exact-lookup index from the generated inventories.

Exact identifier lookup is kept separate from any text search: punctuation in
``::`` paths and dotted names is exactly what a tokenizer destroys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import field, frozen

from library_guides.manifest import load_library_manifest, load_stack_manifest
from library_guides.models.records import ApiBinding, SurfaceEntry
from library_guides.stages.paths import api_path, surfaces_path
from library_guides.store.jsonl import read_records

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

__all__ = ["LookupIndex", "build_index"]


@frozen(kw_only=True)
class LookupIndex:
    """Exact-name lookup over every extracted inventory."""

    bindings: Mapping[str, tuple[ApiBinding, ...]] = field()
    surfaces: Mapping[str, tuple[SurfaceEntry, ...]] = field()

    def lookup(self, name: str) -> tuple[tuple[ApiBinding, ...], tuple[SurfaceEntry, ...]]:
        """Return every binding and surface matching ``name`` exactly.

        Returns:
            Matching API bindings and registered surfaces.

        """
        return self.bindings.get(name, ()), self.surfaces.get(name, ())

    def suffix_matches(self, name: str, *, limit: int = 12) -> tuple[str, ...]:
        """Return identifiers whose final segment equals ``name``.

        An agent usually knows the leaf name, not the full path, so an exact
        miss should still offer the real candidates rather than nothing.

        Returns:
            Matching full identifiers, in sorted order.

        """
        lowered = name.lower()
        found = sorted(
            key
            for key in self.bindings
            if key.rsplit("::", 1)[-1].rsplit(".", 1)[-1].lower() == lowered
        )
        return tuple(found[:limit])

    def size(self) -> tuple[int, int]:
        """Return how many identifiers the index holds.

        Returns:
            Binding and surface identifier counts.

        """
        return len(self.bindings), len(self.surfaces)


def _group_bindings(records: Iterable[ApiBinding]) -> dict[str, tuple[ApiBinding, ...]]:
    grouped: dict[str, list[ApiBinding]] = {}
    for record in records:
        grouped.setdefault(record.identity.public_path, []).append(record)
        for alias in record.identity.aliases:
            grouped.setdefault(alias, []).append(record)
    return {key: tuple(value) for key, value in grouped.items()}


def _group_surfaces(records: Iterable[SurfaceEntry]) -> dict[str, tuple[SurfaceEntry, ...]]:
    grouped: dict[str, list[SurfaceEntry]] = {}
    for record in records:
        grouped.setdefault(record.identity.name, []).append(record)
    return {key: tuple(value) for key, value in grouped.items()}


def build_index(stack_ids: Iterable[str], *, repository_root: Path) -> LookupIndex:
    """Return an exact-lookup index over every library in ``stack_ids``.

    Returns:
        The built index.

    """
    bindings: list[ApiBinding] = []
    surfaces: list[SurfaceEntry] = []
    for stack_id in stack_ids:
        stack = load_stack_manifest(stack_id)
        for library_id in stack.libraries:
            library = load_library_manifest(library_id)
            for profile in library.profiles:
                api_file = api_path(library_id, profile.profile_id, repository_root=repository_root)
                if api_file.is_file():
                    bindings.extend(read_records(api_file, ApiBinding))
                surface_file = surfaces_path(
                    library_id, profile.profile_id, repository_root=repository_root
                )
                if surface_file.is_file():
                    surfaces.extend(read_records(surface_file, SurfaceEntry))
    return LookupIndex(bindings=_group_bindings(bindings), surfaces=_group_surfaces(surfaces))
