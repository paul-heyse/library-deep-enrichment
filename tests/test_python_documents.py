"""Python documentation preserves literal bytes, owner position, and unknown dynamic forms."""

from __future__ import annotations

from pathlib import Path

import pytest
from attrs import evolve
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import Passage
from library_guides.corpus.encoding import bytes_digest
from library_guides.corpus.native_contracts import NativeArtifact
from library_guides.corpus.python_documents import literals, validate
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.native_admission import NativeInputs, admit_artifacts
from library_guides.publication.export import export_view, import_view
from library_guides.semantic_packs import install
from library_guides.workflows.python_documents import build
from library_guides.workflows.python_interfaces import build as interfaces

from tests.test_python_boundaries import _lane


def test_literal_positions_and_dynamic_abstention() -> None:
    """Duplicate names, escapes, and non-ASCII prefixes use byte positions rather than spelling."""
    source = '# café\ndef f():\n    """first\\nline"""\ndef f():\n    compute_doc()\n'.encode()
    index = literals(source)
    assert len(index) == 1
    start, end, text = index[source.index(b"def f")]
    assert source[start:end] == b'"""first\\nline"""'
    assert text == "first\nline"


def test_python_document_owner_and_portable_replay(tmp_path: Path) -> None:
    """Current native source docstrings can be released without evaluating their module."""
    source = b'def run(value: bool = False):\n    """Returns a stream unless the backend materializes.\\nKeep the qualifier."""\n    raise RuntimeError("must not execute")\n'
    root = tmp_path / "source"
    rows = [
        {
            "id": "owner",
            "kind": "definition",
            "file": "subject.py",
            "payload": {
                "node_kind": "function_definition",
                "signature": "def run(value: bool = False):",
                "syntax_valid": True,
                "start": 0,
                "end": len(source),
                "source_digest": bytes_digest(source),
            },
        }
    ]
    artifact = _lane(root, "syntax", rows, source)
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    current = next(corpus.reader().records("native_artifacts"))
    assert isinstance(current, NativeArtifact)
    revision = revision_of(current)
    interfaces(corpus, revision)
    assert not build(corpus, revision).reused
    assert build(corpus, revision).reused
    passage = next(corpus.reader().records("passages"))
    assert isinstance(passage, Passage)
    assert "unless" in passage.text
    assert "\nKeep" in passage.text
    install(
        corpus,
        Path(__file__).parents[1] / "library_guides/assets/packs/input_contracts.json",
        authority="fixture-author",
    )
    assert build(corpus, revision).reused
    assert tuple(corpus.reader().records("passages")) == (passage,)
    context = corpus.reader().get("contexts", current.context)
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit(
        (evolve(context, logical_id="unrelated-witness-context"),),
        expected=corpus.reader().manifest_id,
    )
    assert interfaces(corpus, revision).reused
    assert build(corpus, revision).reused
    with pytest.raises(CorpusError, match="native-owner source alignment"):
        validate(corpus.reader(), (evolve(passage, text="Returns a stream without conditions"),))
    destination = tmp_path / "export"
    export_view(corpus.reader(), destination)
    restored = Corpus(tmp_path / "restored")
    import_view(restored, destination, head="analysis")
    assert tuple(restored.reader().records("passages")) == (passage,)
