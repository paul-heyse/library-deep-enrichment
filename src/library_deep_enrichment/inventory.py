"""Reusable draft inventory and documentation-mapping report pipeline."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

from library_deep_enrichment.collection import load, save
from library_deep_enrichment.docmap import map_document
from library_deep_enrichment.nominations import nominate
from library_deep_enrichment.reader import index
from library_deep_enrichment.store.digests import canonical_bytes
from library_deep_enrichment.store.staging import write_atomic


def report(root: Path, documents: Path, output: Path, *, rules: Path) -> dict[str, object]:
    """Map reference scope and classify evidence-backed discovery candidates.

    Returns:
        Acquisition and mapping counts with explicit uncertainty, not semantic coverage.

    """
    knowledge, candidates = nominate(root, load(root), rules)
    save(root, knowledge)
    write_atomic(output / "nominations.json", canonical_bytes(candidates))
    mappings = []
    for declaration in yaml.safe_load(documents.read_text(encoding="utf-8"))["documents"]:
        path = documents.parent / declaration["path"]
        mapped = map_document(path, knowledge, profile=declaration["profile"])
        write_atomic(output / "document-map" / f"{path.name}.json", canonical_bytes(mapped))
        mappings.append(
            {
                "document": path.name,
                "source_digest": mapped["digest"],
                "sections": len(mapped["sections"]),
                "mentions": dict(
                    Counter(
                        mention["state"]
                        for section in mapped["sections"]
                        for mention in section["mentions"]
                    )
                ),
            }
        )
    result: dict[str, object] = {
        "state": "unreviewed-full-inventory",
        "sources": len(knowledge.sources),
        "bindings": len(knowledge.bindings),
        "evidence": len(knowledge.evidence),
        "relations": len(knowledge.relations),
        "registry_capability_drafts": len(knowledge.capabilities),
        "relationship_resolution": dict(Counter(item.resolution for item in knowledge.relations)),
        "binding_resolution": dict(Counter(item.resolution for item in knowledge.bindings)),
        "family_nominations": dict(
            Counter(family for candidate in candidates for family in candidate["families"])
        ),
        "documents": mappings,
        "limitations": [
            "Inventory counts are not semantic coverage or public-surface completeness.",
            "Prior reference text remains prior-needs-verification.",
            "docs.rs features are not consumer Cargo feature qualification.",
        ],
    }
    write_atomic(output / "inventory.json", canonical_bytes(result))
    temporary = output / "inventory.next.sqlite"
    temporary.unlink(missing_ok=True)
    index(temporary, knowledge, evidence_root=root)
    temporary.replace(output / "inventory.sqlite")
    return result
