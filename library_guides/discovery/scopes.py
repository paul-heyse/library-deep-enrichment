"""Exact contextual discovery populations within the shared admitted corpus."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.contracts import Disposition, Operation, Scope
from library_guides.corpus.encoding import digest
from library_guides.corpus.evidence import select
from library_guides.corpus.native_contracts import NativeFact
from library_guides.corpus.schemas import revision_of
from library_guides.discovery.contracts import DiscoveryScope, RetrievalUnit

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.store import CorpusReader

MAX_SCOPE_UNITS = 10_000


def prefix(scope: DiscoveryScope | None) -> str:
    """Return an output namespace independent of selector revision.

    Returns:
        A stable namespace that prevents different stages from owning the same unit.

    """
    return "retrieval:" if scope is None else f"scoped-retrieval:{digest(scope.logical_id)}:"


def operations(reader: CorpusReader, scope: DiscoveryScope) -> tuple[Operation, ...]:
    """Enumerate every matching operation or reject an oversized finite scope.

    Returns:
        Exact operation revisions; source selectors match native evidence ownership.

    Raises:
        BudgetExceededError: The complete matching population exceeds the declared bound.

    """
    result = []
    for record in reader.records("operations"):
        if not isinstance(record, Operation) or (
            (scope.profiles and record.profile not in scope.profiles)
            or (scope.packages and record.package not in scope.packages)
        ):
            continue
        if scope.artifacts:
            facts = reader.get_many(
                "native_facts",
                (item.revision for item in record.evidence if item.family == "native_facts"),
            )
            if not any(
                isinstance(fact, NativeFact) and fact.artifact in scope.artifacts for fact in facts
            ):
                continue
        result.append(record)
        if len(result) > scope.max_units:
            message = f"discovery scope {scope.logical_id} exceeds its {scope.max_units} unit bound"
            raise BudgetExceededError(message)
    return tuple(sorted(result, key=revision_of))


def population(reader: CorpusReader, scope: DiscoveryScope) -> Scope:
    """Resolve the selector against the independent current interface population.

    Returns:
        A finite universe with exact selector and operation evidence.

    """
    members = operations(reader, scope)
    return Scope(
        logical_id=f"discovery-population:{scope.logical_id}",
        owner="scoped-operation-discovery",
        query=revision_of(scope),
        members=tuple(revision_of(item) for item in members),
        sources=(
            select(scope, "/profiles", "discovery-selector"),
            select(scope, "/packages", "discovery-selector"),
            select(scope, "/artifacts", "discovery-selector"),
            *(select(item, "/signature", "discovery-population") for item in members),
        ),
        disposition=Disposition.COMPLETE,
        frontier=(
            "Exact for the declared admitted interface selection; not a proof of behavioral equivalence or upstream completeness",
        ),
    )


def current(reader: CorpusReader, scope: DiscoveryScope) -> Scope:
    """Require an admitted, current population before consuming scoped products.

    Returns:
        The exact retained population receipt.

    Raises:
        CorpusError: The selector or population is stale or has not been built.

    """
    if reader.get("discovery_scopes", revision_of(scope)) != scope:
        message = "discovery selector differs from the admitted revision"
        raise CorpusError(message)
    retained = next(
        (
            record
            for record in reader.records("scopes")
            if record.logical_id == f"discovery-population:{scope.logical_id}"
        ),
        None,
    )
    if not isinstance(retained, Scope) or retained.query != revision_of(scope):
        message = "build retrieval for this exact discovery scope first"
        raise CorpusError(message)
    return retained


def units(reader: CorpusReader, scope: DiscoveryScope | None = None) -> Iterator[RetrievalUnit]:
    """Select one explicit output population without merging overlapping scope namespaces.

    Yields:
        Every included source unit with a checked independent denominator.

    Raises:
        CorpusError: Stored units do not cover the exact declared operation population.

    """
    expected = set(current(reader, scope).members) if scope is not None else None
    seen: set[str] = set()
    namespace = prefix(scope)
    for record in reader.records("retrieval_units"):
        if isinstance(record, RetrievalUnit) and record.logical_id.startswith(namespace):
            if expected is not None and (record.subject not in expected or record.subject in seen):
                message = "scoped retrieval has an unexpected or duplicated operation"
                raise CorpusError(message)
            seen.add(record.subject)
            yield record
    if expected is not None and seen != expected:
        message = "scoped retrieval is incomplete; rebuild its selected population"
        raise CorpusError(message)
