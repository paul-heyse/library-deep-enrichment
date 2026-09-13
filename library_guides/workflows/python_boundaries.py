"""Bounded Python syntax/type reconciliation under the common stage coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.analyses.fabric_contracts import PythonBoundaryRequest
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.schemas import revision_of
from library_guides.workflows.contracts import FamilySelector
from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import run_stage
from library_guides.workflows.remote import RemoteProducer

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus
    from library_guides.workflows.engine import StageResult


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
