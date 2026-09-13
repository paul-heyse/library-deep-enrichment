"""Contextual drop/shim and closure-environment facts, without assumed protocol meaning."""

from __future__ import annotations

import re

from library_deep_enrichment.analyses.behavior import mir_abi, mir_instances
from library_deep_enrichment.analyses.behavior.integrity import require

SCHEMA = "library-guides.mir-lifecycle.v1"
MODEL = "rust-mir-execution.v4"
MAX_USES = 100_000


def _drop_view(raw: dict, use: dict) -> dict:
    target = use["target"]
    call = {
        "block": use["block"],
        "declaration": None,
        "target": target["definition"] if target else None,
        "substitutions": target["substitutions"] if target else [],
        "instance_kind": target["kind"] if target else "unresolved",
        "complete": target is not None,
        "frontier": [],
    }
    return {
        **raw,
        "behavior": {**raw["behavior"], "calls": [call]},
        "execution": {**raw["execution"], "calls": [use["selection"]]},
    }


def validate(raw: dict) -> dict[int, dict]:
    """Require exact drop and closure denominators and typed compiler target correspondence.

    Returns:
        Drop observations at original blocks, including explicitly unavailable targets.

    """
    uses = raw.get("lifecycle")
    require("missing lifecycle use denominator", condition=isinstance(uses, dict))
    assert isinstance(uses, dict)
    mir_abi.validate(raw)
    require(
        "lifecycle use budget exhausted",
        condition=len(uses["drops"]) + len(uses["closures"]) <= MAX_USES,
    )
    expected = {item["block"]: item for item in raw["payload"]["exits"] if item["kind"] == "drop"}
    result = {}
    for use in uses["drops"]:
        block = use["block"]
        require(
            "duplicate or missing original drop",
            condition=block in expected
            and block not in result
            and use["place"] == expected[block]["destination"]
            and use["selection"]["block"] == block,
        )
        target = use["target"]
        require(
            "drop target lost its exact type or empty-shim observation",
            condition=(
                target is None
                and use["empty_shim"] is None
                and use["selection"]["instance"] is None
            )
            or (
                isinstance(target, dict)
                and target["kind"] == "shim"
                and target["phase"] == mir_instances.PHASE
                and target["key"] == use["selection"]["instance"]
                and type(use["empty_shim"]) is bool
                and target["substitutions"] == [{"kind": "type", "ty": use["ty"]}]
            ),
        )
        mir_instances.validate(_drop_view(raw, use))
        result[block] = use
    require("drop use denominator is incomplete", condition=set(result) == set(expected))
    events = {
        (item["block"], item["statement"]): item
        for item in raw["payload"]["events"]
        if (item.get("constructor") or {}).get("kind") == "closure"
    }
    seen = set()
    for closure in uses["closures"]:
        key = closure["block"], closure["statement"]
        require(
            "closure environment lacks one exact aggregate/capture denominator",
            condition=key in events
            and key not in seen
            and len(events[key]["values"]) == closure["captures"]
            and bool(
                re.fullmatch(
                    r"definition:[0-9a-f]{16}:[0-9a-f]{32}:[0-9a-f]{32}", closure["definition"]
                )
            ),
        )
        seen.add(key)
    require("closure environment denominator is incomplete", condition=seen == set(events))
    return result


def qualify(raw: dict, bodies: dict[str, dict], *, complete_catalog: bool = False) -> None:
    """Join drop targets to the full original instance identity and monomorphized body."""
    if "lifecycle" not in raw:
        return
    mir_abi.qualify(raw, bodies)
    for use in validate(raw).values():
        mir_instances.qualify_calls(_drop_view(raw, use), bodies, complete_catalog=complete_catalog)
        if use["selection"]["state"] == "captured" and use["selection"]["instance"] in bodies:
            require(
                "drop target identity differs from its captured body",
                condition=bodies[use["selection"]["instance"]]["execution"]["identity"]
                == use["target"],
            )


def overlay(raw: dict) -> None:
    """Annotate only a private normalized copy with verified drop and closure identities."""
    drops = validate(raw)
    abis = mir_abi.validate(raw)
    for exit_ in raw["payload"]["exits"]:
        if exit_["block"] in abis:
            exit_["call_abi"] = abis[exit_["block"]]
        exit_["unit_return"] = any(
            local["role"] == "return" and local["ty"]["kind"] == "tuple" and not local["ty"]["args"]
            for local in raw["payload"]["locals"]
        )
        use = drops.get(exit_["block"])
        if use is not None and use["selection"]["state"] == "captured":
            exit_["drop_target"] = use["selection"]["instance"]
    events = {(item["block"], item["statement"]): item for item in raw["payload"]["events"]}
    for closure in raw["lifecycle"]["closures"]:
        events[closure["block"], closure["statement"]]["constructor"]["nominal"] = closure[
            "definition"
        ]
