"""Verified byte maps for source documentation and transformed example views."""

from __future__ import annotations

import ast
import doctest
import re
from itertools import pairwise

from attrs import frozen
from markdown_it import MarkdownIt

from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.facts.contracts import SourceSegment


@frozen(kw_only=True)
class Mapped:
    """Generated UTF-8 bytes with exact host intervals or explicit synthetic pieces."""

    data: bytes
    segments: tuple[SourceSegment, ...]


def identity(data: bytes, offset: int = 0) -> Mapped:
    """Construct an unchanged source interval.

    Returns:
        An exact identity map in byte coordinates.

    """
    return Mapped(
        data=data,
        segments=(
            SourceSegment(
                generated_start=0,
                generated_end=len(data),
                host_start=offset,
                host_end=offset + len(data),
            ),
        ),
    )


def select(source: Mapped, start: int, end: int) -> Mapped:
    """Project a byte range without inventing a linear map through escapes.

    Returns:
        Exact mapped pieces; synthetic or partial transformed pieces stay unmapped.

    Raises:
        CollectionError: If the requested range leaves the generated text.

    """
    if not 0 <= start <= end <= len(source.data):
        message = "source-map selection is out of bounds"
        raise CollectionError(message)
    result = []
    for segment in source.segments:
        lo, hi = max(start, segment.generated_start), min(end, segment.generated_end)
        if lo > hi or (lo == hi and start != end):
            continue
        host_start, host_end = segment.host_start, segment.host_end
        if host_start is not None and host_end is not None:
            if host_end - host_start == segment.generated_end - segment.generated_start:
                host_start += lo - segment.generated_start
                host_end = host_start + hi - lo
            elif (lo, hi) != (segment.generated_start, segment.generated_end):
                host_start = host_end = None
        result.append(
            SourceSegment(
                generated_start=lo - start,
                generated_end=hi - start,
                host_start=host_start,
                host_end=host_end,
            )
        )
    return Mapped(data=source.data[start:end], segments=tuple(result))


def join(parts: tuple[Mapped, ...]) -> Mapped:
    """Compose mapped and synthetic pieces.

    Returns:
        One ordered generated view preserving every source interval.

    """
    offset = 0
    segments = []
    for part in parts:
        segments.extend(
            SourceSegment(
                generated_start=s.generated_start + offset,
                generated_end=s.generated_end + offset,
                host_start=s.host_start,
                host_end=s.host_end,
            )
            for s in part.segments
        )
        offset += len(part.data)
    return Mapped(data=b"".join(part.data for part in parts), segments=tuple(segments))


def synthetic(data: bytes) -> Mapped:
    """Mark wrapper text as generated, without assigning it a source span.

    Returns:
        An explicitly unmapped generated piece.

    """
    return Mapped(
        data=data,
        segments=(
            SourceSegment(
                generated_start=0, generated_end=len(data), host_start=None, host_end=None
            ),
        ),
    )


def normalize_newlines(source: Mapped) -> Mapped:
    """Preserve byte support when CRLF or CR becomes one LF.

    Returns:
        Normalized text with nonlinear newline intervals retained.

    """
    result = []
    previous = 0
    for match in re.finditer(rb"\r\n?", source.data):
        result.append(select(source, previous, match.start()))
        part = select(source, match.start(), match.end())
        result.append(_replacement(part, b"\n"))
        previous = match.end()
    result.append(select(source, previous, len(source.data)))
    return join(tuple(result))


def _replacement(source: Mapped, value: bytes) -> Mapped:
    intervals = [s for s in source.segments if s.host_start is not None]
    # Escape decoding covers the entire encoded interval, never an invented sub-byte map.
    contiguous = (
        bool(intervals)
        and len(intervals) == len(source.segments)
        and all(a.host_end == b.host_start for a, b in pairwise(intervals))
    )
    return Mapped(
        data=value,
        segments=(
            SourceSegment(
                generated_start=0,
                generated_end=len(value),
                host_start=intervals[0].host_start if contiguous else None,
                host_end=intervals[-1].host_end if contiguous else None,
            ),
        ),
    )


def python_literal(source: Mapped) -> Mapped:
    """Decode a static Unicode Python string and verify the complete decoded value.

    Returns:
        Text with exact escape/quote/CRLF source support.

    Raises:
        CollectionError: If a string is dynamic, concatenated or cannot be mapped exactly.

    """
    match = re.match(rb"(?i)(r|u)?(\"\"\"|'''|\"|')", source.data)
    if match is None or not source.data.endswith(match[2]):
        message = "only a single static Unicode literal can become documentation"
        raise CollectionError(message)
    body = normalize_newlines(select(source, match.end(), len(source.data) - len(match[2])))
    result = body if (match[1] or b"").lower() == b"r" else _escapes(body)
    expected = ast.literal_eval(source.data.decode("utf-8"))
    if not isinstance(expected, str) or expected.encode() != result.data:
        message = "decoded literal does not agree with the Python literal oracle"
        raise CollectionError(message)
    return result


def _escapes(source: Mapped) -> Mapped:
    result = []
    previous = 0
    for match in re.finditer(
        rb"\\(?:N\{[^}]+\}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{2}|[0-7]{1,3}|\n|.)",
        source.data,
    ):
        result.append(select(source, previous, match.start()))
        token = match[0].decode()
        decoded = ast.literal_eval("'" + token + "'")
        result.append(_replacement(select(source, match.start(), match.end()), decoded.encode()))
        previous = match.end()
    result.append(select(source, previous, len(source.data)))
    return join(tuple(result))


def rust_line_docs(source: Mapped) -> Mapped:
    """Strip only actual line-documentation prefixes and preserve CRLF support.

    Returns:
        A Markdown view with each retained byte mapped to its source comment.

    Raises:
        CollectionError: If a line is not a Rust documentation comment.

    """
    parts = []
    offset = 0
    for line in source.data.splitlines(keepends=True):
        match = re.match(rb"[ \t]*//(?:/[^/]|!|/$)", line)
        if match is None:
            message = "ordinary comments cannot impersonate Rust item documentation"
            raise CollectionError(message)
        prefix = len(line) - len(line.lstrip(b" \t")) + 3
        if line[prefix : prefix + 1] == b" ":
            prefix += 1
        parts.append(select(source, offset + prefix, offset + len(line)))
        offset += len(line)
    return normalize_newlines(join(tuple(parts)))


def fences(
    source: Mapped, *, default_language: str = "unknown"
) -> tuple[tuple[str, Mapped, tuple[str, ...]], ...]:
    """Find Markdown examples and reconcile every content line to the mapped host.

    Returns:
        Language, exact code view and explicit execution directives.

    """
    source = normalize_newlines(source)
    lines = source.data.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    result = []
    for token in MarkdownIt("commonmark").parse(source.data.decode()):
        if token.type != "fence" or token.map is None:
            continue
        first, last = token.map
        content = token.content.encode().splitlines(keepends=True)
        mapped = _fence_lines(source, lines, offsets, (first, last), content)
        directives = tuple(part for part in re.split(r"[ ,]+", token.info.strip()) if part)
        language = (
            directives[0]
            if directives and directives[0] in {"python", "py", "rust", "rs"}
            else "rust"
            if any(x in directives for x in ("no_run", "compile_fail", "should_panic"))
            else default_language
            if not directives
            else "unknown"
        )
        result.append((language, mapped, directives))
    return tuple(result)


def _fence_lines(
    source: Mapped,
    lines: list[bytes],
    offsets: list[int],
    bounds: tuple[int, int],
    content: list[bytes],
) -> Mapped:
    first, last = bounds
    pieces = []
    for index, line in enumerate(content):
        host_index = first + 1 + index
        if host_index >= last or not lines[host_index].endswith(line):
            message = "fence normalization cannot be reconciled to exact host bytes"
            raise CollectionError(message)
        removed = lines[host_index][: -len(line)] if line else lines[host_index]
        if removed.strip(b" \t>"):
            message = "unsupported fence container prefix"
            raise CollectionError(message)
        start = offsets[host_index] + len(removed)
        pieces.append(select(source, start, start + len(line)))
    return join(tuple(pieces))


def example_view(source: Mapped, language: str, *, executable: bool) -> Mapped:
    """Transform hidden Rustdoc lines or Python prompts without granting execution status.

    Returns:
        The requested example view with synthetic wrappers and source maps retained.

    """
    if language in {"python", "py"} and any(
        line.lstrip().startswith(b">>> ") for line in source.data.splitlines()
    ):
        return join(doctests(source)) if executable else source
    parts = []
    offset = 0
    for line in source.data.splitlines(keepends=True):
        hidden = language in {"rust", "rs"} and (line.startswith(b"# ") or line.rstrip() == b"#")
        if not hidden or executable:
            skip = (
                min(2, len(line.rstrip(b"\r\n")))
                if hidden
                else 1
                if language in {"rust", "rs"} and line.startswith(b"##")
                else 4
                if language in {"python", "py"} and line.startswith((b">>> ", b"... "))
                else 0
            )
            parts.append(select(source, offset + skip, offset + len(line)))
        offset += len(line)
    return join(tuple(parts))


def doctests(source: Mapped) -> tuple[Mapped, ...]:
    """Locate prompt input, excluding expected output without executing source text.

    Returns:
        Exact mapped Python input blocks reconciled against the doctest parser.

    Raises:
        CollectionError: If prompt removal disagrees with the parser's source view.

    """
    source = normalize_newlines(source)
    lines = source.data.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    result = []
    for example in doctest.DocTestParser().get_examples(source.data.decode()):
        parts = []
        for number, expected in enumerate(example.source.encode().splitlines(keepends=True)):
            row = example.lineno + number
            prefix = example.indent + 4
            raw = lines[row]
            part = select(source, offsets[row] + prefix, offsets[row] + len(raw))
            if part.data != expected:
                message = "doctest source cannot be reconciled to exact prompt bytes"
                raise CollectionError(message)
            parts.append(part)
        result.append(join(tuple(parts)))
    return tuple(result)
