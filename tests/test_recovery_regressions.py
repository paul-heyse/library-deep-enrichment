"""Negative controls for evidence, authoring, extraction and publication boundaries."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from attrs import asdict, evolve
from library_guides import authoring, generations
from library_guides.adapters import registry
from library_guides.adapters.docs.markdown_sections import index_markdown
from library_guides.adapters.python.semantic import extract as extract_python
from library_guides.adapters.search.structured import ast_scan
from library_guides.collection import CollectionError, load, save
from library_guides.evidence_graph import EvidenceGraph
from library_guides.intake import ingest
from library_guides.knowledge import Knowledge
from library_guides.qualification import coverage, validate
from library_guides.schemas import validate_document
from library_guides.store.digests import canonical_bytes, digest_bytes

from .test_knowledge_v2 import _sample


def test_withdrawn_dependency_review_removes_capability_coverage(tmp_path: Path) -> None:
    """A current capability fingerprint cannot replace acceptance of its claims."""
    knowledge = _sample(tmp_path)
    changed = evolve(
        knowledge,
        reviews=tuple(review for review in knowledge.reviews if review.subject != "claim:map"),
    )
    for axis in ("use_case", "decision", "composition"):
        result = coverage(tmp_path, changed)[axis]
        assert isinstance(result, dict)
        assert result["fulfilled"] == 0


def test_authored_denominator_cannot_shrink_independent_scope(tmp_path: Path) -> None:
    """Removing an authored obligation cannot manufacture a better coverage result."""
    knowledge = _sample(tmp_path)
    changed = evolve(knowledge, obligations=knowledge.obligations[1:])
    assert any("independent scope" in error for error in validate(tmp_path, changed))
    result = coverage(tmp_path, changed)["surface"]
    assert isinstance(result, dict)
    assert result["required"] == 1
    assert result["fulfilled"] == 0


def test_example_edit_reopens_decision_review(tmp_path: Path) -> None:
    """Example inputs participate in semantic fingerprints even if claims are unchanged."""
    knowledge = _sample(tmp_path)
    before = EvidenceGraph(tmp_path, knowledge).fingerprint("decision:transform")
    (tmp_path / "example.py").write_text("assert False\n", encoding="utf-8")
    assert EvidenceGraph(tmp_path, knowledge).fingerprint("decision:transform") != before


def test_missing_execution_receipt_cannot_be_resealed_as_valid_bundle(tmp_path: Path) -> None:
    """Recomputing bundle hashes cannot bypass the execution publication gate."""
    root, store = tmp_path / "input", tmp_path / "store"
    _sample(root)
    candidate = generations.build(root, store)
    next((candidate / "verification").glob("*.json")).unlink()
    files = generations.manifest(candidate)
    (candidate / "bundle.json").write_bytes(
        canonical_bytes({"generation": digest_bytes(canonical_bytes(files)), "files": files})
    )
    with pytest.raises(CollectionError, match="verification receipt"):
        generations.publish(candidate, store, expected=None)
    assert generations.current(store) is None


def test_failed_intake_preserves_existing_authority(tmp_path: Path) -> None:
    """A failed enumerated input cannot overwrite the previous complete collection."""
    root = tmp_path / "collection"
    _sample(root)
    before = (root / "knowledge.yaml").read_bytes()
    manifest = tmp_path / "intake.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "collection_id": "broken",
                "sources": [
                    {
                        "id": "missing",
                        "adapter": "registry",
                        "package": "example",
                        "version": "1",
                        "profile": "p1",
                        "input": str(tmp_path / "absent.json"),
                        "locator": "https://example.test/1",
                        "attribution": "Synthetic",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt = ingest(manifest, root)
    assert receipt["state"] == "partial"
    assert (root / "knowledge.yaml").read_bytes() == before


def test_proposal_replaces_existing_claim_as_unreviewed_draft(tmp_path: Path) -> None:
    """An update can correct a claim without duplicate IDs or inherited acceptance."""
    knowledge = _sample(tmp_path)
    packet_path, proposal_path = tmp_path / "packet.json", tmp_path / "proposal.json"
    authoring.write_packet(tmp_path, "decision:transform", packet_path)
    packet = json.loads(packet_path.read_bytes())
    changed = evolve(knowledge.claims[0], mechanism="More precise specification wording")
    additions = Knowledge(
        schema_version="library-guides.knowledge.v2", collection_id="draft", claims=(changed,)
    )
    proposal_path.write_bytes(
        canonical_bytes(
            {
                "protocol": "library-guides.proposal.v2",
                "packet_digest": packet["packet_digest"],
                "knowledge": asdict(additions),
                "open_questions": [],
                "usage": {},
            }
        )
    )
    authoring.import_proposal(tmp_path, packet_path, proposal_path)
    updated = load(tmp_path)
    assert next(claim for claim in updated.claims if claim.id == changed.id) == changed
    assert all(review.subject != changed.id for review in updated.reviews)
    assert validate(tmp_path, updated)


def test_registry_preserves_functionality_without_accepting_it(tmp_path: Path) -> None:
    """Generic registry facts yield useful item-cited drafts and no reviews."""
    source = _sample(tmp_path).sources[0]
    data = {
        "records": {
            "add": {
                "description": "Add two arguments",
                "kind": "scalar",
                "attributes": {"arity": "2"},
            }
        }
    }
    path = tmp_path / "registry.json"
    path.write_bytes(canonical_bytes(data))
    knowledge = registry.extract(path, source, package="example", version="1")
    assert knowledge.capabilities[0].intent == "Add two arguments"
    assert knowledge.evidence[0].selector == "json:/records/add"
    assert not knowledge.reviews
    validate_document(json.loads(canonical_bytes(asdict(knowledge))))


def test_documented_python_types_are_separate_from_annotations(tmp_path: Path) -> None:
    """Native documentation can fill a useful gap without pretending compiler certainty."""
    source = _sample(tmp_path).sources[0]
    row = {
        "path": "native.read",
        "canonical": "native.read",
        "kind": "function",
        "parameters": [{"name": "source", "type": "", "kind": "positional", "default": None}],
        "returns": "",
        "resolution": "resolved",
        "docs": "Read data.\n\nParameters\n----------\nsource : str\n    Location.\n\nReturns\n-------\nTable\n    Data.",
    }
    path = tmp_path / "native.json"
    path.write_bytes(canonical_bytes({"records": {"native.read": row}}))
    binding = extract_python(path, source, package="native", version="1").bindings[0]
    assert not binding.parameters[0].type
    assert binding.parameters[0].documented_type == "str"
    assert not binding.returns
    assert binding.documented_returns == "Table"


def test_unicode_eof_markdown_selection_keeps_final_byte() -> None:
    """Byte evidence must survive multibyte characters and a missing final newline."""
    text = "# Café\n\nLast character: λ"
    section = index_markdown(text, document_path="example.md").sections[0]
    assert text.encode()[section.byte_start : section.byte_end].decode().endswith("λ")


def test_source_rule_excludes_comment_and_string_lookalikes(tmp_path: Path) -> None:
    """The syntactic lane provides an actual positive and two textual false-positive controls."""
    (tmp_path / "sample.py").write_text(
        'call(value)\n# call(value)\ntext = "call(value)"\n', encoding="utf-8"
    )
    matches = ast_scan(tmp_path, rule="call", pattern="call($VALUE)", language="python")
    assert len(matches) == 1
    assert matches[0].text == "call(value)"
    assert matches[0].certainty == "syntactic"


def test_nomination_rules_have_positive_and_negative_controls() -> None:
    """Every declared classifier must pass its paired semantic text controls."""
    import library_guides

    assets = Path(library_guides.__file__).parent / "assets"
    rules = yaml.safe_load((assets / "rules/candidates.yaml").read_text(encoding="utf-8"))[
        "families"
    ]
    controls = yaml.safe_load((assets / "rule-tests/candidates.yaml").read_text(encoding="utf-8"))
    assert rules.keys() == controls["positive"].keys() == controls["negative"].keys()
    for name, rule in rules.items():
        assert re.search(rule["pattern"], controls["positive"][name], flags=re.IGNORECASE)
        assert not re.search(rule["pattern"], controls["negative"][name], flags=re.IGNORECASE)


def test_failed_behavior_after_explicit_new_review_still_cannot_publish(tmp_path: Path) -> None:
    """Review acceptance cannot compensate for a failing executable example."""
    root, store = tmp_path / "input", tmp_path / "store"
    knowledge = _sample(root)
    candidate = generations.build(root, store)
    identity = generations.publish(candidate, store, expected=None)
    (root / "example.py").write_text("raise RuntimeError('changed behavior')\n", encoding="utf-8")
    graph = EvidenceGraph(root, knowledge)
    updated = evolve(
        knowledge,
        reviews=tuple(
            evolve(review, digest=graph.fingerprint(review.subject)) for review in knowledge.reviews
        ),
    )
    save(root, updated)
    with pytest.raises(CollectionError, match="verification failed"):
        generations.build(root, store)
    assert generations.current(store) == identity


def test_changed_review_metadata_reuses_semantically_unchanged_products(tmp_path: Path) -> None:
    """Changed builds reuse actual render and verification artifacts by semantic inputs."""
    root, store = tmp_path / "input", tmp_path / "store"
    knowledge = _sample(root)
    knowledge = evolve(knowledge, examples=(evolve(knowledge.examples[0], cacheable=True),))
    graph = EvidenceGraph(root, knowledge)
    knowledge = evolve(
        knowledge,
        reviews=tuple(
            evolve(review, digest=graph.fingerprint(review.subject)) for review in knowledge.reviews
        ),
    )
    save(root, knowledge)
    generations.build(root, store)
    save(
        root,
        evolve(
            knowledge,
            reviews=tuple(
                evolve(review, rationale="More explicit fixture attribution")
                for review in knowledge.reviews
            ),
        ),
    )
    candidate = generations.build(root, store)
    reuse = json.loads((candidate / "stage-reuse.json").read_bytes())
    assert reuse["example:reused"] == 1
    assert reuse["render:reused"] == len(knowledge.capabilities) + len(knowledge.decisions) + len(
        knowledge.integrations
    )
    assert reuse["index:executed"] == 1
