"""Bounded Python syntax/type reconciliation under the common stage coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.fabric_contracts import PythonBoundaryRequest
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.workflows.contracts import FamilySelector
from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import run_stage
from library_deep_enrichment.workflows.remote import RemoteProducer

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus
    from library_deep_enrichment.workflows.engine import StageResult


def build(corpus: Corpus, request: PythonBoundaryRequest) -> StageResult:
    """Admit an explicit owner request and supervise its finite source-alignment computation.

    Returns:
        An admitted typed boundary or unchanged zero-worker reuse.

    """
    Coordinator(corpus, WriterIdentity(principal="python-boundary-request")).commit(
        (request,), expected=corpus.reader().manifest_id
    )
    stage = definition(
        f"python-boundary:{request.logical_id}",
        {
            "python_boundary_requests": ("/owner", "/types"),
            "native_artifacts": ("/sources", "/shards"),
            "native_facts": ("/original",),
        },
        ("python_boundaries",),
        ("analyses/python_fabric.py", "corpus/queries.py", "corpus/store.py"),
    )
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root,
            definition=stage,
            route="python-boundary",
            subject=revision_of(request),
        ),
        selectors=(
            FamilySelector(family="python_boundary_requests", logical_ids=(request.logical_id,)),
        ),
    )
