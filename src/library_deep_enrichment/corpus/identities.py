"""Contextual source identity joins that never merge artifacts by spelling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import frozen

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Entity, Operation, Record, Selection
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.evidence import select
from library_deep_enrichment.corpus.native_contracts import NativeArtifact, NativeFact
from library_deep_enrichment.corpus.schemas import SELECTIONS, TEXTS, fields, register, revision_of

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader


@frozen(kw_only=True)
class ContextualIdentity(Record):
    """An interface's exact source identity or an explicit unresolved source mapping."""

    family: str
    subject: str
    source_facts: tuple[str, ...]
    contexts: tuple[str, ...]
    identities: tuple[str, ...]
    resolution: str
    frontier: tuple[str, ...]
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class IdentityJoin(Record):
    """A checked comparison of contextual source identities, separate from runtime dispatch."""

    left: str
    right: str
    resolution: str
    frontier: tuple[str, ...]


register(
    "contextual_identities",
    ContextualIdentity,
    [
        *fields("family", "subject"),
        ("source_facts", TEXTS),
        ("contexts", TEXTS),
        ("identities", TEXTS),
        *fields("resolution"),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
    ],
)
register(
    "identity_joins",
    IdentityJoin,
    [*fields("left", "right", "resolution"), ("frontier", TEXTS)],
)


def identify(reader: CorpusReader, family: str, subject: str) -> ContextualIdentity:
    """Resolve only exact retained native ownership, never display-name equality.

    Returns:
        A versioned contextual identity with source-versus-runtime limits.

    Raises:
        CorpusError: The subject is not a supported native/interface family.

    """
    record = reader.get(family, subject)
    if family not in {"operations", "entities", "native_facts"} or not isinstance(
        record, (Operation, Entity, NativeFact)
    ):
        message = "contextual identity requires an interface or native fact"
        raise CorpusError(message)
    origins = (
        (subject,)
        if isinstance(record, NativeFact)
        else tuple(
            sorted(
                {
                    item.revision
                    for item in record.evidence
                    if item.family == "native_facts" and item.role == "declaration"
                }
            )
        )
    )
    contexts, identities, support = [], [], []
    for fact in reader.get_many("native_facts", origins):
        if not isinstance(fact, NativeFact):
            message = "identity source is not a native fact"
            raise CorpusError(message)
        artifact = reader.get("native_artifacts", fact.artifact)
        if not isinstance(artifact, NativeArtifact) or artifact.profile != record.profile:
            message = "identity source escaped its exact observation profile"
            raise CorpusError(message)
        contexts.append(artifact.context)
        identities.append(
            digest(["contextual-native.v1", fact.artifact, artifact.context, fact.native_id])
        )
        support.extend(
            (
                select(fact, "/native_id", "local-identity"),
                select(artifact, "/context", "identity-context"),
            )
        )
    resolution = (
        "exact-source" if len(identities) == 1 else "ambiguous" if identities else "unresolved"
    )
    return ContextualIdentity(
        logical_id=f"contextual-identity:{family}:{subject}",
        profile=record.profile,
        family=family,
        subject=subject,
        source_facts=origins,
        contexts=tuple(contexts),
        identities=tuple(identities),
        resolution=resolution,
        frontier=(
            "Source identity does not establish public invocation, compiled availability, runtime dispatch, or cross-language equivalence",
        ),
        support=tuple(support),
    )


def join(left: ContextualIdentity, right: ContextualIdentity) -> IdentityJoin:
    """Compare source identities without promoting same-name or same-file candidates.

    Returns:
        Exact source equality, an ambiguous overlap, or an explicitly unresolved cross-context join.

    """
    common = set(left.identities) & set(right.identities)
    resolution = (
        "exact-source"
        if left.resolution == right.resolution == "exact-source" and common
        else "ambiguous"
        if common
        else "unresolved"
    )
    return IdentityJoin(
        logical_id=f"identity-join:{revision_of(left)}:{revision_of(right)}",
        left=revision_of(left),
        right=revision_of(right),
        resolution=resolution,
        frontier=(
            "Different artifacts, rustdoc item-ID universes, compiler units, stub/runtime roles and environments require an independently evidenced bridge",
        ),
    )


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Return exact source/context prerequisites for portable resolution replay.

    Returns:
        Typed dependencies; no display name acts as a foreign key.

    """
    if isinstance(record, ContextualIdentity):
        return (
            (record.family, record.subject),
            *(("native_facts", value) for value in record.source_facts),
            *(("contexts", value) for value in record.contexts),
        )
    if isinstance(record, IdentityJoin):
        return (("contextual_identities", record.left), ("contextual_identities", record.right))
    return ()


def validate(reader: CorpusReader, record: Record) -> None:
    """Replay contextual resolution before admission, including unresolved boundaries.

    Raises:
        CorpusError: A proposed identity or join invents equivalence or changes its context.

    """
    if isinstance(record, ContextualIdentity):
        expected = identify(reader, record.family, record.subject)
    elif isinstance(record, IdentityJoin):
        left = reader.get("contextual_identities", record.left)
        right = reader.get("contextual_identities", record.right)
        if not isinstance(left, ContextualIdentity) or not isinstance(right, ContextualIdentity):
            message = "identity join requires contextual identities"
            raise CorpusError(message)
        expected = join(left, right)
    else:
        return
    if record != expected:
        message = "contextual identity differs from exact source and context replay"
        raise CorpusError(message)
