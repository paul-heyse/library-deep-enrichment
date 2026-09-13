"""Reader for the shared principle vocabulary."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import yaml
from attrs import field, frozen

from library_guides.content import CONTENT_ROOT
from library_guides.validate.authored import (
    AuthoredRecordError,
    require_mapping,
    require_sequence,
    require_str,
    require_str_sequence,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

__all__ = ["Principle", "load_principles", "principles_path"]

_SCHEMA_VERSION: Final = "library-guides.principles.v1"


@frozen(kw_only=True)
class Principle:
    """One reusable preference with its mechanism, conditions and limits."""

    principle_id: str = field()
    title: str = field()
    definition: str = field()
    mechanism: str = field()
    applies_when: tuple[str, ...] = field(default=())
    decision_implications: tuple[str, ...] = field(default=())
    limits: tuple[str, ...] = field(default=())
    verification: tuple[str, ...] = field(default=())


def principles_path(*, repository_root: Path) -> Path:
    """Return the principle catalog path.

    Returns:
        Path to ``principles/PRINCIPLES.yaml``.

    """
    return repository_root / CONTENT_ROOT / "principles" / "PRINCIPLES.yaml"


def load_principles(*, repository_root: Path) -> Mapping[str, Principle]:
    """Return every declared principle keyed by identifier.

    Returns:
        Mapping of principle identifier to principle.

    Raises:
        AuthoredRecordError: When the catalog declares an unexpected schema.

    """
    path = principles_path(repository_root=repository_root)
    context = f"principles {path}"
    document = require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), context=context)
    declared = require_str(document, "schema_version", context=context)
    if declared != _SCHEMA_VERSION:
        message = f"{context}: schema_version {declared!r} is not {_SCHEMA_VERSION!r}"
        raise AuthoredRecordError(message)
    result: dict[str, Principle] = {}
    for index, raw in enumerate(require_sequence(document, "principles", context=context)):
        where = f"{context}.principles[{index}]"
        mapping = require_mapping(raw, context=where)
        principle_id = require_str(mapping, "id", context=where)
        result[principle_id] = Principle(
            principle_id=principle_id,
            title=require_str(mapping, "title", context=where),
            definition=require_str(mapping, "definition", context=where),
            mechanism=require_str(mapping, "mechanism", context=where),
            applies_when=_optional_list(mapping, "applies_when", context=where),
            decision_implications=_optional_list(mapping, "decision_implications", context=where),
            limits=_optional_list(mapping, "limits", context=where),
            verification=_optional_list(mapping, "verification", context=where),
        )
    return result


def _optional_list(mapping: Mapping[str, object], key: str, *, context: str) -> tuple[str, ...]:
    if key not in mapping:
        return ()
    return require_str_sequence(mapping, key, context=context)
