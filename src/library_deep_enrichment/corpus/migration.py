"""Finite, verified legacy imports; legacy files never remain query authorities."""

from __future__ import annotations

import io
import json
from collections import Counter
from typing import TYPE_CHECKING

from attrs import asdict, fields, frozen

from library_deep_enrichment.collection import confined, evidence_bytes, load
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import (
    Argument,
    ByteRange,
    Context,
    Disposition,
    Job,
    LegacyRecord,
    LegacySelection,
    Operation,
    Passage,
    Record,
    Review,
    SourceFile,
)
from library_deep_enrichment.corpus.encoding import bytes_digest, canonical
from library_deep_enrichment.corpus.evidence import select, stage_blob
from library_deep_enrichment.corpus.schemas import codec_for, revision_of
from library_deep_enrichment.corpus.signature_syntax import return_clause
from library_deep_enrichment.knowledge import Binding

if TYPE_CHECKING:
    from pathlib import Path

    from library_deep_enrichment.corpus.store import Corpus


@frozen(kw_only=True)
class MigrationReceipt:
    """Accounted input families and newly admitted records for a finite import."""

    source_digest: str
    manifest: str
    legacy_families: tuple[tuple[str, int], ...]
    admitted_families: tuple[tuple[str, int], ...]
    limitations: tuple[str, ...]


class LegacyImporter:
    """One finite collection import with owned original bytes and alias mappings."""

    def __init__(self, root: Path) -> None:
        """Pin legacy input bytes; imports validate source digests before admission."""
        self.root = root
        self.knowledge = load(root)
        self.rows: dict[str, Record] = {}
        self.source_blobs: dict[str, str] = {}
        self.evidence: dict[str, LegacySelection] = {}
        self.aliases: dict[str, str] = {}
        self.namespace = bytes_digest((root / "knowledge.yaml").read_bytes())

    def add(self, record: Record) -> str:
        """Stage a deduplicated immutable record.

        Returns:
            Its application revision.

        """
        revision = revision_of(record)
        self.rows[revision] = record
        return revision

    def blob(self, data: bytes, media_type: str) -> ByteRange:
        """Own original or explicitly normalized bytes inside the fabric.

        Returns:
            A verified whole-object range independent of the import path.

        """
        blob, chunks = stage_blob(io.BytesIO(data), media_type=media_type)
        for chunk in chunks:
            self.add(chunk)
        revision = self.add(blob)
        return ByteRange(blob=revision, start=0, end=len(data), digest=bytes_digest(data))

    def acquire(self) -> None:
        """Verify legacy source and evidence bytes, retaining exact selector equivalence.

        Raises:
            CorpusError: Original source bytes or selected evidence changed.

        """
        self.blob((self.root / "knowledge.yaml").read_bytes(), "application/yaml")
        for source in self.knowledge.sources:
            data = confined(self.root, source.path).read_bytes()
            if bytes_digest(data) != source.digest:
                message = f"legacy source digest mismatch: {source.id}"
                raise CorpusError(message)
            interval = self.blob(data, "application/octet-stream")
            self.source_blobs[source.id] = interval.blob
            self.add(
                SourceFile(
                    logical_id=f"legacy-source:{self.namespace}:{source.id}",
                    profile=source.profile,
                    blob=interval.blob,
                    package="",
                    path=source.path,
                    locator=source.locator,
                    license=source.attribution,
                    acquisition=source.acquisition,
                )
            )
        for evidence in self.knowledge.evidence:
            selected = evidence_bytes(self.root, self.knowledge, evidence)
            if bytes_digest(selected) != evidence.digest:
                message = f"legacy evidence digest mismatch: {evidence.id}"
                raise CorpusError(message)
            record = LegacySelection(
                logical_id=f"legacy-selection:{self.namespace}:{evidence.id}",
                source_blob=self.source_blobs[evidence.source],
                selector=evidence.selector,
                expected_digest=evidence.digest,
                selected=self.blob(selected, "application/octet-stream"),
                legacy_subject=evidence.subject,
            )
            self.evidence[evidence.id] = record
            self.add(record)

    def archive_families(self) -> tuple[tuple[str, int], ...]:
        """Retain every supplied legacy family, without treating prose as typed semantics.

        Returns:
            The exact family denominator; each old record has an owned-byte alias.

        """
        counts: list[tuple[str, int]] = []
        for descriptor in fields(type(self.knowledge)):
            records = getattr(self.knowledge, descriptor.name)
            if not isinstance(records, tuple):
                continue
            counts.append((descriptor.name, len(records)))
            for position, record in enumerate(records):
                identifier = str(getattr(record, "id", f"{descriptor.name}:{position}"))
                original = self.blob(canonical(asdict(record)), "application/json")
                alias = LegacyRecord(
                    logical_id=f"legacy-record:{self.namespace}:{descriptor.name}:{identifier}",
                    profile=str(getattr(record, "profile", "")),
                    artifact=self.namespace,
                    legacy_id=identifier,
                    kind=descriptor.name,
                    original=original,
                    normalized_family="",
                    normalized_revision="",
                )
                self.aliases[identifier] = self.add(alias)
        return tuple(counts)

    def interfaces(self) -> None:
        """Normalize contextual bindings and their exact documentation selections."""
        for profile in self.knowledge.profiles:
            self.add(
                Context(
                    logical_id=f"context:{profile.id}",
                    profile=profile.id,
                    language="mixed",
                    package="",
                    version="",
                    toolchain="",
                    target="",
                    features=(),
                    components=profile.components,
                )
            )
        for binding in self.knowledge.bindings:
            operation = self._operation(binding)
            revision = self.add(operation)
            associated = {
                claim
                for capability in self.knowledge.capabilities
                if binding.id in capability.bindings
                for claim in capability.claims
            }
            for claim in self.knowledge.claims:
                if claim.id not in associated:
                    continue
                for evidence_id in claim.evidence:
                    source = self.evidence.get(evidence_id)
                    if source is not None:
                        self._passage(source, revision, binding.profile)

    def _operation(self, binding: Binding) -> Operation:
        # Some old binding projections retained a full signature but omitted
        # the return slot. This is syntax recovery, not an inferred return type.
        returns = binding.returns
        if not returns and " -> " in binding.signature:
            returns = return_clause(binding.signature)
        return Operation(
            logical_id=f"operation:{binding.language}:{binding.package}:{binding.symbol}",
            profile=binding.profile,
            symbol=binding.symbol,
            package=binding.package,
            version=binding.version,
            language=binding.language,
            kind=binding.kind,
            signature=binding.signature,
            returns=returns,
            routes=(binding.symbol, *binding.aliases),
            parameters=tuple(
                Argument(
                    name=arg.name,
                    kind=arg.kind,
                    type_expression=arg.type,
                    default_expression="" if arg.default is None else arg.default,
                    required=arg.default is None,
                )
                for arg in binding.parameters
            ),
            resolution=binding.resolution,
            evidence=tuple(
                select(self.evidence[item], "/selected", "legacy-equivalence")
                for item in binding.evidence
            ),
        )

    def _passage(self, source: LegacySelection, owner: str, profile: str) -> None:
        selected = next(
            (
                evidence_bytes(self.root, self.knowledge, item)
                for item in self.knowledge.evidence
                if source.logical_id.endswith(f":{item.id}")
            ),
            None,
        )
        if selected is None:
            return
        text = selected.decode("utf-8")
        if source.selector.startswith("json:"):
            value = json.loads(text)
            if not isinstance(value, str):
                return
            text = value
        self.add(
            Passage(
                logical_id=f"passage:{owner}:{source.logical_id}",
                profile=profile,
                owner=owner,
                role="upstream-documentation",
                text=text,
                language="en",
                source=source.selected,
                evidence=(select(source, "/selected", "legacy-equivalence"),),
            )
        )

    def reviews(self) -> None:
        """Preserve original attribution without approving new computational assertions."""
        for position, review in enumerate(self.knowledge.reviews):
            self.add(
                Review(
                    logical_id=f"legacy-review:{self.namespace}:{position}",
                    subject=self.aliases.get(review.subject, ""),
                    reviewer=review.reviewer,
                    outcome=review.disposition,
                    rationale=review.rationale,
                    selections=(),
                    inherited_from=self.namespace,
                )
            )


def import_collection(corpus: Corpus, root: Path, *, expected: str) -> MigrationReceipt:
    """Import and account a bounded legacy collection into one coherent fabric commit.

    Returns:
        The committed migration accounting, including remaining raw-lane import work.

    """
    importer = LegacyImporter(root)
    importer.acquire()
    counts = importer.archive_families()
    importer.interfaces()
    importer.reviews()
    importer.add(
        Job(
            logical_id=f"migration:{importer.namespace}",
            stage="legacy-collection-import",
            request=importer.namespace,
            inputs=(),
            universes=(),
            outputs=tuple(importer.rows),
            disposition=Disposition.PARTIAL,
            reason="Bindings, selected evidence, all family records, and reviews imported; native shard acquisition pending",
        )
    )
    manifest = Coordinator(
        corpus, WriterIdentity(principal="legacy-import", role="migration")
    ).commit(
        importer.rows.values(),
        expected=expected,
    )
    return MigrationReceipt(
        source_digest=importer.namespace,
        manifest=manifest,
        legacy_families=counts,
        admitted_families=tuple(
            sorted(Counter(codec_for(item).family for item in importer.rows.values()).items())
        ),
        limitations=(
            "Native fact shards and snapshot files require the lane importer before full-scope cutover",
        ),
    )
