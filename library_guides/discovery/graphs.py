"""Bounded structural, semantic, and fused operation graphs with explicit isolates."""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

import igraph as ig
import leidenalg
import networkx as nx
import numpy as np
from attrs import evolve, frozen
from threadpoolctl import threadpool_limits

from library_guides.corpus.backend import BudgetExceededError
from library_guides.corpus.contracts import Disposition, Relation, Scope, TypeUse
from library_guides.corpus.encoding import digest
from library_guides.corpus.evidence import select
from library_guides.corpus.schemas import revision_of
from library_guides.discovery.contracts import (
    Concept,
    DiscoveryScope,
    Embedding,
    GraphEdge,
    GraphNode,
    RetrievalUnit,
)
from library_guides.discovery.scopes import current
from library_guides.discovery.scopes import units as selected_units

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader


@frozen(kw_only=True)
class GraphBudget:
    """Finite projection bounds; exceeding them is incomplete analysis, not absence."""

    max_nodes: int = 5000
    max_edges: int = 100_000
    neighbors: int = 8
    minimum_similarity: float = 0.72
    seed: int = 19
    resolution: float = 1.0


def _structural(
    reader: CorpusReader, units: dict[str, RetrievalUnit], budget: GraphBudget
) -> list[GraphEdge]:
    edges: dict[tuple[str, str, str], GraphEdge] = {}
    for relation in reader.records("relations"):
        if isinstance(relation, Relation) and relation.source in units and relation.target in units:
            key = (relation.source, relation.target, relation.kind)
            edges[key] = GraphEdge(
                logical_id=f"edge:{digest(key)}",
                projection="structural",
                profile=relation.profile,
                source=relation.source,
                target=relation.target,
                kind=relation.kind,
                weight=1.0,
                support=(select(relation, "/kind", "structural-relation"),),
            )
    occurrences: dict[tuple[str, str, str], list[TypeUse]] = defaultdict(list)
    for use in reader.records("type_uses"):
        if (
            isinstance(use, TypeUse)
            and use.owner in units
            and use.resolution == "exact"
            and use.direct
        ):
            occurrences[use.profile, use.nominal_scope, use.nominal].append(use)
    for members in occurrences.values():
        # A bounded star preserves each nominal component without a quadratic clique.
        ordered = sorted(
            {member.owner: member for member in members}.values(), key=lambda use: use.owner
        )
        for source, target in pairwise(ordered):
            key = (source.owner, target.owner, "shares-contextual-direct-nominal")
            edges[key] = GraphEdge(
                logical_id=f"edge:{digest(key)}",
                projection="structural",
                profile=source.profile,
                source=source.owner,
                target=target.owner,
                kind=key[2],
                weight=0.5,
                support=(
                    select(source, "/nominal", "nominal-context"),
                    select(target, "/nominal", "nominal-context"),
                ),
            )
            if len(edges) > budget.max_edges:
                message = "structural graph exceeded its explicit edge bound"
                raise BudgetExceededError(message)
    return list(edges.values())


def _cosine_rows(matrix: np.ndarray) -> Iterator[np.ndarray]:
    with threadpool_limits(limits=1):
        for start in range(0, len(matrix), 64):
            yield from matrix[start : start + 64] @ matrix.T


def _semantic(
    reader: CorpusReader, units: dict[str, RetrievalUnit], budget: GraphBudget
) -> list[GraphEdge]:
    by_unit = {revision_of(unit): unit for unit in units.values()}
    spaces: dict[tuple[str, str], list[Embedding]] = defaultdict(list)
    for embedding in reader.records("embeddings"):
        if isinstance(embedding, Embedding) and embedding.unit in by_unit:
            spaces[embedding.recipe, embedding.profile].append(embedding)
    edges: dict[tuple[str, str, str], GraphEdge] = {}
    for (recipe, profile), vectors in sorted(spaces.items()):
        vectors.sort(key=lambda item: item.unit)
        matrix = np.asarray([item.vector for item in vectors], dtype=np.float32)
        for index, similarities in enumerate(_cosine_rows(matrix)):
            vector = vectors[index]
            order = np.argsort(-similarities, kind="stable")[: budget.neighbors + 1]
            for neighbor in order:
                position = int(neighbor)
                if position == index or similarities[position] < budget.minimum_similarity:
                    continue
                left, right = sorted(
                    (by_unit[vector.unit].subject, by_unit[vectors[position].unit].subject)
                )
                key = (recipe, left, right)
                edges[key] = GraphEdge(
                    logical_id=f"edge:{digest(key)}",
                    profile=profile,
                    projection="semantic",
                    source=left,
                    target=right,
                    kind="cosine-neighbor",
                    weight=float(similarities[position]),
                    support=(
                        select(vector, "/input_digest", "embedding-input"),
                        select(vectors[position], "/input_digest", "embedding-input"),
                    ),
                )
                if len(edges) > budget.max_edges:
                    message = "semantic graph exceeded its explicit edge bound"
                    raise BudgetExceededError(message)
    return list(edges.values())


def project_graphs(
    reader: CorpusReader,
    budget: GraphBudget = GraphBudget(),
    selection: DiscoveryScope | None = None,
) -> Iterator[Record]:
    """Compute separately interpretable graph communities over a recorded operation universe.

    Yields:
        Nodes, edges, scopes, and analytical memberships; no semantic qualifications.

    Raises:
        BudgetExceededError: The input projection exceeds its finite node boundary.

    """
    units: dict[str, RetrievalUnit] = {}
    for unit in selected_units(reader, selection):
        units[unit.subject] = unit
        if len(units) > budget.max_nodes:
            message = "graph projection exceeded its node budget"
            raise BudgetExceededError(message)
    namespace = "" if selection is None else f"scoped:{digest(selection.logical_id)}:"
    structural = [
        evolve(edge, logical_id=namespace + edge.logical_id)
        for edge in _structural(reader, units, budget)
    ]
    semantic = [
        evolve(edge, logical_id=namespace + edge.logical_id)
        for edge in _semantic(reader, units, budget)
    ]
    yield from structural
    yield from semantic
    for kind, edges in (
        ("structural", structural),
        ("semantic", semantic),
        ("fused", structural + semantic),
    ):
        scope = Scope(
            logical_id=f"{namespace}graph-scope:{kind}",
            owner="operation-discovery",
            query=f"all-admitted-retrieval-units:{kind}"
            if selection is None
            else revision_of(current(reader, selection)),
            members=tuple(sorted(units)),
            sources=tuple(select(unit, "/subject", "graph-universe") for unit in units.values()),
            disposition=Disposition.COMPLETE,
            frontier=(
                "Complete for admitted retrieval units only; neighbors are analytical, not interchangeability",
            ),
        )
        yield scope
        for subject, unit in sorted(units.items()):
            yield GraphNode(
                logical_id=f"{namespace}node:{kind}:{subject}",
                profile=unit.profile,
                projection=kind,
                subject=subject,
                unit=revision_of(unit),
            )
        for concept in _communities(units, edges, scope, kind, budget):
            yield evolve(concept, logical_id=namespace + concept.logical_id)


def _communities(
    units: dict[str, RetrievalUnit],
    edges: list[GraphEdge],
    scope: Scope,
    kind: str,
    budget: GraphBudget,
) -> Iterator[Concept]:
    graph = nx.Graph()
    graph.add_nodes_from(sorted(units))
    for edge in edges:
        if edge.source != edge.target:
            weight = graph.get_edge_data(edge.source, edge.target, {}).get("weight", 0.0)
            graph.add_edge(edge.source, edge.target, weight=weight + edge.weight)
    nodes = sorted(graph.nodes)
    if not nodes:
        return
    indices = {node: index for index, node in enumerate(nodes)}
    pairs = sorted(graph.edges)
    native = ig.Graph(
        n=len(nodes), edges=[(indices[left], indices[right]) for left, right in pairs]
    )
    weights = [float(graph[left][right]["weight"]) for left, right in pairs]
    partition = leidenalg.find_partition(
        native,
        leidenalg.RBConfigurationVertexPartition,
        weights=weights,
        resolution_parameter=budget.resolution,
        seed=budget.seed,
    )
    recipe = digest(
        [
            "nx-igraph-leiden.v1",
            kind,
            budget.seed,
            budget.resolution,
            nodes,
            sorted((edge.source, edge.target, edge.weight) for edge in edges),
        ]
    )
    for group in partition:
        members = tuple(sorted(nodes[int(index)] for index in group))
        yield Concept(
            logical_id=f"community:{kind}:{digest(members)}",
            kind=f"{kind}-community",
            scope=revision_of(scope),
            members=members,
            attributes=(),
            recipe=recipe,
            support=(),
            frontier=("Community membership is navigation, not a shared behavioral contract",),
        )
