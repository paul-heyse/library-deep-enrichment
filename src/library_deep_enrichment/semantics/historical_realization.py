"""Generate operation modes and capabilities from qualified computational assertions."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.contracts import Disposition, Operation, Qualification
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.semantics.contracts import Assertion, Capability, Mode, Predicate, Slot

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_deep_enrichment.corpus.store import CorpusReader


def qualified_assertions(reader: CorpusReader) -> tuple[Assertion, ...]:
    """Select exact assertion revisions carrying successful consequence receipts.

    Returns:
        Admitted and qualified assertions only; candidate rule output remains separate.

    """
    allowed = {
        item.subject
        for item in reader.records("qualifications")
        if isinstance(item, Qualification) and item.disposition == Disposition.COMPLETE
    }
    return tuple(
        item
        for item in reader.records("assertions")
        if isinstance(item, Assertion) and revision_of(item) in allowed
    )


def realize(reader: CorpusReader) -> Iterator[Mode | Capability]:
    """Build reusable result-consumption capabilities without per-operation cards.

    Yields:
        Default operation modes and assertion-backed capability mappings.

    """
    predicates = {
        revision_of(item): item
        for item in reader.records("predicates")
        if isinstance(item, Predicate)
    }
    assertions: dict[str, list[Assertion]] = defaultdict(list)
    for assertion in qualified_assertions(reader):
        assertions[assertion.subject].append(assertion)
    for operation in reader.records("operations"):
        if not isinstance(operation, Operation):
            continue
        operation_revision = revision_of(operation)
        supported = assertions.get(operation_revision, [])
        if not supported:
            continue
        revisions = tuple(sorted(revision_of(item) for item in supported))
        mode = Mode(
            logical_id=f"mode:{operation.logical_id}:default",
            profile=operation.profile,
            operation=operation_revision,
            condition="",
            bindings=(),
            assertions=revisions,
            label=f"{operation.symbol} default contract",
        )
        yield mode
        delivery = [
            item
            for item in supported
            if predicates[item.predicate].name == "documented_result_delivery"
        ]
        operation_classes = [
            item.value.text
            for item in supported
            if predicates[item.predicate].name == "documented_operation_class"
        ]
        schema = (
            "consume-results"
            if delivery
            else operation_classes[0]
            if operation_classes
            else "declared-operation"
        )
        yield Capability(
            logical_id=f"capability:{operation.logical_id}:{schema}",
            profile=operation.profile,
            schema=schema,
            operation=operation_revision,
            mode=revision_of(mode),
            inputs=tuple(
                Slot(
                    role=arg.name,
                    type_expression=arg.type_expression,
                    representation="unknown",
                    resource="",
                    consumes=False,
                )
                for arg in operation.parameters
                if arg.required
            ),
            outputs=(
                Slot(
                    role="result",
                    type_expression=operation.returns,
                    representation="unknown",
                    resource="",
                    consumes=False,
                ),
            ),
            assertions=revisions,
            condition="",
            label=f"{schema}: {operation.symbol}",
        )
