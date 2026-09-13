"""Exact Python docstring literals attached by native owner byte positions."""

from __future__ import annotations

import ast
import json
from collections import defaultdict
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import BudgetExceededError, CorpusError
from library_deep_enrichment.corpus.contracts import ByteRange, Operation, Passage, SourceFile
from library_deep_enrichment.corpus.encoding import bytes_digest
from library_deep_enrichment.corpus.evidence import iter_blob, resolve_bytes
from library_deep_enrichment.corpus.native_contracts import NativeArtifact, NativeFact
from library_deep_enrichment.corpus.python_interfaces import PREFIX
from library_deep_enrichment.corpus.schemas import revision_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader

DOC_PREFIX = "python-source-doc:"
MAX_SOURCE_BYTES = 8 * 1024 * 1024


def literals(data: bytes) -> dict[int, tuple[int, int, str]]:
    """Index constant docstrings by definition byte offset without importing the module.

    Returns:
        Exact literal intervals and decoded string values; computed expressions are omitted.

    """
    offsets: list[int] = []
    offset = 0
    for line in data.splitlines(keepends=True):
        offsets.append(offset)
        offset += len(line)
    result: dict[int, tuple[int, int, str]] = {}
    for node in ast.walk(ast.parse(data)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.body:
            continue
        first = node.body[0]
        if (
            not isinstance(first, ast.Expr)
            or not isinstance(first.value, ast.Constant)
            or not isinstance(first.value.value, str)
        ):
            continue
        value = first.value
        text = value.value
        assert isinstance(text, str)
        if value.end_lineno is not None and value.end_col_offset is not None:
            result[offsets[node.lineno - 1] + node.col_offset] = (
                offsets[value.lineno - 1] + value.col_offset,
                offsets[value.end_lineno - 1] + value.end_col_offset,
                text,
            )
    return result


def _bytes(reader: CorpusReader, source: SourceFile) -> bytes:
    result = bytearray()
    for chunk in iter_blob(reader, source.blob):
        result.extend(chunk)
        if len(result) > MAX_SOURCE_BYTES:
            message = "Python docstring projection exceeds the 8 MiB source-file bound"
            raise BudgetExceededError(message)
    return bytes(result)


def documents(reader: CorpusReader, operations: Iterable[Operation]) -> Iterator[Passage]:
    """Recover source documentation in finite file batches with exact owner alignment.

    Yields:
        Literal source passages, preserving quotes/escapes in their original byte selection.

    Raises:
        CorpusError: An owner does not match its retained source bytes or artifact.

    """
    groups: dict[tuple[str, str], list[tuple[Operation, dict]]] = defaultdict(list)
    for operation in operations:
        if not operation.logical_id.startswith(PREFIX):
            continue
        selected = next(
            item for item in operation.evidence if item.field == "/raw/payload/signature"
        )
        fact = reader.get("native_facts", selected.revision)
        assert isinstance(fact, NativeFact)
        body = json.loads(resolve_bytes(reader, fact.original, max_bytes=1_000_000))["payload"]
        groups[fact.artifact, fact.file].append((operation, body))
    artifacts: dict[str, tuple[SourceFile, ...]] = {}
    for (artifact_revision, file), owners in sorted(groups.items()):
        if artifact_revision not in artifacts:
            artifact = reader.get("native_artifacts", artifact_revision)
            assert isinstance(artifact, NativeArtifact)
            artifacts[artifact_revision] = tuple(
                item
                for item in reader.get_many("source_files", artifact.sources)
                if isinstance(item, SourceFile)
            )
        sources = [
            item
            for item in artifacts[artifact_revision]
            if item.path == file or item.path.endswith("/source/" + file)
        ]
        if len(sources) != 1:
            message = "Python documentation requires one exact retained source file"
            raise CorpusError(message)
        source = sources[0]
        data = _bytes(reader, source)
        observed = bytes_digest(data)
        index = literals(data)
        for operation, body in owners:
            if body.get("source_digest") != observed:
                message = "Python docstring owner refers to different source bytes"
                raise CorpusError(message)
            selected_literal = index.get(body["start"])
            if selected_literal is None:
                continue
            start, end, text = selected_literal
            yield Passage(
                logical_id=DOC_PREFIX + operation.logical_id,
                profile=operation.profile,
                owner=revision_of(operation),
                role="python-source-docstring",
                text=text,
                language="en",
                source=ByteRange(
                    blob=source.blob, start=start, end=end, digest=bytes_digest(data[start:end])
                ),
            )


def project(reader: CorpusReader, artifact_revision: str) -> Iterator[Passage]:
    """Select the current interfaces of one native artifact.

    Yields:
        Only source-aligned passages for that exact artifact's normalized interfaces.

    """
    operations = (
        item
        for item in reader.filtered_records("operations", (("language", "python"),))
        if isinstance(item, Operation)
        and item.logical_id.startswith(PREFIX + artifact_revision + ":")
    )
    yield from documents(reader, operations)


def validate(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Independently check source literal ownership in file batches.

    Raises:
        CorpusError: A literal is attributed to a different owner or source interval.

    """
    proposed = [
        item
        for item in records
        if isinstance(item, Passage) and item.logical_id.startswith(DOC_PREFIX)
    ]
    if not proposed:
        return
    operations = tuple(
        item
        for item in reader.get_many("operations", (item.owner for item in proposed))
        if isinstance(item, Operation)
    )
    expected = {revision_of(item) for item in documents(reader, operations)}
    if any(revision_of(item) not in expected for item in proposed):
        message = "Python docstring differs from exact native-owner source alignment"
        raise CorpusError(message)
