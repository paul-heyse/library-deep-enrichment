"""Reusable declaration neighborhoods, exact projections and unreviewed facet seeds."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import evolve, frozen
from filelock import FileLock

from library_deep_enrichment.collection import CollectionError, load, save, select
from library_deep_enrichment.facts import store
from library_deep_enrichment.facts.contracts import (
    ClaimSupport,
    FacetSeed,
    FactArtifact,
    FactSelection,
)
from library_deep_enrichment.facts.support import SupportGraph
from library_deep_enrichment.knowledge import Binding, Capability, Claim, Evidence, Facet, Source
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.source_pipeline import artifact_index
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes
from library_deep_enrichment.store.staging import write_atomic

_RECIPE = Path(__file__).parents[1] / "assets/analyses/declaration-facets.v1.json"


@frozen(kw_only=True)
class Draft:
    """Typed proposed records; no acquisition or acceptance authority."""

    sources: tuple[Source, ...]
    evidence: tuple[Evidence, ...]
    bindings: tuple[Binding, ...]
    claims: tuple[Claim, ...]
    capabilities: tuple[Capability, ...]
    claim_support: tuple[ClaimSupport, ...]
    seeds: tuple[FacetSeed, ...]


def selection(
    artifact: FactArtifact, record: dict[str, object], pointer: str, *, statement: bool = False
) -> FactSelection:
    """Select the actual declared field and hash its bytes.

    Returns:
        One exact citation retaining evidence class and artifact identity.

    """
    return FactSelection(
        artifact=artifact.id,
        record=str(record["id"]),
        selector=pointer,
        digest=digest_bytes(select(canonical_bytes(record), pointer)),
        role="statement" if statement else "declaration",
    )


def neighborhood(
    root: Path, artifact_id: str, nominal: str, *, limit: int = 30, offset: int = 0
) -> dict[str, object]:
    """Find a bounded page of declaration candidates without implying assignability.

    Returns:
        Operation declarations, exact selectors and explicit scope/behavioral gaps.

    Raises:
        CollectionError: If the fact index returns a malformed page.

    """
    graph = SupportGraph(root, load(root))
    artifact = graph.artifact(artifact_id)
    page = store.query(
        artifact_index(root, artifact), nominal, role="any", limit=limit, offset=offset
    )
    rows = page["rows"]
    if not isinstance(rows, list):
        message = "malformed fact query page"
        raise CollectionError(message)
    records = [
        json.loads(store.record(root, artifact_index(root, artifact), row["id"], artifact=artifact))
        for row in rows
    ]
    return {
        "protocol": "library-guides.declaration-neighborhood.v1",
        "artifact": artifact_id,
        "profile": artifact.profile,
        "nominal": nominal,
        "total": page["total"],
        "next_offset": page["next_offset"],
        "candidates": [
            {
                "id": row["id"],
                "symbol": row["symbol"],
                "signature": row["signature"],
                "public_routes": row["public_routes"],
                "type_occurrences": row["type_occurrences"],
                "semantic_digest": row["semantic_digest"],
            }
            for row in records
        ],
        "certainty": "nominal_declaration_candidates_not_assignability_or_behavior",
        "missing": json.loads(_RECIPE.read_bytes())["unknown"],
    }


def nominate(
    root: Path, artifact_id: str, identifiers: tuple[str, ...], *, family: str
) -> dict[str, object]:
    """Generate evidence-backed drafts for nominated callable contracts.

    Returns:
        Proposed capability IDs; every generated semantic subject remains unreviewed.

    Raises:
        CollectionError: If a source, callable contract or V3 authority is missing.

    """
    with FileLock(str(root / "knowledge.lock"), timeout=60):
        knowledge = load(root)
        if not isinstance(knowledge, KnowledgeV3) or not identifiers or not family.strip():
            message = "nominations require V3, exact records and a task family"
            raise CollectionError(message)
        graph = SupportGraph(root, knowledge)
        artifact = graph.artifact(artifact_id)
        bundles = [_draft(root, artifact, identifier, family) for identifier in identifiers]
        for name in ("sources", "evidence", "bindings", "claims", "capabilities", "claim_support"):
            additions = tuple(item for bundle in bundles for item in getattr(bundle, name))
            existing = getattr(knowledge, name)
            current = {item.id for item in existing}
            # Nominations are idempotent and never overwrite authored or reviewed content.
            knowledge = evolve(
                knowledge,
                **{name: existing + tuple(item for item in additions if item.id not in current)},
            )
        seeds = tuple(seed for bundle in bundles for seed in bundle.seeds)
        seed_keys = {
            (seed.capability, seed.dimension, seed.recipe) for seed in knowledge.facet_seeds
        }
        knowledge = evolve(
            knowledge,
            facet_seeds=knowledge.facet_seeds
            + tuple(
                seed
                for seed in seeds
                if (seed.capability, seed.dimension, seed.recipe) not in seed_keys
            ),
        )
        save(root, knowledge)
    return {
        "state": "drafts",
        "capabilities": [item.id for bundle in bundles for item in bundle.capabilities],
        "automatic_reviews": 0,
    }


def _draft(root: Path, artifact: FactArtifact, identifier: str, family: str) -> Draft:
    record = json.loads(
        store.record(root, artifact_index(root, artifact), identifier, artifact=artifact)
    )
    if record["kind"] != "function" or not record["signature"]:
        message = "callable nomination requires a typed function declaration"
        raise CollectionError(message)
    source, binding, binding_evidence, prefix = _projection(
        root, artifact, canonical_bytes(record), family
    )
    structural = Claim(
        id=f"claim:{prefix}:signature",
        profile=artifact.profile,
        statement=f"Declared callable: {record['signature']}. Its complete generic obligations and qualifiers are retained in the cited function contract.",
        mechanism="Typed Rustdoc declaration; nominal occurrences do not establish assignability or executable effects.",
        evidence=(binding_evidence.id,),
        verification="source_reviewed",
        category="structural",
        conditions=(
            "Documentation-generation context; ordinary consumer availability is not established.",
        ),
    )
    contracts = (selection(artifact, record, "json:/item/inner/function"),)
    if record.get("owner_contract") is not None:
        contracts += (selection(artifact, record, "json:/owner_contract"),)
    support = ClaimSupport(
        id=f"support:{prefix}:signature",
        claim=structural.id,
        assertion=structural.statement,
        kind="signature",
        facts=contracts,
    )
    documented = _documentation(artifact, record, source, prefix)
    claims = (structural, *documented.claims)
    title = documented.claims[0].statement if documented.claims else record["symbol"]

    capability = Capability(
        id=f"capability:{prefix}",
        title=title,
        intent=title,
        profile=artifact.profile,
        family=family,
        bindings=(binding.id,),
        claims=tuple(claim.id for claim in claims),
        facets=(Facet(name="declaration", value=record["signature"], claims=(structural.id,)),),
    )
    return Draft(
        sources=(source,),
        evidence=(binding_evidence, *documented.evidence),
        bindings=(binding,),
        claims=claims,
        capabilities=(capability,),
        claim_support=(support, *documented.claim_support),
        seeds=_seeds(capability.id),
    )


def _documentation(
    artifact: FactArtifact, record: dict[str, object], source: Source, prefix: str
) -> Draft:
    item = record["item"]
    docs = item.get("docs") if isinstance(item, dict) else None
    if not isinstance(docs, str) or not docs.strip():
        return Draft(
            sources=(),
            evidence=(),
            bindings=(),
            claims=(),
            capabilities=(),
            claim_support=(),
            seeds=(),
        )
    title = docs.strip().split("\n\n")[0].replace("\n", " ")
    evidence = Evidence(
        id=f"evidence:{prefix}:documentation",
        source=source.id,
        selector="json:/item/docs",
        digest=digest_bytes(select(canonical_bytes(record), "json:/item/docs")),
        subject=str(record["symbol"]),
        kind="statement",
    )
    claim = Claim(
        id=f"claim:{prefix}:documentation",
        profile=artifact.profile,
        statement=title,
        mechanism="Upstream item documentation states this behavior; extraction has not independently verified its implementation or execution.",
        evidence=(evidence.id,),
        verification="documented",
    )
    support = ClaimSupport(
        id=f"support:{prefix}:documentation",
        claim=claim.id,
        assertion=claim.statement,
        kind="upstream_statement",
        facts=(selection(artifact, record, "json:/item/docs", statement=True),),
        dependency_mode="documentation",
    )
    return Draft(
        sources=(),
        evidence=(evidence,),
        bindings=(),
        claims=(claim,),
        capabilities=(),
        claim_support=(support,),
        seeds=(),
    )


def _projection(
    root: Path, artifact: FactArtifact, raw: bytes, family: str
) -> tuple[Source, Binding, Evidence, str]:
    record = json.loads(raw)
    prefix = "draft:" + digest_bytes(
        canonical_bytes([artifact.profile, record["symbol"], record["semantic_digest"], family])
    )
    body = raw
    path = f"projections/declarations/{digest_bytes(body)}.json"
    write_atomic(root / path, body)
    header = json.loads((root / artifact.header_path).read_bytes())
    package = record["symbol"].split("::")[0]
    source = Source(
        id=f"source:{prefix}",
        path=path,
        digest=digest_bytes(body),
        locator=f"./{path}",
        profile=artifact.profile,
        origin="compiler_api",
        attribution="Upstream crate authors; retained artifact provenance and per-item documentation",
        acquisition=artifact.id,
    )
    binding_evidence = Evidence(
        id=f"evidence:{prefix}:signature",
        source=source.id,
        selector="json:/item/inner/function",
        digest=digest_bytes(select(body, "json:/item/inner/function")),
        subject=record["symbol"],
        kind="api",
    )
    binding = Binding(
        id=f"binding:{prefix}",
        symbol=record["symbol"],
        package=package,
        version=header.get("version") or "unknown",
        profile=artifact.profile,
        language="rust",
        kind="function",
        evidence=(binding_evidence.id,),
        signature=record["signature"],
        aliases=tuple(record["public_routes"]),
        families=(family,),
        resolution="candidate" if not record["public_routes"] else "resolved",
    )
    return source, binding, binding_evidence, prefix


def _seeds(capability: str) -> tuple[FacetSeed, ...]:
    recipe = json.loads(_RECIPE.read_bytes())
    return tuple(
        FacetSeed(
            capability=capability,
            dimension=dimension,
            value=None,
            facts=(),
            missing=(
                f"{dimension} is not established by declarations; inspect source, registry or execution evidence.",
            ),
            recipe=recipe["version"],
        )
        for dimension in recipe["unknown"]
    )
