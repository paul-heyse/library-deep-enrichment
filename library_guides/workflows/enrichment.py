"""Dependency-tracked source structure and mode specialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import run_stage
from library_guides.workflows.remote import RemoteProducer

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus
    from library_guides.workflows.engine import StageResult


def build(corpus: Corpus) -> StageResult:
    """Build exact structured statements and symbolic parameter modes.

    Returns:
        The stage receipt with exact warm reuse and failure currentness.

    """
    stage = definition(
        "source-structure.v1",
        {
            "operations": ("/parameters", "/language"),
            "passages": ("/text", "/owner", "/owner_family"),
        },
        ("document_statements", "parameter_modes"),
        ("semantics/documents.py", "semantics/enrichment_contracts.py"),
    )
    return run_stage(
        corpus, stage, RemoteProducer(root=corpus.root, definition=stage, route="structure")
    )
