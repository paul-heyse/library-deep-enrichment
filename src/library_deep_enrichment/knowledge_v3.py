"""Additive source-evidence authority with an explicit V2 migration boundary."""

from __future__ import annotations

from attrs import frozen

from library_deep_enrichment.facts.contracts import (
    CandidateUniverse,
    ClaimSupport,
    ExampleDiscovery,
    FacetSeed,
    FactArtifact,
    FactHead,
    ReviewRevalidation,
    SemanticProfile,
    SourceSnapshot,
    UniverseDependency,
)
from library_deep_enrichment.knowledge import Knowledge


@frozen(kw_only=True)
class KnowledgeV3(Knowledge):
    """The same authoring authority enriched with immutable source evidence."""

    fact_artifacts: tuple[FactArtifact, ...] = ()
    fact_heads: tuple[FactHead, ...] = ()
    semantic_profiles: tuple[SemanticProfile, ...] = ()
    source_snapshots: tuple[SourceSnapshot, ...] = ()
    claim_support: tuple[ClaimSupport, ...] = ()
    facet_seeds: tuple[FacetSeed, ...] = ()
    example_discoveries: tuple[ExampleDiscovery, ...] = ()
    revalidations: tuple[ReviewRevalidation, ...] = ()
    candidate_universes: tuple[CandidateUniverse, ...] = ()
    universe_dependencies: tuple[UniverseDependency, ...] = ()
