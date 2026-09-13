"""Single-writer coherent admission with a final atomic control-table commit."""

from __future__ import annotations

from collections import defaultdict
from itertools import batched, islice
from typing import TYPE_CHECKING

from attrs import frozen
from filelock import FileLock

from library_guides.corpus.backend import (
    Backend,
    BudgetExceededError,
    CorpusError,
    PredecessorConflictError,
    literal,
)
from library_guides.corpus.contracts import (
    AdmissionBatch,
    Binding,
    Head,
    Manifest,
    Member,
    Policy,
    Record,
    Review,
)
from library_guides.corpus.encoding import CONVERTER
from library_guides.corpus.invalidation import invalidate
from library_guides.corpus.manifests import (
    HEAD_SCHEMA,
    MANIFEST_SCHEMA,
    MEMBER_SCHEMA,
    logical_digest,
    membership_digest,
    read_head,
)
from library_guides.corpus.ownership import validate_ownership
from library_guides.corpus.schemas import REGISTRY, codec_for, revision_of
from library_guides.corpus.validation import AdmissionReader, validate_staged

MAX_POINT_REUSE_RECORDS = 64

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from library_guides.corpus.store import Corpus, CorpusReader


@frozen(kw_only=True)
class WriterIdentity:
    """Coordinator authorization, separate from producer-supplied record fields."""

    principal: str
    role: str = "producer"


@frozen(kw_only=True)
class CommitSelection:
    """A validated logical selection and the exact physical versions to publish."""

    previous: Head | None
    head: str
    predecessor: str
    manifest_id: str
    members: dict[tuple[str, str, str], Member]
    versions: dict[str, int]


def _check_authority(record: Record, identity: WriterIdentity) -> None:
    if isinstance(record, Policy) and identity.role not in {"policy", "migration"}:
        message = "producer cannot change independent policy"
        raise CorpusError(message)
    if isinstance(record, Review) and identity.role not in {"review", "migration"}:
        message = "producer cannot manufacture an interpretation review"
        raise CorpusError(message)


def _append_family(backend: Backend, family: str, rows: list[dict[str, object]]) -> int:
    codec = REGISTRY[family]
    pending: dict[str, dict[str, object]] = {}
    for row in rows:
        revision = str(row["revision"])
        if revision in pending and pending[revision] != row:
            message = f"revision collision: {family}/{revision}"
            raise CorpusError(message)
        pending[revision] = row
    if backend.exists(family):
        for identifiers in batched(tuple(pending), 512, strict=False):
            predicate = "revision IN (" + ",".join(literal(item) for item in identifiers) + ")"
            for existing in backend.scan(family, where=predicate, limit=len(identifiers)):
                codec.decode(existing)
                revision = str(existing["revision"])
                if existing != pending.pop(revision, None):
                    message = f"non-unique or conflicting immutable revision: {family}/{revision}"
                    raise CorpusError(message)
    return backend.append(family, codec.schema, list(pending.values()))


def _stage(
    records: Iterable[Record],
    identity: WriterIdentity,
    limit: int,
) -> tuple[dict[str, list[dict[str, object]]], dict[tuple[str, str, str], Member]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    members: dict[tuple[str, str, str], Member] = {}
    for count, record in enumerate(records, 1):
        if count > limit:
            message = f"admission record budget exceeded: {limit}"
            raise BudgetExceededError(message)
        _check_authority(record, identity)
        codec = codec_for(record)
        row = codec.encode(record)
        codec.decode(row)
        key = (codec.family, record.logical_id, record.profile)
        member = Member(
            family=codec.family,
            logical_id=record.logical_id,
            profile=record.profile,
            revision=str(row["revision"]),
        )
        if key in members and members[key] != member:
            message = f"two current revisions for logical key: {key}"
            raise CorpusError(message)
        members[key] = member
        groups[codec.family].append(row)
    return groups, members


class Coordinator:
    """The only sanctioned persistent writer for one local corpus."""

    def __init__(
        self,
        corpus: Corpus,
        identity: WriterIdentity,
        *,
        imported_predecessor: str | None = None,
        historical_checker: str = "current",
    ) -> None:
        """Bind an explicit authority; workers receive staging contracts only.

        Raises:
            CorpusError: A producer attempts to set portable import identity.

        """
        if imported_predecessor is not None and identity.role != "migration":
            message = "only the verified portable importer can set imported lineage"
            raise CorpusError(message)
        self.corpus = corpus
        self.identity = identity
        self.imported_predecessor = imported_predecessor
        from library_guides.corpus.checker_epochs import fingerprint

        fingerprint(historical_checker)
        if historical_checker != "current" and imported_predecessor is None:
            message = "historical checking is restricted to verified portable imports"
            raise CorpusError(message)
        self.historical_checker = historical_checker

    def commit(
        self,
        records: Iterable[Record] | AdmissionBatch,
        *,
        expected: str,
        head: str = "analysis",
        replace: bool = False,
        checkpoint: Callable[[str], None] | None = None,
    ) -> str:
        """Admit one coherent selection and atomically advance its named head.

        ``checkpoint`` is a fault-injection/observability seam after durable writes.
        A failure before ``control`` leaves the previous sanctioned view intact.

        Returns:
            The committed portable manifest identifier.

        Raises:
            PredecessorConflictError: The caller's expected head is stale.
            CorpusError: An import attempts to mutate or misclassify a historical view.

        """
        batch = (
            records
            if isinstance(records, AdmissionBatch)
            else AdmissionBatch(records=tuple(islice(records, self.corpus.max_rows + 1)))
        )
        groups, staged = _stage(batch.records, self.identity, self.corpus.max_rows)
        self.corpus.root.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.corpus.root / ".writer.lock")):
            backend = Backend(self.corpus.root)
            previous = read_head(backend, head)
            actual = "" if previous is None else previous.manifest
            if actual != expected:
                message = f"stale {head} predecessor: expected {expected}, current {actual}"
                raise PredecessorConflictError(message)
            reader = self.corpus.reader(head)
            if reader.semantic_checker != "current" or (
                self.historical_checker != "current" and (actual or not replace)
            ):
                message = "historical views are immutable; qualify a separate current successor"
                raise CorpusError(message)
            if self._unchanged(reader, batch, staged, replace=replace):
                return reader.manifest_id
            batch = self._invalidate(
                reader, batch, staged, active=head == "analysis" and not replace
            )
            groups, staged = _stage(batch.records, self.identity, self.corpus.max_rows)
            if head == "analysis" and not replace:
                validate_ownership(reader, batch, staged)
            validate_staged(
                AdmissionReader(reader, groups, replace=replace, retire=batch.retire),
                checker=self.historical_checker,
            )
            members = self._members(reader, batch, staged, replace=replace)
            member_digest = membership_digest(members.values())
            if (
                reader.manifest is not None
                and reader.manifest.members_digest == member_digest
                and self.imported_predecessor is None
            ):
                return reader.manifest_id
            predecessor = (
                expected if self.imported_predecessor is None else self.imported_predecessor
            )
            manifest_id = logical_digest(predecessor, member_digest)
            from library_guides.corpus.checker_epochs import check_manifest

            check_manifest(manifest_id, self.historical_checker)
            versions = (
                {}
                if replace or reader.manifest is None
                else {binding.family: binding.version for binding in reader.manifest.bindings}
            )
            for family, rows in sorted(groups.items()):
                versions[family] = _append_family(backend, family, rows)
                if checkpoint:
                    checkpoint(family)
            from library_guides.corpus.checker_epochs import retain

            retain(backend, manifest_id, self.historical_checker)
            return self._publish(
                backend,
                CommitSelection(
                    previous=previous,
                    head=head,
                    predecessor=predecessor,
                    manifest_id=manifest_id,
                    members=members,
                    versions=versions,
                ),
                checkpoint=checkpoint,
            )

    def _unchanged(
        self,
        reader: CorpusReader,
        batch: AdmissionBatch,
        staged: dict[tuple[str, str, str], Member],
        *,
        replace: bool,
    ) -> bool:
        if (
            replace
            or batch.retire
            or self.imported_predecessor is not None
            or not 0 < len(staged) <= MAX_POINT_REUSE_RECORDS
        ):
            return False
        return all(
            (current := reader.lookup(*key)) is not None and revision_of(current) == member.revision
            for key, member in staged.items()
        )

    @staticmethod
    def _invalidate(
        reader: CorpusReader,
        batch: AdmissionBatch,
        staged: dict[tuple[str, str, str], Member],
        *,
        active: bool,
    ) -> AdmissionBatch:
        if not active:
            return batch
        pending, withdrawn = invalidate(reader, staged, batch.retire)
        return AdmissionBatch(records=(*batch.records, *pending), retire=withdrawn)

    def refresh_indexes(self, *, expected: str, head: str = "analysis") -> str:
        """Bind fresh index coverage without changing logical records or pruning history.

        Returns:
            A coherent successor view with identical selected record membership.

        Raises:
            PredecessorConflictError: The requested head changed before maintenance.
            CorpusError: The selected membership differs from the committed manifest.

        """
        with FileLock(str(self.corpus.root / ".writer.lock")):
            reader = self.corpus.reader(head)
            if reader.semantic_checker != "current":
                message = "historical views are immutable; qualify a separate current successor"
                raise CorpusError(message)
            if reader.manifest_id != expected:
                message = "index maintenance requires the exact current predecessor"
                raise PredecessorConflictError(message)
            if reader.manifest is None:
                return ""
            members = {
                (item.family, item.logical_id, item.profile): item for item in reader.members()
            }
            selected_digest = membership_digest(members.values())
            if (
                selected_digest != reader.manifest.members_digest
                or len(members) != reader.manifest.count
            ):
                message = "maintenance membership differs from its retained manifest"
                raise CorpusError(message)
            backend = Backend(self.corpus.root)
            versions = {
                binding.family: backend.refresh_indexes(binding.family)
                for binding in reader.manifest.bindings
            }
            return self._publish(
                backend,
                CommitSelection(
                    previous=read_head(backend, head),
                    head=head,
                    predecessor=expected,
                    manifest_id=logical_digest(expected, selected_digest),
                    members=members,
                    versions=versions,
                ),
                checkpoint=None,
            )

    def _members(
        self,
        reader: CorpusReader,
        batch: AdmissionBatch,
        staged: dict[tuple[str, str, str], Member],
        *,
        replace: bool,
    ) -> dict[tuple[str, str, str], Member]:
        members = (
            {} if replace else {(m.family, m.logical_id, m.profile): m for m in reader.members()}
        )
        for retired in batch.retire:
            key = (retired.family, retired.logical_id, retired.profile)
            if members.get(key) != retired:
                message = f"retirement does not match the pinned predecessor: {key}"
                raise CorpusError(message)
            if retired.family in {"policies", "reviews"}:
                _check_authority(reader.get(retired.family, retired.revision), self.identity)
            members.pop(key)
        members.update(staged)
        if len(members) > self.corpus.max_rows:
            message = "selected membership exceeds the corpus row boundary"
            raise BudgetExceededError(message)
        return members

    def _publish(
        self,
        backend: Backend,
        selection: CommitSelection,
        *,
        checkpoint: Callable[[str], None] | None,
    ) -> str:
        members = selection.members
        manifest_id = selection.manifest_id
        membership_rows = [
            {"manifest": manifest_id, **CONVERTER.unstructure(member)}
            for member in sorted(
                members.values(), key=lambda m: (m.family, m.logical_id, m.profile)
            )
        ]
        # A failed earlier attempt may already contain this exact immutable selection.
        if backend.exists("memberships"):
            present = list(
                backend.scan(
                    "memberships",
                    where=f"manifest = {literal(manifest_id)}",
                    limit=self.corpus.max_rows,
                )
            )
            if present:
                if sorted(present, key=str) != sorted(membership_rows, key=str):
                    message = f"conflicting manifest membership: {manifest_id}"
                    raise CorpusError(message)
                membership_rows = []
        membership_version = backend.append("memberships", MEMBER_SCHEMA, membership_rows)
        manifest = Manifest(
            digest=manifest_id,
            predecessor=selection.predecessor,
            members_digest=membership_digest(members.values()),
            membership_version=membership_version,
            bindings=tuple(
                Binding(family=name, version=version)
                for name, version in sorted(selection.versions.items())
            ),
            count=len(members),
        )
        if checkpoint:
            checkpoint("memberships")
        manifest_rows = [CONVERTER.unstructure(manifest)]
        if backend.exists("manifests"):
            existing = list(
                backend.scan("manifests", where=f"digest = {literal(manifest_id)}", limit=1)
            )
            if existing:
                # An orphan manifest remains bound to its original valid table versions.
                manifest = CONVERTER.structure(existing[0], Manifest)
                manifest_rows = []
        version = backend.append("manifests", MANIFEST_SCHEMA, manifest_rows)
        backend.protect("memberships", manifest.membership_version, manifest_id)
        for binding in manifest.bindings:
            backend.protect(binding.family, binding.version, manifest_id)
        backend.protect("manifests", version, manifest_id)
        if checkpoint:
            checkpoint("manifests")
        control = Head(
            name=selection.head,
            sequence=1 if selection.previous is None else selection.previous.sequence + 1,
            manifest=manifest_id,
            manifest_version=version,
            predecessor="" if selection.previous is None else selection.previous.manifest,
        )
        backend.append("control_heads", HEAD_SCHEMA, [CONVERTER.unstructure(control)])
        if checkpoint:
            checkpoint("control")
        return manifest_id
