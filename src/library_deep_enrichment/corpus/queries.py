"""Validated equality selectors for indexed typed columns, without raw SQL input."""

from __future__ import annotations

import pyarrow as pa

from library_deep_enrichment.corpus.backend import CorpusError, literal
from library_deep_enrichment.corpus.schemas import REGISTRY


def predicate(family: str, equals: tuple[tuple[str, str], ...]) -> str:
    """Compile exact text-column equalities from the registered family schema.

    Returns:
        A safely quoted nonempty predicate over explicit typed column names.

    Raises:
        CorpusError: A selector is empty, repeated, or names a non-text/unknown column.

    """
    schema = REGISTRY[family].schema
    names = [name for name, _ in equals]
    if (
        not names
        or len(names) != len(set(names))
        or any(
            name not in schema.names or not pa.types.is_string(schema.field(name).type)
            for name in names
        )
    ):
        message = "equality selectors require unique registered text columns"
        raise CorpusError(message)
    return " AND ".join(f'"{name}" = {literal(value)}' for name, value in equals)
