"""Producer-owned finite staging without any persistent table-writing capability."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from library_guides.corpus.backend import BudgetExceededError
from library_guides.corpus.contracts import ByteRange, RawObservation, Record, Selection
from library_guides.corpus.encoding import bytes_digest, canonical, digest
from library_guides.corpus.evidence import field_value, stage_blob
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from collections.abc import Mapping


class ObservationBuilder:
    """Stage normalized family records and their exact original producer observations."""

    def __init__(self, producer: str, *, max_records: int = 100_000) -> None:
        """Bind an extractor revision and an explicit finite record boundary."""
        self.producer = producer
        self.max_records = max_records
        self.records: dict[str, Record] = {}
        self.observations: dict[str, Mapping[str, object]] = {}

    def add(self, record: Record) -> str:
        """Stage an immutable revision without access to corpus tables.

        Returns:
            The application content identifier.

        Raises:
            BudgetExceededError: The staged record inventory exceeds its declared bound.

        """
        if len(self.records) >= self.max_records:
            message = f"producer staging exceeds {self.max_records} records"
            raise BudgetExceededError(message)
        revision = revision_of(record)
        self.records[revision] = record
        return revision

    def own_bytes(self, value: bytes, *, media_type: str) -> ByteRange:
        """Retain exact captured bytes as a managed source object.

        Returns:
            A portable original-byte selection.

        """
        blob, chunks = stage_blob(io.BytesIO(value), media_type=media_type)
        for chunk in chunks:
            self.add(chunk)
        revision = self.add(blob)
        return ByteRange(blob=revision, start=0, end=len(value), digest=bytes_digest(value))

    def observe(
        self,
        identifier: str,
        data: Mapping[str, object],
        *,
        profile: str,
        kind: str,
        context: str = "",
    ) -> RawObservation:
        """Capture an original structured producer observation before normalization.

        Returns:
            The immutable observation record and its retained source bytes.

        """
        observation = RawObservation(
            logical_id=identifier,
            profile=profile,
            producer=self.producer,
            kind=kind,
            context=context,
            original=self.own_bytes(canonical(data), media_type="application/json"),
        )
        revision = self.add(observation)
        self.observations[revision] = data
        return observation

    def select(self, observation: RawObservation, field: str, role: str) -> Selection:
        """Select one exact observed field for a typed normalization or rule premise.

        Returns:
            A logical field/value selection checked again at admission and use.

        """
        revision = revision_of(observation)
        value = field_value(self.observations[revision], field)
        return Selection(
            family="raw_observations",
            revision=revision,
            field=f"/raw{field}",
            digest=digest(value),
            role=role,
        )
