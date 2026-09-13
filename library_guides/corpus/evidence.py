"""Exact logical field selections and original byte ranges in one fabric."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.contracts import (
    Blob,
    BlobChunk,
    ByteRange,
    LegacyRecord,
    RawObservation,
    Record,
    Selection,
)
from library_guides.corpus.encoding import bytes_digest, digest, payload
from library_guides.corpus.native_contracts import NativeFact
from library_guides.corpus.schemas import codec_for, revision_of

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from typing import BinaryIO

    from library_guides.corpus.store import CorpusReader

CHUNK_SIZE = 4 * 1024 * 1024


def _field_step(value: object, key: str) -> object:
    if isinstance(value, dict):
        return value[key]
    if isinstance(value, (tuple, list)) and key.isdecimal():
        return value[int(key)]
    message = f"invalid field traversal at {key}"
    raise CorpusError(message)


def field_value(body: Mapping[str, object], path: str) -> object:
    """Resolve a JSON-pointer-shaped logical field path through typed content.

    Returns:
        The exact selected scalar, ordered sequence, or typed structure.

    Raises:
        CorpusError: The field is absent or the path is malformed.

    """
    if not path.startswith("/") or path == "/":
        message = f"a nonempty logical field path is required: {path}"
        raise CorpusError(message)
    value: object = body
    for part in path[1:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        try:
            value = _field_step(value, key)
        except (KeyError, IndexError) as error:
            message = f"absent logical field: {path}"
            raise CorpusError(message) from error
    return value


def select(record: Record, path: str, role: str) -> Selection:
    """Create an exact selection; admission membership is checked on resolution.

    Returns:
        A stable family/revision/field/value witness.

    """
    return Selection(
        family=codec_for(record).family,
        revision=revision_of(record),
        field=path,
        digest=digest(field_value(payload(record), path)),
        role=role,
    )


def resolve(reader: CorpusReader, selection: Selection) -> object:
    """Verify admitted membership, record content, and selected value integrity.

    Returns:
        The verified value; no file-path citation can substitute for this.

    Raises:
        CorpusError: The selected canonical value has changed.

    """
    if selection.family in {
        "legacy_records",
        "raw_observations",
        "native_facts",
    } and selection.field.startswith("/raw/"):
        record = reader.get(selection.family, selection.revision)
        if not isinstance(record, (LegacyRecord, RawObservation, NativeFact)):
            message = "legacy record contract mismatch"
            raise CorpusError(message)
        original = json.loads(resolve_bytes(reader, record.original, max_bytes=32 * 1024 * 1024))
        value = field_value(original, selection.field.removeprefix("/raw"))
    else:
        value = field_value(reader.row(selection.family, selection.revision), selection.field)
    if digest(value) != selection.digest:
        message = f"selection digest mismatch: {selection.revision}{selection.field}"
        raise CorpusError(message)
    return value


def read_field(reader: CorpusReader, family: str, revision: str, path: str) -> object:
    """Read an exact admitted field, including native producer fields in retained source bytes.

    Returns:
        The selected original value after record and byte integrity checks.

    Raises:
        CorpusError: A raw field request does not name an original observation record.

    """
    record = reader.get(family, revision)
    if path.startswith("/raw/"):
        if not isinstance(record, (LegacyRecord, RawObservation, NativeFact)):
            message = "raw fields require an original observation record"
            raise CorpusError(message)
        source = json.loads(resolve_bytes(reader, record.original, max_bytes=32 * 1024 * 1024))
        return field_value(source, path.removeprefix("/raw"))
    return field_value(payload(record), path)


def stage_blob(
    stream: BinaryIO,
    *,
    media_type: str,
    max_bytes: int = 512 * 1024 * 1024,
) -> tuple[Blob, tuple[BlobChunk, ...]]:
    """Read a bounded object into verified, deduplicatable byte chunks.

    Returns:
        The manifest and bounded chunks for one coordinator transaction.

    Raises:
        BudgetExceededError: The original byte object exceeds the acquisition budget.

    """
    chunks: list[BlobChunk] = []
    whole = hashlib.sha256()
    size = 0
    while data := stream.read(CHUNK_SIZE):
        size += len(data)
        if size > max_bytes:
            message = f"source object exceeds {max_bytes} bytes"
            raise BudgetExceededError(message)
        whole.update(data)
        chunk_digest = bytes_digest(data)
        chunks.append(BlobChunk(logical_id=f"chunk:{chunk_digest}", data=data, digest=chunk_digest))
    content_digest = whole.hexdigest()
    blob = Blob(
        logical_id=f"blob:{content_digest}:{media_type}",
        digest=content_digest,
        size=size,
        media_type=media_type,
        chunks=tuple(revision_of(chunk) for chunk in chunks),
        chunk_sizes=tuple(len(chunk.data) for chunk in chunks),
    )
    return blob, tuple(chunks)


def iter_blob(reader: CorpusReader, revision: str) -> Iterator[bytes]:
    """Stream and verify a complete original object without a local source path.

    Yields:
        Verified original chunks in order.

    Raises:
        CorpusError: A chunk, total byte count, or whole-object digest is invalid.

    """
    blob = reader.get("blobs", revision)
    if not isinstance(blob, Blob):
        message = "blob family contract mismatch"
        raise CorpusError(message)
    whole = hashlib.sha256()
    size = 0
    for chunk_revision in blob.chunks:
        chunk = reader.get("blob_chunks", chunk_revision)
        if not isinstance(chunk, BlobChunk) or bytes_digest(chunk.data) != chunk.digest:
            message = f"corrupt source chunk: {chunk_revision}"
            raise CorpusError(message)
        whole.update(chunk.data)
        size += len(chunk.data)
        yield chunk.data
    if size != blob.size or whole.hexdigest() != blob.digest:
        message = f"corrupt complete source object: {revision}"
        raise CorpusError(message)


def resolve_bytes(
    reader: CorpusReader, selection: ByteRange, *, max_bytes: int = 1_048_576
) -> bytes:
    """Read a bounded range from verified chunks without assembling the whole object.

    Returns:
        Exact original bytes, including original newline and Unicode encoding.

    Raises:
        CorpusError: The interval or selected bytes fail validation.
        BudgetExceededError: The requested range exceeds the packet boundary.

    """
    if selection.start < 0 or selection.end < selection.start:
        message = "invalid original byte interval"
        raise CorpusError(message)
    if selection.end - selection.start > max_bytes:
        message = f"byte selection exceeds packet budget: {max_bytes}"
        raise BudgetExceededError(message)
    offset = 0
    pieces: list[bytes] = []
    blob = reader.get("blobs", selection.blob)
    if not isinstance(blob, Blob) or sum(blob.chunk_sizes) != blob.size:
        message = "invalid source object chunk manifest"
        raise CorpusError(message)
    for revision, size in zip(blob.chunks, blob.chunk_sizes, strict=True):
        start = max(0, selection.start - offset)
        end = min(size, selection.end - offset)
        if end > start:
            chunk = reader.get("blob_chunks", revision)
            if not isinstance(chunk, BlobChunk) or len(chunk.data) != size:
                message = "invalid selected source chunk"
                raise CorpusError(message)
            pieces.append(chunk.data[start:end])
        offset += size
    value = b"".join(pieces)
    if selection.end > offset or bytes_digest(value) != selection.digest:
        message = "original byte selection digest or extent mismatch"
        raise CorpusError(message)
    return value
