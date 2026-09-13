"""Retain actual async construction/polling mechanics without transferring drop claims."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import asdict
from library_guides.analyses.fabric_contracts import AnalysisRequest, SourceAnalysis
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.encoding import canonical
from library_guides.corpus.evidence import resolve_bytes
from library_guides.corpus.identities import identify, join
from library_guides.corpus.native_contracts import NativeFact
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.publication.closure import evidence_closure
from library_guides.publication.export import export_view, import_view
from library_guides.workflows.source_analysis import build

from pilot.intelligence.qualify_reuse import REPORTS, RUN, verify_freeze

ARTIFACT = "9273f84c75cc267e5e2a773e1092d57acf67d85a9e7f02c122a3a13b43e5e4ad"
SYMBOLS = {
    "datafusion::dataframe::DataFrame::execute_stream",
    "datafusion::dataframe::DataFrame::execute_stream::{closure#0}",
    "datafusion::dataframe::DataFrame::create_physical_plan",
    "datafusion::dataframe::DataFrame::create_physical_plan::{closure#0}",
    "datafusion::execution::session_state::SessionState::create_physical_plan",
    "datafusion::execution::session_state::SessionState::create_physical_plan::{closure#0}",
}


def run() -> None:
    """Replay actual retained DataFusion bodies and preserve their open boundaries."""
    freeze = verify_freeze()
    reader = Corpus(
        Path("/home/paul/smartref/.cache/library-guides-intelligence/pilot-v4/corpus"),
        max_rows=2_500_000,
    ).reader()
    owners = [
        item
        for item in reader.filtered_records("native_facts", (("artifact", ARTIFACT),))
        if isinstance(item, NativeFact) and item.symbol in SYMBOLS
    ]
    assert {item.symbol for item in owners} == SYMBOLS
    corpus = Corpus(RUN / f"result-mechanism-{freeze[:16]}", max_rows=2_500_000)
    records = evidence_closure(
        reader, tuple(("native_facts", revision_of(item)) for item in owners)
    )
    writer = Coordinator(corpus, WriterIdentity(principal="finite-native-result-analysis"))
    writer.commit(records, expected="")
    request = AnalysisRequest(
        logical_id="datafusion-stream-construction-and-polling",
        profile=owners[0].profile,
        artifact=ARTIFACT,
        owners=tuple(revision_of(item) for item in owners),
    )
    first, warm = build(corpus, request), build(corpus, request)
    assert warm.reused
    results = [
        item
        for item in corpus.reader().records("source_analyses")
        if isinstance(item, SourceAnalysis)
    ]
    assert len(results) == len(owners)
    assert any(item.frontier for item in results)
    identities = [identify(corpus.reader(), "native_facts", revision_of(item)) for item in owners]
    writer.commit(
        (*identities, join(identities[0], identities[0])), expected=corpus.reader().manifest_id
    )
    source = []
    for owner in owners:
        raw = json.loads(resolve_bytes(corpus.reader(), owner.original))
        source.append(
            {
                "owner": revision_of(owner),
                "symbol": owner.symbol,
                "source": raw["payload"]["source"],
                "events": len(raw["payload"]["events"]),
                "exit_kinds": sorted({item["kind"] for item in raw["payload"]["exits"]}),
                "callee_declarations": sorted(
                    {
                        str(item["callee"]["ty"]["nominal"])
                        for item in raw["payload"]["exits"]
                        if item.get("callee") and item["callee"].get("ty")
                    }
                ),
            }
        )
    destination = corpus.root / "export"
    export_view(corpus.reader(), destination)
    restored = Corpus(corpus.root / "restored", max_rows=2_500_000)
    assert import_view(restored, destination) == corpus.reader().manifest_id
    (REPORTS / "completion-result-mechanism.json").write_bytes(
        canonical(
            {
                "freeze": freeze,
                "manifest": corpus.reader().manifest_id,
                "export": str(destination),
                "source_manifest": reader.manifest_id,
                "request": asdict(request),
                "first": asdict(first),
                "warm": asdict(warm),
                "results": [asdict(item) for item in results],
                "source": source,
                "identity_resolution": [asdict(item) for item in identities],
                "restored_identically": True,
                "interpretation": "The public async constructor, lowered coroutine body, and physical-plan construction path are distinct exact compiler owners. The finite model follows declared local calls and preserves external, dynamic, coroutine and unmodeled-effect frontiers. It does not infer Rust stream-drop cancellation from future construction, transfer this contract to Python, prove effect absence, or claim a closed call graph.",
                "private_helper_claim": "No distinct source-private helper visibility qualification is inferred from a lowered closure name.",
                "author": "implementation-agent",
                "reviewer": "same implementation-agent",
                "independent_review": False,
            }
        )
        + b"\n"
    )
    assert verify_freeze() == freeze


if __name__ == "__main__":
    run()
