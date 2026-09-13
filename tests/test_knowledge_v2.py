"""Adversarial acceptance checks for the replacement evidence compiler."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml
from attrs import asdict, evolve
from library_deep_enrichment import authoring, build_system, generations, reader
from library_deep_enrichment.collection import CollectionError, save
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
from library_deep_enrichment.qualification import coverage, validate
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


def test_absent_sources_and_obligations_are_not_success(tmp_path: Path) -> None:
    """Empty input cannot qualify through a vacuous loop."""
    knowledge = Knowledge(schema_version="library-guides.knowledge.v2", collection_id="empty")
    assert validate(tmp_path, knowledge)


def test_file_citation_cannot_replace_item_evidence(tmp_path: Path) -> None:
    """A syntactically nonempty citation to an entire file is not a citation."""
    knowledge = _sample(tmp_path)
    evidence = evolve(knowledge.evidence[0], selector="json:")
    assert validate(tmp_path, evolve(knowledge, evidence=(evidence, *knowledge.evidence[1:])))


def test_changed_selected_statement_reopens_every_dependent_review(tmp_path: Path) -> None:
    """Digest integrity and dependency fingerprints both detect semantic edits."""
    knowledge = _sample(tmp_path)
    (tmp_path / "source.json").write_bytes(
        canonical_bytes({"map": "Opposite behavior", "batch": "unchanged"})
    )
    errors = validate(tmp_path, knowledge)
    assert any("source changed" in error for error in errors)
    assert any("decision:transform" in error for error in errors)


def test_new_alternative_reopens_decision_without_changing_selected_apis(tmp_path: Path) -> None:
    """Candidate-set dependencies prevent stale recommendations after additive releases."""
    knowledge = _sample(tmp_path)
    added = evolve(knowledge.bindings[0], id="api:new", symbol="example.native_batch")
    updated = evolve(knowledge, bindings=(*knowledge.bindings, added))
    before = EvidenceGraph(tmp_path, knowledge)
    after = EvidenceGraph(tmp_path, updated)
    assert before.fingerprint("cap:map") == after.fingerprint("cap:map")
    assert before.fingerprint("decision:transform") != after.fingerprint("decision:transform")


def test_wrong_profile_evidence_is_rejected(tmp_path: Path) -> None:
    """A same-named item in another version cannot support this profile."""
    knowledge = _sample(tmp_path)
    wrong = evolve(knowledge.claims[0], profile="different")
    errors = validate(tmp_path, evolve(knowledge, claims=(wrong, *knowledge.claims[1:])))
    assert any("wrong evidence profile" in error for error in errors)


def test_unreviewed_claim_never_counts_as_coverage(tmp_path: Path) -> None:
    """Coverage counts accepted evidence closures, not authored rows."""
    knowledge = _sample(tmp_path)
    unreviewed = evolve(knowledge, reviews=())
    axis = coverage(tmp_path, unreviewed)["decision"]
    assert isinstance(axis, dict)
    assert axis["fulfilled"] == 0


def test_publication_is_atomic_and_predecessor_guarded(tmp_path: Path) -> None:
    """A stale writer cannot replace another writer's complete generation."""
    root, store = tmp_path / "input", tmp_path / "store"
    _sample(root)
    staged = generations.build(root, store)
    identity = generations.publish(staged, store, expected=None)
    with pytest.raises(CollectionError, match="conflict"):
        generations.publish(staged, store, expected=None)
    assert generations.current(store) == identity
    assert generations.resolve(store).name == identity


def test_failed_example_preserves_published_generation(tmp_path: Path) -> None:
    """Behavioral failure cannot publish even when prose and citations validate."""
    root, store = tmp_path / "input", tmp_path / "store"
    _sample(root)
    staged = generations.build(root, store)
    identity = generations.publish(staged, store, expected=None)
    (root / "example.py").write_text("raise RuntimeError('behavior changed')\n", encoding="utf-8")
    with pytest.raises(CollectionError, match="review required"):
        generations.build(root, store)
    assert generations.current(store) == identity


def test_unchanged_build_reuses_verified_bytes_without_model_work(tmp_path: Path) -> None:
    """The actual scheduler performs no work for a verified no-op update."""
    root, store = tmp_path / "input", tmp_path / "store"
    _sample(root)
    first = build_system.run(root, store)
    second = build_system.run(root, store)
    assert first["state"] == "executed"
    assert second["state"] == "reused"
    assert second["model_calls"] == 0


def test_discovery_and_exact_lookup_preserve_scope(tmp_path: Path) -> None:
    """Python/Rust or version collisions cannot escape the requested profile."""
    knowledge = _sample(tmp_path)
    path = tmp_path / "index.sqlite"
    reader.index(path, knowledge)
    assert reader.search(path, "example.map", profile="p1", exact=True)
    assert not reader.search(path, "example.map", profile="other", exact=True)
    assert reader.search(path, "Transform callable", profile="p1")
    assert not reader.search(path, "Transform callable", profile="other")


def test_rendered_claims_have_specific_resolvable_citations(tmp_path: Path) -> None:
    """The consumer artifact retains item selectors and conditions."""
    knowledge = _sample(tmp_path)
    text = reader.render(tmp_path, knowledge, "decision:transform")
    assert "json:/map" in text
    assert "SHA-256" in text
    assert "Reversing conditions" in text


def test_model_response_cannot_invent_evidence_or_review_itself(tmp_path: Path) -> None:
    """Automated and file-based authoring share the same strict ingestion gate."""
    knowledge = _sample(tmp_path)
    request = authoring.packet(tmp_path, knowledge, "decision:transform")
    proposal = {
        "protocol": "library-guides.proposal.v2",
        "packet_digest": request["packet_digest"],
        "knowledge": {
            "schema_version": "library-guides.knowledge.v2",
            "collection_id": "draft",
            "claims": [
                {
                    "id": "invented",
                    "profile": "p1",
                    "statement": "Unsupported",
                    "mechanism": "Guess",
                    "evidence": ["does-not-exist"],
                }
            ],
        },
        "open_questions": [],
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }
    with pytest.raises(CollectionError, match="unsupported citation"):
        authoring.validate_proposal(proposal, request)


def test_packet_hash_changes_with_questions_and_candidate_attributes(tmp_path: Path) -> None:
    """Changing semantic fields invalidates model response reuse."""
    knowledge = _sample(tmp_path)
    first = authoring.packet(tmp_path, knowledge, "decision:transform")
    changed = evolve(knowledge.capabilities[0], intent="Different applicability")
    second = authoring.packet(
        tmp_path,
        evolve(knowledge, capabilities=(changed, *knowledge.capabilities[1:])),
        "decision:transform",
    )
    assert first["packet_digest"] != second["packet_digest"]
