"""Rust type graph controls for methods, field ownership and namespace collisions."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import evolve
from library_deep_enrichment.adapters.rust.semantic import extract
from library_deep_enrichment.evidence_graph import EvidenceGraph
from library_deep_enrichment.linking import link

from tests.support.knowledge import _sample


def test_index_keeps_associated_methods_fields_and_item_namespaces(tmp_path: Path) -> None:
    """Rustdoc paths alone omit members and cannot distinguish value/type namespaces."""
    items = {
        "0": ("demo", {"module": {"items": [1, 2, 3, 4]}}),
        "1": ("Value", {"struct": {"kind": {"plain": {"fields": [5]}}, "impls": [6]}}),
        "2": ("parse", {"module": {"items": []}}),
        "3": (
            "parse",
            {
                "function": {
                    "sig": {"inputs": [], "output": {"resolved_path": {"id": 1, "path": "Value"}}}
                }
            },
        ),
        "4": ("Alias", {"type_alias": {"type": {"resolved_path": {"id": 1, "path": "Value"}}}}),
        "5": ("count", {"struct_field": {"primitive": "i64"}}),
        "6": (
            None,
            {
                "impl": {
                    "for": {"resolved_path": {"id": 1, "path": "Value"}},
                    "trait": None,
                    "items": [7],
                }
            },
        ),
        "7": (
            "consume",
            {
                "function": {
                    "sig": {
                        "inputs": [["value", {"resolved_path": {"id": 1, "path": "Value"}}]],
                        "output": {"primitive": "bool"},
                    }
                }
            },
        ),
    }
    document = {
        "root": 0,
        "crate_version": "1",
        "paths": {"1": {"path": ["demo", "Value"], "crate_id": 0, "kind": "struct"}},
        "index": {
            key: {
                "name": name,
                "inner": inner,
                "crate_id": 0,
                "visibility": "public",
                "docs": None,
                "links": {},
                "attrs": [],
            }
            for key, (name, inner) in items.items()
        },
    }
    source = evolve(_sample(tmp_path).sources[0], origin="compiler_api", path="rust.json")
    (tmp_path / source.path).write_text(json.dumps(document), encoding="utf-8")
    knowledge = link(extract(tmp_path / source.path, source, package="demo"))
    bindings = {
        binding.symbol: binding for binding in knowledge.bindings if binding.kind != "module"
    }
    assert bindings["demo::Value::count"].signature.endswith("i64")
    assert bindings["demo::Value::consume"].parameters[0].type == "demo::Value"
    assert bindings["demo::Alias"].signature.endswith("demo::Value")
    assert len({binding.id for binding in knowledge.bindings}) == len(knowledge.bindings)
    assert any(
        edge.kind == "produces" and edge.target == bindings["demo::Value"].id
        for edge in knowledge.relations
    )
    assert any(
        edge.kind == "member_of" and edge.source == bindings["demo::Value::count"].id
        for edge in knowledge.relations
    )
    graph = EvidenceGraph(tmp_path, knowledge)
    for evidence in knowledge.evidence:
        assert graph.selected(evidence)


def test_reexported_trait_members_survive_private_defining_module(tmp_path: Path) -> None:
    """A public trait path owns methods even when module traversal cannot reach it."""
    document = {
        "root": 0,
        "crate_version": "1",
        "paths": {"2": {"path": ["demo", "private", "Provider"], "crate_id": 0, "kind": "trait"}},
        "index": {
            "0": {
                "name": "demo",
                "crate_id": 0,
                "visibility": "public",
                "docs": None,
                "links": {},
                "attrs": [],
                "inner": {"module": {"items": [1, 4]}},
            },
            "1": {
                "name": "private",
                "crate_id": 0,
                "visibility": "crate",
                "docs": None,
                "links": {},
                "attrs": [],
                "inner": {"module": {"items": [2]}},
            },
            "2": {
                "name": "Provider",
                "crate_id": 0,
                "visibility": "public",
                "docs": "Provides rows",
                "links": {},
                "attrs": [],
                "inner": {"trait": {"items": [3]}},
            },
            "3": {
                "name": "scan",
                "crate_id": 0,
                "visibility": "default",
                "docs": "Scans rows",
                "links": {},
                "attrs": [],
                "inner": {"function": {"sig": {"inputs": [], "output": None}}},
            },
            "4": {
                "name": None,
                "crate_id": 0,
                "visibility": "public",
                "docs": None,
                "links": {},
                "attrs": [],
                "inner": {"use": {"name": "Provider", "id": 2, "is_glob": False}},
            },
        },
    }
    source = evolve(_sample(tmp_path).sources[0], origin="compiler_api", path="reexport.json")
    (tmp_path / source.path).write_text(json.dumps(document), encoding="utf-8")
    knowledge = extract(tmp_path / source.path, source, package="demo")
    assert any(binding.symbol == "demo::private::Provider::scan" for binding in knowledge.bindings)
    method = next(
        binding for binding in knowledge.bindings if binding.symbol.endswith("Provider::scan")
    )
    assert "demo::Provider::scan" in method.aliases
    assert any(
        evidence.subject == "demo::private::Provider::scan" and evidence.kind == "statement"
        for evidence in knowledge.evidence
    )
