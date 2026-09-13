"""Refresh the retained real discovery scope and preserve it through index maintenance."""

from __future__ import annotations

import json
import logging
from time import perf_counter

from attrs import asdict
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.discovery.contracts import DiscoveryScope
from library_deep_enrichment.discovery.scopes import current
from library_deep_enrichment.runtime import RuntimeConfig, embedding_client
from library_deep_enrichment.workflows.discovery import (
    build_embeddings,
    build_fca,
    build_graphs,
    build_labels,
    build_retrieval,
)
from library_deep_enrichment.paths import default_corpus, runtime_root

from pilot.intelligence.qualify_reuse import REPORTS, ROOT, verify_freeze

LOG = logging.getLogger(__name__)


def _build(corpus: Corpus) -> dict[str, object]:
    """Run each scoped stage and verify that labels preserve base-stage reuse.

    Returns:
        Complete first/warm receipts for the declared independent population.

    """
    scope = CONVERTER.structure(
        json.loads((ROOT / "pilot/intelligence/scopes/arrow-schema-native.json").read_bytes()),
        DiscoveryScope,
    )
    client = embedding_client(
        RuntimeConfig(root=runtime_root())
    )
    stages = []
    for name, build in (
        ("retrieval", lambda: build_retrieval(corpus, scope)),
        ("embeddings", lambda: build_embeddings(corpus, client, scope)),
        ("graphs", lambda: build_graphs(corpus, scope)),
        ("concepts", lambda: build_fca(corpus, scope)),
        ("labels", lambda: build_labels(corpus, scope)),
    ):
        LOG.info("BUILD %s", name)
        first, warm = build(), build()
        assert warm.reused
        stages.append({"stage": name, "first": asdict(first), "warm": asdict(warm)})
    base = (build_retrieval(corpus, scope), build_embeddings(corpus, client, scope))
    assert all(item.reused for item in base)
    return {
        "selector": asdict(scope),
        "independent_population": len(current(corpus.reader(), scope).members),
        "stages": stages,
        "base_after_labels": [asdict(item) for item in base],
    }


def run() -> None:
    """Qualify scoped FCA/labels, unchanged base products, and exact maintained membership."""
    freeze = verify_freeze()
    corpus = Corpus(
        default_corpus(), max_rows=2_500_000
    )
    before = corpus.reader()
    source_members = tuple(before.members("native_artifacts"))
    started = perf_counter()
    results = _build(corpus)
    after = corpus.reader()
    assert tuple(after.members("native_artifacts")) == source_members
    first_page = after.page("operations", max_rows=5)
    assert after.manifest is not None
    LOG.info("MAINTAIN %s", after.manifest_id)
    maintained = Coordinator(
        corpus, WriterIdentity(principal="completion-index-maintenance")
    ).refresh_indexes(expected=after.manifest_id)
    reader = corpus.reader()
    assert reader.manifest is not None
    assert reader.manifest.members_digest == after.manifest.members_digest
    assert reader.manifest.count == after.manifest.count
    assert after.page("operations", max_rows=5) == first_page
    assert tuple(reader.members("native_artifacts")) == source_members
    assert verify_freeze() == freeze
    report = {
        "freeze": freeze,
        "source_manifest": before.manifest_id,
        "built_manifest": after.manifest_id,
        "maintained_manifest": maintained,
        **results,
        "source_artifacts_unchanged": len(source_members),
        "maintenance_membership_unchanged": True,
        "pinned_reader_unchanged": True,
        "membership_sha256": reader.manifest.members_digest,
        "selected_records": reader.manifest.count,
        "elapsed_seconds": perf_counter() - started,
        "limits": [
            "Exact declared contextual population, not exhaustive upstream semantic coverage",
            "Whole-record input revisions; no field-only semantic equivalence cache claim",
            "No source extraction is requested; label completion preserves zero-producer retrieval/embedding reuse",
            "Index-only delta refresh; no history pruning or corpus compaction",
        ],
    }
    (REPORTS / "completion-final-discovery-maintenance.json").write_bytes(canonical(report) + b"\n")
    LOG.info("DONE %s", maintained)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
