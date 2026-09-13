"""Document sections and exact API joins, retaining uncertainty and provenance."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

from attrs import asdict

from library_guides.adapters.docs.markdown_sections import index_markdown
from library_guides.knowledge import Knowledge
from library_guides.store.digests import digest_file

_IDENTIFIER = re.compile(r"`([A-Za-z_][\w]*(?:(?:::|\.)[\w]+)*)`")


class Mention(TypedDict):
    """An exact match or explicitly unaccepted name candidate."""

    text: str
    state: str
    bindings: list[str]
    candidates: list[str]


class MappedSection(TypedDict):
    """A structural section and its binding mentions."""

    section: dict[str, object]
    mentions: list[Mention]
    authority: str


class DocumentMap(TypedDict):
    """An exact document snapshot and scoped structural mappings."""

    document: str
    digest: str
    profile: str
    sections: list[MappedSection]


def map_document(path: Path, knowledge: Knowledge, *, profile: str) -> DocumentMap:
    """Join exact qualified names or aliases, never accepting leaf-name similarity.

    Returns:
        Section identities, source digests and explicitly qualified mention matches.

    """
    text = path.read_text(encoding="utf-8")
    sections = index_markdown(text, document_path=path.name)
    exact: dict[str, list[str]] = {}
    leaves: dict[str, list[str]] = {}
    for binding in knowledge.bindings:
        if binding.profile != profile:
            continue
        for name in (binding.symbol, *binding.aliases):
            exact.setdefault(name, []).append(binding.id)
            leaf = name.replace("::", ".").rsplit(".", 1)[-1]
            leaves.setdefault(leaf, []).append(binding.id)
    mappings: list[MappedSection] = []
    payload = text.encode()
    for section in sections.sections:
        body = payload[section.byte_start : section.byte_end].decode()
        mentions: list[Mention] = []
        for name in sorted(set(_IDENTIFIER.findall(body))):
            matches = exact.get(name, [])
            state = "exact" if len(matches) == 1 else "ambiguous" if matches else "unresolved"
            mentions.append(
                {
                    "text": name,
                    "state": state,
                    "bindings": matches,
                    "candidates": sorted(set(leaves.get(name, []))) if not matches else [],
                }
            )
        mappings.append(
            {
                "section": asdict(section),
                "mentions": mentions,
                "authority": "prior-needs-verification",
            }
        )
    return {
        "document": path.name,
        "digest": digest_file(path),
        "profile": profile,
        "sections": mappings,
    }
