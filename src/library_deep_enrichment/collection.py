"""Load, validate and fingerprint a complete evidence-backed collection."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from attrs import asdict
from cattrs import Converter
from jsonschema.exceptions import ValidationError

from library_deep_enrichment.knowledge import (
    Binding,
    Capability,
    Claim,
    Decision,
    Evidence,
    Integration,
    Knowledge,
    Review,
)
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.schemas import validate_document
from library_deep_enrichment.store.digests import canonical_bytes
from library_deep_enrichment.store.staging import write_atomic

type Subject = Binding | Capability | Claim | Decision | Integration

_CONVERTER = Converter(forbid_extra_keys=True)


class CollectionError(ValueError):
    """A collection is malformed, stale or insufficiently supported."""


def confined(root: Path, relative: str) -> Path:
    """Resolve a collection-owned path without allowing directory escape.

    Returns:
        A path confined to the collection root.

    Raises:
        CollectionError: If the path is absolute or escapes the root.

    """
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        message = f"path escapes collection: {relative}"
        raise CollectionError(message)
    return path


def load(root: Path) -> Knowledge:
    """Load the v2 authority, rejecting missing or unsupported input.

    Returns:
        The typed collection.

    Raises:
        CollectionError: If no valid collection is present.

    """
    path = root / "knowledge.yaml"
    if not path.is_file():
        message = f"no v2 collection at {path}; ingest sources or select a reviewed collection"
        raise CollectionError(message)
    raw = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    if not isinstance(raw, dict) or raw.get("schema_version") not in {
        "library-guides.knowledge.v2",
        "library-guides.knowledge.v3",
    }:
        message = f"unsupported knowledge schema at {path}"
        raise CollectionError(message)
    try:
        validate_document(raw)
    except ValidationError as error:
        message = f"invalid collection contract at {list(error.absolute_path)}: {error.message}"
        raise CollectionError(message) from error
    model = KnowledgeV3 if raw["schema_version"] == "library-guides.knowledge.v3" else Knowledge
    return _CONVERTER.structure(raw, model)


def save(root: Path, knowledge: Knowledge) -> None:
    """Persist reviewed authoring input using deterministic YAML."""
    text = yaml.dump(
        asdict(knowledge), Dumper=yaml.CSafeDumper, sort_keys=False, allow_unicode=True
    )
    write_atomic(root / "knowledge.yaml", text.encode())


def subjects(knowledge: Knowledge) -> dict[str, Subject]:
    """Index semantic owners, rejecting ambiguous identities.

    Returns:
        Subjects indexed by their unique identifier.

    Raises:
        CollectionError: If identifiers are duplicated.

    """
    result: dict[str, Subject] = {}
    for record in (
        *knowledge.bindings,
        *knowledge.claims,
        *knowledge.capabilities,
        *knowledge.decisions,
        *knowledge.integrations,
    ):
        if record.id in result:
            message = f"duplicate subject id: {record.id}"
            raise CollectionError(message)
        result[record.id] = record
    return result


def select(payload: bytes, selector: str) -> bytes:
    """Select exact text bytes or an RFC 6901 JSON value.

    Returns:
        Canonical selected bytes used by evidence digests.

    Raises:
        CollectionError: If the selector does not describe a valid location.

    """
    if selector.startswith("bytes:"):
        _, start, end = selector.split(":")
        left, right = int(start), int(end)
        if not 0 <= left < right <= len(payload):
            message = f"invalid byte selector: {selector}"
            raise CollectionError(message)
        return payload[left:right]
    if not selector.startswith("json:"):
        message = f"unsupported selector: {selector}"
        raise CollectionError(message)
    value = json.loads(payload)
    pointer = selector.removeprefix("json:")
    if pointer and not pointer.startswith("/"):
        message = f"invalid JSON pointer: {selector}"
        raise CollectionError(message)
    for encoded in pointer.split("/")[1:]:
        token = encoded.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return canonical_bytes(value)


def evidence_bytes(root: Path, knowledge: Knowledge, evidence: Evidence) -> bytes:
    """Read a concrete evidence selection from its owning artifact.

    Returns:
        Selected bytes; failures are never converted into empty evidence.

    """
    sources = {item.id: item for item in knowledge.sources}
    return select(confined(root, sources[evidence.source].path).read_bytes(), evidence.selector)


def dependencies(knowledge: Knowledge, record: Subject) -> tuple[str, ...]:
    """Return positive and candidate-set semantic dependencies.

    Returns:
        The identifiers that must be included in a review fingerprint.

    """
    universes = (
        tuple(d.universe for d in knowledge.universe_dependencies if d.subject == record.id)
        if isinstance(knowledge, KnowledgeV3)
        else ()
    )
    if isinstance(record, (Binding, Claim)):
        support = (
            tuple(item.id for item in knowledge.claim_support if item.claim == record.id)
            if isinstance(knowledge, KnowledgeV3) and isinstance(record, Claim)
            else ()
        )
        return (*record.evidence, *support, *universes)
    if isinstance(record, Capability):
        return (
            *universes,
            *record.claims,
            *record.bindings,
            *(realization.principle for realization in record.realizations),
            *(claim for realization in record.realizations for claim in realization.claims),
            *(claim for facet in record.facets for claim in facet.claims),
        )
    if isinstance(record, Integration):
        return (record.producer, record.consumer, *record.claims, *record.examples, *universes)
    candidates = tuple(
        item.id
        for item in knowledge.capabilities
        if item.family == record.family and item.profile == record.profile
    )
    bindings = tuple(
        item.id
        for item in knowledge.bindings
        if (record.family in item.families or not item.families) and item.profile == record.profile
    )
    return (
        *universes,
        *record.claims,
        *(c.capability for c in record.candidates),
        *(claim for c in record.candidates for claim in c.claims),
        *candidates,
        *bindings,
        *record.examples,
    )


def fingerprint(root: Path, knowledge: Knowledge, identifier: str) -> str:
    """Fingerprint actual selected evidence and the complete semantic closure.

    Returns:
        Content digest including competing candidates and their properties.

    """
    from library_deep_enrichment.evidence_graph import EvidenceGraph

    return EvidenceGraph(root, knowledge).fingerprint(identifier)


def review_current(root: Path, knowledge: Knowledge, review: Review) -> bool:
    """Check that acceptance applies to precisely the evidence now present.

    Returns:
        Whether this review authorizes the current subject.

    """
    from library_deep_enrichment.revalidation import equivalent

    current = fingerprint(root, knowledge, review.subject)
    refreshed = isinstance(knowledge, KnowledgeV3) and any(
        p.subject == review.subject
        and p.previous_digest == review.digest
        and p.current_digest == current
        and equivalent(root, knowledge, p)
        for p in knowledge.revalidations
    )
    return bool(
        review.reviewer.strip()
        and review.rationale.strip()
        and review.disposition == "accepted"
        and (review.digest == current or refreshed)
    )
