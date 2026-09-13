"""Run every retained declaration job with the final native decoder and exact contexts."""

from __future__ import annotations

import json
from collections import Counter

from attrs import asdict

from library_deep_enrichment.corpus.encoding import canonical
from library_deep_enrichment.corpus.evidence import resolve_bytes
from library_deep_enrichment.corpus.native_contracts import NativeArtifact
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.workflows.native import build
from pilot.intelligence.qualify_reuse import REPORTS, ROOT, RUN, verify_freeze

DECLARED_JOBS = 47


def run() -> None:
    """Requalify the complete native manifest, including zero-worker unchanged reuse."""
    freeze = verify_freeze()
    work = RUN / f"direct-native-final-{freeze[:16]}"
    corpus = Corpus(work / "corpus", max_rows=2_500_000)
    source = ROOT / "pilot/source_semantics/manifests/retained-rustdoc.local.yaml"
    first = build(corpus, source, work / "transport")
    warm = build(corpus, source, work / "transport")
    assert warm.reused
    assert not warm.outputs
    reader = corpus.reader()
    formats: Counter[int] = Counter()
    artifacts = []
    for artifact in reader.records("native_artifacts"):
        assert isinstance(artifact, NativeArtifact)
        header = json.loads(resolve_bytes(reader, artifact.header, max_bytes=32 * 1024 * 1024))
        formats[header["format"]] += 1
        artifacts.append(
            {
                "id": artifact.logical_id,
                "profile": artifact.profile,
                "format": header["format"],
                "records": artifact.record_count,
            }
        )
    assert len(artifacts) == DECLARED_JOBS
    assert verify_freeze() == freeze
    report = {
        "freeze": freeze,
        "corpus": str(corpus.root),
        "manifest": reader.manifest_id,
        "first": asdict(first),
        "warm": asdict(warm),
        "declared_jobs": DECLARED_JOBS,
        "native_artifacts": len(artifacts),
        "formats": dict(formats),
        "artifacts": artifacts,
        "supplemental_matrix": "tests/test_declaration_formats.py: all 21 ItemEnum and 14 Type wire variants, 166 declarations per format; 57/59/60/61 native admission and portable restoration. Synthetic additions do not certify consumer availability.",
    }
    (REPORTS / "completion-native-final-producers.json").write_bytes(canonical(report) + b"\n")
    (REPORTS / "completion-native-final-warm.json").write_bytes(
        canonical(
            {
                "freeze": freeze,
                "first_receipt": "completion-native-final-producers.json",
                "result": asdict(warm),
                "declared_jobs": DECLARED_JOBS,
            }
        )
        + b"\n"
    )


if __name__ == "__main__":
    run()
