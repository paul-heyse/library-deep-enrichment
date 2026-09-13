"""Operation shape compilation shares the ordinary admission and invalidation flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import evolve

from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import run_stage
from library_deep_enrichment.workflows.remote import RemoteProducer

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus
    from library_deep_enrichment.workflows.engine import StageResult


def build(corpus: Corpus) -> StageResult:
    """Compile typed call shapes without flattening wrappers or erasing nominal context.

    Returns:
        A current shape generation with exact source and substitution inputs.

    """
    stage = definition(
        "operation-shapes.v1",
        {
            "operations": ("/parameters", "/returns", "/evidence", "/profile"),
            "type_uses": ("/owner", "/nominal", "/nominal_scope", "/selector", "/resolution"),
        },
        ("operation_shapes",),
        ("semantics/type_shapes.py",),
    )
    stage = evolve(stage, max_bytes=512 * 1024 * 1024, max_seconds=1200.0)
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root, definition=stage, route="shapes", memory_bytes=8 * 1024**3
        ),
    )
