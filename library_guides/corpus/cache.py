"""A reader-local bounded cache of verified immutable records."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

from library_guides.corpus.contracts import BlobChunk
from library_guides.corpus.encoding import canonical, payload

if TYPE_CHECKING:
    from library_guides.corpus.contracts import Record

MAX_ENTRIES = 2048
MAX_BYTES = 64 * 1024 * 1024


class RecordCache:
    """Cache decoded frozen records within a conservative byte and entry budget."""

    def __init__(self) -> None:
        """Create a cache owned by exactly one pinned reader."""
        self.entries: OrderedDict[tuple[str, str], tuple[Record, int]] = OrderedDict()
        self.size = 0

    def get(self, key: tuple[str, str]) -> Record | None:
        """Look up an already verified immutable record.

        Returns:
            The retained record or a cache miss.

        """
        entry = self.entries.get(key)
        if entry is None:
            return None
        self.entries.move_to_end(key)
        return entry[0]

    def put(self, key: tuple[str, str], record: Record) -> None:
        """Retain a record when it fits; evict least-recently-used entries first."""
        retained = self.entries.get(key)
        if retained is not None and retained[0] is record:
            self.entries.move_to_end(key)
            return
        # A frozen bytes payload already has its exact resident representation;
        # charging four times its base64 JSON needlessly evicts shared source
        # chunks. Other structured records retain the conservative estimate.
        size = (
            len(record.data)
            + 4 * (len(record.logical_id) + len(record.profile) + len(record.digest))
            + 4096
            if isinstance(record, BlobChunk)
            else len(canonical(payload(record))) * 4 + 4096
        )
        if size > MAX_BYTES:
            return
        previous = self.entries.pop(key, None)
        if previous is not None:
            self.size -= previous[1]
        while self.entries and (self.size + size > MAX_BYTES or len(self.entries) >= MAX_ENTRIES):
            _, (_, removed_size) = self.entries.popitem(last=False)
            self.size -= removed_size
        self.entries[key] = record, size
        self.size += size
