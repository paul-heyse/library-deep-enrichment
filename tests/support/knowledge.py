"""Adversarial acceptance checks for the replacement evidence compiler."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from attrs import asdict, evolve

from library_deep_enrichment.collection import save
from library_deep_enrichment.evidence_graph import EvidenceGraph
from library_deep_enrichment.knowledge import (
    Binding,
    Candidate,
    Capability,
    Claim,
    Decision,
    Evidence,
    Example,
    Facet,
    Integration,
    Knowledge,
    Obligation,
    Profile,
    Review,
    Source,
)
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes


def _sample(root: Path) -> Knowledge:
    root.mkdir(parents=True, exist_ok=True)
    data = {
        "map": "Map applies a callable separately to each element.",
        "batch": "Batch calls a callable once with the full collection.",
    }
    payload = canonical_bytes(data)
    (root / "source.json").write_bytes(payload)
    source = Source(
        id="source",
        path="source.json",
        digest=digest_bytes(payload),
        locator="https://example.test/api/1",
        profile="p1",
        origin="documentation",
        attribution="Synthetic regression fixture",
    )
    evidence = tuple(
        Evidence(
            id=f"e:{key}",
            source="source",
            selector=f"json:/{key}",
            subject=key,
            digest=digest_bytes(canonical_bytes(text)),
            kind="statement",
        )
        for key, text in data.items()
    )
    bindings = tuple(
        Binding(
            id=f"api:{key}",
            symbol=f"example.{key}",
            package="example",
            version="1",
            profile="p1",
            language="python",
            kind="function",
            evidence=(f"e:{key}",),
            signature=f"{key}(values, function)",
            families=("transform",),
        )
        for key in data
    )
    claims = tuple(
        Claim(
            id=f"claim:{key}",
            profile="p1",
            statement=text,
            mechanism="Explicit synthetic specification",
            evidence=(f"e:{key}",),
        )
        for key, text in data.items()
    )
    caps = tuple(
        Capability(
            id=f"cap:{key}",
            title=key,
            intent=text,
            profile="p1",
            family="transform",
            bindings=(f"api:{key}",),
            claims=(f"claim:{key}",),
            facets=(Facet(name="placement", value=key, claims=(f"claim:{key}",)),),
        )
        for key, text in data.items()
    )
    decision = Decision(
        id="decision:transform",
        stack="example",
        profile="p1",
        task="Transform values",
        requirements=("Choose callable granularity",),
        family="transform",
        candidates=tuple(
            Candidate(capability=cap.id, when=cap.intent, claims=cap.claims) for cap in caps
        ),
        comparison="Choose per-element or whole collection",
        claims=tuple(claim.id for claim in claims),
        reversing_conditions=("Batch callable required",),
        examples=("example",),
    )
    integration = Integration(
        id="integration:map-batch",
        profile="p1",
        producer="cap:map",
        consumer="cap:batch",
        representation="list",
        ownership="caller owns list",
        lifecycle="synchronous",
        failures=("callable errors propagate",),
        claims=("claim:map", "claim:batch"),
        examples=("example",),
    )
    script = "assert list(map(lambda x: x + 1, [1, 2])) == [2, 3]\n"
    (root / "example.py").write_text(script, encoding="utf-8")
    example = Example(
        id="example",
        profile="p1",
        argv=(sys.executable, "example.py"),
        inputs=("example.py",),
        claims=("claim:map",),
    )
    obligations = tuple(
        Obligation(id=axis, axis=axis, profile="p1", target=target)
        for axis, target in (
            ("surface", "api:map"),
            ("use_case", "cap:map"),
            ("decision", decision.id),
            ("composition", integration.id),
        )
    )
    knowledge = Knowledge(
        schema_version="library-guides.knowledge.v2",
        collection_id="regression",
        profiles=(Profile(id="p1", description="Synthetic test specification version 1"),),
        sources=(source,),
        evidence=evidence,
        bindings=bindings,
        claims=claims,
        capabilities=caps,
        decisions=(decision,),
        integrations=(integration,),
        obligations=obligations,
        examples=(example,),
    )
    graph = EvidenceGraph(root, knowledge)
    reviews = tuple(
        Review(
            subject=item.id,
            reviewer="synthetic-test-reviewer",
            rationale="Regression fixture",
            digest=graph.fingerprint(item.id),
            disposition="accepted",
        )
        for item in (*claims, *caps, decision, integration)
    )
    knowledge = evolve(knowledge, reviews=reviews)
    (root / "obligations.yaml").write_text(
        yaml.safe_dump({"obligations": [asdict(item) for item in obligations]}), encoding="utf-8"
    )
    save(root, knowledge)
    return knowledge
