"""Replay pre-schema comparisons with their recorded physical input ordering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import Scope
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.validation import AdmissionReader
from library_guides.semantics.historical_task_matching import compare

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader
    from library_guides.semantics.contracts import Comparison, Task


class OrderedReader(AdmissionReader):
    """Order the complete input family without adding, omitting, or changing selected records."""

    def __init__(self, base: CorpusReader, order: tuple[str, ...]) -> None:
        """Retain the original selected universe ordering as historical execution input."""
        super().__init__(base, {}, replace=False)
        self.order = order

    def records(self, family: str) -> Iterator[Record]:
        """Yield every operation once; other families retain their exact source reader.

        Yields:
            The same complete input population in the historically recorded order.

        Raises:
            CorpusError: The recorded ordering repeats or invents a selected operation.

        """
        if family != "operations":
            yield from super().records(family)
            return
        records = {revision_of(item): item for item in super().records(family)}
        for revision in self.order:
            if revision not in records:
                message = "historical candidate order repeats or invents an operation"
                raise CorpusError(message)
            yield records.pop(revision)
        yield from records.values()


def replay(reader: CorpusReader, task: Task, comparison: Comparison) -> Comparison:
    """Recompute historical semantics while retaining its explicit candidate ordering.

    Returns:
        The exact old comparison, including its original scope digest.

    Raises:
        CorpusError: The retained scope has no historical operation order.

    """
    scope = reader.get("scopes", comparison.universe)
    if not isinstance(scope, Scope) or any(item.family != "operations" for item in scope.sources):
        message = "historical comparison requires its exact operation scope"
        raise CorpusError(message)
    source = OrderedReader(reader, tuple(item.revision for item in scope.sources))
    return compare(source, task)[1]
