"""Behavior requests use the existing supervised worker and admission coordinator."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.behavior.contracts import BehaviorRequest
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import StageResult, run_stage
from library_deep_enrichment.workflows.remote import RemoteProducer
from library_deep_enrichment.workflows.selected_dependencies import exact_selectors

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus


def build(corpus: Corpus, request: BehaviorRequest) -> StageResult:
    """Admit and run one finite characterization population with exact currentness.

    Returns:
        A complete stage result or reuse of the unchanged admitted selection.

    """
    reader = corpus.reader()
    Coordinator(corpus, WriterIdentity(principal="behavior-request")).commit(
        (request,), expected=reader.manifest_id
    )
    root = Path(__file__).parents[1]
    modules = tuple(
        sorted(
            path.relative_to(root).as_posix() for path in (root / "analyses/behavior").glob("*.py")
        )
    )
    stage = definition(
        "behavior:" + request.logical_id,
        {
            "behavior_requests": (
                "/owners",
                "/artifacts",
                "/type_artifacts",
                "/bindings",
                "/limits",
                "/phase",
            ),
            "native_artifacts": ("/shards", "/receipt", "/sources", "/context", "/input"),
            "native_facts": ("/original", "/artifact", "/file", "/kind"),
            "source_files": ("/blob",),
            "blobs": ("/digest", "/size"),
            "contexts": ("/toolchain", "/features", "/components"),
        },
        (
            "behavior_programs",
            "behavior_summaries",
            "behavior_typing",
            "behavior_coverage",
            "behavior_origins",
        ),
        (*modules, "workflows/behavior.py", "workflows/selected_dependencies.py"),
    )
    reader = corpus.reader()
    # Source artifacts own immutable complete shards; execution rows are the extra
    # Python projection inputs, beyond the selected definition rows themselves.
    roots = [("behavior_requests", revision_of(request))]
    from library_deep_enrichment.corpus.native_contracts import NativeArtifact, NativeFact

    for artifact in reader.get_many("native_artifacts", request.artifacts):
        assert isinstance(artifact, NativeArtifact)
        if artifact.lane == "execution":
            roots.extend(
                ("native_facts", revision_of(item))
                for item in reader.filtered_records(
                    "native_facts", (("artifact", revision_of(artifact)), ("kind", "execution"))
                )
                if isinstance(item, NativeFact)
            )
    for revision in request.type_artifacts:
        roots.extend(
            ("native_facts", revision_of(item))
            for item in reader.filtered_records("native_facts", (("artifact", revision),))
        )
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root, definition=stage, route="behavior", subject=revision_of(request)
        ),
        selectors=exact_selectors(reader, stage, tuple(roots)),
    )
