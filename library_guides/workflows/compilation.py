"""Admit observed compilation correspondence through the existing analytical coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.analyses.compilation_contracts import CompilationRequest
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.schemas import revision_of
from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import StageResult, run_stage
from library_guides.workflows.remote import RemoteProducer
from library_guides.workflows.selected_dependencies import exact_selectors

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus


def build(corpus: Corpus, request: CompilationRequest) -> StageResult:
    """Capture unit membership and replay exact input observations under checked currentness.

    Returns:
        A supervised admitted population or reuse of unchanged exact evidence.

    """
    reader = corpus.reader()
    Coordinator(corpus, WriterIdentity(principal="compilation-request")).commit(
        (request,), expected=reader.manifest_id
    )
    stage = definition(
        "compilation-population:" + request.logical_id,
        {
            "compilation_requests": (
                "/executables",
                "/metadata",
                "/messages",
                "/max_facts",
                "/max_bytes",
            ),
            "native_artifacts": (
                "/header",
                "/shards",
                "/receipt",
                "/sources",
                "/context",
                "/record_count",
                "/input",
            ),
            "native_facts": ("/original", "/artifact", "/kind"),
            "source_files": ("/blob", "/path"),
            "blobs": ("/digest", "/size"),
            "contexts": ("/toolchain", "/features", "/components"),
        },
        ("compilation_populations",),
        (
            "analyses/compilation_contracts.py",
            "analyses/compilation_schemas.py",
            "analyses/compilation_inputs.py",
            "analyses/compilation_join.py",
            "analyses/compilation.py",
            "analyses/callable_sources.py",
            "analyses/behavior/integrity.py",
            "facts/compiler_invocation.py",
            "facts/witness_origins.py",
            "workflows/compilation.py",
            "workflows/selected_dependencies.py",
        ),
    )
    reader = corpus.reader()
    roots = [("compilation_requests", revision_of(request))]
    for artifact in sorted(set(request.metadata + request.messages)):
        roots.extend(
            ("native_facts", revision_of(item))
            for item in reader.filtered_records("native_facts", (("artifact", artifact),))
        )
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root,
            definition=stage,
            route="compilation-population",
            subject=revision_of(request),
        ),
        selectors=exact_selectors(reader, stage, tuple(roots)),
    )
