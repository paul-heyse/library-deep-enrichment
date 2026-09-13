"""Render, check, and write one stack's generated blocks.

``check`` and ``write`` share one render call, so the drift report can never
disagree with what a write would produce.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import field, frozen

from library_deep_enrichment.content import load_document_notes
from library_deep_enrichment.manifest import load_stack_manifest
from library_deep_enrichment.render.blocks import BlockDrift, render_drift_report
from library_deep_enrichment.render.stack import RenderedStack, render_stack
from library_deep_enrichment.store.staging import PublicationRefusedError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

__all__ = ["StackCheckReport", "check_stack", "mirror_plan", "render_for_stack", "write_stack"]


@frozen(kw_only=True)
class StackCheckReport:
    """Whether a stack's consumer files match what the build would write."""

    stack_id: str = field()
    drifts: tuple[BlockDrift, ...] = field()
    mirror_mismatches: tuple[str, ...] = field(default=())

    @property
    def drifted(self) -> bool:
        """Whether anything is stale.

        Returns:
            ``True`` when a block or a mirror is out of date.

        """
        return bool(self.drifts or self.mirror_mismatches)

    @property
    def summary(self) -> str:
        """A readable report.

        Returns:
            The drift report followed by any mirror mismatches.

        """
        parts = [render_drift_report(self.drifts)]
        if self.mirror_mismatches:
            listed = "\n".join(f"  {path}" for path in self.mirror_mismatches)
            parts.append(
                f"{len(self.mirror_mismatches)} mirror(s) differ from their source:\n{listed}"
            )
        return "\n\n".join(parts)


def render_for_stack(stack_id: str, *, repository_root: Path) -> RenderedStack:
    """Return the fully rendered consumer files for one stack.

    Returns:
        The rendered stack.

    """
    manifest = load_stack_manifest(stack_id)
    notes = load_document_notes(stack_id, repository_root=repository_root)
    return render_stack(manifest, repository_root, section_notes=notes)


def mirror_plan(stack_id: str, rendered: Mapping[str, str]) -> dict[str, str]:
    """Return the text every mirror file must contain.

    Args:
        stack_id: Stack identifier.
        rendered: Rendered text keyed by repository-relative path.

    Returns:
        Mapping of mirror path to the authoritative text it must equal.

    """
    manifest = load_stack_manifest(stack_id)
    plan: dict[str, str] = {}
    for group in manifest.mirror_groups:
        source = rendered.get(group.authoritative)
        if source is None:
            continue
        for mirror in group.mirrors:
            plan[mirror] = source
    return plan


def check_stack(stack_id: str, *, repository_root: Path) -> StackCheckReport:
    """Return whether a stack's consumer files are up to date.

    Returns:
        The check report.

    """
    rendered = render_for_stack(stack_id, repository_root=repository_root)
    expected = dict(rendered.files)
    expected.update(mirror_plan(stack_id, rendered.files))
    drifts: list[BlockDrift] = []
    mismatches: list[str] = []
    mirrors = mirror_plan(stack_id, rendered.files)
    for relative, text in sorted(expected.items()):
        path = repository_root / relative
        actual = path.read_text(encoding="utf-8") if path.is_file() else ""
        if actual == text:
            continue
        if relative in mirrors:
            mismatches.append(relative)
            continue
        drifts.append(_drift_for(relative, text, actual))
    return StackCheckReport(
        stack_id=stack_id,
        drifts=tuple(drifts),
        mirror_mismatches=tuple(mismatches),
    )


def write_stack(stack_id: str, *, repository_root: Path) -> tuple[str, ...]:
    """Reject publication through the retired per-file consumer writer.

    Raises:
        PublicationRefusedError: Always; consumers require a qualified v2 generation.

    """
    message = f"legacy publication disabled for {stack_id} at {repository_root}; use a v2 bundle"
    raise PublicationRefusedError(message)


def _drift_for(relative: str, expected: str, actual: str) -> BlockDrift:
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()
    first_changed: int | None = None
    for index, (left, right) in enumerate(zip(expected_lines, actual_lines, strict=False), start=1):
        if left != right:
            first_changed = index
            break
    if first_changed is None and len(expected_lines) != len(actual_lines):
        first_changed = min(len(expected_lines), len(actual_lines)) + 1
    return BlockDrift(
        path=relative,
        block_name="stack",
        expected_lines=len(expected_lines),
        actual_lines=len(actual_lines),
        first_changed_line=first_changed,
    )
