"""Structural inventory of a Markdown document.

Section identity is a heading path plus an occurrence index, never a line
number. Line numbers re-break on every edit, which is why the hand-maintained
navigators already drifted; a heading path survives insertion and deletion
above it, and a content digest says when a cited target may have moved.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from attrs import field, frozen
from markdown_it import MarkdownIt

from library_deep_enrichment.store.digests import digest_bytes

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

__all__ = [
    "DocumentIndex",
    "DocumentSection",
    "index_markdown",
    "index_markdown_file",
    "slugify_heading",
]

_NON_SLUG = re.compile(r"[^a-z0-9]+")
_INLINE_CODE = re.compile(r"`([^`]*)`")


def slugify_heading(text: str) -> str:
    """Return a stable slug for one heading's text.

    Returns:
        Lowercase dash-separated slug with inline code markers removed.

    """
    plain = _INLINE_CODE.sub(r"\1", text)
    return _NON_SLUG.sub("-", plain.lower()).strip("-")


@frozen(kw_only=True)
class DocumentSection:
    """One heading and the extent of the content beneath it."""

    section_id: str = field()
    heading_text: str = field()
    heading_path: tuple[str, ...] = field()
    level: int = field()
    occurrence: int = field()
    start_line: int = field()
    end_line: int = field()
    subtree_end_line: int = field()
    byte_start: int = field()
    byte_end: int = field()
    code_block_count: int = field(default=0)
    table_count: int = field(default=0)
    link_targets: tuple[str, ...] = field(default=())

    def line_span(self) -> int:
        """Return how many display lines this heading owns before its children.

        Returns:
            Inclusive line count.

        """
        return self.end_line - self.start_line + 1

    def subtree_line_span(self) -> int:
        """Return how many display lines this section covers including children.

        A chapter index wants this span, not the few lines between a heading and
        its first subsection.

        Returns:
            Inclusive line count.

        """
        return self.subtree_end_line - self.start_line + 1


@frozen(kw_only=True)
class DocumentIndex:
    """Every section of one document, pinned to that document's content."""

    document_path: str = field()
    content_digest: str = field()
    line_count: int = field()
    byte_count: int = field()
    sections: tuple[DocumentSection, ...] = field()

    def by_id(self) -> dict[str, DocumentSection]:
        """Return sections keyed by their stable identifier.

        Returns:
            Mapping of section identifier to section.

        """
        return {section.section_id: section for section in self.sections}

    def top_level(self) -> tuple[DocumentSection, ...]:
        """Return only the shallowest heading level present.

        Returns:
            Sections at the minimum heading level, in document order.

        """
        if not self.sections:
            return ()
        shallowest = min(section.level for section in self.sections)
        return tuple(section for section in self.sections if section.level == shallowest)

    def find_heading(self, heading_text: str) -> DocumentSection | None:
        """Return the first section whose heading text matches exactly.

        Returns:
            The matching section, or ``None``.

        """
        for section in self.sections:
            if section.heading_text == heading_text:
                return section
        return None


def _heading_text(tokens: Sequence[object], index: int) -> str:
    inline = tokens[index + 1]
    content = getattr(inline, "content", "")
    return str(content).strip()


@frozen(kw_only=True)
class _HeadingRecord:
    """One parsed heading, before its extent is known."""

    heading_text: str = field()
    heading_path: tuple[str, ...] = field()
    level: int = field()
    occurrence: int = field()
    start_line: int = field()


def _collect_headings(text: str) -> tuple[_HeadingRecord, ...]:
    parser = MarkdownIt("commonmark")
    tokens = parser.parse(text)
    counters: dict[tuple[str, ...], int] = {}
    path_stack: list[tuple[int, str]] = []
    records: list[_HeadingRecord] = []
    for position, token in enumerate(tokens):
        if getattr(token, "type", "") != "heading_open":
            continue
        level = int(str(getattr(token, "tag", "h1"))[1:])
        heading_text = _heading_text(tokens, position)
        token_map = getattr(token, "map", None)
        start_line = (token_map[0] + 1) if token_map else 1
        while path_stack and path_stack[-1][0] >= level:
            path_stack.pop()
        path_stack.append((level, heading_text))
        heading_path = tuple(entry[1] for entry in path_stack)
        counters[heading_path] = counters.get(heading_path, 0) + 1
        records.append(
            _HeadingRecord(
                heading_text=heading_text,
                heading_path=heading_path,
                level=level,
                occurrence=counters[heading_path],
                start_line=start_line,
            )
        )
    return tuple(records)


def index_markdown(text: str, *, document_path: str) -> DocumentIndex:
    """Return the section inventory of one Markdown document.

    Args:
        text: Full document text.
        document_path: Repository-relative path recorded on the index.

    Returns:
        The document index.

    """
    lines = text.splitlines()
    total_lines = len(lines)
    line_offsets = _line_byte_offsets(text)
    records = _collect_headings(text)
    sections: list[DocumentSection] = []
    for position, record in enumerate(records):
        following = (
            records[position + 1].start_line - 1 if position + 1 < len(records) else total_lines
        )
        end_line = max(following, record.start_line)
        subtree_end_line = max(_subtree_end(records, position, total_lines), record.start_line)
        body = "\n".join(lines[record.start_line - 1 : end_line])
        sections.append(
            DocumentSection(
                section_id=_section_id(record.heading_path, record.occurrence),
                heading_text=record.heading_text,
                heading_path=record.heading_path,
                level=record.level,
                occurrence=record.occurrence,
                start_line=record.start_line,
                end_line=end_line,
                subtree_end_line=subtree_end_line,
                byte_start=line_offsets[record.start_line - 1],
                byte_end=line_offsets[end_line],
                code_block_count=_count_code_blocks(body),
                table_count=_count_tables(body),
                link_targets=_link_targets(body),
            )
        )
    encoded = text.encode("utf-8")
    return DocumentIndex(
        document_path=document_path,
        content_digest=digest_bytes(encoded),
        line_count=total_lines,
        byte_count=len(encoded),
        sections=tuple(sections),
    )


def index_markdown_file(path: Path, *, document_path: str | None = None) -> DocumentIndex:
    """Return the section inventory of a Markdown file.

    Args:
        path: File to read.
        document_path: Recorded path; defaults to ``path`` as POSIX text.

    Returns:
        The document index.

    """
    return index_markdown(
        path.read_text(encoding="utf-8"),
        document_path=document_path or path.as_posix(),
    )


def _subtree_end(
    records: Sequence[_HeadingRecord],
    position: int,
    total_lines: int,
) -> int:
    level = records[position].level
    for later in records[position + 1 :]:
        if later.level <= level:
            return later.start_line - 1
    return total_lines


def _count_code_blocks(body: str) -> int:
    fences = sum(1 for line in body.splitlines() if line.lstrip().startswith("```"))
    return fences // 2


def _section_id(heading_path: tuple[str, ...], occurrence: int) -> str:
    parts = heading_path
    slug = "/".join(slugify_heading(part) for part in parts)
    return slug if occurrence == 1 else f"{slug}#{occurrence}"


def _line_byte_offsets(text: str) -> list[int]:
    offsets: list[int] = []
    running = 0
    for line in text.splitlines(keepends=True):
        offsets.append(running)
        running += len(line.encode("utf-8"))
    return [*offsets, running]


def _count_tables(body: str) -> int:
    count = 0
    previous_was_header = False
    for line in body.splitlines():
        stripped = line.strip()
        is_separator = stripped.startswith("|") and set(stripped) <= set("|-: ")
        if is_separator and previous_was_header:
            count += 1
            previous_was_header = False
            continue
        previous_was_header = stripped.startswith("|")
    return count


def _link_targets(body: str) -> tuple[str, ...]:
    return tuple(sorted(set(re.findall(r"\]\(([^)\s]+)", body))))
