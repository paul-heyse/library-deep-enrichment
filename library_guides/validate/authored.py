"""Fail-closed readers for authored YAML records.

Every accessor names the context it was reading, so a manifest defect reports
where it is rather than surfacing later as a confusing attribute error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "AuthoredRecordError",
    "require_mapping",
    "require_sequence",
    "require_str",
    "require_str_sequence",
    "require_value_in",
]


class AuthoredRecordError(ValueError):
    """Raised when an authored record is missing or malformed."""


def require_mapping(value: object, *, context: str) -> Mapping[str, object]:
    """Return ``value`` when it is a mapping with string keys.

    Returns:
        The validated mapping.

    Raises:
        AuthoredRecordError: When the value is not a string-keyed mapping.

    """
    if not isinstance(value, dict):
        message = f"{context}: expected a mapping, got {type(value).__name__}"
        raise AuthoredRecordError(message)
    for key in value:
        if not isinstance(key, str):
            message = f"{context}: expected string keys, got {type(key).__name__}"
            raise AuthoredRecordError(message)
    return value


def require_str(mapping: Mapping[str, object], key: str, *, context: str) -> str:
    """Return a required non-empty string field.

    Returns:
        The field value.

    Raises:
        AuthoredRecordError: When the field is absent, not a string, or empty.

    """
    if key not in mapping:
        message = f"{context}: missing required field {key!r}"
        raise AuthoredRecordError(message)
    value = mapping[key]
    if not isinstance(value, str) or not value.strip():
        message = f"{context}: field {key!r} must be a non-empty string"
        raise AuthoredRecordError(message)
    return value


def require_sequence(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> Sequence[object]:
    """Return a required list field.

    Returns:
        The field value.

    Raises:
        AuthoredRecordError: When the field is absent or not a list.

    """
    if key not in mapping:
        message = f"{context}: missing required field {key!r}"
        raise AuthoredRecordError(message)
    value = mapping[key]
    if not isinstance(value, list):
        message = f"{context}: field {key!r} must be a list"
        raise AuthoredRecordError(message)
    return value


def require_str_sequence(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> tuple[str, ...]:
    """Return a required list-of-strings field.

    Returns:
        The field values.

    Raises:
        AuthoredRecordError: When any entry is not a string.

    """
    values = require_sequence(mapping, key, context=context)
    result: list[str] = []
    for index, entry in enumerate(values):
        if not isinstance(entry, str):
            message = f"{context}: {key}[{index}] must be a string"
            raise AuthoredRecordError(message)
        result.append(entry)
    return tuple(result)


def require_value_in(value: str, allowed: frozenset[str], *, context: str) -> str:
    """Return ``value`` when it is a member of ``allowed``.

    Returns:
        The validated value.

    Raises:
        AuthoredRecordError: When the value is outside the allowed set.

    """
    if value not in allowed:
        options = ", ".join(sorted(allowed))
        message = f"{context}: {value!r} is not one of: {options}"
        raise AuthoredRecordError(message)
    return value
