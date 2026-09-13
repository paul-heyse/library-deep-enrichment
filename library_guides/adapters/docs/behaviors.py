"""Behavior-granularity inventory of a long-form reference document.

A *behavior* is the unit the deep-dives actually document: a numbered
subsection such as ``21.5 collect vs execute_stream`` or ``21.8 Memory benefits
and limits``. Chapters are navigation; behaviors are the capability surface the
guide has to account for, so they are the denominator coverage is measured
against.

Anti-pattern inventories and agent-rule blocks are behavior-bearing too even
though they carry no section number, so they are collected alongside and
labelled by kind rather than being silently dropped.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from attrs import field, frozen

from library_guides.adapters.docs.markdown_sections import index_markdown, slugify_heading
from library_guides.store.digests import digest_bytes

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

__all__ = [
    "DEFAULT_BEHAVIOR_PATTERN",
    "Behavior",
    "BehaviorIndex",
    "BehaviorKind",
    "IdentifierShape",
    "identifier_shape",
    "index_behaviors",
    "index_behaviors_file",
    "total_behaviors",
]

DEFAULT_BEHAVIOR_PATTERN: Final = r"^([SC]?\d+(?:\.\d+)+)\s+(.*)$"
"""Numbered-subsection form shared by every deep-dive in this corpus."""

# An identifier worth cross-checking: inline code that looks like a code path,
# not prose in backticks. Requires a leading letter and no whitespace.
_IDENTIFIER: Final = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*(?:(?:::|\.)[A-Za-z0-9_]+)*)`")
_ANTI_PATTERN: Final = re.compile(r"anti-?pattern", re.IGNORECASE)
_AGENT_RULES: Final = re.compile(r"\b(agent rules?|agent checklist|invariants?)\b", re.IGNORECASE)
_MIN_IDENTIFIER_LENGTH: Final = 3


class BehaviorKind:
    """What sort of documented unit a behavior record represents."""

    BEHAVIOR = "behavior"
    ANTI_PATTERN = "anti_pattern"
    AGENT_RULES = "agent_rules"


class IdentifierShape:
    """What a backticked token looks like, before any lookup is attempted.

    Shape decides which inventory a token could possibly resolve against. Without
    it a SQL keyword such as ``AND`` and a type such as ``SessionContext`` are
    both just "unresolved", which buries the real API gaps under noise.
    """

    QUALIFIED = "qualified"
    TYPE_LIKE = "type_like"
    CALLABLE_LIKE = "callable_like"
    CONSTANT_LIKE = "constant_like"
    OTHER = "other"


def identifier_shape(token: str) -> str:
    """Return the shape of one backticked token.

    Returns:
        One of the :class:`IdentifierShape` values.

    """
    if "::" in token or "." in token:
        return IdentifierShape.QUALIFIED
    if token.isupper():
        return IdentifierShape.CONSTANT_LIKE
    if token[:1].isupper():
        return IdentifierShape.TYPE_LIKE
    if token.islower() and ("_" in token or token.isalpha()):
        return IdentifierShape.CALLABLE_LIKE
    return IdentifierShape.OTHER


@frozen(kw_only=True)
class Behavior:
    """One documented behavior, pinned to its source span.

    ``behavior_id`` is the durable handle. It is built from the document alias
    and the section number, so it survives every edit that does not renumber the
    document, unlike the line offsets the hand-maintained navigators used.
    """

    behavior_id: str = field()
    doc_id: str = field()
    document_path: str = field()
    kind: str = field()
    number: str = field()
    title: str = field()
    chapter_key: str = field()
    level: int = field()
    start_line: int = field()
    end_line: int = field()
    byte_start: int = field()
    byte_end: int = field()
    line_count: int = field()
    cited_identifiers: tuple[str, ...] = field(default=())
    api_shaped_identifiers: tuple[str, ...] = field(default=())

    def is_cross_checkable(self) -> bool:
        """Return whether this behavior cites anything an inventory can verify.

        Returns:
            ``True`` when at least one identifier could name an API.

        """
        return bool(self.api_shaped_identifiers)


@frozen(kw_only=True)
class BehaviorIndex:
    """Every behavior in one document, pinned to that document's content."""

    doc_id: str = field()
    document_path: str = field()
    content_digest: str = field()
    behaviors: tuple[Behavior, ...] = field()

    def by_kind(self, kind: str) -> tuple[Behavior, ...]:
        """Return behaviors of one kind.

        Returns:
            Matching behaviors in document order.

        """
        return tuple(item for item in self.behaviors if item.kind == kind)

    def by_id(self) -> dict[str, Behavior]:
        """Return behaviors keyed by their durable identifier.

        Returns:
            Mapping of behavior identifier to behavior.

        """
        return {item.behavior_id: item for item in self.behaviors}


def _cited_identifiers(body: str) -> tuple[str, ...]:
    found = {match for match in _IDENTIFIER.findall(body) if len(match) >= _MIN_IDENTIFIER_LENGTH}
    return tuple(sorted(found))


def _kind_for(title: str) -> str | None:
    if _ANTI_PATTERN.search(title):
        return BehaviorKind.ANTI_PATTERN
    if _AGENT_RULES.search(title):
        return BehaviorKind.AGENT_RULES
    return None


def index_behaviors(
    text: str,
    *,
    doc_id: str,
    document_path: str,
    behavior_pattern: str = DEFAULT_BEHAVIOR_PATTERN,
) -> BehaviorIndex:
    """Return the behavior inventory of one long-form document.

    Args:
        text: Full document text.
        doc_id: Short document alias recorded on every behavior.
        document_path: Repository-relative path.
        behavior_pattern: Regex whose first group is the section number.

    Returns:
        The behavior index.

    """
    pattern = re.compile(behavior_pattern)
    structure = index_markdown(text, document_path=document_path)
    lines = text.splitlines()
    seen: dict[str, int] = {}
    behaviors: list[Behavior] = []

    for section in structure.sections:
        match = pattern.match(section.heading_text)
        kind = BehaviorKind.BEHAVIOR if match else _kind_for(section.heading_text)
        if kind is None:
            continue
        number = match.group(1) if match else slugify_heading(section.heading_text)
        title = match.group(2) if match else section.heading_text
        key = f"{doc_id}:{number}"
        seen[key] = seen.get(key, 0) + 1
        behavior_id = key if seen[key] == 1 else f"{key}#{seen[key]}"
        body = "\n".join(lines[section.start_line - 1 : section.subtree_end_line])
        cited = _cited_identifiers(body)
        behaviors.append(
            Behavior(
                behavior_id=behavior_id,
                doc_id=doc_id,
                document_path=document_path,
                kind=kind,
                number=number,
                title=title,
                chapter_key=number.split(".")[0] if match else "",
                level=section.level,
                start_line=section.start_line,
                end_line=section.subtree_end_line,
                byte_start=section.byte_start,
                byte_end=section.byte_end,
                line_count=section.subtree_line_span(),
                cited_identifiers=cited,
                api_shaped_identifiers=tuple(
                    token
                    for token in cited
                    if identifier_shape(token) != IdentifierShape.CONSTANT_LIKE
                ),
            )
        )

    return BehaviorIndex(
        doc_id=doc_id,
        document_path=document_path,
        content_digest=digest_bytes(text.encode("utf-8")),
        behaviors=tuple(behaviors),
    )


def index_behaviors_file(
    path: Path,
    *,
    doc_id: str,
    document_path: str | None = None,
    behavior_pattern: str = DEFAULT_BEHAVIOR_PATTERN,
) -> BehaviorIndex:
    """Return the behavior inventory of a document on disk.

    Returns:
        The behavior index.

    """
    return index_behaviors(
        path.read_text(encoding="utf-8"),
        doc_id=doc_id,
        document_path=document_path or path.as_posix(),
        behavior_pattern=behavior_pattern,
    )


def total_behaviors(indexes: Sequence[BehaviorIndex]) -> int:
    """Return how many behaviors a set of indexes holds.

    Returns:
        The summed behavior count.

    """
    return sum(len(index.behaviors) for index in indexes)
