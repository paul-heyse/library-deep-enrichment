"""Admit finite callable catalogs through the existing supervised analytical authority."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.analyses.callable_contracts import CallableRequest
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.schemas import revision_of
from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import StageResult, run_stage
from library_guides.workflows.remote import RemoteProducer
from library_guides.workflows.selected_dependencies import exact_selectors

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus


def build(corpus: Corpus, request: CallableRequest) -> StageResult:
    """Capture catalog membership and replay source joins under exact currentness.

    Returns:
        A checked finite population or reuse of the identical admitted inputs.

    """
    reader = corpus.reader()
    Coordinator(corpus, WriterIdentity(principal="callable-request")).commit(
        (request,), expected=reader.manifest_id
    )
    stage = definition(
        "callable-population:" + request.logical_id,
        {
            "callable_requests": (
                "/interfaces",
                "/executables",
                "/files",
                "/max_facts",
                "/max_bytes",
            ),
            "native_artifacts": ("/shards", "/receipt", "/sources", "/context", "/record_count"),
            "native_facts": ("/original", "/artifact", "/kind", "/file", "/native_id"),
            "source_files": ("/blob", "/path"),
            "blobs": ("/digest", "/size"),
            "contexts": ("/toolchain", "/features", "/components"),
        },
        ("callable_populations",),
        (
            "analyses/callable_contracts.py",
            "analyses/callable_schemas.py",
            "analyses/callable_sources.py",
            "analyses/callable_population.py",
            "analyses/behavior/integrity.py",
            "facts/witness_origins.py",
            "workflows/callables.py",
            "workflows/selected_dependencies.py",
        ),
    )
    reader = corpus.reader()
    roots = [("callable_requests", revision_of(request))]
    for artifact in sorted(set(request.interfaces + request.executables)):
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
            route="callable-population",
            subject=revision_of(request),
        ),
        selectors=exact_selectors(reader, stage, tuple(roots)),
    )
