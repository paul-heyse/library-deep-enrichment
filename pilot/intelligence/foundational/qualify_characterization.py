"""Characterize a complete retained behavior population in a new, isolated evidence copy."""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path
from unittest.mock import patch

from attrs import frozen
from library_deep_enrichment.analyses.behavior.contracts import BehaviorRequest
from library_deep_enrichment.analyses.characterization.contracts import (
    BehaviorCharacterization,
    CharacterizationRequest,
)
from library_deep_enrichment.analyses.characterization.service import analyze
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.workflows.characterization import build


@frozen(kw_only=True)
class Options:
    """Explicit acquisition-free selection and fresh output location."""

    archive: Path
    behavior: str
    profile: str
    output: Path
    max_work: int


def _qualify(options: Options) -> dict:
    started = time.monotonic()
    corpus = Corpus(options.output / "corpus")
    original_manifest = import_view(corpus, options.archive, head="analysis")
    behavior = corpus.reader().lookup("behavior_requests", options.behavior, options.profile)
    if not isinstance(behavior, BehaviorRequest):
        message = "archive lacks the exact requested behavior population"
        raise CorpusError(message)
    request = CharacterizationRequest(
        logical_id="qualified-characterization:" + options.behavior,
        behaviors=(revision_of(behavior),),
        max_work=options.max_work,
    )
    cold = build(corpus, request)
    warm_started = time.monotonic()
    with (
        patch(
            "library_deep_enrichment.workflows.remote.RemoteProducer.__call__",
            side_effect=AssertionError("unchanged request invoked a producer"),
        ),
        patch(
            "library_deep_enrichment.analyses.characterization.service.analyze",
            side_effect=AssertionError("unchanged request recomputed dimensions"),
        ),
    ):
        warm = build(corpus, request)
        assert warm.reused
    warm_seconds = time.monotonic() - warm_started
    profiles = tuple(
        item
        for item in corpus.reader().records("behavior_characterizations")
        if isinstance(item, BehaviorCharacterization) and item.request == revision_of(request)
    )
    assert {item.owner for item in profiles} == set(behavior.owners)
    portable_count, portable_seconds = _portable(corpus, options.output, request, profiles)
    (options.output / "profiles.json").write_bytes(
        canonical(CONVERTER.unstructure(profiles)) + b"\n"
    )
    return {
        "state": "completed_finite_characterization",
        "original_manifest": original_manifest,
        "archive": str(options.archive),
        "manifest": corpus.reader().manifest_id,
        "behavior": CONVERTER.unstructure(behavior),
        "request": CONVERTER.unstructure(request),
        "cold": CONVERTER.unstructure(cold),
        "warm_reused": warm.reused,
        "warm_seconds_including_planning": warm_seconds,
        "unchanged_new_producers": 0,
        "unchanged_new_characterization_calls": 0,
        "owners": len(profiles),
        "summaries_unavailable": sum(not item.summary for item in profiles),
        "with_ambient_binding_uses": sum(
            any(source.kind == "module_binding" for source in item.dependencies)
            for item in profiles
        ),
        "with_input_dependent_region_extents": sum(
            any(region.argument_dependencies for region in item.resources) for item in profiles
        ),
        "with_cyclic_local_cost_frontiers": sum(
            any(not cost.upper for cost in item.costs) for item in profiles
        ),
        "with_ordering_obligations": sum(bool(item.ordering) for item in profiles),
        "portable_records": portable_count,
        "portable_seconds_including_replay": portable_seconds,
        "elapsed_seconds": time.monotonic() - started,
        "coordinator_process_lifetime_high_water_rss_bytes": resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss
        * 1024,
        "interpretation": "Derived dimensions over the entire exact behavior-owner population. Unmapped public candidates remain in the separate callable population. Local count bounds exclude callees; unknown effects and lifetime/scheduler obligations remain open.",
        "qualification_authority": "implementation-author execution; no independent human review or terminal gate claim",
    }


def _portable(
    corpus: Corpus,
    output: Path,
    request: CharacterizationRequest,
    profiles: tuple[BehaviorCharacterization, ...],
) -> tuple[int, float]:
    started = time.monotonic()
    archive = output / "portable"
    exported = export_view(corpus.reader(), archive)
    restored = Corpus(output / "restored")
    assert import_view(restored, archive, head="analysis") == exported.manifest
    assert set(map(revision_of, analyze(restored.reader(), request))) == set(
        map(revision_of, profiles)
    )
    return exported.count, time.monotonic() - started


def main() -> None:
    """Run from explicit retained inputs and preserve a report even when qualification fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--behavior", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-work", type=int, default=1_000_000)
    arguments = parser.parse_args()
    options = Options(
        archive=arguments.archive,
        behavior=arguments.behavior,
        profile=arguments.profile,
        output=arguments.output,
        max_work=arguments.max_work,
    )
    options.output.mkdir(parents=True, exist_ok=False)
    try:
        report = _qualify(options)
    except Exception as error:
        report = {
            "state": "failed",
            "options": {
                "archive": str(options.archive),
                "behavior": options.behavior,
                "profile": options.profile,
                "output": str(options.output),
                "max_work": options.max_work,
            },
            "error_type": type(error).__name__,
            "error": str(error),
        }
        (options.output / "report.json").write_bytes(canonical(report) + b"\n")
        raise
    (options.output / "report.json").write_bytes(canonical(report) + b"\n")
    sys.stdout.write(
        json.dumps(
            {key: value for key, value in report.items() if key not in {"behavior", "request"}}
        )
        + "\n",
    )


if __name__ == "__main__":
    main()
