"""Import verified native lane products into the same owned evidence fabric."""

from __future__ import annotations

import json
from collections import Counter
from typing import TYPE_CHECKING

from library_guides.collection import confined
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import ByteRange, Disposition, Job, LegacyRecord, SourceFile
from library_guides.corpus.declarations import normalize_declaration
from library_guides.corpus.encoding import bytes_digest
from library_guides.corpus.migration import LegacyImporter, MigrationReceipt
from library_guides.corpus.schemas import codec_for
from library_guides.facts.store import verify
from library_guides.knowledge_v3 import KnowledgeV3

if TYPE_CHECKING:
    from pathlib import Path

    from library_guides.corpus.store import Corpus
    from library_guides.facts.contracts import FactArtifact


def _acquire_artifact(importer: LegacyImporter, artifact: FactArtifact) -> None:
    paths = {
        artifact.input_path,
        artifact.header_path,
        artifact.receipt_path,
        *(item.path for item in artifact.witnesses),
    }
    if artifact.acquisition_path:
        paths.add(artifact.acquisition_path)
    for path in sorted(paths):
        source = importer.blob(
            confined(importer.root, path).read_bytes(), "application/octet-stream"
        )
        importer.add(
            SourceFile(
                logical_id=f"native-input:{artifact.id}:{path}",
                profile=artifact.profile,
                blob=source.blob,
                package="",
                path=path,
                locator=artifact.id,
                license="retained upstream attribution",
                acquisition=f"verified:{artifact.receipt_digest}",
            )
        )


def _import_shards(importer: LegacyImporter, artifact: FactArtifact, version: str) -> int:
    count = 0
    for shard in artifact.shards:
        path = confined(importer.root, shard.path)
        source = importer.blob(path.read_bytes(), "application/x-ndjson")
        offset = 0
        with path.open("rb") as stream:
            for line in stream:
                raw = json.loads(line)
                alias = LegacyRecord(
                    logical_id=f"native-record:{artifact.id}:{raw['id']}",
                    profile=artifact.profile,
                    artifact=artifact.id,
                    legacy_id=raw["id"],
                    kind=raw.get("kind", artifact.artifact_kind),
                    original=ByteRange(
                        blob=source.blob,
                        start=offset,
                        end=offset + len(line),
                        digest=bytes_digest(line),
                    ),
                    normalized_family="declaration-contract",
                    normalized_revision="",
                )
                importer.add(alias)
                normalize_declaration(importer, alias, raw, version=version)
                offset += len(line)
                count += 1
    return count


def import_declarations(
    corpus: Corpus, root: Path, artifact_id: str, *, expected: str
) -> MigrationReceipt:
    """Import complete D0 source bytes, original records, typed interfaces, and type trees.

    Returns:
        A finite accounting receipt with contextual-resolution limitations explicit.

    Raises:
        CorpusError: The selected legacy input is not a complete D0 artifact.

    """
    importer = LegacyImporter(root)
    knowledge = importer.knowledge
    if not isinstance(knowledge, KnowledgeV3):
        message = "native lane import requires a V3 source collection"
        raise CorpusError(message)
    artifact = next(item for item in knowledge.fact_artifacts if item.id == artifact_id)
    if artifact.artifact_kind != "declarations":
        message = "this normalizer admits declaration artifacts only"
        raise CorpusError(message)
    verify(root, artifact)
    importer.acquire()
    counts = importer.archive_families()
    importer.reviews()
    _acquire_artifact(importer, artifact)
    profile = next(item for item in knowledge.semantic_profiles if item.id == artifact.context)
    count = _import_shards(importer, artifact, profile.version)
    importer.add(
        Job(
            logical_id=f"native-import:{artifact.job or artifact.id}",
            profile=artifact.profile,
            stage="native-declarations-import.v1",
            request=artifact.id,
            inputs=(),
            universes=(),
            outputs=tuple(importer.rows),
            disposition=Disposition.COMPLETE,
            reason=f"Verified and admitted all {count} D0 records; type identities remain contextual to the artifact",
        )
    )
    manifest = Coordinator(
        corpus, WriterIdentity(principal="native-lane-import", role="migration")
    ).commit(
        importer.rows.values(),
        expected=expected,
    )
    return MigrationReceipt(
        source_digest=artifact.input_digest,
        manifest=manifest,
        legacy_families=(*counts, ("native_declarations", count)),
        admitted_families=tuple(
            sorted(Counter(codec_for(item).family for item in importer.rows.values()).items())
        ),
        limitations=(
            "Cross-artifact nominal identity and compiler applicability are separate resolution/witness products",
        ),
    )
