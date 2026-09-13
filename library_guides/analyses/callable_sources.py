"""Byte-checked acquisition catalogs and explicit coordinate conversion for source joins."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from attrs import frozen

from library_guides.analyses.behavior.integrity import require
from library_guides.corpus.contracts import Blob, ByteRange, SourceFile
from library_guides.corpus.evidence import resolve_bytes
from library_guides.corpus.schemas import revision_of
from library_guides.facts.witness_origins import read as read_origins

if TYPE_CHECKING:
    from library_guides.corpus.native_contracts import NativeArtifact
    from library_guides.corpus.store import CorpusReader

MAX_BYTES = 8 * 1024 * 1024
COORDINATE_SIZE = 2


@frozen(kw_only=True)
class RetainedSource:
    """One selected artifact's byte identity; original paths are never reopened."""

    revision: str
    digest: str
    data: bytes

    def offset(self, position: list[int]) -> int:
        """Convert rustdoc's one-based character position to checked UTF-8 byte coordinates.

        Returns:
            A byte boundary in the retained source.

        """
        require(
            "invalid rustdoc coordinate",
            condition=isinstance(position, list)
            and len(position) == COORDINATE_SIZE
            and all(type(value) is int and value > 0 for value in position),
        )
        line, column = position
        lines = self.data.splitlines(keepends=True)
        require("rustdoc line escapes source", condition=line <= len(lines))
        text = lines[line - 1].decode("utf-8")
        require("rustdoc column escapes source", condition=column - 1 <= len(text))
        return sum(map(len, lines[: line - 1])) + len(text[: column - 1].encode("utf-8"))


def sources(reader: CorpusReader, artifact: NativeArtifact) -> dict[str, RetainedSource]:
    """Index exact retained bytes without trusting relocated witness filenames.

    Returns:
        Byte digests mapped to source records under the requested artifact.

    """
    result = {}
    total = 0
    for source in reader.get_many("source_files", artifact.sources):
        assert isinstance(source, SourceFile)
        blob = reader.get("blobs", source.blob)
        assert isinstance(blob, Blob)
        if blob.size > MAX_BYTES:
            continue  # Large acquired inputs are not source files for this bounded adapter.
        total += blob.size
        require("callable source byte budget exceeded", condition=total <= 64 * MAX_BYTES)
        selection = ByteRange(blob=source.blob, start=0, end=blob.size, digest=blob.digest)
        value = RetainedSource(
            revision=revision_of(source),
            digest=blob.digest,
            data=resolve_bytes(reader, selection, max_bytes=MAX_BYTES),
        )
        if value.digest not in result or value.revision < result[value.digest].revision:
            result[value.digest] = value
    return result


def paths(
    reader: CorpusReader, artifact: NativeArtifact, retained: dict[str, RetainedSource]
) -> dict[str, RetainedSource]:
    """Recover only recorded acquisition path-to-digest associations.

    Returns:
        Known original paths; absent historical attribution remains unresolved.

    """
    receipt = json.loads(resolve_bytes(reader, artifact.receipt, max_bytes=MAX_BYTES))
    result = {}
    for path, entry in read_origins(receipt):
        source_digest = entry.get("digest")
        require("witness origin lacks byte identity", condition=isinstance(source_digest, str))
        assert isinstance(source_digest, str)
        source = retained.get(source_digest)
        require("witness origin lacks retained bytes", condition=source is not None)
        assert source is not None
        require("witness origin byte length differs", condition=len(source.data) == entry["size"])
        result[path] = source
    return result
