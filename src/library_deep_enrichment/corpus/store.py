"""Pinned sanctioned reads and the public corpus entry point."""

from __future__ import annotations

from collections import OrderedDict
from itertools import batched, islice
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import Backend, CorpusError, literal
from library_deep_enrichment.corpus.cache import RecordCache
from library_deep_enrichment.corpus.catalog import load_schemas
from library_deep_enrichment.corpus.contracts import Member, Record
from library_deep_enrichment.corpus.encoding import CONVERTER
from library_deep_enrichment.corpus.manifests import membership_digest, read_head, read_manifest
from library_deep_enrichment.corpus.schemas import REGISTRY

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    from library_deep_enrichment.corpus.contracts import Manifest
    from library_deep_enrichment.corpus.paging import Page

MAX_CACHED_MEMBERS = 200_000
MAX_LOGICAL_LOOKUPS = 1024
SMALL_FAMILIES = frozenset(
    {
        "policies",
        "predicates",
        "rules",
        "stage_definitions",
        "embedding_recipes",
        "capability_schemas",
    }
)
MAX_SMALL_FAMILY = 512


class CorpusReader:
    """One immutable view; later head advances never alter this reader."""

    def __init__(self, root: Path, head: str = "analysis", *, max_rows: int = 250_000) -> None:
        """Pin the control, manifest, membership, and family versions once."""
        load_schemas()
        self._root = root
        self._backend = Backend(root)
        self._head = read_head(self._backend, head)
        self.manifest: Manifest | None = (
            None if self._head is None else read_manifest(self._backend, self._head)
        )
        self.max_rows = max_rows
        self._cache = RecordCache()
        self._logical_lookups: OrderedDict[tuple[str, str, str], Record | None] = OrderedDict()
        self._small_families: dict[str, tuple[Record, ...]] = {}
        self._selected: dict[str, frozenset[str]] | None = None
        self._family_members: OrderedDict[str, frozenset[str]] = OrderedDict()
        self._oversized_families: set[str] = set()
        self._versions = (
            {}
            if self.manifest is None
            else {binding.family: binding.version for binding in self.manifest.bindings}
        )

    @property
    def manifest_id(self) -> str:
        """The pinned logical identity, or empty for an uncreated view."""
        return "" if self.manifest is None else self.manifest.digest

    @property
    def semantic_checker(self) -> str:
        """The current checker or a verified immutable historical computation identity."""
        from library_deep_enrichment.corpus.checker_epochs import selected

        return selected(self._backend, self.manifest_id)

    def previous(self) -> CorpusReader | None:
        """Read a retained committed predecessor, never an arbitrary orphan manifest.

        Returns:
            The exact historical selection, or no predecessor when portable history is absent.

        """
        from library_deep_enrichment.corpus.contracts import Head

        if self.manifest is None or not self.manifest.predecessor:
            return None
        revision = self.manifest.predecessor
        version = self._backend.table("manifests").version
        found = tuple(
            self._backend.scan(
                "manifests", version=version, where=f"digest = {literal(revision)}", limit=1
            )
        )
        if not found:
            return None
        committed = tuple(
            self._backend.scan(
                "control_heads", where=f"manifest = {literal(revision)}", limit=self.max_rows
            )
        )
        if not committed:
            return None
        retained = read_manifest(
            self._backend,
            Head(
                name="ancestor",
                sequence=0,
                manifest=revision,
                manifest_version=version,
                predecessor="",
            ),
        )
        result = CorpusReader(self._root, max_rows=self.max_rows)
        result.manifest = retained
        result._head = None
        result._versions = {binding.family: binding.version for binding in retained.bindings}
        return result

    def members(self, family: str = "") -> Iterator[Member]:
        """Yield only this manifest's exact members, never orphan/history rows.

        Yields:
            Only this manifest's exact members, never orphan/history rows.

        """
        if self.manifest is None:
            return
        predicate = f"manifest = {literal(self.manifest.digest)}"
        if family:
            predicate += f" AND family = {literal(family)}"
        for row in self._backend.scan(
            "memberships",
            version=self.manifest.membership_version,
            where=predicate,
            limit=self.max_rows,
        ):
            row.pop("manifest")
            yield CONVERTER.structure(row, Member)

    def rows(self, family: str) -> Iterator[dict[str, object]]:
        """Yield selected typed rows using bounded revision batches.

        Yields:
            Selected typed rows using bounded revision batches.

        Raises:
            CorpusError: A selected row is absent or duplicated.

        """
        if family not in self._versions:
            return
        for members in batched(self.members(family), 512, strict=False):
            expected = {member.revision for member in members}
            predicate = "revision IN (" + ",".join(literal(item) for item in expected) + ")"
            seen: set[str] = set()
            for row in self._backend.scan(
                family,
                version=self._versions[family],
                where=predicate,
                limit=len(expected),
            ):
                revision = str(row["revision"])
                if revision in seen:
                    message = f"duplicate immutable row: {family}/{revision}"
                    raise CorpusError(message)
                seen.add(revision)
                yield row
            if seen != expected:
                message = f"missing selected rows: {family}/{sorted(expected - seen)}"
                raise CorpusError(message)

    def records(self, family: str) -> Iterator[Record]:
        """Yield strictly decoded selected records of one registered family.

        Yields:
            Strictly decoded selected records of one registered family.

        """
        cached = self._small_families.get(family)
        if cached is not None:
            yield from cached
            return
        codec = REGISTRY[family]
        retained: list[Record] = []
        eligible = family in SMALL_FAMILIES
        for row in self.rows(family):
            record = codec.decode(row)
            if eligible:
                retained.append(record)
                if len(retained) > MAX_SMALL_FAMILY:
                    eligible = False
                    retained.clear()
            yield record
        if eligible:
            self._small_families[family] = tuple(retained)

    def filtered_records(
        self, family: str, equals: tuple[tuple[str, str], ...]
    ) -> Iterator[Record]:
        """Push a finite typed selector into storage and intersect with pinned membership.

        Yields:
            Selected matching records only; historical or orphan rows never enter the result.

        """
        from library_deep_enrichment.corpus.queries import predicate

        where = predicate(family, equals)
        if self.manifest is None or family not in self._versions:
            return
        rows = self._backend.scan(
            family, version=self._versions[family], where=where, limit=self.max_rows
        )
        for batch in batched(rows, 512, strict=False):
            revisions = ",".join(literal(str(row["revision"])) for row in batch)
            members = self._backend.scan(
                "memberships",
                version=self.manifest.membership_version,
                where=f"manifest = {literal(self.manifest_id)} AND family = {literal(family)} AND revision IN ({revisions})",
                limit=len(batch),
            )
            selected = {str(row["revision"]) for row in members}
            for row in batch:
                if str(row["revision"]) in selected:
                    yield REGISTRY[family].decode(row)

    def _is_member(self, family: str, revision: str) -> bool:
        if self.manifest is None:
            return False
        if self._selected is None and self.manifest.count <= MAX_CACHED_MEMBERS:
            grouped: dict[str, set[str]] = {}
            selected = tuple(self.members())
            if (
                len(selected) != self.manifest.count
                or membership_digest(selected) != self.manifest.members_digest
            ):
                message = "pinned membership differs from the committed logical manifest"
                raise CorpusError(message)
            for member in selected:
                grouped.setdefault(member.family, set()).add(member.revision)
            self._selected = {name: frozenset(values) for name, values in grouped.items()}
        if self._selected is not None:
            return revision in self._selected.get(family, frozenset())
        cached = self._family_contains(family, revision)
        if cached is not None:
            return cached
        return bool(
            list(
                self._backend.scan(
                    "memberships",
                    version=self.manifest.membership_version,
                    where=(
                        f"manifest = {literal(self.manifest_id)} AND family = {literal(family)} "
                        f"AND revision = {literal(revision)}"
                    ),
                    limit=1,
                )
            )
        )

    def _family_contains(self, family: str, revision: str) -> bool | None:
        if family not in self._oversized_families:
            if family not in self._family_members:
                selected_family = tuple(islice(self.members(family), MAX_CACHED_MEMBERS + 1))
                if len(selected_family) > MAX_CACHED_MEMBERS:
                    self._oversized_families.add(family)
                else:
                    while (
                        self._family_members
                        and sum(len(values) for values in self._family_members.values())
                        + len(selected_family)
                        > MAX_CACHED_MEMBERS
                    ):
                        self._family_members.popitem(last=False)
                    self._family_members[family] = frozenset(
                        item.revision for item in selected_family
                    )
            if family in self._family_members:
                self._family_members.move_to_end(family)
                return revision in self._family_members[family]
        return None

    def _raw_row(self, family: str, revision: str) -> dict[str, object]:
        """Read one admitted revision; raw latest-table access is insufficient.

        Returns:
            One admitted revision; raw latest-table access is insufficient.

        Raises:
            CorpusError: The revision is not a member of this pinned view.

        """
        if self.manifest is None or family not in self._versions:
            message = f"unadmitted family: {family}"
            raise CorpusError(message)
        if not self._is_member(family, revision):
            message = f"revision outside pinned membership: {family}/{revision}"
            raise CorpusError(message)
        rows = list(
            self._backend.scan(
                family,
                version=self._versions[family],
                where=f"revision = {literal(revision)}",
                limit=1,
            )
        )
        if len(rows) != 1:
            message = f"missing immutable row: {family}/{revision}"
            raise CorpusError(message)
        return rows[0]

    def row(self, family: str, revision: str) -> dict[str, object]:
        """Return a fresh boundary representation of one verified member.

        Returns:
            A mutable caller-owned representation, never the cached frozen record.

        """
        return REGISTRY[family].encode(self.get(family, revision))

    def get(self, family: str, revision: str) -> Record:
        """Return one verified and admitted record.

        Returns:
            One verified and admitted record.

        """
        key = family, revision
        retained = self._cache.get(key)
        if retained is not None:
            return retained
        record = REGISTRY[family].decode(self._raw_row(family, revision))
        self._cache.put(key, record)
        return record

    def lookup(self, family: str, logical_id: str, profile: str = "") -> Record | None:
        """Return the selected revision for an exact contextual logical key.

        Returns:
            The selected revision for an exact contextual logical key.

        """
        if self.manifest is None:
            return None
        key = family, logical_id, profile
        if key in self._logical_lookups:
            self._logical_lookups.move_to_end(key)
            return self._logical_lookups[key]
        predicate = (
            f"manifest = {literal(self.manifest_id)} AND family = {literal(family)} "
            f"AND logical_id = {literal(logical_id)} AND profile = {literal(profile)}"
        )
        rows = tuple(
            self._backend.scan(
                "memberships",
                version=self.manifest.membership_version,
                where=predicate,
                columns=["revision"],
                limit=1,
            )
        )
        result = next(self.get_many(family, (str(rows[0]["revision"]),))) if rows else None
        if len(self._logical_lookups) >= MAX_LOGICAL_LOOKUPS:
            self._logical_lookups.popitem(last=False)
        self._logical_lookups[key] = result
        return result

    def get_many(self, family: str, revisions: Iterable[str]) -> Iterator[Record]:
        """Resolve exact members in finite batches without per-record membership queries.

        Yields:
            Verified records in request order, including repeated requested revisions.

        Raises:
            CorpusError: Any requested revision is unselected, absent, or duplicated.

        """
        for batch in batched(revisions, 128, strict=False):
            if self.manifest is None or family not in self._versions:
                message = f"unadmitted family: {family}"
                raise CorpusError(message)
            found = {
                revision: record
                for revision in batch
                if (record := self._cache.get((family, revision))) is not None
            }
            missing = set(batch) - found.keys()
            if missing:
                predicate = "revision IN (" + ",".join(literal(r) for r in sorted(missing)) + ")"
                members = tuple(
                    self._backend.scan(
                        "memberships",
                        version=self.manifest.membership_version,
                        where=(
                            f"manifest = {literal(self.manifest_id)} "
                            f"AND family = {literal(family)} AND {predicate}"
                        ),
                        columns=["revision"],
                        limit=len(missing),
                    )
                )
                if {str(row["revision"]) for row in members} != missing:
                    message = f"revision outside pinned membership: {family} batch"
                    raise CorpusError(message)
                for row in self._backend.scan(
                    family, version=self._versions[family], where=predicate, limit=len(missing)
                ):
                    revision = str(row["revision"])
                    if revision in found:
                        message = f"duplicate immutable row: {family}/{revision}"
                        raise CorpusError(message)
                    record = REGISTRY[family].decode(row)
                    found[revision] = record
                    self._cache.put((family, revision), record)
                if found.keys() != set(batch):
                    message = f"missing selected rows: {family} batch"
                    raise CorpusError(message)
            yield from (found[revision] for revision in batch)

    def prefetch(self, selections: Iterable[tuple[str, str]]) -> None:
        """Warm the bounded record cache through the same exact selected-read contract."""
        for batch in batched(selections, 128, strict=False):
            grouped: dict[str, set[str]] = {}
            for family, revision in batch:
                grouped.setdefault(family, set()).add(revision)
            for family, revisions in grouped.items():
                for _ in self.get_many(family, sorted(revisions)):
                    pass

    def page(
        self,
        family: str,
        *,
        profile: str | None = None,
        continuation: str = "",
        max_rows: int = 20,
        max_bytes: int = 900_000,
    ) -> Page:
        """Return a bounded ordered page with exact counts and a selection-pinned cursor.

        Returns:
            A complete page or explicit continuation; no partial population becomes complete.

        """
        from library_deep_enrichment.corpus.paging import PageRequest, read

        return read(
            self,
            self._backend,
            PageRequest(
                family=family,
                profile=profile,
                continuation=continuation,
                max_rows=max_rows,
                max_bytes=max_bytes,
            ),
        )


class Corpus:
    """A local fabric with separate explicit read and coordinator capabilities."""

    def __init__(self, root: Path, *, max_rows: int = 250_000) -> None:
        """Choose a tooling-owned corpus root and finite scan policy."""
        load_schemas()
        self.root = root
        self.max_rows = max_rows

    def reader(self, head: str = "analysis") -> CorpusReader:
        """Return a newly pinned reader for a named analysis or release head.

        Returns:
            A newly pinned reader for a named analysis or release head.

        """
        return CorpusReader(self.root, head, max_rows=self.max_rows)
