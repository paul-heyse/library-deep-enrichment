"""Recompute admitted call-shape consequences against exact contextual declarations."""

from __future__ import annotations

from itertools import batched
from typing import TYPE_CHECKING

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import Operation, TypeUse
from library_guides.semantics.type_shapes import OperationShape, operation_shape

if TYPE_CHECKING:
    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader


def validate_shapes(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Validate a finite shape projection without trusting its source pointer alone.

    Raises:
        CorpusError: A shape loses a wrapper, substitutes the wrong Self, or changes context.

    """
    proposed = [item for item in records if isinstance(item, OperationShape)]
    if not proposed:
        return
    owners = {item.operation for item in proposed}
    grouped: dict[str, list[TypeUse]] = {}
    for item in reader.records("type_uses"):
        if isinstance(item, TypeUse) and item.owner in owners:
            grouped.setdefault(item.owner, []).append(item)
    for batch in batched(proposed, 128, strict=False):
        operations = tuple(reader.get_many("operations", (item.operation for item in batch)))
        reader.prefetch(
            (source.family, source.revision)
            for operation in operations
            if isinstance(operation, Operation) and operation.language == "rust"
            for source in operation.evidence
            if source.family in {"native_facts", "legacy_records"}
            and source.field == "/raw/signature"
        )
        for item, operation in zip(batch, operations, strict=True):
            if (
                not isinstance(operation, Operation)
                or operation_shape(reader, operation, tuple(grouped.get(item.operation, ())))
                != item
            ):
                message = "operation shape differs from its exact declared types and contextual substitutions"
                raise CorpusError(message)
