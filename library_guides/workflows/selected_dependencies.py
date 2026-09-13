"""Finite exact-input closure for stages whose candidate universe is explicitly requested."""

from __future__ import annotations

from collections import defaultdict
from itertools import batched
from typing import TYPE_CHECKING

from library_guides.corpus.backend import BudgetExceededError
from library_guides.corpus.contracts import Selection
from library_guides.corpus.validation import _supports, references
from library_guides.workflows.contracts import FamilySelector

if TYPE_CHECKING:
    from library_guides.corpus.store import CorpusReader
    from library_guides.workflows.contracts import StageDefinition

_MAX_DEPENDENCIES = 100_000


def exact_selectors(
    reader: CorpusReader, definition: StageDefinition, roots: tuple[tuple[str, str], ...]
) -> tuple[FamilySelector, ...]:
    """Select declared exact prerequisites without depending on unrelated new blob membership.

    Returns:
        Exact logical-head selectors. Open candidate searches require their own membership
        selectors; this function is only for explicitly finite request universes.

    Raises:
        BudgetExceededError: The finite prerequisite graph exceeds the declared bound.

    """
    declared = {item.family for item in definition.inputs}
    selected: dict[str, set[str]] = defaultdict(set)
    pending = set(roots)
    seen: set[tuple[str, str]] = set()
    while pending:
        window = pending - seen
        pending = set()
        groups: dict[str, list[str]] = defaultdict(list)
        for family, revision in sorted(window):
            if family in declared:
                groups[family].append(revision)
                seen.add((family, revision))
        if len(seen) > _MAX_DEPENDENCIES:
            message = "exact stage dependency closure exceeds its finite bound"
            raise BudgetExceededError(message)
        for family, revisions in groups.items():
            for batch in batched(revisions, 128, strict=False):
                for record in reader.get_many(family, batch):
                    selected[family].add(record.logical_id)
                    # Managed blob bytes are content addressed. Do not read multi-MiB chunks
                    # during planning; the native/read validator verifies bodies when used.
                    if family == "blobs":
                        continue
                    pending.update(references(record))
                    pending.update(
                        (item.family, item.revision)
                        if isinstance(item, Selection)
                        else ("blobs", item.blob)
                        for item in _supports(record)
                    )
    return tuple(
        FamilySelector(family=family, logical_ids=tuple(sorted(selected[family])))
        if selected[family]
        else FamilySelector(family=family, logical_ids=("",), prefix="nonempty:")
        for family in sorted(declared)
    )
