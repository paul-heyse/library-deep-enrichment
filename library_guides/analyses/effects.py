"""Finite transitive may-effects over compiler-linked local definitions."""

from __future__ import annotations

from collections import deque

from library_guides.analyses.flow import analyze
from library_guides.collection import CollectionError

_MAX_OWNERS = 200
_MAX_UPDATES = 100_000


def summarize(records: tuple[dict, ...]) -> dict[str, dict]:
    """Compute a least fixed point, including recursive components, with open frontiers.

    Returns:
        Per-owner may-effects and exact local edges; recursion never creates a support cycle.

    Raises:
        CollectionError: If owner identity or iteration exceeds the finite query universe.

    """
    if not records or len(records) > _MAX_OWNERS or len({r["id"] for r in records}) != len(records):
        message = "effect analysis needs 1..200 unique owners"
        raise CollectionError(message)
    owners = {r["id"]: r for r in records}
    effects: dict[str, set[str]] = {}
    frontier: dict[str, set[str]] = {}
    callees: dict[str, set[str]] = {}
    callers: dict[str, set[str]] = {key: set() for key in owners}
    for key, record in owners.items():
        effects[key], frontier[key], callees[key] = _local(record, set(owners))
        for target in callees[key]:
            callers[target].add(key)
    queue = deque(owners)
    updates = 0
    while queue:
        key = queue.popleft()
        updates += 1
        if updates > _MAX_UPDATES:
            message = "effect fixed point exceeds iteration budget"
            raise CollectionError(message)
        for caller in sorted(callers[key]):
            e = effects[caller] | effects[key]
            f = frontier[caller] | frontier[key]
            if e != effects[caller] or f != frontier[caller]:
                effects[caller], frontier[caller] = e, f
                queue.append(caller)
    return {
        key: {
            "may_effects": sorted(effects[key]),
            "frontier": sorted(frontier[key]),
            "local_callees": sorted(callees[key]),
            "scope": sorted(owners),
            "model": "full-cfg.local-definitions.projected-memory.v1",
            "termination": "finite powerset fixed point; no termination guarantee for the library operation",
            "closed": not frontier[key],
        }
        for key in sorted(owners)
    }


def _local(record: dict, owners: set[str]) -> tuple[set[str], set[str], set[str]]:
    key = record["id"]
    body = record["payload"]
    reachable = set(analyze(body).reachable)
    effects = set()
    frontier = {v for v in body.get("frontier", ()) if not v.endswith(":callee_effects")}
    callees: set[str] = set()
    _events(body, reachable, effects, frontier)
    for exit_ in body["exits"]:
        if exit_["block"] not in reachable:
            continue
        kind = exit_["kind"]
        if kind in {"drop", "inline_asm"}:
            frontier.add(kind + "_effects")
        if kind in {"assert", "abort", "resume"}:
            effects.add(kind)
        if kind != "call":
            continue
        instance = exit_.get("instance") or {}
        definition = instance.get("local_definition")
        target = key.rsplit(":", 1)[0] + ":" + definition if definition else None
        if instance.get("kind") == "item" and target in owners:
            callees.add(target)
        else:
            frontier.add(f"bb{exit_['block']}:unresolved_or_unselected_callee")
    return effects, frontier, callees


def _events(body: dict, reachable: set[int], effects: set[str], frontier: set[str]) -> None:
    for event in body["events"]:
        if event["block"] not in reachable:
            continue
        place = event.get("destination")
        if place and place["projection"]:
            effects.add("projected_memory_write")
        if event["kind"].startswith("unmodeled"):
            frontier.add("unmodeled_statement")
