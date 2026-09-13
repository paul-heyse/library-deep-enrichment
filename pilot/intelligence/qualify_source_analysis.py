"""Real Arrow Schema MIR analysis through the shared corpus and portable evidence flow."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from library_deep_enrichment.analyses.fabric_contracts import AnalysisRequest, SourceAnalysis
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.paths import default_corpus, intelligence_root
from library_deep_enrichment.publication.closure import evidence_closure
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.workflows.source_analysis import build

OWNERS = (
    "3fc60a92b3ec67c9aeb2d24f0a5a7befd146c23d8212bef87784e3ce2b377e31",
    "ab889efc2d79eadc682bb5cbdfeccce9014e001f5fd391d7bb9d3e968054d023",
    "a0f5ed09a6de64af2bd66fcfcee8b4c99bc0f2a8c07212cb19b10382c595e59c",
    "1d82f921740a7d899bd9014b092e2edc019c7af6a628a16be4b5b05409866936",
    "bbc26b6cad763ff65df47e6d4d07b761989a66ddbcb567c7e3aa1199fae79617",
)


def main() -> None:
    """Replay retained source-model consequences without legacy stores or native extraction."""
    reader = Corpus(default_corpus(), max_rows=2_500_000).reader()
    corpus = Corpus(intelligence_root() / "source-analysis" / uuid4().hex)
    records = evidence_closure(reader, tuple(("native_facts", owner) for owner in OWNERS))
    Coordinator(corpus, WriterIdentity(principal="retained-MIR-slice", role="migration")).commit(
        records, expected=""
    )
    request = AnalysisRequest(
        logical_id="schema-construction-and-project",
        profile="arrow-schema-local-58.4",
        artifact="2ce758e2fa3e18ce0ed36564df3d81b1ea9c06acfb1fbf5bc73800f50a5e20b4",
        owners=OWNERS,
    )
    stage = build(corpus, request)
    warm = build(corpus, request)
    assert warm.reused
    results = tuple(
        item
        for item in corpus.reader().records("source_analyses")
        if isinstance(item, SourceAnalysis)
    )
    assert len(results) == len(OWNERS)
    assert any(item.frontier for item in results)
    export = corpus.root.with_name(corpus.root.name + "-export")
    export_view(corpus.reader(), export)
    restored = Corpus(corpus.root.with_name(corpus.root.name + "-restored"))
    assert import_view(restored, export, head="analysis") == corpus.reader().manifest_id
    report = {
        "source_manifest": reader.manifest_id,
        "corpus": str(corpus.root),
        "manifest": corpus.reader().manifest_id,
        "request": CONVERTER.unstructure(request),
        "stage": CONVERTER.unstructure(stage),
        "warm": CONVERTER.unstructure(warm),
        "results": [CONVERTER.unstructure(item) for item in results],
        "restored_manifest": restored.reader().manifest_id,
        "native_workers_invoked": 0,
        "legacy_authoring_reads": 0,
        "interpretation": "Modeled may-dependencies, control, and effects over five exact MIR owners. External/unselected callees remain open; no universal preservation or effect-free claim.",
        "result_revisions": [revision_of(item) for item in results],
    }
    Path(
        "tooling/library_deep_enrichment/pilot/intelligence/reports/resume-native-source-analysis.json"
    ).write_bytes(canonical(report) + b"\n")


if __name__ == "__main__":
    main()
