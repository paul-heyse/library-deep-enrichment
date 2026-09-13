"""Existing supervised stage flow for reusable behavioral dimensions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from library_guides.analyses.characterization.contracts import CharacterizationRequest
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.schemas import revision_of
from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import StageResult, run_stage
from library_guides.workflows.remote import RemoteProducer
from library_guides.workflows.selected_dependencies import exact_selectors

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus


def build(corpus: Corpus, request: CharacterizationRequest) -> StageResult:
    """Admit evidence-linked dimensions over a complete finite outcome population.

    Returns:
        A supervised checked stage or exact unchanged reuse.

    """
    Coordinator(corpus, WriterIdentity(principal="characterization-request")).commit(
        (request,), expected=corpus.reader().manifest_id
    )
    root = Path(__file__).parents[1]
    modules = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in (root / "analyses/characterization").glob("*.py")
        )
    )
    stage = definition(
        "behavior-characterization:" + request.logical_id,
        {
            "characterization_requests": ("/behaviors", "/max_owners", "/max_terms", "/max_work"),
            "behavior_requests": ("/owners", "/artifacts", "/limits", "/phase"),
            "behavior_coverage": ("/state", "/program", "/summary", "/phase"),
            "behavior_programs": ("/terms", "/instructions", "/edges", "/frontier"),
            "behavior_summaries": ("/terms", "/clauses", "/precision", "/frontier"),
        },
        ("behavior_characterizations",),
        (
            *modules,
            "workflows/characterization.py",
            "workflows/selected_dependencies.py",
            "analyses/behavior/integrity.py",
        ),
    )
    reader = corpus.reader()
    roots = [("characterization_requests", revision_of(request))]
    for behavior in request.behaviors:
        roots.extend(
            ("behavior_coverage", revision_of(item))
            for item in reader.filtered_records("behavior_coverage", (("request", behavior),))
        )
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root,
            definition=stage,
            route="behavior-characterization",
            subject=revision_of(request),
        ),
        selectors=exact_selectors(reader, stage, tuple(roots)),
    )
