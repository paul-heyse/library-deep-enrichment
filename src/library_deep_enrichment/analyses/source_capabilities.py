"""Reusable Python source capabilities from declarations and verified docstring roles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from attrs import evolve
from filelock import FileLock

from library_deep_enrichment import source_maps
from library_deep_enrichment.collection import CollectionError, confined, load, save, select
from library_deep_enrichment.facts.contracts import ClaimSupport, FacetSeed, FactArtifact, FactSelection
from library_deep_enrichment.facts.support import SupportGraph
from library_deep_enrichment.knowledge import Binding, Capability, Claim, Evidence, Facet, Source
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes
from library_deep_enrichment.store.staging import write_atomic

_DIMENSIONS = (
    "shape_cardinality",
    "execution_stage",
    "state_effects",
    "ownership_lifetime",
    "representation_semantics",
    "composition",
)


def nominate(
    root: Path, artifact_id: str, identifiers: tuple[str, ...], family: str
) -> dict[str, object]:
    """Create source-backed drafts without inventing export, dispatch or native behavior.

    Returns:
        Capability IDs and explicit missing source documentation.

    Raises:
        CollectionError: If source owners are absent, ambiguous or not Python definitions.

    """
    with FileLock(str(root / "knowledge.lock"), timeout=60):
        knowledge = load(root)
        if not isinstance(knowledge, KnowledgeV3) or not identifiers or not family:
            message = "source capability nomination requires V3, owners and a task family"
            raise CollectionError(message)
        artifact = SupportGraph(root, knowledge).artifact(artifact_id)
        if artifact.artifact_kind != "syntax":
            message = "source capability nomination requires structural facts"
            raise CollectionError(message)
        rows = _rows(root, artifact)
        drafted = []
        for identifier in identifiers:
            if identifier not in rows:
                message = f"source owner is absent: {identifier}"
                raise CollectionError(message)
            bundle = _draft(root, artifact, rows, identifier, family)
            origins = [s for s in knowledge.source_snapshots if s.id in artifact.snapshots]
            if len(origins) == 1:
                bundle = evolve(
                    bundle,
                    bindings=tuple(
                        evolve(b, package=origins[0].package, version=origins[0].version)
                        for b in bundle.bindings
                    ),
                )
            for field in (
                "sources",
                "evidence",
                "bindings",
                "claims",
                "capabilities",
                "claim_support",
            ):
                current = getattr(knowledge, field)
                present = {item.id for item in current}
                knowledge = evolve(
                    knowledge,
                    **{
                        field: current
                        + tuple(v for v in getattr(bundle, field) if v.id not in present)
                    },
                )
            seeds = {(s.capability, s.dimension, s.recipe) for s in knowledge.facet_seeds}
            knowledge = evolve(
                knowledge,
                facet_seeds=knowledge.facet_seeds
                + tuple(
                    s
                    for s in bundle.facet_seeds
                    if (s.capability, s.dimension, s.recipe) not in seeds
                ),
            )
            drafted.extend(c.id for c in bundle.capabilities)
        save(root, knowledge)
    return {"state": "drafts", "capabilities": drafted, "automatic_reviews": 0}


def _rows(root: Path, artifact: FactArtifact) -> dict[str, dict]:
    rows = {}
    for shard in artifact.shards:
        with confined(root, shard.path).open("rb") as stream:
            for line in stream:
                row = json.loads(line)
                if row["payload"].get("family") == "syntax" and (
                    row["kind"] == "definition" or row["payload"].get("documentation")
                ):
                    rows[row["id"]] = row
    return rows


def _draft(
    root: Path, artifact: FactArtifact, rows: dict[str, dict], identifier: str, family: str
) -> KnowledgeV3:
    row = rows[identifier]
    payload = row["payload"]
    if (
        payload.get("node_kind") not in {"function_definition", "class_definition"}
        or not payload.get("signature")
        or not payload.get("syntax_valid")
    ):
        message = "nomination requires a valid Python source definition with a real signature"
        raise CollectionError(message)
    symbol = _symbol(row, rows)
    key = "source-draft:" + digest_bytes(
        canonical_bytes([artifact.profile, artifact.job, symbol, family])
    )
    source = _projection(root, artifact, row, key)
    evidence = _evidence(source, row, key, "json:/payload/signature", statement=False)
    claim = Claim(
        id="claim:" + key + ":declaration",
        profile=artifact.profile,
        statement=f"The Python source declares `{payload['signature']}`.",
        mechanism="Source syntax with annotations/default expressions retained; decorator transformation and native dispatch are not established by this declaration.",
        evidence=(evidence.id,),
        verification="source_reviewed",
        category="structural",
        conditions=(
            "Frozen source view; source presence does not establish an exported or executable public API.",
        ),
    )
    binding = Binding(
        id="binding:" + key,
        symbol=symbol,
        package=symbol.split(".")[0],
        version="source-snapshot; inspect context",
        profile=artifact.profile,
        language="python",
        kind="function" if payload["node_kind"] == "function_definition" else "class",
        signature=payload["signature"],
        evidence=(evidence.id,),
        resolution="candidate",
        families=(family,),
    )
    support = ClaimSupport(
        id="support:" + key + ":declaration",
        claim=claim.id,
        assertion=claim.statement,
        kind="shape",
        facts=(_selection(artifact, row, "json:/payload/signature", "declaration"),),
    )
    docs = [
        r
        for r in rows.values()
        if r["payload"].get("owner") == identifier
        and r["payload"].get("documentation") == "python_docstring"
    ]
    documented = _documentation(root, artifact, docs, key)
    claims = (claim, *documented.claims)
    capability = Capability(
        id="capability:" + key,
        title=documented.claims[0].statement
        if documented.claims
        else f"Inspect {symbol}: source purpose is undocumented",
        intent=documented.claims[0].statement
        if documented.claims
        else f"Inspect {symbol}: source purpose is undocumented",
        profile=artifact.profile,
        family=family,
        bindings=(binding.id,),
        claims=tuple(c.id for c in claims),
        facets=(Facet(name="source_declaration", value=payload["signature"], claims=(claim.id,)),),
    )
    seeds = tuple(
        FacetSeed(
            capability=capability.id,
            dimension=d,
            value=None,
            facts=(),
            missing=(
                "Source declaration and documentation do not settle this dimension; request mechanism, type/native-boundary or execution evidence.",
            ),
            recipe="source-capability.v1",
        )
        for d in _DIMENSIONS
    )
    return evolve(
        documented,
        sources=(source, *documented.sources),
        evidence=(evidence, *documented.evidence),
        bindings=(binding,),
        claims=claims,
        claim_support=(support, *documented.claim_support),
        capabilities=(capability,),
        facet_seeds=seeds,
    )


def _symbol(row: dict, rows: dict[str, dict]) -> str:
    names = [row["payload"]["name"]]
    parent = row["payload"].get("owner")
    while parent in rows:
        names.insert(0, rows[parent]["payload"]["name"])
        parent = rows[parent]["payload"].get("owner")
    module = list(Path(row["file"]).with_suffix("").parts)
    if module[-1] == "__init__":
        module.pop()
    return ".".join((*module, *names))


def _projection(root: Path, artifact: FactArtifact, row: dict, key: str) -> Source:
    body = canonical_bytes(row)
    path = f"projections/source/{digest_bytes(body)}.json"
    write_atomic(confined(root, path), body)
    return Source(
        id="source:" + key,
        path=path,
        digest=digest_bytes(body),
        locator="./" + path,
        profile=artifact.profile,
        origin="fact",
        attribution="Upstream library authors; exact frozen source and extraction provenance retained",
        acquisition=artifact.id,
    )


def _evidence(source: Source, row: dict, key: str, pointer: str, *, statement: bool) -> Evidence:
    return Evidence(
        id="evidence:" + key,
        source=source.id,
        selector=pointer,
        digest=digest_bytes(select(canonical_bytes(row), pointer)),
        subject=row["id"],
        kind="statement" if statement else "fact",
    )


def _selection(
    artifact: FactArtifact, row: dict, pointer: str, role: Literal["declaration", "statement"]
) -> FactSelection:
    return FactSelection(
        artifact=artifact.id,
        record=row["id"],
        selector=pointer,
        digest=digest_bytes(select(canonical_bytes(row), pointer)),
        role=role,
    )


def _documentation(root: Path, artifact: FactArtifact, docs: list[dict], key: str) -> KnowledgeV3:
    result = KnowledgeV3(schema_version="library-guides.knowledge.v3", collection_id="draft")
    if len(docs) != 1 or not docs[0]["payload"].get("documentation_text"):
        return result
    row = docs[0]
    text = (
        source_maps.python_literal(
            source_maps.identity(row["payload"]["documentation_text"].encode())
        )
        .data.decode()
        .strip()
    )
    title = text.split("\n\n")[0].replace("\n", " ").strip()
    if not title:
        return result
    key += ":documentation"
    source = _projection(root, artifact, row, key)
    evidence = _evidence(source, row, key, "json:/payload/documentation_text", statement=True)
    claim = Claim(
        id="claim:" + key,
        profile=artifact.profile,
        statement=title,
        mechanism="The actual source docstring states this behavior; native implementation behavior is not independently verified by locating it.",
        evidence=(evidence.id,),
        verification="documented",
    )
    support = ClaimSupport(
        id="support:" + key,
        claim=claim.id,
        assertion=claim.statement,
        kind="upstream_statement",
        dependency_mode="documentation",
        facts=(_selection(artifact, row, "json:/payload/documentation_text", "statement"),),
    )
    return evolve(
        result, sources=(source,), evidence=(evidence,), claims=(claim,), claim_support=(support,)
    )
