"""Refresh exact declaration citations without replacing authored assertions or reviews."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import evolve
from filelock import FileLock

from library_deep_enrichment.collection import CollectionError, confined, load, save, select
from library_deep_enrichment.facts.contracts import FactArtifact, FactSelection
from library_deep_enrichment.facts.support import SupportGraph
from library_deep_enrichment.knowledge import Binding
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes
from library_deep_enrichment.store.staging import write_atomic


def _rows(root: Path, artifact: FactArtifact) -> dict[str, dict]:
    return {
        row["id"]: row
        for shard in artifact.shards
        for line in confined(root, shard.path).read_bytes().splitlines()
        if (row := json.loads(line))
    }


def refresh(root: Path, previous: str, current: str) -> dict[str, object]:
    """Rebind a same-job declaration revision only where owner identity is unambiguous.

    Returns:
        Updated citations and explicit removed/ambiguous owners; reviews are preserved stale.

    Raises:
        CollectionError: If artifact context or projection integrity is inconsistent.

    """
    with FileLock(str(root / "knowledge.lock"), timeout=60):
        knowledge = load(root)
        if not isinstance(knowledge, KnowledgeV3):
            message = "declaration refresh requires V3"
            raise CollectionError(message)
        graph = SupportGraph(root, knowledge)
        old, new = graph.artifact(previous, current=False), graph.artifact(current)
        if (
            old.artifact_kind != "declarations"
            or new.artifact_kind != "declarations"
            or (old.profile, old.job) != (new.profile, new.job)
        ):
            message = "refresh requires two declaration revisions of the same requested job/profile"
            raise CollectionError(message)
        old_rows, new_rows = _rows(root, old), _rows(root, new)
        mapping, dispositions = _match(old_rows, new_rows)
        updated = _project(root, knowledge, old, new, mapping)
        supports = tuple(
            evolve(
                s,
                facts=tuple(
                    _selection(new, mapping[f.record], f)
                    if f.artifact == old.id and f.record in mapping
                    else f
                    for f in s.facts
                ),
            )
            for s in updated.claim_support
        )
        save(root, evolve(updated, claim_support=supports))
    return {
        "previous": old.id,
        "current": new.id,
        "owners": dispositions,
        "automatic_reviews": 0,
        "assertions": "preserved; changed contracts or missing owners require review",
    }


def _match(old: dict[str, dict], new: dict[str, dict]) -> tuple[dict[str, dict], list[dict]]:
    by_owner: dict[tuple[str, str], list[dict]] = {}
    counts: dict[tuple[str, str], int] = {}
    for row in new.values():
        by_owner.setdefault((row["symbol"], row["kind"]), []).append(row)
    for row in old.values():
        key = row["symbol"], row["kind"]
        counts[key] = counts.get(key, 0) + 1
    mapping = {}
    dispositions = []
    for identifier, row in old.items():
        key = row["symbol"], row["kind"]
        candidates = by_owner.get(key, [])
        if len(candidates) == 1 and counts[key] == 1:
            mapping[identifier] = candidates[0]
            state = (
                "same_contract"
                if row["semantic_digest"] == candidates[0]["semantic_digest"]
                else "changed_contract"
            )
        else:
            state = "ambiguous" if candidates else "removed"
        dispositions.append({"record": identifier, "symbol": row["symbol"], "state": state})
    return mapping, dispositions


def _project(
    root: Path,
    knowledge: KnowledgeV3,
    old: FactArtifact,
    new: FactArtifact,
    mapping: dict[str, dict],
) -> KnowledgeV3:
    sources = []
    projected = {}
    for source in knowledge.sources:
        if source.acquisition != old.id:
            sources.append(source)
            continue
        body = confined(root, source.path).read_bytes()
        if digest_bytes(body) != source.digest:
            message = "source projection changed before refresh"
            raise CollectionError(message)
        row = mapping.get(json.loads(body)["id"])
        if row is None:
            sources.append(source)
            continue
        body = canonical_bytes(row)
        path = f"projections/declarations/{digest_bytes(body)}.json"
        write_atomic(confined(root, path), body)
        projected[source.id] = row
        sources.append(
            evolve(
                source,
                path=path,
                digest=digest_bytes(body),
                locator="./" + path,
                acquisition=new.id,
            )
        )
    evidence = tuple(
        evolve(e, digest=digest_bytes(select(canonical_bytes(projected[e.source]), e.selector)))
        if e.source in projected
        else e
        for e in knowledge.evidence
    )
    by_evidence = {e.id: projected[e.source] for e in evidence if e.source in projected}
    bindings = tuple(_binding(b, by_evidence) for b in knowledge.bindings)
    return evolve(knowledge, sources=tuple(sources), evidence=evidence, bindings=bindings)


def _binding(binding: Binding, rows: dict[str, dict]) -> Binding:
    declarations = [rows[e] for e in binding.evidence if e in rows]
    if len(declarations) != 1:
        return binding
    row = declarations[0]
    return evolve(binding, signature=row["signature"], aliases=tuple(row["public_routes"]))


def _selection(artifact: FactArtifact, row: dict, selection: FactSelection) -> FactSelection:
    return evolve(
        selection,
        artifact=artifact.id,
        record=row["id"],
        digest=digest_bytes(select(canonical_bytes(row), selection.selector)),
    )
