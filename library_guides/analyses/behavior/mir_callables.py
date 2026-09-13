"""Qualify exact compiler function-item operands before tracking callable value flow."""

from __future__ import annotations

from library_guides.analyses.behavior import mir_instances
from library_guides.analyses.behavior.integrity import require

SCHEMA = "library-guides.mir-callables.v1"
MODEL = "rust-mir-execution.v3"
MAX_REFERENCES = 100_000


def operands(raw: dict) -> dict[tuple[int, int | None, str, int], dict]:
    """Index the retained operand denominator without recovering identities from display names.

    Returns:
        Exact event/call operand positions, including unresolved function items.

    """
    body = raw["payload"]
    result = {
        (event["block"], event["statement"], "event_value", index): value
        for event in body["events"]
        for index, value in enumerate(event["values"])
    }
    for exit_ in body["exits"]:
        if exit_["kind"] == "call":
            result[exit_["block"], None, "callee", 0] = exit_["callee"]
            result.update(
                {
                    (exit_["block"], None, "call_argument", index): value
                    for index, value in enumerate(exit_["args"])
                }
            )
    return result


def validate(raw: dict) -> dict[tuple[int, int | None, str, int], dict]:
    """Reject omitted, duplicate, cross-unit or non-function reference evidence.

    Returns:
        One compiler-qualified reference for each encountered function-item operand.

    """
    references = raw.get("callables")
    require("missing callable-reference denominator", condition=isinstance(references, list))
    assert isinstance(references, list)
    require("callable-reference budget exceeded", condition=len(references) <= MAX_REFERENCES)
    expected = {
        key
        for key, value in operands(raw).items()
        if (value.get("ty") or {}).get("kind") == "function_definition"
    }
    result = {}
    events = {(event["block"], event["statement"]): event for event in raw["payload"]["events"]}
    for item in references:
        point = item["point"]
        key = point["block"], point["statement"], point["role"], point["operand"]
        require(
            "duplicate or non-function callable reference",
            condition=key in expected and key not in result,
        )
        event = events.get(key[:2])
        require(
            "pointer coercion is not an exact function-item cast",
            condition=not item["pointer_coercion"]
            or (event is not None and event["kind"] == "cast" and key[2:] == ("event_value", 0)),
        )
        call, selection = item["call"], item["selection"]
        require(
            "callable reference point mismatch",
            condition=call["block"] == selection["block"] == point["block"],
        )
        # Reuse the exact item/substitution/unit checks, with a single reference denominator.
        view = {
            **raw,
            "behavior": {**raw["behavior"], "calls": [call]},
            "execution": {**raw["execution"], "calls": [selection]},
        }
        mir_instances.validate(view)
        result[key] = item
    require("callable reference denominator is incomplete", condition=set(result) == expected)
    return result


def qualify(raw: dict, bodies: dict[str, dict], *, complete_catalog: bool = False) -> None:
    """Join references to their captured definition and exact substitutions before dispatch."""
    if "callables" not in raw:
        return
    for item in validate(raw).values():
        view = {
            **raw,
            "behavior": {**raw["behavior"], "calls": [item["call"]]},
            "execution": {**raw["execution"], "calls": [item["selection"]]},
        }
        mir_instances.qualify_calls(view, bodies, complete_catalog=complete_catalog)


def overlay(raw: dict) -> dict:
    """Annotate a copied compiler projection with validated callable-value identities.

    Returns:
        The supplied private normalized copy, with no mutation of retained native evidence.

    """
    indexed = operands(raw)
    events = {(event["block"], event["statement"]): event for event in raw["payload"]["events"]}
    for key, item in validate(raw).items():
        selection = item["selection"]
        if selection["state"] == "captured":
            indexed[key]["callable_target"] = selection["instance"]
            if item["pointer_coercion"]:
                events[key[:2]]["function_pointer_coercion"] = True
        else:
            indexed[key]["callable_frontier"] = selection["state"]
    return raw
