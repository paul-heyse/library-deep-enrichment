"""Versioned concrete-instance identity checks and call overlays over retained compiler facts."""

from __future__ import annotations

import re

from library_guides.analyses.behavior.integrity import require

SCHEMA = "library-guides.mir-instances.v1"
PHASE = "rustc_public_eager_monomorphized_body"
GENERIC_PHASE = "rustc_public_generic_definition_body"
_STATES = frozenset(
    {
        "captured",
        "body_unavailable",
        "depth_budget_exhausted",
        "candidate_budget_exhausted",
        "instance_budget_exhausted",
        "operand_type_unavailable",
        "indirect_dispatch_requires_value_flow",
        "generic_instance_resolution_not_attempted",
        "instance_resolution_unavailable",
        "non_item_or_foreign_instance_not_selected",
        "outside_requested_root_closure",
    }
)


def validate(raw: dict) -> dict[int, dict]:
    """Keep compiler instance bodies distinct and require an outcome for every explicit call.

    Returns:
        Exact original call overlays; captured targets stay in the observing compiler unit.

    """
    execution = raw.get("execution")
    require("missing concrete-instance execution metadata", condition=isinstance(execution, dict))
    assert isinstance(execution, dict)
    require(
        "malformed compiler body identity",
        condition=bool(
            re.fullmatch(r"(?:mir|mir-instance):[0-9a-f]{64}:[0-9a-f]{32,64}", raw["id"])
        ),
    )
    unit = raw["id"].split(":")[1]
    identity = execution.get("identity")
    metadata = raw["behavior"]
    if raw["kind"] == "mir_instance":
        require(
            "concrete instance body identity or phase mismatch",
            condition=isinstance(identity, dict)
            and identity.get("key") == raw["id"]
            and identity.get("definition") == metadata.get("definition")
            and identity.get("kind") in ({"item", "shim"} if "lifecycle" in raw else {"item"})
            and identity.get("phase") == metadata.get("phase") == PHASE
            and _instance_key(raw["id"], unit),
        )
    else:
        require(
            "generic body was promoted to a concrete instance",
            condition=raw["kind"] == "mir_owner"
            and identity is None
            and metadata.get("phase") == GENERIC_PHASE,
        )
    calls = execution["calls"]
    require(
        "instance capture call denominator differs from native calls",
        condition=len({call["block"] for call in calls}) == len(calls)
        and {call["block"] for call in calls} == {call["block"] for call in metadata["calls"]},
    )
    native_calls = {item["block"]: item for item in metadata["calls"]}
    for call in calls:
        target = call.get("instance")
        require(
            "invalid instance call state or cross-unit identity",
            condition=call["state"] in _STATES
            and (target is None or (isinstance(target, str) and _instance_key(target, unit)))
            and (call["state"] != "captured" or target is not None),
        )
        native_call = native_calls[call["block"]]
        require(
            "captured instance lacks exact item dispatch",
            condition=call["state"] != "captured"
            or (
                native_call["complete"]
                and native_call["instance_kind"]
                in ({"item", "shim"} if "lifecycle" in raw else {"item"})
            ),
        )
    return {call["block"]: call for call in calls}


def qualify_calls(raw: dict, bodies: dict[str, dict], *, complete_catalog: bool = False) -> None:
    """Check concrete target definition and exact substituted arguments before composition."""
    if "execution" not in raw:
        return
    observed = validate(raw)
    for call in raw["behavior"]["calls"]:
        use = observed[call["block"]]
        if use["state"] != "captured":
            continue
        body = bodies.get(use["instance"])
        require(
            "captured instance is missing from its complete catalog",
            condition=body is not None or not complete_catalog,
        )
        if body is None:
            continue
        validate(body)
        identity = body["execution"]["identity"]
        require(
            "instance target definition or substitutions differ from the observed call",
            condition=identity is not None
            and identity["key"] == use["instance"]
            and identity["definition"] == call["target"]
            and identity["kind"] == call["instance_kind"]
            and identity["substitutions"] == call["substitutions"],
        )


def _instance_key(key: str, unit: str) -> bool:
    return (
        bool(re.fullmatch(r"mir-instance:[0-9a-f]{64}:[0-9a-f]{64}", key))
        and key.split(":")[1] == unit
    )


def target(call: dict, overlay: dict | None) -> str:
    """Choose a captured instance only from its compiler-qualified overlay.

    Returns:
        A concrete target, an existing generic-definition target, or no exact target.

    """
    if overlay is not None and overlay["state"] == "captured":
        return overlay["instance"]
    return (call.get("target") or "") if call.get("complete") else ""
