"""Evaluate bounded helper selection over a retained Rust development population."""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from attrs import evolve, frozen
from library_guides.analyses.behavior.contracts import BehaviorRequest, BehaviorSummary
from library_guides.analyses.behavior.coverage import BehaviorCoverage
from library_guides.analyses.call_graph.contracts import (
    CallClosure,
    CallClosureRequest,
    CallIndex,
    CallIndexRequest,
)
from library_guides.analyses.call_graph.service import validate
from library_guides.corpus.encoding import CONVERTER, canonical
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.publication.export import export_view, import_view
from library_guides.workflows.behavior import build as build_behavior
from library_guides.workflows.call_graph import build


@frozen(kw_only=True)
class Options:
    """A preserved archive, exact behavior context and bounded new selection."""

    archive: Path
    behavior: str
    profile: str
    output: Path
    max_owners: int
    max_depth: int


def _outcomes(corpus: Corpus, request: BehaviorRequest) -> dict:
    result = {}
    for row in corpus.reader().filtered_records(
        "behavior_coverage", (("request", revision_of(request)),)
    ):
        assert isinstance(row, BehaviorCoverage)
        summary = corpus.reader().get("behavior_summaries", row.summary) if row.summary else None
        assert summary is None or isinstance(summary, BehaviorSummary)
        result[row.owner] = {
            "state": row.state,
            "phase": row.phase,
            "precision": summary.precision if summary else "",
            "clauses": len(summary.clauses) if summary else 0,
            "unknown_call_effects": sum(
                effect.kind == "unknown_call"
                for clause in summary.clauses
                for effect in clause.effects
            )
            if summary
            else 0,
        }
    assert set(result) == set(request.owners)
    return result


def _qualify(options: Options) -> dict:
    started = time.monotonic()
    corpus = Corpus(options.output / "corpus")
    report = {"original_manifest": import_view(corpus, options.archive, head="analysis")}
    roots = corpus.reader().lookup("behavior_requests", options.behavior, options.profile)
    assert isinstance(roots, BehaviorRequest)
    before = _outcomes(corpus, roots)
    index_request = CallIndexRequest(
        logical_id="qualified-calls:" + options.behavior,
        profile=options.profile,
        artifacts=roots.artifacts,
    )
    report["index_stage"] = CONVERTER.unstructure(build(corpus, index_request))
    index = corpus.reader().lookup(
        "call_indexes", "call-index:" + index_request.logical_id, options.profile
    )
    assert isinstance(index, CallIndex)
    request = CallClosureRequest(
        logical_id="qualified-helpers:" + options.behavior,
        profile=options.profile,
        index=revision_of(index),
        roots=roots.owners,
        limits=evolve(roots.limits, owners=options.max_owners),
        max_depth=options.max_depth,
    )
    report["selection_stage"] = CONVERTER.unstructure(build(corpus, request))
    selection = corpus.reader().lookup(
        "call_closures", "call-closure:" + request.logical_id, options.profile
    )
    assert isinstance(selection, CallClosure)
    behavior = corpus.reader().get("behavior_requests", selection.behavior)
    assert isinstance(behavior, BehaviorRequest)
    report["interpretation_stage"] = CONVERTER.unstructure(build_behavior(corpus, behavior))
    after = _outcomes(corpus, behavior)
    with patch(
        "library_guides.workflows.remote.RemoteProducer.__call__", side_effect=AssertionError
    ):
        assert build(corpus, index_request).reused
        assert build(corpus, request).reused
        assert build_behavior(corpus, behavior).reused
    return {
        "state": "completed_bounded_helper_experiment",
        **report,
        "manifest": corpus.reader().manifest_id,
        "index": CONVERTER.unstructure(index),
        "selection": CONVERTER.unstructure(selection),
        "behavior": CONVERTER.unstructure(behavior),
        "before": before,
        "after": after,
        "selected_owners": len(behavior.owners),
        "root_owners": len(roots.owners),
        "helper_owners": len(selection.helpers),
        "call_dispositions": dict(Counter(call.state for call in selection.calls)),
        "unchanged_new_producer_calls": 0,
        "portable_replayed": True,
        "portable_records": _portable(corpus, options.output, index, selection, behavior),
        "elapsed_seconds": time.monotonic() - started,
        "coordinator_process_lifetime_high_water_rss_bytes": resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss
        * 1024,
        "interpretation": "Exact finite catalog selection does not establish whole-program, instance, effect or native-boundary closure. Original root and unresolved-source reservation denominators remain unchanged.",
    }


def _portable(
    corpus: Corpus,
    output: Path,
    index: CallIndex,
    selection: CallClosure,
    behavior: BehaviorRequest,
) -> int:
    exported = export_view(corpus.reader(), output / "portable")
    restored = Corpus(output / "restored")
    assert import_view(restored, output / "portable", head="analysis") == exported.manifest
    validate(restored.reader(), (index, selection))
    assert _outcomes(restored, behavior) == _outcomes(corpus, behavior)
    return exported.count


def main() -> None:
    """Run in a fresh corpus copy and retain failure diagnostics alongside successful reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--behavior", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-owners", type=int, default=128)
    parser.add_argument("--max-depth", type=int, default=12)
    args = parser.parse_args()
    options = Options(
        archive=args.archive,
        behavior=args.behavior,
        profile=args.profile,
        output=args.output,
        max_owners=args.max_owners,
        max_depth=args.max_depth,
    )
    options.output.mkdir(parents=True, exist_ok=False)
    try:
        report = _qualify(options)
    except Exception as error:
        (options.output / "report.json").write_bytes(
            canonical({"state": "failed", "error_type": type(error).__name__, "error": str(error)})
            + b"\n"
        )
        raise
    (options.output / "report.json").write_bytes(canonical(report) + b"\n")
    sys.stdout.write(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key not in {"index", "selection", "behavior", "before", "after"}
            }
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
