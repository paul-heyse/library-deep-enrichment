"""Resolve TSP coordinates using retained artifact inputs, without live filesystem reads."""

from __future__ import annotations

import json
import posixpath
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlsplit

from attrs import define, field

from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.behavior.typing_contracts import DeclarationLocation
from library_deep_enrichment.corpus.contracts import Blob, ByteRange, SourceFile
from library_deep_enrichment.corpus.encoding import bytes_digest
from library_deep_enrichment.corpus.evidence import resolve_bytes
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.store.digests import canonical_bytes

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.native_contracts import NativeArtifact
    from library_deep_enrichment.corpus.store import CorpusReader

MAX_BYTES = 8 * 1024 * 1024
MAX_NODES = 50_000
MAX_DEPTH = 100
MAX_BMP = 0xFFFF


def utf16_offset(source: bytes, line: int, character: int) -> int:
    """Convert an exact LSP coordinate, rejecting split surrogates and out-of-line columns.

    Returns:
        A UTF-8 byte boundary in the retained source.

    """
    require(
        "invalid LSP declaration coordinate",
        condition=type(line) is int and type(character) is int and line >= 0 and character >= 0,
    )
    rows = source.split(b"\n")
    require("LSP line leaves retained source", condition=line < len(rows))
    text = rows[line].removesuffix(b"\r").decode("utf-8")
    units, offset = 0, sum(len(row) + 1 for row in rows[:line])
    for value in text:
        if units == character:
            return offset
        units += 2 if ord(value) > MAX_BMP else 1
        offset += len(value.encode("utf-8"))
    require("LSP column splits a surrogate or leaves its line", condition=units == character)
    return offset


@define
class RetainedFiles:
    """A finite URI/digest map from the original type-worker request and admitted sources."""

    reader: CorpusReader
    artifact: NativeArtifact
    files: dict[str, tuple[str, str]] = field(factory=dict)
    sources: dict[str, tuple[SourceFile, Blob]] = field(factory=dict)
    content: dict[str, bytes] = field(factory=dict)
    total_bytes: int = 0

    def __attrs_post_init__(self) -> None:
        """Bind request file names to bytes; never resolve a source from a URI on disk."""
        request = json.loads(resolve_bytes(self.reader, self.artifact.input, max_bytes=MAX_BYTES))
        root = request["root"]
        require("type request root is not absolute", condition=posixpath.isabs(root))
        for item in request["files"]:
            absolute = posixpath.normpath(posixpath.join(root, item["path"]))
            require("repeated type request source path", condition=absolute not in self.files)
            self.files[absolute] = (item["path"], item["digest"])
        for source in self.reader.get_many("source_files", self.artifact.sources):
            assert isinstance(source, SourceFile)
            blob = self.reader.get("blobs", source.blob)
            assert isinstance(blob, Blob)
            prior = self.sources.get(blob.digest)
            if prior is None or revision_of(source) < revision_of(prior[0]):
                self.sources[blob.digest] = (source, blob)

    def read(self, digest: str) -> tuple[SourceFile, bytes]:
        """Load a bounded digest-selected source from the corpus.

        Returns:
            Its typed source witness and original bytes.

        """
        require("typed declaration source was not retained", condition=digest in self.sources)
        source, blob = self.sources[digest]
        if digest not in self.content:
            self.total_bytes += blob.size
            require("typed source byte budget exhausted", condition=self.total_bytes <= MAX_BYTES)
            self.content[digest] = resolve_bytes(
                self.reader,
                ByteRange(blob=source.blob, start=0, end=blob.size, digest=blob.digest),
                max_bytes=MAX_BYTES,
            )
        return source, self.content[digest]

    def declaration(self, value: dict | None, path: str) -> DeclarationLocation:
        """Qualify a declaration location without upgrading static evidence into dispatch.

        Returns:
            A source-backed coordinate or an attributed unresolved/stub disposition.

        """
        name = (value.get("name") or "") if value is not None else ""
        category = str(value.get("category", "")) if value is not None else ""
        state = "declaration_absent" if value is None else "synthesized"
        source, start, end, identity = "", -1, -1, ""
        if value is not None and value.get("kind") == 0:
            node = value["node"]
            uri = urlsplit(node["uri"])
            filename = unquote(uri.path)
            selected = self.files.get(filename) if uri.scheme == "file" and not uri.netloc else None
            if selected is None or selected[1] not in self.sources:
                state = "source_not_retained"
            else:
                witness, data = self.read(selected[1])
                begin, finish = node["range"]["start"], node["range"]["end"]
                start = utf16_offset(data, begin["line"], begin["character"])
                end = utf16_offset(data, finish["line"], finish["character"])
                require("reversed TSP declaration range", condition=start <= end)
                source = revision_of(witness)
                state = (
                    "unresolved_zero_range"
                    if start == end
                    else "stub_interface"
                    if selected[0].endswith(".pyi")
                    else "source_declaration"
                )
                if start < end:
                    identity = bytes_digest(
                        canonical_bytes(
                            [self.artifact.context, selected[0], selected[1], start, end, category]
                        )
                    )
        return DeclarationLocation(
            path=path,
            name=name,
            category=category,
            source=source,
            start=start,
            end=end,
            state=state,
            identity=identity,
        )

    def declarations(self, value: dict) -> tuple[DeclarationLocation, ...]:
        """Walk all nested substitutions and type arguments under finite graph bounds.

        Returns:
            Locations identified by structural paths rather than TSP-local numbers.

        """
        pending = [(value, "", 0)]
        result, visited = [], 0
        while pending:
            item, path, depth = pending.pop()
            visited += 1
            require(
                "TSP type graph exceeds bounds",
                condition=visited <= MAX_NODES and depth <= MAX_DEPTH,
            )
            if isinstance(item, dict):
                if "declaration" in item:
                    result.append(self.declaration(item["declaration"], path + "/declaration"))
                pending.extend(
                    (child, path + "/" + key.replace("~", "~0").replace("/", "~1"), depth + 1)
                    for key, child in sorted(item.items(), reverse=True)
                    if key != "declaration"
                )
            elif isinstance(item, list):
                pending.extend(
                    (child, path + "/" + str(index), depth + 1)
                    for index, child in reversed(tuple(enumerate(item)))
                )
        return tuple(result)
