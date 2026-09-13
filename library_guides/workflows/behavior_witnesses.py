"""Supervised finite observation checks with ordinary corpus admission and warm reuse."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from library_guides.analyses.behavior.witness_contracts import BehaviorWitnessRequest
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.schemas import revision_of
from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import StageResult, run_stage
from library_guides.workflows.remote import RemoteProducer
from library_guides.workflows.selected_dependencies import exact_selectors

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus


def build(corpus: Corpus, request: BehaviorWitnessRequest) -> StageResult:
    """Admit and compare the exact finite witness population, retaining disagreements.

    Returns:
        A coherent checked result or unchanged warm reuse.

    """
    reader = corpus.reader()
    Coordinator(corpus, WriterIdentity(principal="behavior-witness-request")).commit(
        (request,), expected=reader.manifest_id
    )
    root = Path(__file__).parents[1]
    modules = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in (root / "analyses/behavior").glob("witness_*.py")
        )
    )
    stage = definition(
        "behavior-witness:" + request.logical_id,
        {
            "behavior_witness_requests": (
                "/summaries",
                "/observations",
                "/evidence",
                "/max_cases",
                "/max_cells",
            ),
            "behavior_summaries": ("/clauses", "/terms", "/program", "/model"),
            "behavior_programs": (
                "/parameters",
                "/nominals",
                "/context",
                "/instructions",
                "/terms",
                "/owner",
            ),
            "behavior_origins": ("/summary", "/entries", "/model", "/request"),
            "raw_observations": ("/original", "/producer", "/context"),
            "blobs": ("/digest", "/size"),
        },
        ("behavior_witness_checks",),
        (
            *modules,
            "analyses/behavior/integrity.py",
            "analyses/behavior/origins.py",
            "workflows/behavior_witnesses.py",
            "workflows/selected_dependencies.py",
        ),
    )
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root,
            definition=stage,
            route="behavior-witness",
            subject=revision_of(request),
        ),
        selectors=exact_selectors(
            corpus.reader(), stage, (("behavior_witness_requests", revision_of(request)),)
        ),
    )
