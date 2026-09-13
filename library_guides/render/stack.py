"""Render one stack's generated blocks into its declared consumer files.

The consumer list comes from the stack manifest and is read here exactly once.
Duplicating a target inventory across a generator, a command, and a test is how
the existing hand-maintained navigators drifted apart.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import field, frozen

from library_guides.adapters.docs.markdown_sections import index_markdown_file
from library_guides.adapters.python.dist_metadata import (
    read_declared_requirements,
    read_locked_distributions,
)
from library_guides.adapters.rust.cargo_metadata import (
    read_locked_packages,
    read_workspace_dependencies,
)
from library_guides.decisions import load_decisions
from library_guides.manifest import load_library_manifest
from library_guides.render.blocks import replace_block
from library_guides.render.markdown import (
    ResolvedAnchor,
    SectionIndexRow,
    build_inventory_rows,
    render_api_families,
    render_decision_briefs,
    render_decision_index,
    render_document_inventory,
    render_section_index,
    render_version_anchors,
)
from library_guides.stages.paths import api_path, surfaces_path
from library_guides.store.digests import digest_sequence
from library_guides.validate.authored import AuthoredRecordError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from library_guides.adapters.docs.markdown_sections import DocumentIndex
    from library_guides.manifest import DocumentEntry, StackManifest

__all__ = ["RenderedStack", "render_stack", "resolve_anchors"]


@frozen(kw_only=True)
class RenderedStack:
    """Every consumer file's full rendered text, keyed by repository path."""

    stack_id: str = field()
    files: Mapping[str, str] = field()
    blocks: Mapping[str, str] = field()
    document_indexes: Mapping[str, DocumentIndex] = field()
    source_digest: str = field()


def resolve_anchors(manifest: StackManifest, repository_root: Path) -> tuple[ResolvedAnchor, ...]:
    """Return each declared version anchor with its declared and resolved facts.

    Args:
        manifest: The stack manifest.
        repository_root: Repository root holding the manifests and lock files.

    Returns:
        Resolved anchors in declaration order.

    Raises:
        AuthoredRecordError: When an anchor names a dependency that is absent.

    """
    cargo_declared = read_workspace_dependencies(repository_root / "Cargo.toml")
    cargo_locked = read_locked_packages(repository_root / "Cargo.lock")
    python_locked = read_locked_distributions(repository_root / "uv.lock")
    python_declared = read_declared_requirements(repository_root / "pyproject.toml")
    resolved: list[ResolvedAnchor] = []
    for anchor in manifest.version_anchors:
        if anchor.source == "cargo_workspace_dependency":
            declaration = cargo_declared.get(anchor.key)
            if declaration is None:
                message = f"stack {manifest.stack_id}: Cargo.toml declares no {anchor.key!r}"
                raise AuthoredRecordError(message)
            resolved.append(
                ResolvedAnchor(
                    anchor_id=anchor.anchor_id,
                    declared=declaration.requirement,
                    resolved=cargo_locked.get(anchor.key),
                    origin="`Cargo.toml` workspace dependency / `Cargo.lock`",
                )
            )
            continue
        distribution = python_locked.get(anchor.key)
        if distribution is None:
            message = f"stack {manifest.stack_id}: uv.lock resolves no {anchor.key!r}"
            raise AuthoredRecordError(message)
        resolved.append(
            ResolvedAnchor(
                anchor_id=anchor.anchor_id,
                declared=python_declared.get(anchor.key, "undeclared"),
                resolved=distribution.version,
                origin="`pyproject.toml` dependency / `uv.lock`",
            )
        )
    return tuple(resolved)


def _count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _inventory_rows(
    library_ids: Sequence[str],
    *,
    repository_root: Path,
) -> tuple[tuple[str, str, int, int, str], ...]:
    """Return one row per library profile summarising its extracted inventory.

    Returns:
        Library, profile, binding count, surface count, and evidence scope.

    """
    rows: list[tuple[str, str, int, int, str]] = []
    for library_id in library_ids:
        library = load_library_manifest(library_id)
        rows.extend(
            (
                library_id,
                profile.profile_id,
                _count_lines(
                    api_path(library_id, profile.profile_id, repository_root=repository_root)
                ),
                _count_lines(
                    surfaces_path(library_id, profile.profile_id, repository_root=repository_root)
                ),
                profile.scope,
            )
            for profile in library.profiles
        )
    return tuple(rows)


def _section_rows(
    entry: DocumentEntry,
    index: DocumentIndex,
    notes: Mapping[str, str],
) -> tuple[SectionIndexRow, ...]:
    candidates = tuple(
        section for section in index.sections if section.level in entry.chapter_levels
    )
    selected = tuple(
        section for section in candidates if entry.chapter_key(section.heading_text) is not None
    )
    if not selected:
        selected = candidates or index.top_level()
    return tuple(
        SectionIndexRow(
            section_id=section.section_id,
            heading_text=section.heading_text,
            line_hint=section.start_line,
            line_span=section.subtree_line_span(),
            notes=notes.get(section.section_id, ""),
        )
        for section in selected
    )


def render_stack(
    manifest: StackManifest,
    repository_root: Path,
    *,
    section_notes: Mapping[str, Mapping[str, str]] | None = None,
) -> RenderedStack:
    """Return every consumer file's rendered text for one stack.

    Args:
        manifest: The stack manifest.
        repository_root: Repository root.
        section_notes: Authored per-section summaries keyed by document alias
            then stable section identifier. Mechanical facts are generated;
            these curated summaries are preserved verbatim.

    Returns:
        The rendered stack.

    Raises:
        AuthoredRecordError: When a declared document is missing from disk.

    """
    notes = section_notes or {}
    indexes: dict[str, DocumentIndex] = {}
    for entry in manifest.documents:
        path = repository_root / entry.path
        if not path.is_file():
            message = f"stack {manifest.stack_id}: declared document {entry.path} is missing"
            raise AuthoredRecordError(message)
        indexes[entry.doc_id] = index_markdown_file(path, document_path=entry.path)

    ordered = tuple(indexes[entry.doc_id] for entry in manifest.documents)
    briefs = tuple(load_decisions(manifest.stack_id, repository_root=repository_root).values())
    publishable = tuple(brief for brief in briefs if brief.is_publishable())
    blocks: dict[str, str] = {
        "decision-index": render_decision_index(publishable),
        "decision-briefs": render_decision_briefs(publishable),
        "api-families": render_api_families(
            _inventory_rows(manifest.libraries, repository_root=repository_root)
        ),
        "version-anchors": render_version_anchors(resolve_anchors(manifest, repository_root)),
        "document-inventory": render_document_inventory(
            build_inventory_rows(manifest.documents, ordered)
        ),
        "section-index": "\n\n".join(
            render_section_index(
                entry.doc_id,
                entry.path,
                indexes[entry.doc_id].content_digest,
                _section_rows(entry, indexes[entry.doc_id], notes.get(entry.doc_id, {})),
            )
            for entry in manifest.documents
        ),
    }
    source_digest = digest_sequence(
        [indexes[entry.doc_id].content_digest for entry in manifest.documents]
    )

    files: dict[str, str] = {}
    for target in manifest.consumers:
        path = repository_root / target.path
        if not path.is_file():
            message = f"stack {manifest.stack_id}: consumer {target.path} is missing"
            raise AuthoredRecordError(message)
        text = path.read_text(encoding="utf-8")
        for block_name in target.blocks:
            text = replace_block(
                text,
                block_name,
                blocks[block_name],
                source_digest=source_digest,
            )
        files[target.path] = text

    return RenderedStack(
        stack_id=manifest.stack_id,
        files=files,
        blocks=blocks,
        document_indexes=indexes,
        source_digest=source_digest,
    )
