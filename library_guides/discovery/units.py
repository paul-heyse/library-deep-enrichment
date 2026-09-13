"""Build bounded source views without duplicating labels or weakening source qualifications."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from library_guides.corpus.contracts import Operation, Passage
from library_guides.corpus.encoding import digest
from library_guides.corpus.evidence import select
from library_guides.corpus.schemas import revision_of
from library_guides.discovery.contracts import DiscoveryScope, RetrievalUnit
from library_guides.discovery.scopes import operations, prefix

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.store import CorpusReader

MAX_UNIT_CHARACTERS = 8000


def build_units(
    reader: CorpusReader, scope: DiscoveryScope | None = None
) -> Iterator[RetrievalUnit]:
    """Project operation interfaces and attributed documentation for discovery.

    Yields:
        Bounded views with explicit text truncation and the full source selections.

    """
    passages: dict[str, list[Passage]] = defaultdict(list)
    for passage in reader.records("passages"):
        if isinstance(passage, Passage) and passage.owner_family == "operations":
            passages[passage.owner].append(passage)
    selected = operations(reader, scope) if scope is not None else reader.records("operations")
    for operation in selected:
        if not isinstance(operation, Operation):
            continue
        owner = revision_of(operation)
        documents = sorted(passages.get(owner, []), key=lambda item: (item.role, item.logical_id))
        parts = [f"{operation.symbol}{operation.signature}", f"Returns: {operation.returns}"]
        support = [
            select(operation, "/signature", "declaration"),
            select(operation, "/returns", "declaration"),
        ]
        for document in documents:
            parts.append(f"{document.role}: {document.text}")
            support.append(select(document, "/text", "upstream-text"))
        original = "\n\n".join(parts)
        text = original[:MAX_UNIT_CHARACTERS]
        yield RetrievalUnit(
            logical_id=f"{prefix(scope)}{operation.logical_id}",
            profile=operation.profile,
            subject=owner,
            family="operations",
            title=operation.symbol,
            text=text,
            text_digest=digest(text),
            support=tuple(support),
            frontier=("retrieval text truncated; inspect the full cited sources",)
            if len(original) > len(text)
            else (),
        )
