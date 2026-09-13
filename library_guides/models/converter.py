"""Deterministic structure and unstructure hooks for the record model."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from cattrs import Converter

from library_guides.models.enums import (
    Ecosystem,
    EvidenceOrigin,
    ResolutionState,
    ReviewState,
    StageCompletion,
    SurfaceKind,
    VerificationLevel,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["RECORD_CONVERTER", "structure_record", "unstructure_record"]

_STR_ENUMS: tuple[type[StrEnum], ...] = (
    Ecosystem,
    EvidenceOrigin,
    ResolutionState,
    ReviewState,
    StageCompletion,
    SurfaceKind,
    VerificationLevel,
)


def _build_converter() -> Converter:
    converter = Converter(forbid_extra_keys=True)
    for enum_type in _STR_ENUMS:
        converter.register_unstructure_hook(enum_type, str)
    return converter


RECORD_CONVERTER: Converter = _build_converter()


def unstructure_record(record: object) -> Mapping[str, object]:
    """Return the plain mapping form of one record.

    Args:
        record: Any record defined in :mod:`library_guides.models.records`.

    Returns:
        Mapping whose values are JSON-encodable primitives, lists, and mappings.

    Raises:
        TypeError: When the converter produced a non-mapping payload.

    """
    payload = RECORD_CONVERTER.unstructure(record)
    if not isinstance(payload, dict):
        message = f"record {type(record).__name__} did not unstructure to a mapping"
        raise TypeError(message)
    return payload


def structure_record[RecordT](payload: Mapping[str, object], record_type: type[RecordT]) -> RecordT:
    """Return one record rebuilt from its mapping form.

    Args:
        payload: Mapping previously produced by :func:`unstructure_record`.
        record_type: Target record class.

    Returns:
        The reconstructed record.

    """
    return RECORD_CONVERTER.structure(payload, record_type)
