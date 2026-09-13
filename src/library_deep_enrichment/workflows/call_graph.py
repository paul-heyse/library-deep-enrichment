"""Supervised complete call indexing and dependency-owned behavior request expansion."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.call_graph.contracts import (
    CallClosureRequest,
    CallIndexRequest,
)
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import StageResult, run_stage
from library_deep_enrichment.workflows.remote import RemoteProducer
from library_deep_enrichment.workflows.selected_dependencies import exact_selectors

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus


def build(corpus: Corpus, request: CallIndexRequest | CallClosureRequest) -> StageResult:
    """Keep generated behavior requests owned by the exact catalog selection stage.

    Returns:
        Complete checked indexing/selection, or reuse of the exact existing request.

    """
    Coordinator(corpus, WriterIdentity(principal="call-graph-request")).commit(
        (request,), expected=corpus.reader().manifest_id
    )
    root = Path(__file__).parents[1]
    modules = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in (root / "analyses/call_graph").glob("*.py")
        )
    )
    indexing = isinstance(request, CallIndexRequest)
    route = "native-call-index" if indexing else "native-call-closure"
    family = "call_index_requests" if indexing else "call_closure_requests"
    inputs: dict[str, tuple[str, ...]] = {
        "native_artifacts": ("/shards", "/sources", "/context", "/record_count"),
        "native_facts": ("/original", "/artifact", "/native_id"),
        "source_files": ("/blob", "/path"),
        "blobs": ("/digest", "/size"),
        "contexts": ("/toolchain", "/features", "/components"),
    }
    inputs[family] = (
        ("/artifacts", "/max_facts", "/max_bytes")
        if indexing
        else ("/index", "/roots", "/max_depth", "/limits")
    )
    if not indexing:
        inputs["call_indexes"] = ("/owners", "/model", "/frontier")
        inputs["call_index_requests"] = ("/artifacts", "/max_facts", "/max_bytes")
    stage = definition(
        route + ":" + request.logical_id,
        inputs,
        ("call_indexes",)
        if indexing
        else ("call_closures", "callable_closures", "lifecycle_closures", "behavior_requests"),
        (
            *modules,
            "workflows/call_graph.py",
            "workflows/selected_dependencies.py",
            "analyses/behavior/integrity.py",
            "analyses/behavior/service.py",
            "analyses/behavior/contracts.py",
            "analyses/behavior/mir_instances.py",
            "analyses/behavior/mir_callables.py",
            "analyses/behavior/mir_lifecycle.py",
            "analyses/behavior/mir_abi.py",
        ),
    )
    reader = corpus.reader()
    roots = [(family, revision_of(request))]
    if isinstance(request, CallIndexRequest):
        for artifact in sorted(request.artifacts):
            roots.extend(
                ("native_facts", revision_of(item))
                for item in reader.filtered_records("native_facts", (("artifact", artifact),))
            )
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root, definition=stage, route=route, subject=revision_of(request)
        ),
        selectors=exact_selectors(reader, stage, tuple(roots)),
    )
