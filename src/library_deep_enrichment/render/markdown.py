"""Pure record-to-markdown rendering.

Every function here takes data and returns text. None of them read or write
files, so a test can assert on rendered output without a filesystem, and the
same function serves both the writer and the drift check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import field, frozen

if TYPE_CHECKING:
    from collections.abc import Sequence

    from library_deep_enrichment.adapters.docs.markdown_sections import DocumentIndex
    from library_deep_enrichment.decisions import DecisionBrief
    from library_deep_enrichment.manifest import DocumentEntry

__all__ = [
    "DocumentInventoryRow",
    "ResolvedAnchor",
    "SectionIndexRow",
    "build_inventory_rows",
    "render_api_families",
    "render_decision_briefs",
    "render_decision_index",
    "render_document_inventory",
    "render_section_index",
    "render_table",
    "render_version_anchors",
]


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Return a GitHub-flavoured markdown table.

    Returns:
        The table text without a trailing newline.

    """
    lines = [
        f"| {' | '.join(headers)} |",
        f"|{'|'.join('---' for _ in headers)}|",
    ]
    lines.extend(f"| {' | '.join(row)} |" for row in rows)
    return "\n".join(lines)


@frozen(kw_only=True)
class ResolvedAnchor:
    """One version anchor with its declared and resolved facts separated."""

    anchor_id: str = field()
    declared: str = field()
    resolved: str | None = field(default=None)
    origin: str = field()

    def describe_resolution(self) -> str:
        """Return the resolved version, or an explicit unknown marker.

        Returns:
            The resolved version text.

        """
        return self.resolved or "unresolved"


def render_version_anchors(anchors: Sequence[ResolvedAnchor]) -> str:
    """Return the version-anchor table.

    Declared intent and lock resolution are separate columns because they are
    separate facts; an exact pin makes them agree, a range does not.

    Returns:
        The rendered block body.

    """
    rows = [
        [
            f"`{anchor.anchor_id}`",
            f"`{anchor.declared}`",
            f"`{anchor.describe_resolution()}`",
            anchor.origin,
        ]
        for anchor in anchors
    ]
    table = render_table(("Anchor", "Declared", "Resolved", "Read from"), rows)
    note = (
        "These are declaration and lock facts for this repository. They do not "
        "establish what a separately deployed process resolves, nor that an "
        "optional feature is enabled."
    )
    return f"{table}\n\n{note}"


@frozen(kw_only=True)
class DocumentInventoryRow:
    """One routed document with its current measured size."""

    doc_id: str = field()
    path: str = field()
    line_count: int = field()
    section_count: int = field()
    content_digest: str = field()
    scope: str = field()
    deep_dive_prefix: str = field(default="")


def render_document_inventory(rows: Sequence[DocumentInventoryRow]) -> str:
    """Return the routed-document table.

    Returns:
        The rendered block body.

    """
    table = render_table(
        ("Doc", "Path", "Lines", "Headings", "Deep-dive prefix", "Scope"),
        [
            [
                f"**{row.doc_id}**",
                f"`{row.path}`",
                f"{row.line_count:,}",
                f"{row.section_count:,}",
                row.deep_dive_prefix or "—",
                row.scope,
            ]
            for row in rows
        ],
    )
    total_lines = sum(row.line_count for row in rows)
    total_sections = sum(row.section_count for row in rows)
    summary = f"{len(rows)} documents, {total_lines:,} lines, {total_sections:,} headings."
    return f"{table}\n\n{summary}"


def build_inventory_rows(
    entries: Sequence[DocumentEntry],
    indexes: Sequence[DocumentIndex],
) -> tuple[DocumentInventoryRow, ...]:
    """Return inventory rows pairing manifest entries with measured indexes.

    Args:
        entries: Manifest document entries, in declaration order.
        indexes: Document indexes in the same order.

    Returns:
        One row per document.

    """
    return tuple(
        DocumentInventoryRow(
            doc_id=entry.doc_id,
            path=entry.path,
            line_count=index.line_count,
            section_count=len(index.sections),
            content_digest=index.content_digest,
            scope=entry.scope,
            deep_dive_prefix=entry.deep_dive_prefix,
        )
        for entry, index in zip(entries, indexes, strict=True)
    )


@frozen(kw_only=True)
class SectionIndexRow:
    """One chapter of a routed document.

    ``line_hint`` is a convenience for jumping into a large file. It is not the
    anchor: ``heading_text`` resolved against ``section_id`` is, which is why a
    changed document digest invalidates the hint rather than the row.
    """

    section_id: str = field()
    heading_text: str = field()
    line_hint: int = field()
    line_span: int = field()
    notes: str = field(default="")


def render_section_index(
    doc_id: str,
    document_path: str,
    content_digest: str,
    rows: Sequence[SectionIndexRow],
) -> str:
    """Return one document's chapter index.

    Returns:
        The rendered block body.

    """
    heading = f"#### `{doc_id}` — `{document_path}`"
    provenance = (
        f"Generated against content digest `{content_digest[:16]}`. "
        "Jump by heading text; the line hint is only valid while that digest holds."
    )
    table = render_table(
        ("Chapter", "Line hint", "Lines", "Covers"),
        [
            [
                row.heading_text,
                str(row.line_hint),
                str(row.line_span),
                row.notes or "—",
            ]
            for row in rows
        ],
    )
    return f"{heading}\n\n{provenance}\n\n{table}"


def render_decision_index(briefs: Sequence[DecisionBrief]) -> str:
    """Return the task-to-decision routing table.

    Returns:
        The rendered block body.

    """
    rows = [
        [
            brief.use_case,
            f"`{brief.decision_id}`",
            ", ".join(f"`{candidate.api}`" for candidate in brief.candidates[:3]),
        ]
        for brief in briefs
    ]
    if not rows:
        return "No decision briefs are authored for this stack yet."
    table = render_table(("I need to…", "Brief", "Candidate APIs"), rows)
    note = (
        "Retrieve the brief, not just the API: it carries the requirement that "
        "decides the choice and the condition that would reverse it."
    )
    return f"{table}\n\n{note}"


def render_decision_briefs(briefs: Sequence[DecisionBrief]) -> str:
    """Return every decision brief as readable sections.

    Returns:
        The rendered block body.

    """
    if not briefs:
        return "No decision briefs are authored for this stack yet."
    sections: list[str] = []
    for brief in briefs:
        candidates = render_table(
            ("Candidate", "Exact API", "Fits when"),
            [[c.summary, f"`{c.api}`", c.fits_when] for c in brief.candidates],
        )
        requirements = "\n".join(f"- {item}" for item in brief.decisive_requirements)
        reversing = "\n".join(f"- {item}" for item in brief.reversing_conditions)
        principles = ", ".join(f"`{p}`" for p in brief.principles)
        sections.append(
            f"#### {brief.use_case}\n\n"
            f"**Decisive requirements**\n\n{requirements}\n\n"
            f"{candidates}\n\n"
            f"**What separates them.** {brief.comparison.strip()}\n\n"
            f"**Would reverse this choice**\n\n{reversing}\n\n"
            f"**Next step.** {brief.next_step.strip()}\n\n"
            f"**Principles:** {principles}"
        )
    return "\n\n".join(sections)


def render_api_families(rows: Sequence[tuple[str, str, int, int, str]]) -> str:
    """Return the generated inventory summary per library profile.

    Returns:
        The rendered block body.

    """
    if not rows:
        return "No API inventory has been extracted yet."
    table = render_table(
        ("Library", "Profile", "API bindings", "Registered surfaces", "Evidence is for"),
        [[f"`{a}`", f"`{b}`", f"{c:,}", f"{d:,}", e] for a, b, c, d, e in rows],
    )
    note = (
        "Counts are of the *observed* inventory for each profile. An item present "
        "here is discoverable; that is not the same as its semantics being explained."
    )
    return f"{table}\n\n{note}"
