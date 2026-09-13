"""Historical preservation cannot license new weak semantics or silently alter portable identity."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.checker_epochs import HISTORICAL, fingerprint
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.publication.export import export_view, import_view
from tests.test_corpus_fabric import _job

if TYPE_CHECKING:
    from pathlib import Path


def test_historical_checker_rejects_new_archive_and_producer(tmp_path: Path) -> None:
    """A producer cannot select old semantics, and migration cannot label new content historical."""
    corpus = Corpus(tmp_path)
    with pytest.raises(CorpusError, match="verified portable imports"):
        Coordinator(corpus, WriterIdentity(principal="producer"), historical_checker=HISTORICAL)
    writer = Coordinator(
        corpus,
        WriterIdentity(principal="importer", role="migration"),
        imported_predecessor="",
        historical_checker=HISTORICAL,
    )
    with pytest.raises(CorpusError, match="inventoried original release"):
        writer.commit((_job("newly-created"),), expected="", replace=True)
    assert not corpus.reader().manifest_id
    with pytest.raises(CorpusError, match="unsupported historical"):
        fingerprint("../../untrusted-code.py")


def test_duplicate_portable_family_rejected_before_admission(tmp_path: Path) -> None:
    """A valid family repeated in a forged envelope cannot silently deduplicate into another head."""
    corpus = Corpus(tmp_path / "source")
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit((_job("first"),), expected="")
    destination = tmp_path / "export"
    export_view(corpus.reader(), destination)
    path = destination / "manifest.json"
    manifest = json.loads(path.read_bytes())
    manifest["families"].append(manifest["families"][0])
    path.write_text(json.dumps(manifest))
    target = Corpus(tmp_path / "target")
    with pytest.raises(CorpusError, match="repeat a name"):
        import_view(target, destination)
    assert not target.reader("release").manifest_id
