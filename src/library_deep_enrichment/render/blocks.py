"""Generated-block splicing with fail-closed drift detection.

Prose outside the markers stays hand-authored. Only the marked region is owned
by the build, so a generated section index can be refreshed without disturbing
the reviewed guidance around it.

The marker carries the digest of the input the block was generated from. A
reader can therefore tell that a block is stale without rerunning the build, and
``--check`` can explain precisely what changed.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import field, frozen

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "MARKER_NAMESPACE",
    "BlockDrift",
    "PartialMarkerError",
    "block_markers",
    "compare_blocks",
    "render_drift_report",
    "replace_block",
    "replace_file_block",
]

MARKER_NAMESPACE = "library-deep-enrichment"

_MAX_REPORTED_FILES = 10
_MAX_REPORTED_LINES = 40


class PartialMarkerError(ValueError):
    """Raised when a file carries one half of a generated-block marker pair."""


def block_markers(block_name: str, *, source_digest: str | None = None) -> tuple[str, str]:
    """Return the begin and end markers for one generated block.

    Args:
        block_name: Stable block identifier, such as ``section-index``.
        source_digest: Digest of the input the block was generated from.

    Returns:
        The begin and end marker strings.

    """
    suffix = f" {source_digest[:16]}" if source_digest else ""
    begin = f"<!-- BEGIN GENERATED {MARKER_NAMESPACE} {block_name}{suffix} -->"
    end = f"<!-- END GENERATED {MARKER_NAMESPACE} {block_name} -->"
    return begin, end


def _begin_pattern(block_name: str) -> re.Pattern[str]:
    escaped = re.escape(block_name)
    return re.compile(
        rf"<!-- BEGIN GENERATED {re.escape(MARKER_NAMESPACE)} {escaped}(?: [0-9a-f]+)? -->"
    )


def replace_block(
    text: str, block_name: str, body: str, *, source_digest: str | None = None
) -> str:
    """Return ``text`` with the named block's contents replaced.

    When the markers are absent the block is appended, so a new block can be
    introduced without hand-editing every target first.

    Args:
        text: Current file contents.
        block_name: Stable block identifier.
        body: Generated markdown to place between the markers.
        source_digest: Digest recorded in the begin marker.

    Returns:
        The updated text.

    Raises:
        PartialMarkerError: When only one marker of the pair is present.

    """
    begin, end = block_markers(block_name, source_digest=source_digest)
    begin_match = _begin_pattern(block_name).search(text)
    end_index = text.find(end)
    if (begin_match is None) != (end_index == -1):
        message = f"partial generated-block markers for {block_name!r}"
        raise PartialMarkerError(message)
    stripped_body = body.strip("\n")
    if begin_match is None:
        head = text.rstrip()
        return f"{head}\n\n{begin}\n{stripped_body}\n{end}\n"
    if end_index < begin_match.start():
        message = f"generated-block markers for {block_name!r} are out of order"
        raise PartialMarkerError(message)
    return f"{text[: begin_match.start()]}{begin}\n{stripped_body}\n{text[end_index:]}"


def replace_file_block(
    path: Path,
    block_name: str,
    body: str,
    *,
    source_digest: str | None = None,
) -> bool:
    """Rewrite one generated block in ``path`` when its contents changed.

    Args:
        path: Target file, which must already exist.
        block_name: Stable block identifier.
        body: Generated markdown.
        source_digest: Digest recorded in the begin marker.

    Returns:
        ``True`` when the file was rewritten.

    Raises:
        FileNotFoundError: When the target file does not exist.

    """
    if not path.is_file():
        message = f"generated-block target does not exist: {path}"
        raise FileNotFoundError(message)
    current = path.read_text(encoding="utf-8")
    updated = replace_block(current, block_name, body, source_digest=source_digest)
    if updated == current:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


@frozen(kw_only=True)
class BlockDrift:
    """One target whose checked-in bytes differ from the rendered bytes."""

    path: str = field()
    block_name: str = field()
    expected_lines: int = field()
    actual_lines: int = field()
    first_changed_line: int | None = field(default=None)
    diff_lines: tuple[str, ...] = field(default=())


def compare_blocks(
    rendered: Mapping[tuple[str, str], str],
    *,
    read_text: object = None,
) -> tuple[BlockDrift, ...]:
    """Return the drift between rendered blocks and the files on disk.

    Args:
        rendered: Mapping of ``(path, block_name)`` to the rendered file text.
        read_text: Unused; present so callers can pass an injected reader later.

    Returns:
        One entry per drifted target, in path order.

    """
    del read_text
    drifts: list[BlockDrift] = []
    for (path_text, block_name), expected in sorted(rendered.items()):
        path = Path(path_text)
        actual = path.read_text(encoding="utf-8") if path.is_file() else ""
        if actual == expected:
            continue
        drifts.append(_describe_drift(path_text, block_name, expected, actual))
    return tuple(drifts)


def _describe_drift(path: str, block_name: str, expected: str, actual: str) -> BlockDrift:
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()
    first_changed: int | None = None
    for index, (left, right) in enumerate(zip(expected_lines, actual_lines, strict=False), start=1):
        if left != right:
            first_changed = index
            break
    if first_changed is None and len(expected_lines) != len(actual_lines):
        first_changed = min(len(expected_lines), len(actual_lines)) + 1
    diff = tuple(
        difflib.unified_diff(
            actual_lines,
            expected_lines,
            fromfile=f"{path} (on disk)",
            tofile=f"{path} (rendered)",
            lineterm="",
            n=2,
        )
    )
    return BlockDrift(
        path=path,
        block_name=block_name,
        expected_lines=len(expected_lines),
        actual_lines=len(actual_lines),
        first_changed_line=first_changed,
        diff_lines=diff[:_MAX_REPORTED_LINES],
    )


def render_drift_report(drifts: Sequence[BlockDrift]) -> str:
    """Return a readable summary of drifted generated blocks.

    Returns:
        A report naming each drifted target and where it first differs.

    """
    if not drifts:
        return "generated blocks are up to date"
    lines = [f"{len(drifts)} generated block(s) are stale:"]
    for drift in drifts[:_MAX_REPORTED_FILES]:
        where = (
            f" first change at line {drift.first_changed_line}" if drift.first_changed_line else ""
        )
        lines.append(f"  {drift.path} [{drift.block_name}]{where}")
        lines.extend(f"    {line}" for line in drift.diff_lines)
    if len(drifts) > _MAX_REPORTED_FILES:
        lines.append(f"  ... and {len(drifts) - _MAX_REPORTED_FILES} more")
    return "\n".join(lines)
