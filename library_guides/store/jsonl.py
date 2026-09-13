"""Deterministic JSONL artifact writing and reading.

The encoder refuses to coerce unknown objects. A silent ``str()`` fallback would
turn an extraction defect into a plausible-looking record.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from library_guides.models.converter import structure_record, unstructure_record
from library_guides.store.staging import write_atomic

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping
    from pathlib import Path

__all__ = ["encode_line", "read_records", "write_records"]


def _reject(value: object) -> object:
    message = f"{type(value).__name__} is not JSON-encodable; add an explicit hook"
    raise TypeError(message)


def encode_line(payload: Mapping[str, object]) -> str:
    """Return one canonical JSONL line for ``payload``.

    Returns:
        A newline-terminated JSON object with sorted keys.

    """
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_reject,
    )
    return f"{encoded}\n"


def write_records(path: Path, records: Iterable[object]) -> int:
    """Write ``records`` to ``path`` as canonical JSONL.

    Args:
        path: Destination file; parent directories are created.
        records: Records defined in :mod:`library_guides.models.records`.

    Returns:
        The number of records written.

    """
    lines = [encode_line(unstructure_record(record)) for record in records]
    write_atomic(path, "".join(lines).encode("utf-8"))
    return len(lines)


def read_records[RecordT](path: Path, record_type: type[RecordT]) -> Iterator[RecordT]:
    """Yield records rebuilt from a canonical JSONL file.

    Args:
        path: Source file.
        record_type: Target record class.

    Yields:
        One reconstructed record per non-empty line.

    """
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            yield structure_record(json.loads(stripped), record_type)
