"""Independent checks that normalized declaration fields match their retained source selections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import (
    LegacyRecord,
    Operation,
    RegistryEntry,
    RegistryProperty,
    TypeUse,
)
from library_guides.corpus.evidence import resolve
from library_guides.corpus.native_contracts import NativeFact
from library_guides.corpus.python_interfaces import validate as validate_python_interface

if TYPE_CHECKING:
    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader


def _nominal(reader: CorpusReader, record: TypeUse) -> None:
    expected: dict[str, object] = {
        "role": record.role,
        "position": record.position,
        "direct": record.direct,
        "selector": record.selector,
    }
    if record.resolution == "exact":
        expected["resolved_symbol"] = record.nominal
    found: set[str] = set()
    for evidence in record.evidence:
        key = evidence.field.rsplit("/", 1)[-1]
        if key in expected:
            if resolve(reader, evidence) != expected[key]:
                message = f"normalized nominal occurrence differs from its source field: {key}"
                raise CorpusError(message)
            found.add(key)
        source = reader.get(evidence.family, evidence.revision)
        if (
            isinstance(source, (LegacyRecord, NativeFact))
            and source.artifact != record.nominal_scope
        ):
            message = "nominal resolution escaped its original artifact scope"
            raise CorpusError(message)
        if isinstance(source, (LegacyRecord, NativeFact)):
            owner = reader.get("operations", record.owner)
            if not isinstance(owner, Operation) or not any(
                item.family == evidence.family and item.revision == evidence.revision
                for item in owner.evidence
            ):
                message = "nominal occurrence was attached to a different declaration owner"
                raise CorpusError(message)
    if record.resolution == "exact" and not set(expected) <= found:
        message = "exact nominal occurrence lacks the source fields needed to verify its roles"
        raise CorpusError(message)


def _signature(reader: CorpusReader, operation: Operation) -> None:
    for evidence in operation.evidence:
        if (
            evidence.field.endswith("/signature")
            and isinstance(value := resolve(reader, evidence), str)
            and value != operation.signature
        ):
            message = "normalized callable signature differs from its original declaration"
            raise CorpusError(message)


def _property(reader: CorpusReader, record: RegistryProperty) -> None:
    values = [
        resolve(reader, selection)
        for selection in record.evidence
        if selection.field.rsplit("/", 1)[-1] in {"value", record.name}
    ]
    if not values:
        message = "registry property has no exact source value selection"
        raise CorpusError(message)
    value = values[0] if all(item == values[0] for item in values) else None
    text = "" if value is None else str(value).lower() if type(value) is bool else str(value)
    kind = "null" if value is None else "boolean" if type(value) is bool else "text"
    if record.value_text != text or record.value_kind != kind:
        message = "registry property differs from its exact nullable source declaration"
        raise CorpusError(message)


def _registry_entry(reader: CorpusReader, record: RegistryEntry) -> None:
    kinds: list[object] = []
    for selection in record.evidence:
        key = selection.field.rsplit("/", 1)[-1]
        if key == "kind":
            kinds.append(resolve(reader, selection))
        elif "/routines/" in selection.field:
            value = resolve(reader, selection)
            if isinstance(value, dict) and "function_type" in value:
                kinds.append(value["function_type"])
    common = kinds[0] if kinds and all(item == kinds[0] for item in kinds) else None
    if not kinds or str(common or "unknown") != record.kind:
        message = "registry function kind differs from the original observed catalog rows"
        raise CorpusError(message)


def validate(reader: CorpusReader, record: Record) -> None:
    """Recheck normalization without trusting a valid citation to entail an arbitrary field."""
    if isinstance(record, TypeUse):
        _nominal(reader, record)
    elif isinstance(record, Operation):
        _signature(reader, record)
        validate_python_interface(reader, record)
    elif isinstance(record, RegistryEntry):
        _registry_entry(reader, record)
    elif isinstance(record, RegistryProperty):
        _property(reader, record)
