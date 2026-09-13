"""Current Python source-interface normalization with explicit artifact ownership."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.native_contracts import NativeArtifact
from library_guides.workflows.contracts import FamilySelector
from library_guides.workflows.discovery import definition
from library_guides.workflows.engine import run_stage
from library_guides.workflows.remote import RemoteProducer

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus
    from library_guides.workflows.engine import StageResult


def build(corpus: Corpus, artifact_revision: str) -> StageResult:
    """Produce current source interfaces under one retained artifact and exact context.

    Returns:
        An admitted generation or exact zero-worker reuse.

    Raises:
        CorpusError: The requested native artifact does not carry syntax observations.

    """
    reader = corpus.reader()
    artifact = reader.get("native_artifacts", artifact_revision)
    if not isinstance(artifact, NativeArtifact) or artifact.lane != "syntax":
        message = "select a current native syntax artifact"
        raise CorpusError(message)
    stage = definition(
        f"python-interfaces:{artifact.external_id}",
        {
            "native_artifacts": ("/context", "/shards"),
            "native_facts": ("/original",),
            "contexts": ("/package", "/version"),
        },
        ("operations", "gaps"),
        ("corpus/python_interfaces.py", "corpus/queries.py", "corpus/store.py"),
    )
    return run_stage(
        corpus,
        stage,
        RemoteProducer(
            root=corpus.root, definition=stage, route="python-interfaces", subject=artifact_revision
        ),
        selectors=(
            FamilySelector(family="native_artifacts", logical_ids=(artifact.logical_id,)),
            FamilySelector(family="native_facts", prefix=f"native-fact:{artifact.external_id}:"),
            FamilySelector(
                family="contexts",
                logical_ids=(reader.get("contexts", artifact.context).logical_id,),
            ),
        ),
    )
