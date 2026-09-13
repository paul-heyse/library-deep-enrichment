"""Explicit native analysis requests share stage ownership, receipts, and currentness."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.analyses.fabric_contracts import AnalysisRequest
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.schemas import revision_of
from library_guides.workflows.contracts import FamilySelector
from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import StageResult, run_stage
from library_guides.workflows.remote import RemoteProducer

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus


def build(corpus: Corpus, request: AnalysisRequest) -> StageResult:
    """Admit a finite source-model request and execute through the ordinary stage coordinator.

    Returns:
        A current result or exact reuse, with no automatic behavioral qualification.

    """
    reader = corpus.reader()
    Coordinator(corpus, WriterIdentity(principal="source-analysis-request")).commit(
        (request,), expected=reader.manifest_id
    )
    stage = definition(
        f"source-analysis:{request.logical_id}",
        {
            "analysis_requests": ("/owners", "/artifact"),
            "native_artifacts": ("/shards", "/receipt"),
        },
        ("source_analyses",),
        ("analyses/fabric.py", "analyses/flow.py", "analyses/effects.py"),
    )
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root, definition=stage, route="mir-analysis", subject=revision_of(request)
        ),
        selectors=(FamilySelector(family="analysis_requests", logical_ids=(request.logical_id,)),),
    )
