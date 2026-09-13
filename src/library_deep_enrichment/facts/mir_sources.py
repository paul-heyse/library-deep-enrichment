"""Acquire the exact source-byte closure of a bounded compiler frame stream."""

from __future__ import annotations

import json
from pathlib import Path

from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.facts.contracts import Budget, FileEntry
from library_deep_enrichment.facts.protocol import Frames
from library_deep_enrichment.store.digests import digest_file

_PREFIX_BYTES = 4


def witnesses(path: Path, budget: Budget) -> tuple[FileEntry, ...]:
    """Retain compiler-mapped helper and standard-library source dependencies before admission.

    Returns:
        Source witnesses whose actual bytes match every claimed exact compiler mapping.

    Raises:
        CollectionError: The stream, source identity or finite acquisition budget is invalid.

    """
    if path.stat().st_size > budget.input_bytes:
        message = "compiler stream exceeds source acquisition budget"
        raise CollectionError(message)
    with path.open("rb") as stream:
        prefix = stream.read(_PREFIX_BYTES)
        size = int.from_bytes(prefix, "big")
        if len(prefix) != _PREFIX_BYTES or not 0 < size <= budget.frame_bytes:
            message = "invalid compiler source acquisition header"
            raise CollectionError(message)
        header_bytes = stream.read(size)
        header = json.loads(header_bytes).get("header", {})
        parser = Frames(budget, header.get("request_id", ""), header.get("input_digest", ""))
        tuple(parser.feed(prefix + header_bytes))
        paths: dict[str, str] = {}
        while chunk := stream.read(min(budget.frame_bytes, 1024 * 1024)):
            for row in parser.feed(chunk):
                _sources(row, paths, budget.max_records)
        parser.finish()
    result = []
    total = 0
    for name, digest in sorted(paths.items()):
        source = Path(name)
        size = source.stat().st_size
        total += size
        if total > budget.input_bytes or digest_file(source) != digest:
            message = "compiler-mapped source changed or exceeds acquisition budget"
            raise CollectionError(message)
        result.append(FileEntry(path=name, size=size, digest=digest, kind="rust"))
    return tuple(result)


def _sources(value: dict, paths: dict[str, str], limit: int) -> None:
    pending: list[object] = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, dict):
            if item.get("mapping") == "exact_original_file_bytes":
                path, digest = item.get("file"), item.get("source_digest")
                if (
                    not isinstance(path, str)
                    or not isinstance(digest, str)
                    or paths.get(path, digest) != digest
                ):
                    message = "conflicting or malformed compiler source identity"
                    raise CollectionError(message)
                paths[path] = digest
                if len(paths) > limit:
                    message = "compiler source denominator exceeds acquisition budget"
                    raise CollectionError(message)
            pending.extend(item.values())
