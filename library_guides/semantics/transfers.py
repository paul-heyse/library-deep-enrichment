"""Finite state propagation under separately approved operation mappings and models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import Policy
from library_guides.corpus.encoding import CONVERTER, digest
from library_guides.corpus.schemas import revision_of
from library_guides.semantics.conditions import check_condition
from library_guides.semantics.contracts import Assignment, Expression, State, Value, ValueKind
from library_guides.semantics.enrichment_contracts import (
    StateTransfer,
    TransferMapping,
    TransferModel,
    TransferRule,
)

if TYPE_CHECKING:
    from library_guides.corpus.store import CorpusReader

MAX_TRANSFER_RULES = 128
MAX_TRANSFER_INPUTS = 256


def _value(rule: TransferRule, known: dict[str, Value]) -> Value | None:
    if rule.operator == "constant" and not rule.inputs:
        return rule.value
    if rule.operator == "drop":
        return None
    values = [known.get(name) for name in rule.inputs]
    if not values or any(value is None for value in values):
        return None
    present = [value for value in values if value is not None]
    if rule.operator == "copy" and len(present) == 1:
        return present[0]
    if all(value.kind == ValueKind.INTEGER for value in present):
        numbers = [int(value.text) for value in present]
        reducers = {"sum": sum, "minimum": min, "maximum": max}
        if rule.operator in reducers:
            return Value(kind=ValueKind.INTEGER, text=str(reducers[rule.operator](numbers)))
    return None


def evaluate(
    reader: CorpusReader, mapping: TransferMapping, inputs: tuple[Assignment, ...]
) -> StateTransfer:
    """Apply only approved state transitions; no unspecified property flows automatically.

    Returns:
        A narrow modeled or finite witnessed transition with explicit unknowns.

    Raises:
        CorpusError: A mapping/model is unapproved or exceeds its finite boundary.

    """
    model = reader.get("transfer_models", mapping.model)
    if (
        not isinstance(model, TransferModel)
        or len(model.rules) > MAX_TRANSFER_RULES
        or len(inputs) > MAX_TRANSFER_INPUTS
    ):
        message = "invalid or oversized finite transfer model"
        raise CorpusError(message)
    approvals = {
        (policy.kind, policy.subject)
        for policy in reader.records("policies")
        if isinstance(policy, Policy)
    }
    if ("transfer-model-approval", revision_of(model)) not in approvals or (
        "transfer-mapping-approval",
        revision_of(mapping),
    ) not in approvals:
        message = "state transfer requires independent approval of both model and contextual library mapping"
        raise CorpusError(message)
    expressions = {
        revision_of(item): item
        for item in reader.records("expressions")
        if isinstance(item, Expression)
    }
    states = [
        check_condition(condition, expressions, inputs).state
        for condition in (model.condition, mapping.condition)
    ]
    state = (
        State.SUPPORTED
        if all(item == State.SUPPORTED for item in states)
        else next(item for item in states if item != State.SUPPORTED)
    )
    known = {item.variable: item.value for item in inputs}
    frontier: list[str] = []
    if any(known[item.variable] != item.value for item in inputs):
        state = State.CONFLICTING
        frontier.append("Input assignments contain conflicting values for the same property")
    outputs: list[Assignment] = []
    if state == State.SUPPORTED:
        for rule in model.rules:
            value = _value(rule, known)
            if value is None:
                frontier.append(
                    f"{rule.output}: explicitly dropped"
                    if rule.operator == "drop"
                    else f"{rule.output}: missing inputs or unsupported transfer"
                )
            else:
                outputs.append(Assignment(variable=rule.output, value=value))
    else:
        frontier.append(
            "Known inputs do not establish the model and mapping applicability conditions"
        )
    return StateTransfer(
        logical_id=f"state-transfer:{digest([revision_of(mapping), CONVERTER.unstructure(inputs)])}",
        profile=mapping.profile,
        mapping=revision_of(mapping),
        inputs=inputs,
        outputs=tuple(outputs),
        condition_state=state,
        interpretation=mapping.interpretation,
        scope=mapping.scope,
        frontier=tuple(frontier),
    )
