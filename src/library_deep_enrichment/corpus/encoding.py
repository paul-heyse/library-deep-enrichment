"""Strict canonical values shared by record revisions and field selections."""

from __future__ import annotations

import base64
import hashlib
import json
from enum import StrEnum
from typing import TYPE_CHECKING

from cattrs import Converter

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.contracts import Record


def _strict_scalar[T](value: object, expected: type[T]) -> T:
    if type(value) is not expected:
        message = f"expected exact {expected.__name__}, got {type(value).__name__}"
        raise TypeError(message)
    return value


CONVERTER = Converter(forbid_extra_keys=True, detailed_validation=True)
for _scalar in (str, int, bool, float, bytes):
    CONVERTER.register_structure_hook(_scalar, _strict_scalar)


def _structure_enum[T: StrEnum](value: object, expected: type[T]) -> T:
    return expected(value)


CONVERTER.register_structure_hook(StrEnum, _structure_enum)
CONVERTER.register_unstructure_hook(StrEnum, lambda value: value.value)


def payload(record: Record) -> dict[str, object]:
    """Return the explicit record boundary representation.

    Returns:
        Typed field values with tuples and nested contracts unstructured.

    """
    return CONVERTER.unstructure(record)


def _json_leaf(value: object) -> object:
    if isinstance(value, bytes):
        return {"$bytes": base64.b64encode(value).decode("ascii")}
    message = f"unsupported canonical value: {type(value).__name__}"
    raise TypeError(message)


def canonical(value: object) -> bytes:
    """Encode finite canonical content, preserving byte values explicitly.

    Returns:
        Stable UTF-8 bytes. Nonfinite floats require a tagged language value.

    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_json_leaf,
    ).encode("utf-8")


def digest(value: object) -> str:
    """Return the SHA-256 of canonical content.

    Returns:
        The SHA-256 of canonical content.

    """
    return hashlib.sha256(canonical(value)).hexdigest()


def bytes_digest(value: bytes) -> str:
    """Return the SHA-256 of original bytes.

    Returns:
        The SHA-256 of original bytes.

    """
    return hashlib.sha256(value).hexdigest()
