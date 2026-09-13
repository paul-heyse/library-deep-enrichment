"""Declared coverage obligations per capability-family kind."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

import yaml
from attrs import field, frozen

from library_guides.validate.authored import (
    AuthoredRecordError,
    require_mapping,
    require_str,
    require_str_sequence,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["FamilyObligation", "load_obligations", "obligations_path"]

_SCHEMA_VERSION: Final = "library-guides.obligations.v1"


@frozen(kw_only=True)
class FamilyObligation:
    """What one capability-family kind must explain."""

    family_kind: str = field()
    title: str = field()
    required_facets: tuple[str, ...] = field()
    optional_facets: tuple[str, ...] = field(default=())

    def missing(self, present: frozenset[str]) -> tuple[str, ...]:
        """Return required facets that are not present.

        Returns:
            Missing facet names in declaration order.

        """
        return tuple(facet for facet in self.required_facets if facet not in present)


def obligations_path() -> Path:
    """Return the checked-in obligations catalog path.

    Returns:
        Path to ``obligations/capability_families.yaml``.

    """
    return Path(__file__).resolve().parent / "assets" / "obligations" / "capability_families.yaml"


def load_obligations(*, path: Path | None = None) -> Mapping[str, FamilyObligation]:
    """Return every declared family obligation.

    Returns:
        Mapping of family kind to its obligation.

    Raises:
        AuthoredRecordError: When the catalog declares an unexpected schema.

    """
    source = path or obligations_path()
    context = f"obligations {source}"
    document = require_mapping(yaml.safe_load(source.read_text(encoding="utf-8")), context=context)
    declared = require_str(document, "schema_version", context=context)
    if declared != _SCHEMA_VERSION:
        message = f"{context}: schema_version {declared!r} is not {_SCHEMA_VERSION!r}"
        raise AuthoredRecordError(message)
    families = require_mapping(document.get("families") or {}, context=f"{context}.families")
    result: dict[str, FamilyObligation] = {}
    for kind, raw in families.items():
        where = f"{context}.families.{kind}"
        mapping = require_mapping(raw, context=where)
        optional = (
            require_str_sequence(mapping, "optional_facets", context=where)
            if "optional_facets" in mapping
            else ()
        )
        result[kind] = FamilyObligation(
            family_kind=kind,
            title=require_str(mapping, "title", context=where),
            required_facets=require_str_sequence(mapping, "required_facets", context=where),
            optional_facets=optional,
        )
    return result
