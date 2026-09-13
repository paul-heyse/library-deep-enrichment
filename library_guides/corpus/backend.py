"""Private Lance adapter; only the coordinator may append persistent rows."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

import lancedb
import pyarrow as pa
from lancedb.index import BTree
from lancedb.table import LanceTable

MAX_PINNED_TABLE_HANDLES = 64

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path


class CorpusError(ValueError):
    """A corpus invariant, integrity, or admission precondition failed."""


class BudgetExceededError(CorpusError):
    """Work stopped at an explicit boundary; the result is not complete."""


class PredecessorConflictError(CorpusError):
    """The named head advanced after the producer pinned its input."""


def literal(value: str) -> str:
    """Return a quoted SQL scalar, never an executable predicate fragment.

    Returns:
        A quoted SQL scalar, never an executable predicate fragment.

    """
    return "'" + value.replace("'", "''") + "'"


class Backend:
    """A fresh-connection adapter with explicit versioned reads."""

    def __init__(self, root: Path) -> None:
        """Open a local corpus; no process-global connection is shared."""
        self._db = lancedb.connect(str(root))
        self._pinned_tables: OrderedDict[tuple[str, int], LanceTable] = OrderedDict()

    def exists(self, name: str) -> bool:
        """Return whether a registered physical table exists.

        Returns:
            Whether a registered physical table exists.

        """
        return name in self._db.list_tables(limit=1000).tables

    def table(self, name: str, version: int | None = None) -> LanceTable:
        """Reuse bounded exact-version read handles; latest writer handles remain fresh.

        Returns:
            An internal handle pinned to the requested immutable version, or fresh latest.

        Raises:
            CorpusError: Storage is not the qualified local Lance implementation.

        """
        if version is not None and (name, version) in self._pinned_tables:
            self._pinned_tables.move_to_end((name, version))
            return self._pinned_tables[name, version]
        table = self._db.open_table(name)
        if not isinstance(table, LanceTable):
            message = "the corpus requires the qualified local Lance table implementation"
            raise CorpusError(message)
        if version is not None:
            table.checkout(version)
            if len(self._pinned_tables) >= MAX_PINNED_TABLE_HANDLES:
                self._pinned_tables.popitem(last=False)
            self._pinned_tables[name, version] = table
        return table

    def append(self, name: str, schema: pa.Schema, rows: Sequence[dict[str, object]]) -> int:
        """Append a validated batch and return its committed table version.

        Returns:
            Append a validated batch and return its committed table version.

        Raises:
            CorpusError: Existing storage has an incompatible schema.

        """
        table = (
            self.table(name) if self.exists(name) else self._db.create_table(name, schema=schema)
        )
        if not isinstance(table, LanceTable):
            message = "admission requires the qualified local Lance table implementation"
            raise CorpusError(message)
        if not table.schema.equals(schema, check_metadata=True):
            message = f"incompatible corpus schema: {name}"
            raise CorpusError(message)
        if rows:
            table.add(pa.Table.from_pylist(list(rows), schema=schema))
        self._indexes(table)
        return table.version

    @staticmethod
    def _indexes(table: LanceTable) -> None:
        indexed = {column: index for index in table.list_indices() for column in index.columns}
        pending: list[str] = []
        for column in (
            "revision",
            "logical_id",
            "profile",
            "manifest",
            "family",
            "name",
            "artifact",
            "kind",
            "symbol",
            "file",
            "owner",
        ):
            if column in table.schema.names and pa.types.is_string(table.schema.field(column).type):
                existing = indexed.get(column)
                statistics = table.index_stats(existing.name) if existing is not None else None
                if statistics is None:
                    table.create_index(column, config=BTree(), replace=True)
                elif statistics.num_unindexed_rows and existing is not None:
                    pending.append(existing.name)
        if pending:
            # Index-only delta maintenance preserves all data fragments, protected
            # versions, and historical index fragments. Generic optimize() also
            # compacts/prunes and is deliberately not used at an admission boundary.
            table.to_lance().optimize.optimize_indices(num_indices_to_merge=0, index_names=pending)
            table.checkout_latest()
            for name in pending:
                statistics = table.index_stats(name)
                if statistics is None or statistics.num_unindexed_rows:
                    message = f"incremental index update left uncovered rows: {name}"
                    raise CorpusError(message)

    def refresh_indexes(self, name: str) -> int:
        """Refresh scalar coverage without invoking compaction or version pruning.

        Returns:
            The physical version to bind through a coordinator commit.

        """
        table = self.table(name)
        self._indexes(table)
        return table.version

    def scan(
        self,
        name: str,
        *,
        version: int | None = None,
        where: str = "true",
        columns: list[str] | None = None,
        limit: int = 250_000,
    ) -> Iterator[dict[str, object]]:
        """Yield bounded projected rows from one exact table snapshot.

        Yields:
            Bounded projected rows from one exact table snapshot.

        Raises:
            BudgetExceededError: The requested finite scan exceeds its row budget.

        """
        query = self.table(name, version).search().where(where).limit(limit + 1)
        if columns is not None:
            query = query.select(columns)
        count = 0
        for batch in query.to_batches(batch_size=1024):
            for row in batch.to_pylist():
                count += 1
                if count > limit:
                    message = f"scan budget exceeded: {name}, limit={limit}; narrow the selection"
                    raise BudgetExceededError(message)
                yield row

    def protect(self, name: str, version: int, manifest: str) -> None:
        """Protect a selected version; automatic pruning is deliberately absent."""
        table = self.table(name)
        tag = f"m_{manifest}"
        if tag not in table.tags.list():
            table.tags.create(tag, version)
