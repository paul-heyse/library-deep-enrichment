"""Build portable, explicitly bounded semantic pilots from a broad evidence inventory."""

from __future__ import annotations

from pathlib import Path

from attrs import evolve

from library_deep_enrichment.collection import CollectionError, confined, save
from library_deep_enrichment.knowledge import Knowledge
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.store.staging import write_atomic


def select_scope(
    root: Path, knowledge: Knowledge, identifiers: tuple[str, ...], destination: Path
) -> Knowledge:
    """Select exact bindings and their upstream documentation without inventing semantics.

    Returns:
        An evidence-only collection ready for bounded semantic authoring.

    Raises:
        CollectionError: If a requested identity is absent or duplicated.

    """
    selected = tuple(item for item in knowledge.bindings if item.id in identifiers)
    if len(selected) != len(set(identifiers)):
        message = "scope identifiers must each resolve exactly once"
        raise CollectionError(message)
    evidence_ids = {key for binding in selected for key in binding.evidence}
    symbols = {(item.profile, item.symbol) for item in selected}
    sources = {item.id: item for item in knowledge.sources}
    evidence = tuple(
        item
        for item in knowledge.evidence
        if item.id in evidence_ids or (sources[item.source].profile, item.subject) in symbols
    )
    source_ids = {item.source for item in evidence}
    kept_sources = tuple(item for item in knowledge.sources if item.id in source_ids)
    for source in kept_sources:
        write_atomic(confined(destination, source.path), confined(root, source.path).read_bytes())
    relations = tuple(
        evolve(item, resolution="external") if item.target not in identifiers else item
        for item in knowledge.relations
        if item.source in identifiers and item.evidence in {ref.id for ref in evidence}
    )
    result = Knowledge(
        schema_version="library-guides.knowledge.v2",
        collection_id=knowledge.collection_id + "-scope",
        sources=kept_sources,
        evidence=evidence,
        bindings=selected,
        relations=relations,
        profiles=knowledge.profiles,
    )
    if isinstance(knowledge, KnowledgeV3):
        fact_ids = {source.acquisition for source in kept_sources}
        result = KnowledgeV3(
            schema_version="library-guides.knowledge.v3",
            collection_id=result.collection_id,
            sources=result.sources,
            evidence=result.evidence,
            bindings=result.bindings,
            relations=result.relations,
            profiles=result.profiles,
        )
        result = _fact_authority(root, knowledge, result, fact_ids, destination)
    save(destination, result)
    return result


def facts_scope(root: Path, identifiers: tuple[str, ...], destination: Path) -> KnowledgeV3:
    """Create an explicitly unreviewed fact scope without changing the source policy.

    Returns:
        A portable V3 authority requiring its own independently declared task policy.

    Raises:
        CollectionError: If the destination exists or an artifact cannot be selected exactly.

    """
    from library_deep_enrichment.collection import load
    from library_deep_enrichment.facts.support import SupportGraph

    original = load(root)
    if (
        destination.exists()
        or not isinstance(original, KnowledgeV3)
        or not identifiers
        or len(set(identifiers)) != len(identifiers)
    ):
        message = "fact scope requires V3, unique artifacts and a new destination"
        raise CollectionError(message)
    graph = SupportGraph(root, original)
    for identifier in identifiers:
        graph.artifact(identifier)
    result = KnowledgeV3(
        schema_version="library-guides.knowledge.v3",
        collection_id=original.collection_id + "-fact-scope",
        profiles=original.profiles,
    )
    result = _fact_authority(root, original, result, set(identifiers), destination)
    save(destination, result)
    return result


def _fact_authority(
    root: Path, original: KnowledgeV3, result: KnowledgeV3, identifiers: set[str], destination: Path
) -> KnowledgeV3:
    catalog = {item.id: item for item in original.fact_artifacts}
    pending = list(identifiers)
    while pending:
        identifier = pending.pop()
        for dependency in catalog[identifier].dependencies:
            if dependency.artifact not in identifiers:
                identifiers.add(dependency.artifact)
                pending.append(dependency.artifact)
    artifacts = tuple(item for item in original.fact_artifacts if item.id in identifiers)
    snapshots = tuple(
        item
        for item in original.source_snapshots
        if item.id in {key for artifact in artifacts for key in artifact.snapshots}
    )
    paths = {entry.path for snapshot in snapshots for entry in snapshot.files}
    for artifact in artifacts:
        paths.update((artifact.input_path, artifact.header_path, artifact.receipt_path))
        paths.update(shard.path for shard in artifact.shards)
        paths.update(item.path for item in artifact.witnesses)
        if artifact.acquisition_path:
            paths.add(artifact.acquisition_path)
    for path in paths:
        write_atomic(confined(destination, path), confined(root, path).read_bytes())
    return evolve(
        result,
        fact_artifacts=artifacts,
        source_snapshots=snapshots,
        semantic_profiles=tuple(
            item
            for item in original.semantic_profiles
            if item.id in {artifact.context for artifact in artifacts}
        ),
        fact_heads=tuple(head for head in original.fact_heads if head.artifact in identifiers),
    )
