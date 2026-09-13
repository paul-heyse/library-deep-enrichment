"""Generate guarded modes and reusable capabilities from qualified computational assertions."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from library_guides.corpus.contracts import Disposition, Operation, Policy, Qualification
from library_guides.corpus.schemas import revision_of
from library_guides.semantics.contracts import (
    Assertion,
    Capability,
    CapabilitySchema,
    Mode,
    Slot,
    State,
)
from library_guides.semantics.type_shapes import OperationShape

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.store import CorpusReader


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


def _schemas(
    assertions: list[Assertion], definitions: tuple[CapabilitySchema, ...]
) -> tuple[str, ...]:
    matching = []
    for schema in definitions:
        if schema.any_qualified_support:
            continue
        if schema.requirements and all(
            any(
                item.predicate == requirement.predicate
                and item.interpretation in requirement.interpretations
                and item.state == State.SUPPORTED
                and (
                    requirement.operator == "exists"
                    or (requirement.operator == "equal" and item.value == requirement.value)
                )
                for item in assertions
            )
            for requirement in schema.requirements
        ):
            matching.append(schema.name)
    if not matching and assertions:
        matching.extend(schema.name for schema in definitions if schema.any_qualified_support)
    return tuple(sorted(matching))


def _capabilities(
    operation: Operation,
    supported: list[Assertion],
    definitions: tuple[CapabilitySchema, ...],
    condition: str,
    shape: OperationShape | None = None,
) -> Iterator[Mode | Capability]:
    revisions = tuple(sorted(revision_of(item) for item in supported))
    key = condition or "default"
    mode = Mode(
        logical_id=f"mode:{operation.logical_id}:{key}",
        profile=operation.profile,
        operation=revision_of(operation),
        condition=condition,
        bindings=(),
        assertions=revisions,
        label=f"{operation.symbol} {'guarded' if condition else 'default'} contract",
    )
    yield mode
    for schema in _schemas(supported, definitions):
        yield Capability(
            logical_id=f"capability:{operation.logical_id}:{schema}:{key}",
            profile=operation.profile,
            schema=schema,
            operation=revision_of(operation),
            mode=revision_of(mode),
            inputs=shape.inputs
            if shape is not None
            else tuple(
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
            outputs=shape.outputs
            if shape is not None
            else (
                Slot(
                    role="result",
                    type_expression=operation.returns,
                    representation="unknown",
                    resource="",
                    consumes=False,
                ),
            ),
            assertions=revisions,
            condition=condition,
            label=f"{schema}: {operation.symbol}",
        )


def realize(reader: CorpusReader) -> Iterator[Mode | Capability]:
    """Preserve applicability guards when realizing reusable capability schemas.

    Yields:
        Modes and mappings without strengthening conditional assertions to unconditional ones.

    """
    approved = {
        item.subject
        for item in reader.records("policies")
        if isinstance(item, Policy) and item.kind == "schema-approval"
    }
    definitions = tuple(
        item
        for item in reader.records("capability_schemas")
        if isinstance(item, CapabilitySchema) and revision_of(item) in approved
    )
    assertions: dict[str, list[Assertion]] = defaultdict(list)
    shapes = {
        item.operation: item
        for item in reader.records("operation_shapes")
        if isinstance(item, OperationShape)
    }
    for assertion in qualified_assertions(reader):
        assertions[assertion.subject].append(assertion)
    for operation in reader.records("operations"):
        if not isinstance(operation, Operation):
            continue
        supported = assertions.get(revision_of(operation), [])
        common = [item for item in supported if not item.condition]
        for condition in sorted({item.condition for item in supported}):
            selected = common + [
                item for item in supported if condition and item.condition == condition
            ]
            yield from _capabilities(
                operation, selected, definitions, condition, shapes.get(revision_of(operation))
            )
