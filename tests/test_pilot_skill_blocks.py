"""The pilot skills' generated blocks stay true to the repository.

These guard the defects that made the hand-maintained navigators unreliable:
stale line counts, a wrong version anchor, bare line-offset routing that drifts
on every edit, and two copies of the same skill disagreeing with each other.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from library_deep_enrichment.adapters.docs.markdown_sections import index_markdown_file
from library_deep_enrichment.manifest import load_stack_manifest
from library_deep_enrichment.render.blocks import block_markers
from library_deep_enrichment.render.pipeline import check_stack, render_for_stack

STACKS = ("datafusion-arrow-rust", "datafusion-pyarrow-python")

_GENERATED_BLOCKS = (
    "section-index",
    "document-inventory",
    "version-anchors",
    "decision-index",
    "decision-briefs",
    "api-families",
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

# A routing anchor that is only a line number re-breaks on every upstream edit.
# Generated blocks may carry a line *hint* beside a heading; hand-authored prose
# may not route by offset alone.
_BARE_OFFSET = re.compile(r"\b(?:line|offset|L)\s*[`']?\d{4,}", re.IGNORECASE)


def _block_span(text: str, block_name: str) -> tuple[int, int] | None:
    begin_pattern = re.compile(
        rf"<!-- BEGIN GENERATED library-deep-enrichment {re.escape(block_name)}(?: [0-9a-f]+)? -->"
    )
    _, end_marker = block_markers(block_name)
    begin = begin_pattern.search(text)
    end = text.find(end_marker)
    if begin is None or end == -1:
        return None
    return begin.start(), end + len(end_marker)


def _strip_generated(text: str) -> str:
    for block_name in _GENERATED_BLOCKS:
        span = _block_span(text, block_name)
        if span is not None:
            text = text[: span[0]] + text[span[1] :]
    return text


@pytest.mark.parametrize("stack_id", STACKS)
def test_legacy_blocks_cannot_qualify_after_review_is_withdrawn(stack_id: str) -> None:
    """Old consumer blocks must remain detectably stale until v2 qualification."""
    report = check_stack(stack_id, repository_root=REPOSITORY_ROOT)
    assert report.drifted
    manifest = load_stack_manifest(stack_id)
    skill_paths = [item.path for item in manifest.consumers if item.path.endswith("SKILL.md")]
    assert skill_paths
    assert all(
        "bounded reviewed pilot" in (REPOSITORY_ROOT / path).read_text(encoding="utf-8")
        for path in skill_paths
    )


@pytest.mark.parametrize("stack_id", STACKS)
def test_mirror_copies_are_byte_identical(stack_id: str) -> None:
    """A skill published to two hosts must not fork into two different skills."""
    manifest = load_stack_manifest(stack_id)
    assert manifest.mirror_groups, f"{stack_id} declares no mirror group"
    for group in manifest.mirror_groups:
        source = (REPOSITORY_ROOT / group.authoritative).read_bytes()
        for mirror in group.mirrors:
            assert (REPOSITORY_ROOT / mirror).read_bytes() == source, (
                f"{mirror} has diverged from {group.authoritative}"
            )


@pytest.mark.parametrize("stack_id", STACKS)
def test_every_routed_document_exists(stack_id: str) -> None:
    """A guide must never route an agent at a file that is not there."""
    manifest = load_stack_manifest(stack_id)
    for entry in manifest.documents:
        assert (REPOSITORY_ROOT / entry.path).is_file(), f"{entry.doc_id} -> {entry.path}"


@pytest.mark.parametrize("stack_id", STACKS)
def test_every_indexed_chapter_heading_resolves(stack_id: str) -> None:
    """Routing is by heading text, so every cited heading must still exist."""
    rendered = render_for_stack(stack_id, repository_root=REPOSITORY_ROOT)
    manifest = load_stack_manifest(stack_id)
    block = rendered.blocks["section-index"]
    cited = [
        line.split(" | ")[0].removeprefix("| ").strip()
        for line in block.splitlines()
        if line.startswith("| ") and not line.startswith("| Chapter")
    ]
    assert cited, "the section index rendered no chapters"
    headings: set[str] = set()
    for entry in manifest.documents:
        index = index_markdown_file(REPOSITORY_ROOT / entry.path, document_path=entry.path)
        headings.update(section.heading_text for section in index.sections)
    unresolved = [heading for heading in cited if heading not in headings]
    assert not unresolved, f"section index cites missing headings: {unresolved[:5]}"


@pytest.mark.parametrize("stack_id", STACKS)
def test_hand_authored_prose_does_not_route_by_bare_line_offset(stack_id: str) -> None:
    """Offsets outside a digest-pinned block drift silently and mislead."""
    manifest = load_stack_manifest(stack_id)
    for target in manifest.consumers:
        prose = _strip_generated((REPOSITORY_ROOT / target.path).read_text(encoding="utf-8"))
        offenders = _BARE_OFFSET.findall(prose)
        assert not offenders, f"{target.path} routes by bare line offset: {offenders[:5]}"


def test_rust_version_anchors_match_the_workspace() -> None:
    """A guide must report the version this workspace actually resolves."""
    rendered = render_for_stack("datafusion-arrow-rust", repository_root=REPOSITORY_ROOT)
    block = rendered.blocks["version-anchors"]
    manifest = tomllib.loads((REPOSITORY_ROOT / "Cargo.toml").read_text(encoding="utf-8"))
    dependencies = manifest["workspace"]["dependencies"]
    datafusion = dependencies["datafusion"]["version"]
    arrow = dependencies["arrow"]["version"]
    assert f"`{datafusion}`" in block
    assert f"`{arrow}`" in block


def test_python_version_anchors_separate_declaration_from_resolution() -> None:
    """A declared range and a resolved version are different facts."""
    rendered = render_for_stack("datafusion-pyarrow-python", repository_root=REPOSITORY_ROOT)
    block = rendered.blocks["version-anchors"]
    assert "pyarrow>=" in block, "the declared requirement is missing"
    assert "| `25." in block or "`25." in block, "the resolved version is missing"
    assert "Declared" in block
    assert "Resolved" in block


@pytest.mark.parametrize("stack_id", STACKS)
def test_document_inventory_line_counts_match_disk(stack_id: str) -> None:
    """Every hand-maintained line count in both skills had drifted."""
    rendered = render_for_stack(stack_id, repository_root=REPOSITORY_ROOT)
    block = rendered.blocks["document-inventory"]
    manifest = load_stack_manifest(stack_id)
    for entry in manifest.documents:
        actual = len((REPOSITORY_ROOT / entry.path).read_text(encoding="utf-8").splitlines())
        assert f"| {actual:,} |" in block, f"{entry.doc_id} line count {actual:,} not reported"
