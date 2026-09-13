"""Structured documentation and qualitative review controls."""

from __future__ import annotations

import zlib
from pathlib import Path

import pytest
import yaml
from library_guides.adapters.docs.structured import rst_sections, sphinx_inventory
from library_guides.collection import CollectionError
from library_guides.evidence_graph import EvidenceGraph
from library_guides.qualitative import audit

from .test_knowledge_v2 import _sample


def test_rst_retains_unknown_directive_diagnostics(tmp_path: Path) -> None:
    """Unsupported Sphinx constructs remain visible instead of silently disappearing."""
    path = tmp_path / "source.rst"
    path.write_text(
        "Document\n========\n\nSection\n-------\n\nA paragraph.\n\n.. unknown-pilot-directive:: value\n",
        encoding="utf-8",
    )
    result = rst_sections(path)
    assert result["sections"]
    assert "unknown-pilot-directive" in str(result["diagnostics"])


def test_sphinx_inventory_expands_exact_object_uri(tmp_path: Path) -> None:
    """Locators retain their domain, role, version and profile."""
    path = tmp_path / "objects.inv"
    header = b"# Sphinx inventory version 2\n# Project: Example\n# Version: 1\n# The remainder of this file is compressed using zlib.\n"
    path.write_bytes(header + zlib.compress(b"demo.fn py:function 1 api.html#$ -\n"))
    result = sphinx_inventory(path, base_url="https://example.test/1/", profile="p1")
    assert result["objects"] == [
        {
            "name": "demo.fn",
            "domain": "py",
            "role": "function",
            "uri": "https://example.test/1/api.html#demo.fn",
        }
    ]
    assert result["profile"] == "p1"


def test_qualitative_review_rejects_a_stale_artifact_without_any_runner(tmp_path: Path) -> None:
    """Qualitative evidence must be current even though there is no model score."""
    knowledge = _sample(tmp_path)
    tasks, observations, report = (
        tmp_path / "tasks.yaml",
        tmp_path / "observations.yaml",
        tmp_path / "review.md",
    )
    tasks.write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "id": "transform",
                        "prompt": "Transform values",
                        "profile": "p1",
                        "requirements": ["Compare granularity"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    observations.write_text(
        yaml.safe_dump(
            {
                "observations": [
                    {
                        "task": "transform",
                        "disposition": "supported",
                        "reviewer": "Synthetic regression reviewer",
                        "finding": "The declared comparison distinguishes granularity",
                        "comparison": "Explicit conditions retained",
                        "reversing_condition": "Whole-batch callable required",
                        "follow_up": "Revisit on evidence changes",
                        "records": [
                            [
                                "decision:transform",
                                EvidenceGraph(tmp_path, knowledge).fingerprint(
                                    "decision:transform"
                                ),
                            ]
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    receipt = audit(tmp_path, tasks, observations, report)
    assert receipt["model_runs"] == 0
    assert receipt["full_task_scope_supported"] is True
    (tmp_path / "example.py").write_text("assert False\n", encoding="utf-8")
    with pytest.raises(CollectionError, match="stale"):
        audit(tmp_path, tasks, observations, report)
