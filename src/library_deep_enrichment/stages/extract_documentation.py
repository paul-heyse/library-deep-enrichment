"""Capture upstream documentation as first-class evidence.

Upstream doc comments are the library's own account of its behavior. They are
independent of any locally authored reference, which makes them the primary
grounding for behavior derivation rather than a nice-to-have.

They are stored as observations rather than as fields on an API binding: a doc
comment is a *statement about* an item, carrying its own evidence origin and its
own review status, and keeping it separate leaves the inventory lean.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

from attrs import field, frozen

from library_deep_enrichment.models.enums import EvidenceOrigin, ResolutionState
from library_deep_enrichment.models.records import Observation

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

__all__ = [
    "DOC_PREDICATE",
    "DocumentationHarvest",
    "harvest_rustdoc_documentation",
    "harvest_surface_documentation",
]

DOC_PREDICATE: Final = "upstream_documentation"
_MIN_USEFUL_CHARS: Final = 12


@frozen(kw_only=True)
class DocumentationHarvest:
    """Upstream documentation statements gathered for one profile."""

    library_id: str = field()
    profile_id: str = field()
    observations: tuple[Observation, ...] = field()
    documented_items: int = field()
    total_items: int = field()
    total_characters: int = field()

    def summary(self) -> str:
        """Describe the harvest in one line.

        Returns:
            A short human-readable summary.

        """
        share = self.documented_items / self.total_items if self.total_items else 0.0
        return (
            f"{self.library_id}/{self.profile_id}: "
            f"{self.documented_items:,}/{self.total_items:,} items documented ({share:.0%}), "
            f"{self.total_characters:,} characters of upstream prose"
        )


def _local_documented_items(document: Mapping[str, object]) -> Iterator[tuple[str, str]]:
    index = document.get("index")
    paths = document.get("paths")
    if not isinstance(index, dict) or not isinstance(paths, dict):
        return
    for item_id, item in index.items():
        if not isinstance(item, dict):
            continue
        docs = item.get("docs")
        if not isinstance(docs, str) or len(docs.strip()) < _MIN_USEFUL_CHARS:
            continue
        entry = paths.get(item_id)
        if not isinstance(entry, dict) or entry.get("crate_id") != 0:
            continue
        parts = entry.get("path")
        if not isinstance(parts, list) or not parts:
            continue
        yield "::".join(str(part) for part in parts), docs.strip()


def harvest_rustdoc_documentation(
    payload: bytes,
    *,
    library_id: str,
    profile_id: str,
    crate: str,
) -> DocumentationHarvest:
    """Return every doc comment a rustdoc document carries for its own items.

    Args:
        payload: Decompressed rustdoc JSON bytes.
        library_id: Owning library identifier.
        profile_id: Profile this documentation is evidence for.
        crate: Cargo package name, recorded in the observation scope.

    Returns:
        The harvest.

    """
    document = json.loads(payload)
    index = document.get("index")
    total = len(index) if isinstance(index, dict) else 0
    observations: list[Observation] = []
    characters = 0
    for public_path, text in _local_documented_items(document):
        characters += len(text)
        observations.append(
            Observation(
                observation_id=f"{profile_id}:{public_path}:doc",
                library_id=library_id,
                subject=public_path,
                predicate=DOC_PREDICATE,
                object_value=text,
                evidence_origin=EvidenceOrigin.DOCUMENTATION_STATEMENT,
                resolution_state=ResolutionState.RESOLVED,
                extractor_id="rustdoc_doc_comment",
                scope=(crate,),
            )
        )
    return DocumentationHarvest(
        library_id=library_id,
        profile_id=profile_id,
        observations=tuple(observations),
        documented_items=len(observations),
        total_items=total,
        total_characters=characters,
    )


def harvest_surface_documentation(
    surfaces: tuple[object, ...],
    *,
    library_id: str,
    profile_id: str,
) -> DocumentationHarvest:
    """Return documentation statements carried by registry-reported surfaces.

    A registry description and syntax example are upstream documentation too, and
    for a natively implemented library they are often the only documentation a
    static extractor can reach.

    Returns:
        The harvest.

    """
    observations: list[Observation] = []
    characters = 0
    for surface in surfaces:
        description = getattr(surface, "description", None)
        identity = getattr(surface, "identity", None)
        name = getattr(identity, "name", None)
        if not isinstance(description, str) or not isinstance(name, str):
            continue
        if len(description.strip()) < _MIN_USEFUL_CHARS:
            continue
        attributes = dict(getattr(surface, "attributes", ()))
        example = attributes.get("syntax_example", "")
        text = f"{description.strip()}\n\nSyntax: {example}" if example else description.strip()
        characters += len(text)
        observations.append(
            Observation(
                observation_id=f"{profile_id}:{name}:doc",
                library_id=library_id,
                subject=name,
                predicate=DOC_PREDICATE,
                object_value=text,
                evidence_origin=EvidenceOrigin.DOCUMENTATION_STATEMENT,
                resolution_state=ResolutionState.RESOLVED,
                extractor_id="registry_description",
                scope=(str(getattr(surface, "surface_kind", "")),),
            )
        )
    return DocumentationHarvest(
        library_id=library_id,
        profile_id=profile_id,
        observations=tuple(observations),
        documented_items=len(observations),
        total_items=len(surfaces),
        total_characters=characters,
    )
