"""Exact source joins keep package, source-role and compiler-unit identity separate."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Literal

from attrs import asdict, frozen

from library_deep_enrichment.collection import CollectionError, confined
from library_deep_enrichment.facts.contracts import FactArtifact, SourceAnchor, SourceSegment
from library_deep_enrichment.facts.support import SupportGraph
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes, digest_file


@frozen(kw_only=True)
class Join:
    """An exact byte join or an explicit unresolved boundary, never a name guess."""

    state: Literal["exact", "ambiguous", "unmapped"]
    anchor: SourceAnchor | None
    identity: str | None
    reasons: tuple[str, ...]


def source_join(
    root: Path, knowledge: KnowledgeV3, artifact: FactArtifact, observation: dict
) -> Join:
    """Reconcile actual producer coordinates to a verified frozen source entry.

    Returns:
        The byte-identical source join, with macro expansion separated from source ownership.

    Raises:
        CollectionError: If source bytes differ from the captured observation.

    """
    SupportGraph(root, knowledge).artifact(artifact.id)
    paths = _paths(root, artifact, observation.get("file", ""))
    entries = [
        (s, e)
        for s in knowledge.source_snapshots
        if s.id in artifact.snapshots
        for e in s.files
        if e.path in paths or e.path.removeprefix(f"snapshots/{s.source_digest}/source/") in paths
    ]
    if len(entries) != 1:
        return Join(
            state="ambiguous" if entries else "unmapped",
            anchor=None,
            identity=None,
            reasons=(
                "Source path does not identify one file in the declared snapshots; no basename/fuzzy join attempted.",
            ),
        )
    snapshot, entry = entries[0]
    expected = observation.get("source_digest")
    if not expected:
        return Join(
            state="unmapped",
            anchor=None,
            identity=None,
            reasons=("Observation does not carry a source-byte digest.",),
        )
    if expected != entry.digest or digest_file(confined(root, entry.path)) != expected:
        message = "source observation and frozen bytes disagree"
        raise CollectionError(message)
    start = observation.get("byte_start", observation.get("start"))
    end = observation.get("byte_end", observation.get("end"))
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= entry.size:
        return Join(
            state="unmapped",
            anchor=None,
            identity=None,
            reasons=(
                "No verified bounded raw-byte interval; line/column positions alone do not authorize this join.",
            ),
        )
    anchor = SourceAnchor(
        snapshot=snapshot.id,
        file=entry.path,
        digest=entry.digest,
        role="expansion_location" if observation.get("expansion") else "source_location",
        segments=(
            SourceSegment(
                generated_start=0, generated_end=end - start, host_start=start, host_end=end
            ),
        ),
    )
    identity = "source-site:" + digest_bytes(canonical_bytes([asdict(anchor), artifact.context]))
    return Join(
        state="exact",
        anchor=anchor,
        identity=identity,
        reasons=(
            "Exact bytes and context; source-location equality alone does not identify runtime dispatch or a cross-language entity.",
        ),
    )


def _paths(root: Path, artifact: FactArtifact, file: str) -> set[str]:
    paths = {file}
    source = PurePosixPath(file)
    for witness in artifact.witnesses:
        if witness.kind != "unit_provenance":
            continue
        value = json.loads(confined(root, witness.path).read_bytes())
        for original, snapshot in value.get("source_roots", []):
            prefix = PurePosixPath(original)
            if source.is_relative_to(prefix):
                relative = source.relative_to(prefix)
                if ".." not in relative.parts:
                    paths.add(f"snapshots/{snapshot.removeprefix('snapshot:')}/source/{relative}")
    return paths
