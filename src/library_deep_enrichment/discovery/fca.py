"""Exact bounded FCA over qualified observed support, preserving open-world meaning."""

from __future__ import annotations

from itertools import islice
from typing import TYPE_CHECKING

from attrs import frozen
from fcapy.algorithms.concept_construction import close_by_one
from fcapy.context import FormalContext

from library_deep_enrichment.corpus.backend import BudgetExceededError
from library_deep_enrichment.corpus.contracts import Disposition, Operation, Scope
from library_deep_enrichment.corpus.encoding import CONVERTER, digest
from library_deep_enrichment.corpus.evidence import select
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.discovery.contracts import Attribute, Concept
from library_deep_enrichment.discovery.scopes import operations
from library_deep_enrichment.semantics.contracts import State
from library_deep_enrichment.semantics.realization import qualified_assertions

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_deep_enrichment.corpus.contracts import Record, Selection
    from library_deep_enrichment.corpus.store import CorpusReader
    from library_deep_enrichment.discovery.contracts import DiscoveryScope


@frozen(kw_only=True)
class SupportContext:
    """The finite positive incidence relation; false cells mean no admitted positive support."""

    objects: tuple[str, ...]
    attributes: tuple[Attribute, ...]
    support: tuple[Selection, ...]
    matrix: tuple[tuple[bool, ...], ...]
    namespace: str = ""
    selection: str = ""

    def formal(self) -> FormalContext:
        """Create a bounded FCApy object without assigning truth to missing evidence.

        Returns:
            The exact observed-support incidence context.

        """
        return FormalContext(
            data=[list(row) for row in self.matrix],
            object_names=list(self.objects),
            attribute_names=[revision_of(item) for item in self.attributes],
        )

    def closure(self, attributes: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Compute a demand-driven support closure without constructing the whole lattice.

        Returns:
            Exact extent and closed intent under this recorded support matrix.

        """
        names = tuple(revision_of(item) for item in self.attributes)
        selected = [names.index(name) for name in attributes]
        if not self.attributes:
            return self.objects, ()
        context = self.formal()
        extent = tuple(context.extension_i(selected))
        intent = tuple(context.intention_i(extent))
        return tuple(self.objects[index] for index in extent), tuple(
            names[index] for index in intent
        )


def support_context(
    reader: CorpusReader,
    *,
    profiles: tuple[str, ...] = (),
    max_cells: int = 2_000_000,
    scope: DiscoveryScope | None = None,
) -> SupportContext:
    """Assess positive support classes before applying mathematical closure.

    Returns:
        Incidence containing qualified supported assertions only, with exact qualifiers.

    Raises:
        BudgetExceededError: The object/attribute matrix would exceed its declared boundary.

    """
    selected = reader.records("operations") if scope is None else operations(reader, scope)
    namespace = "" if scope is None else f"scoped:{digest(scope.logical_id)}:"
    objects = tuple(
        sorted(
            revision_of(item)
            for item in selected
            if isinstance(item, Operation) and (not profiles or item.profile in profiles)
        )
    )
    allowed = set(objects)
    attributes: dict[str, Attribute] = {}
    positives: set[tuple[str, str]] = set()
    support: list[Selection] = [] if scope is None else [select(scope, "/profiles", "fca-selector")]
    for assertion in qualified_assertions(reader):
        if assertion.subject not in allowed or assertion.state != State.SUPPORTED:
            continue
        values = {
            "predicate": assertion.predicate,
            "value_digest": digest(CONVERTER.unstructure(assertion.value)),
            "condition": assertion.condition,
            "interpretation": str(assertion.interpretation),
            "quantifier": assertion.quantifier,
            "domain": assertion.domain,
            "phase": assertion.phase,
        }
        attribute = Attribute(logical_id=f"{namespace}attribute:{digest(values)}", **values)
        key = revision_of(attribute)
        attributes[key] = attribute
        positives.add((assertion.subject, key))
        support.append(select(assertion, "/state", "qualified-positive-incidence"))
        if len(objects) * len(attributes) > max_cells:
            message = "FCA support projection exceeded its explicit cell budget"
            raise BudgetExceededError(message)
    names = sorted(attributes)
    return SupportContext(
        objects=objects,
        attributes=tuple(attributes[name] for name in names),
        support=tuple(sorted(support, key=lambda item: (item.family, item.revision, item.field))),
        matrix=tuple(tuple((obj, name) in positives for name in names) for obj in objects),
        namespace=namespace,
        selection="" if scope is None else revision_of(scope),
    )


def concepts(context: SupportContext, *, max_concepts: int = 256) -> Iterator[Record]:
    """Enumerate a bounded exact support lattice with an honest truncation disposition.

    Yields:
        Attribute classes, a finite scope receipt, and support conjunction concepts.

    """
    yield from context.attributes
    enumerated = (
        list(islice(close_by_one(context.formal()), max_concepts + 1))
        if context.objects and context.attributes
        else []
    )
    truncated = len(enumerated) > max_concepts
    scope = Scope(
        logical_id=f"{context.namespace}fca-scope:{digest(context.objects)}",
        owner="positive-support-context",
        query="qualified-supported-incidence"
        + (f":{context.selection}" if context.selection else ""),
        members=context.objects,
        sources=context.support,
        disposition=Disposition.PARTIAL if truncated else Disposition.COMPLETE,
        frontier=(
            "Missing cells mean no qualified positive support, never semantic false",
            *(
                ["Concept enumeration reached its bound; closure queries remain exact"]
                if truncated
                else []
            ),
        ),
    )
    yield scope
    names = [revision_of(item) for item in context.attributes]
    recipe = digest(["fcapy-close-by-one.v1", context.objects, names, context.matrix, max_concepts])
    for item in enumerated[:max_concepts]:
        members = tuple(sorted(context.objects[int(index)] for index in item.extent_i))
        attributes = tuple(sorted(names[int(index)] for index in item.intent_i))
        yield Concept(
            logical_id=f"{context.namespace}support-concept:{digest([members, attributes])}",
            kind="observed-support-conjunction",
            scope=revision_of(scope),
            members=members,
            attributes=attributes,
            recipe=recipe,
            support=(),
            frontier=scope.frontier,
        )
