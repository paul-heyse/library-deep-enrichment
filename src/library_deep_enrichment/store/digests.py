"""Content addressing.

Semantic digests deliberately exclude operational metadata such as acquisition
time, so refreshing an unchanged source does not invalidate the whole guide.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

__all__ = [
    "OPERATIONAL_KEYS",
    "canonical_bytes",
    "content_addressed",
    "digest_bytes",
    "digest_file",
    "digest_mapping",
    "digest_sequence",
    "semantic_payload",
]

OPERATIONAL_KEYS: frozenset[str] = frozenset(
    {
        "acquired_at",
        "acquisition_time",
        "elapsed_ms",
        "fetched_at",
        "generated_at",
        "observed_at",
    }
)
"""Keys excluded from semantic digests because they change without meaning."""


def canonical_bytes(value: object) -> bytes:
    """Return the canonical JSON encoding of ``value``.

    Returns:
        Deterministic UTF-8 bytes with sorted keys and no incidental whitespace.

    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest_bytes(payload: bytes) -> str:
    """Return the hexadecimal SHA-256 digest of ``payload``.

    Returns:
        Lowercase hexadecimal digest.

    """
    return hashlib.sha256(payload).hexdigest()


def digest_file(path: Path) -> str:
    """Return the hexadecimal SHA-256 digest of a file's bytes.

    Returns:
        Lowercase hexadecimal digest.

    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Return ``payload`` without operational keys, recursively.

    Returns:
        A copy suitable for a semantic digest.

    """
    result: dict[str, object] = {}
    for key, value in payload.items():
        if key in OPERATIONAL_KEYS:
            continue
        if isinstance(value, dict):
            result[key] = semantic_payload(value)
        else:
            result[key] = value
    return result


def digest_mapping(payload: Mapping[str, object]) -> str:
    """Return the semantic digest of a mapping.

    Returns:
        Lowercase hexadecimal digest over the operational-key-free payload.

    """
    return digest_bytes(canonical_bytes(semantic_payload(payload)))


def digest_sequence(values: Iterable[str]) -> str:
    """Return a digest over an ordered sequence of digests or identifiers.

    Returns:
        Lowercase hexadecimal digest.

    """
    return digest_bytes(canonical_bytes(list(values)))


def content_addressed(payload: Mapping[str, object], field: str) -> dict[str, object]:
    """Return ``payload`` with its own semantic digest stored under ``field``.

    Returns:
        A copy of the mapping carrying its digest.

    """
    result = dict(payload)
    result[field] = digest_mapping(payload)
    return result
