"""Behavior is derived from primary evidence, with prior documents as priors only.

The knowledge base must not inherit a hand-written document's errors or its blind
spots. These tests pin the properties that keep evidence primary: upstream prose
is captured whole, packets carry evidence separately from grounding, and a name
that could mean two things stays ambiguous.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from library_deep_enrichment.adapters.docs.behaviors import (
    BehaviorKind,
    IdentifierShape,
    identifier_shape,
    index_behaviors,
)
from library_deep_enrichment.manifest import known_stack_ids, load_library_manifest, load_stack_manifest
from library_deep_enrichment.models.enums import Ecosystem, EvidenceOrigin, ResolutionState
from library_deep_enrichment.models.records import ApiBinding, Observation
from library_deep_enrichment.packets import PacketBudget, PacketRequest, build_packets
from library_deep_enrichment.retrieve.index_build import build_index
from library_deep_enrichment.stages.extract_documentation import (
    DOC_PREDICATE,
    harvest_rustdoc_documentation,
)
from library_deep_enrichment.stages.paths import api_path, documentation_path
from library_deep_enrichment.stages.resolve import ResolutionPass, resolve_behaviors
from library_deep_enrichment.store.jsonl import read_records

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

_DOC_TEXT = "Represents a logical expression such as `A + 1`, built by the planner."


def _rustdoc_payload() -> bytes:
    document = {
        "root": "0",
        "crate_version": "1.0.0",
        "format_version": 60,
        "index": {
            "1": {"docs": _DOC_TEXT, "visibility": "public", "inner": {"struct": {}}},
            "2": {"docs": "hi", "visibility": "public", "inner": {"struct": {}}},
        },
        "paths": {
            "0": {"crate_id": 0, "path": ["demo"], "kind": "module"},
            "1": {"crate_id": 0, "path": ["demo", "Expr"], "kind": "struct"},
            "2": {"crate_id": 0, "path": ["demo", "Tiny"], "kind": "struct"},
            "3": {"crate_id": 1, "path": ["other", "Foreign"], "kind": "struct"},
        },
        "external_crates": {"1": {"name": "other"}},
    }
    return json.dumps(document).encode("utf-8")


def test_upstream_doc_comments_are_captured_whole() -> None:
    """Truncating to a first line discards the evidence derivation depends on."""
    harvest = harvest_rustdoc_documentation(
        _rustdoc_payload(), library_id="demo", profile_id="demo-p", crate="demo"
    )
    by_subject = {o.subject: o for o in harvest.observations}
    assert by_subject["demo::Expr"].object_value == _DOC_TEXT
    assert by_subject["demo::Expr"].evidence_origin is EvidenceOrigin.DOCUMENTATION_STATEMENT
    assert by_subject["demo::Expr"].predicate == DOC_PREDICATE


def test_trivial_and_foreign_documentation_is_not_harvested() -> None:
    """A two-character doc comment is noise; a dependency's docs are its own."""
    harvest = harvest_rustdoc_documentation(
        _rustdoc_payload(), library_id="demo", profile_id="demo-p", crate="demo"
    )
    subjects = {o.subject for o in harvest.observations}
    assert "demo::Tiny" not in subjects
    assert "other::Foreign" not in subjects


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("datafusion::expr::Expr", IdentifierShape.QUALIFIED),
        ("SessionContext", IdentifierShape.TYPE_LIKE),
        ("execute_stream", IdentifierShape.CALLABLE_LIKE),
        ("ORDER_BY", IdentifierShape.CONSTANT_LIKE),
        ("AND", IdentifierShape.CONSTANT_LIKE),
    ],
)
def test_identifier_shape_separates_apis_from_keywords(token: str, expected: str) -> None:
    """A SQL keyword must not be reported as a missing API."""
    assert identifier_shape(token) == expected


def test_behaviors_carry_stable_ids_and_their_kind() -> None:
    """A behavior id survives edits above it; a line offset does not."""
    text = (
        "# Doc\n\n"
        "## 1.1 First behavior\n\nBody citing `demo::Expr` here.\n\n"
        "## 1.2 Second behavior\n\nMore text.\n\n"
        "## Anti-patterns\n\nDo not do this.\n"
    )
    index = index_behaviors(text, doc_id="demo", document_path="demo.md")
    ids = {b.behavior_id for b in index.behaviors}
    assert "demo:1.1" in ids
    assert "demo:1.2" in ids
    assert index.by_kind(BehaviorKind.ANTI_PATTERN)
    first = index.by_id()["demo:1.1"]
    assert "demo::Expr" in first.cited_identifiers
    assert first.is_cross_checkable()


def test_a_shifted_document_keeps_the_same_behavior_ids() -> None:
    """Inserting content above a behavior must not change its identity."""
    body = "## 2.1 Stable\n\nText.\n"
    before = index_behaviors(f"# Doc\n\n{body}", doc_id="demo", document_path="demo.md")
    after = index_behaviors(
        f"# Doc\n\nAdded paragraph.\n\n{body}", doc_id="demo", document_path="demo.md"
    )
    assert set(before.by_id()) == set(after.by_id())
    assert before.by_id()["demo:2.1"].start_line != after.by_id()["demo:2.1"].start_line


def test_an_ambiguous_name_is_never_silently_bound() -> None:
    """A leaf name matching several identities must stay ambiguous."""
    text = "## 1.1 Uses a common name\n\nDiscusses `SessionContext` generally.\n"
    index = index_behaviors(text, doc_id="df-rust", document_path="demo.md")
    lookup = build_index(known_stack_ids(), repository_root=REPOSITORY_ROOT)
    result = resolve_behaviors([index], lookup, ecosystem_by_doc={"df-rust": Ecosystem.RUST})
    states = {o.resolution_state for o in result.observations}
    assert states
    assert ResolutionState.RESOLVED not in states or len(result.observations) > 1
    for observation in result.observations:
        if observation.resolution_state is ResolutionState.AMBIGUOUS:
            assert observation.competing_subjects


def test_every_observation_records_which_pass_produced_it() -> None:
    """Resolution quality is only auditable if the pass is recorded."""
    text = "## 1.1 Cites a qualified path\n\nSee `datafusion::dataframe::DataFrame`.\n"
    index = index_behaviors(text, doc_id="df-rust", document_path="demo.md")
    lookup = build_index(known_stack_ids(), repository_root=REPOSITORY_ROOT)
    result = resolve_behaviors([index], lookup, ecosystem_by_doc={"df-rust": Ecosystem.RUST})
    assert result.observations
    for observation in result.observations:
        assert observation.extractor_id in {
            ResolutionPass.QUALIFIED_PATH,
            ResolutionPass.QUALIFIED_ALIAS,
            ResolutionPass.REGISTERED_SURFACE,
            ResolutionPass.SHORT_NAME_IN_SCOPE,
            ResolutionPass.SHORT_NAME_AMBIGUOUS,
        }


def _first_rust_profile() -> tuple[str, str]:
    for stack_id in known_stack_ids():
        stack = load_stack_manifest(stack_id)
        if stack.ecosystem != "rust":
            continue
        library = load_library_manifest(stack.libraries[0])
        return stack.libraries[0], library.profiles[0].profile_id
    message = "no rust stack is declared"
    raise AssertionError(message)


def test_packets_keep_evidence_and_grounding_separate() -> None:
    """A prior document is compared against, never treated as authority."""
    library_id, profile_id = _first_rust_profile()
    bindings = list(
        read_records(api_path(library_id, profile_id, repository_root=REPOSITORY_ROOT), ApiBinding)
    )[:60]
    packets = build_packets(
        PacketRequest(
            library_id=library_id,
            profile_id=profile_id,
            bindings=bindings,
            documentation={},
            grounding={},
        )
    )
    assert packets
    for packet in packets:
        assert packet.evidence
        assert packet.grounding == ()
        assert packet.open_questions


def test_packets_respect_their_declared_budget() -> None:
    """Unbounded packets make model cost per unit of work unpredictable."""
    library_id, profile_id = _first_rust_profile()
    bindings = list(
        read_records(api_path(library_id, profile_id, repository_root=REPOSITORY_ROOT), ApiBinding)
    )[:400]
    budget = PacketBudget(max_items=10, max_documentation_chars=2_000)
    packets = build_packets(
        PacketRequest(
            library_id=library_id,
            profile_id=profile_id,
            bindings=bindings,
            documentation={},
            budget=budget,
        )
    )
    assert packets
    assert all(len(packet.evidence) <= budget.max_items for packet in packets)


def test_packet_digest_is_stable_and_content_sensitive() -> None:
    """Caching a model response requires a key that tracks the packet's content."""
    library_id, profile_id = _first_rust_profile()
    bindings = list(
        read_records(api_path(library_id, profile_id, repository_root=REPOSITORY_ROOT), ApiBinding)
    )[:20]
    request = PacketRequest(
        library_id=library_id, profile_id=profile_id, bindings=bindings, documentation={}
    )
    first = build_packets(request)[0]
    second = build_packets(request)[0]
    assert first.digest() == second.digest()
    enriched = build_packets(
        PacketRequest(
            library_id=library_id,
            profile_id=profile_id,
            bindings=bindings,
            documentation={bindings[0].identity.public_path: "new upstream prose"},
        )
    )[0]
    assert enriched.digest() != first.digest()


def test_upstream_documentation_was_actually_harvested_for_a_rust_profile() -> None:
    """A structurally present harvester that produced nothing would be inert."""
    library_id, profile_id = _first_rust_profile()
    path = documentation_path(library_id, profile_id, repository_root=REPOSITORY_ROOT)
    assert path.is_file(), f"no upstream documentation harvested at {path}"
    records = list(read_records(path, Observation))
    minimum_records = 500
    minimum_characters = 100_000
    assert len(records) >= minimum_records
    assert all(r.predicate == DOC_PREDICATE for r in records)
    assert sum(len(r.object_value) for r in records) > minimum_characters
