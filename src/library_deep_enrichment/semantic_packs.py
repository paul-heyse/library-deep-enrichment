"""Data-authored vocabulary, rule, task, and transition packs with explicit approvals."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import frozen

from library_deep_enrichment.application import admit
from library_deep_enrichment.corpus.backend import BudgetExceededError, CorpusError
from library_deep_enrichment.corpus.contracts import Policy, Record, SourceFile
from library_deep_enrichment.corpus.encoding import CONVERTER, bytes_digest
from library_deep_enrichment.corpus.schemas import REGISTRY, codec_for, revision_of
from library_deep_enrichment.corpus.staging import ObservationBuilder
from library_deep_enrichment.semantics.enrichment_contracts import (
    TransferMapping,
    TransferModel,
    WitnessRecipe,
)
from library_deep_enrichment.semantics.vocabulary import approve_rules

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus, CorpusReader

PACK_FAMILIES = frozenset(
    {
        "predicates",
        "rules",
        "capability_schemas",
        "expressions",
        "tasks",
        "transfer_models",
        "transfer_mappings",
        "witness_recipes",
        "preference_policies",
    }
)
MAX_PACK_BYTES = 4 * 1024 * 1024
MAX_PACK_RECORDS = 2000
PACK_CONVERTER = CONVERTER.copy()
# The JSON envelope is retained only until references are resolved. Every
# resulting record then passes the ordinary strict family codec; the corpus
# converter itself never accepts opaque object fields.
PACK_CONVERTER.register_structure_hook_func(lambda kind: kind is object, lambda value, _: value)


@frozen(kw_only=True)
class PackRow:
    """A typed family envelope around a declaration awaiting reference resolution."""

    family: str
    record: dict[str, object]


@frozen(kw_only=True)
class PackDocument:
    """The finite external authoring format; extra fields are rejected."""

    schema: str
    rationale: str
    records: tuple[PackRow, ...]


@frozen(kw_only=True)
class PackReceipt:
    """Account for models, operation-specific mappings, and the selected authority route."""

    manifest: str
    source_digest: str
    families: tuple[tuple[str, int], ...]
    operation_mappings: int
    approved: bool


class PackLoader:
    """Resolve a finite topological pack into exact record revisions and owned assets."""

    def __init__(self, source: Path, reader: CorpusReader) -> None:
        """Pin the pack root and corpus selection before resolving references."""
        self.root = source.parent.resolve()
        self.reader = reader
        self.builder = ObservationBuilder("semantic-pack-import.v1")
        self.aliases: dict[str, str] = {}

    def resolve(self, value: object) -> object:
        """Resolve explicit references without evaluating strings or invoking a model.

        Returns:
            A plain typed-boundary value with exact current or pack-local revisions.

        """
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, dict):
            if set(value) == {"$ref"}:
                return self.aliases[str(value["$ref"])]
            if set(value) == {"$lookup"}:
                return self._lookup(value["$lookup"])
            if set(value) == {"$asset"}:
                return self._asset(value["$asset"])
            return {str(key): self.resolve(item) for key, item in value.items()}
        return value

    def _lookup(self, query: object) -> str:
        if not isinstance(query, dict) or set(query) != {"family", "logical_id", "profile"}:
            message = "pack lookups require family, logical_id, and exact profile"
            raise CorpusError(message)
        record = self.reader.lookup(
            str(query["family"]), str(query["logical_id"]), str(query["profile"])
        )
        if record is None:
            message = "pack lookup has no current exact contextual record"
            raise CorpusError(message)
        return revision_of(record)

    def _asset(self, value: object) -> object:
        if not isinstance(value, dict) or set(value) != {"path", "media_type"}:
            message = "a pack asset requires a path and media_type"
            raise CorpusError(message)
        path = (self.root / str(value["path"])).resolve()
        if not path.is_relative_to(self.root) or path.stat().st_size > MAX_PACK_BYTES:
            message = "pack asset escapes its root or exceeds the source byte budget"
            raise CorpusError(message)
        return CONVERTER.unstructure(
            self.builder.own_bytes(path.read_bytes(), media_type=str(value["media_type"]))
        )

    def records(self, rows: tuple[PackRow, ...]) -> tuple[Record, ...]:
        """Structure every declaration with the single registered attrs/cattrs contract.

        Returns:
            Source records in declared dependency order; duplicate aliases are rejected.

        Raises:
            CorpusError: A pack requests an unsupported family or duplicate logical alias.

        """
        result: list[Record] = []
        for row in rows:
            if row.family not in PACK_FAMILIES:
                message = "pack rows require one allowed family and one exact typed record"
                raise CorpusError(message)
            codec = REGISTRY[row.family]
            record = CONVERTER.structure(self.resolve(row.record), codec.record_type)
            if record.logical_id in self.aliases:
                message = "pack-local logical aliases must be unique"
                raise CorpusError(message)
            self.aliases[record.logical_id] = self.builder.add(record)
            result.append(record)
        return tuple(result)


def _approvals(records: tuple[Record, ...], authority: str, rationale: str) -> tuple[Policy, ...]:
    kinds: dict[type[Record], str] = {
        TransferModel: "transfer-model-approval",
        TransferMapping: "transfer-mapping-approval",
        WitnessRecipe: "witness-recipe-approval",
    }
    extra = tuple(
        Policy(
            logical_id=f"approval:{record.logical_id}",
            kind=kinds[type(record)],
            subject=revision_of(record),
            authority=authority,
            rationale=rationale,
            allowed_predicates=(),
            required_scopes=(),
        )
        for record in records
        if type(record) in kinds
    )
    return (*approve_rules(records, authority=authority, rationale=rationale), *extra)


def install(corpus: Corpus, source: Path, *, authority: str, approve: bool = False) -> PackReceipt:
    """Admit a pack as candidate models or explicitly attributed approved models.

    Returns:
        The current manifest and concrete reuse/override accounting.

    Raises:
        CorpusError: The pack format or approval rationale is missing.
        BudgetExceededError: The package exceeds finite source or record boundaries.

    """
    if source.stat().st_size > MAX_PACK_BYTES:
        message = "semantic pack exceeds its source byte boundary"
        raise BudgetExceededError(message)
    original = source.read_bytes()
    data = PACK_CONVERTER.structure(json.loads(original), PackDocument)
    if data.schema != "library-guides.semantic-pack.v1" or not data.rationale.strip():
        message = "a semantic pack requires schema, rationale, and ordered records"
        raise CorpusError(message)
    if len(data.records) > MAX_PACK_RECORDS:
        message = "semantic pack exceeds its finite model inventory"
        raise BudgetExceededError(message)
    reader = corpus.reader()
    loader = PackLoader(source, reader)
    records = loader.records(data.records)
    approvals = _approvals(records, authority, data.rationale) if approve else ()
    interval = loader.builder.own_bytes(original, media_type="application/json")
    loader.builder.add(
        SourceFile(
            logical_id=f"semantic-pack:{bytes_digest(original)}",
            blob=interval.blob,
            package="",
            path=source.name,
            locator="authoring-pack",
            license="project-authored",
            acquisition=f"author:{authority}",
        )
    )
    manifest = admit(
        corpus,
        (*loader.builder.records.values(), *approvals),
        authority=authority,
        role="policy" if approve else "producer",
        expected=reader.manifest_id,
    )
    return PackReceipt(
        manifest=manifest,
        source_digest=bytes_digest(original),
        families=tuple(sorted(Counter(codec_for(item).family for item in records).items())),
        operation_mappings=sum(isinstance(item, TransferMapping) for item in records),
        approved=approve,
    )
