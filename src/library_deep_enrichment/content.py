"""Readers for the authored content tree.

The content tree under ``docs/library_ref/agent_reference/`` owns reviewed
material. The build reads it and never rewrites it: mechanical facts are
generated beside curated text, not over it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

import yaml

from library_deep_enrichment.validate.authored import require_mapping, require_str

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "CONTENT_ROOT",
    "document_notes_path",
    "load_document_notes",
]

CONTENT_ROOT: Final = Path("docs/library_ref/agent_reference")

_NOTES_SCHEMA: Final = "library-guides.document_notes.v1"


def document_notes_path(stack_id: str, *, repository_root: Path) -> Path:
    """Return where one stack's curated chapter summaries live.

    Returns:
        Path to the stack's ``document_notes.yaml``.

    """
    return repository_root / CONTENT_ROOT / "stacks" / stack_id / "document_notes.yaml"


def load_document_notes(
    stack_id: str,
    *,
    repository_root: Path,
) -> Mapping[str, Mapping[str, str]]:
    """Return curated chapter summaries keyed by document alias then section id.

    An absent file is not an error: a stack may be indexed mechanically before
    anyone has written a summary for it.

    Args:
        stack_id: Stack identifier.
        repository_root: Repository root.

    Returns:
        Mapping of document alias to a mapping of section identifier to summary.

    Raises:
        ValueError: When the file declares an unexpected schema version.

    """
    path = document_notes_path(stack_id, repository_root=repository_root)
    if not path.is_file():
        return {}
    context = f"document notes {path}"
    document = require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), context=context)
    declared = require_str(document, "schema_version", context=context)
    require_str(document, "stack_id", context=context)
    if declared != _NOTES_SCHEMA:
        message = f"{context}: schema_version {declared!r} is not {_NOTES_SCHEMA!r}"
        raise ValueError(message)
    documents = require_mapping(document.get("documents") or {}, context=f"{context}.documents")
    notes: dict[str, Mapping[str, str]] = {}
    for doc_id, raw in documents.items():
        entries = require_mapping(raw or {}, context=f"{context}.documents.{doc_id}")
        notes[doc_id] = {
            section_id: value for section_id, value in entries.items() if isinstance(value, str)
        }
    return notes
