"""Supervised exact source docstrings for current normalized Python interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.native_contracts import NativeArtifact
from library_guides.corpus.python_interfaces import PREFIX
from library_guides.workflows.contracts import FamilySelector
from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import run_stage
from library_guides.workflows.remote import RemoteProducer

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus
    from library_guides.workflows.engine import StageResult


def build(corpus: Corpus, artifact: str) -> StageResult:
    """Attach original literal documentation to current interfaces of one exact artifact.

    Returns:
        A complete finite projection receipt, including absence of literal docstrings.

    Raises:
        CorpusError: The selected source is not a native artifact.

    """
    reader = corpus.reader()
    selected = reader.get("native_artifacts", artifact)
    if not isinstance(selected, NativeArtifact):
        message = "Python documentation requires an exact native artifact"
        raise CorpusError(message)
    sources = reader.get_many("source_files", selected.sources)
    stage = definition(
        f"python-documents:{artifact}",
        {
            "operations": ("/evidence",),
            "native_artifacts": ("/sources",),
            "source_files": ("/blob", "/path"),
        },
        ("passages",),
        ("corpus/python_documents.py", "corpus/python_interfaces.py", "corpus/store.py"),
    )
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root, definition=stage, route="python-documents", subject=artifact
        ),
        selectors=(
            FamilySelector(family="operations", prefix=PREFIX + artifact + ":"),
            FamilySelector(family="native_artifacts", logical_ids=(selected.logical_id,)),
            FamilySelector(
                family="source_files", logical_ids=tuple(source.logical_id for source in sources)
            ),
        ),
    )
