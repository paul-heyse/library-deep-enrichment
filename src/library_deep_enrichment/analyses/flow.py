"""Finite MIR local-value dependency propagation; opaque memory/calls stay frontiers."""

from __future__ import annotations

from collections import deque

from attrs import frozen

from library_deep_enrichment.collection import CollectionError

_MAX_BLOCKS = 20_000
_MAX_STEPS = 200_000
_MAX_ORIGINS = 2_000
_MAX_POSTDOMINATORS = 1_000

type State = dict[int, frozenset[str]]


@frozen(kw_only=True)
class Flow:
    """May-dependencies are not value equality, ownership or an effect-free guarantee."""

    reachable: tuple[int, ...]
    return_dependencies: tuple[str, ...]
    indirect_candidates: tuple[tuple[int, tuple[str, ...]], ...]
    projected_writes: tuple[tuple[int, int, tuple[str, ...]], ...]
    call_arguments: tuple[tuple[int, tuple[tuple[str, ...], ...]], ...]
    frontier: tuple[str, ...]
    steps: int


def _origins(value: dict, state: State) -> frozenset[str]:
    place = value.get("place")
    if place is not None:
        result = state.get(place["local"], frozenset({"unknown:uninitialized"}))
        if place["projection"]:
            result |= frozenset({"unknown:projected_memory"})
        return result
    ty = value.get("ty") or {}
    if ty.get("kind") == "function_definition" and ty.get("nominal"):
        return frozenset({"callable:" + ty["nominal"]})
    return frozenset({"constant" if value.get("mode") == "constant" else "unknown:operand"})


def _assign(state: State, destination: dict, origins: frozenset[str]) -> None:
    local = destination["local"]
    if destination["projection"]:
        # A field/heap abstraction cannot kill the other fields or an aliased target.
        state[local] = (
            state.get(local, frozenset()) | origins | frozenset({"unknown:projected_write"})
        )
    else:
        state[local] = origins


def _event(event: dict, state: State) -> None:
    destination = event.get("destination")
    if destination is None:
        return
    if event["kind"] in {"storage_dead", "storage_live"}:
        state[destination["local"]] = frozenset({"unknown:uninitialized"})
        return
    if event["kind"] == "set_discriminant":
        # Changing the tag does not erase origins in the retained aggregate fields.
        return
    origins = frozenset().union(*(_origins(value, state) for value in event["values"]))
    if event["kind"].startswith("unmodeled"):
        origins |= frozenset({"unknown:unmodeled_transfer"})
    if event.get("constructor"):
        origins |= frozenset({f"constructor:{event['block']}:{event['statement']}"})
    elif event["kind"] == "aggregate":
        origins |= frozenset({"unknown:aggregate_constructor"})
    _assign(state, destination, origins or frozenset({"constant"}))


def _merge(previous: State, incoming: State) -> State:
    result = {
        local: previous.get(local, frozenset()) | incoming.get(local, frozenset())
        for local in previous.keys() | incoming.keys()
    }
    if any(len(value) > _MAX_ORIGINS for value in result.values()):
        message = "MIR flow exceeds finite origin budget; no closed result admitted"
        raise CollectionError(message)
    return result


def analyze(owner: dict) -> Flow:
    """Propagate dependency origins to a fixed point over the complete retained CFG.

    Returns:
        Reachability, return dependencies and unresolved function-pointer candidates.

    Raises:
        CollectionError: If CFG identity or declared analysis budgets are invalid.

    """
    exits, events = _cfg(owner)
    states: dict[int, State] = {
        0: {
            local["index"]: frozenset(
                {
                    "argument:" + str(local["index"])
                    if local["role"] == "argument"
                    else "unknown:uninitialized"
                }
            )
            for local in owner["locals"]
        }
    }
    queue = deque([0])
    steps = 0
    while queue:
        steps += 1
        if steps > _MAX_STEPS:
            message = "MIR fixed-point budget exceeded; no closed result admitted"
            raise CollectionError(message)
        block = queue.popleft()
        state = dict(states[block])
        for event in sorted(events[block], key=lambda e: e["statement"]):
            _event(event, state)
        terminal = exits[block]
        if terminal["kind"] == "call" and terminal.get("destination"):
            dependencies = frozenset().union(
                *(_origins(value, state) for value in terminal["args"])
            )
            _assign(
                state, terminal["destination"], dependencies | frozenset({f"unknown:call:{block}"})
            )
        for successor in terminal["successors"]:
            # On unwind the return destination is not initialized; include that uncertainty.
            incoming = (
                _merge(state, states[block]) if successor == terminal.get("unwind_block") else state
            )
            merged = _merge(states.get(successor, {}), incoming)
            if successor not in states or merged != states[successor]:
                states[successor] = merged
                queue.append(successor)
    return _summarize(owner, events, states, steps)


def _summarize(
    owner: dict, events: dict[int, list[dict]], states: dict[int, State], steps: int
) -> Flow:
    returns: set[str] = set()
    calls = []
    arguments = []
    writes = []
    frontier = set(owner.get("frontier", []))
    for terminal in owner["exits"]:
        block = terminal["block"]
        if block not in states:
            continue
        state = dict(states[block])
        for event in sorted(events[block], key=lambda e: e["statement"]):
            destination = event.get("destination")
            if destination and destination["projection"]:
                writes.append(
                    (
                        block,
                        event["statement"],
                        tuple(sorted(state.get(destination["local"], frozenset()))),
                    )
                )
                frontier.add(f"bb{block}:aliased_or_projected_write")
            if event["kind"].startswith("unmodeled"):
                frontier.add(f"bb{block}:unmodeled_transfer")
            frontier.update(
                value
                for operand in event["values"]
                for value in _origins(operand, state)
                if value.startswith("unknown:")
            )
            _event(event, state)
        if terminal["kind"] == "return":
            returns.update(state.get(0, frozenset({"unknown:return"})))
        if terminal["kind"] == "call":
            arguments.append(
                (block, tuple(tuple(sorted(_origins(v, state))) for v in terminal["args"]))
            )
            origins = _origins(terminal["callee"], state)
            calls.append(
                (
                    block,
                    tuple(
                        sorted(
                            x.removeprefix("callable:")
                            for x in origins
                            if x.startswith("callable:")
                        )
                    ),
                )
            )
            frontier.add(f"bb{block}:callee_effects")
        if terminal["kind"] in {"drop", "inline_asm"}:
            frontier.add(f"bb{block}:{terminal['kind']}_effects")
    frontier.update(value for value in returns if value.startswith("unknown:"))
    return Flow(
        reachable=tuple(sorted(states)),
        return_dependencies=tuple(sorted(returns)),
        indirect_candidates=tuple(calls),
        projected_writes=tuple(writes),
        call_arguments=tuple(arguments),
        frontier=tuple(sorted(frontier)),
        steps=steps,
    )


def control_dependence(owner: dict, reachable: tuple[int, ...]) -> dict[str, object]:
    """Compute post-dominator control dependence under explicit terminating-path semantics.

    Returns:
        Branch-controlled blocks; ordinary dominance alone creates no relation.

    """
    virtual = -1
    nodes = set(reachable) | {virtual}
    if len(nodes) > _MAX_POSTDOMINATORS:
        return {
            "state": "partial",
            "edges": [],
            "frontier": ["post-dominator memory budget"],
            "policy": "bounded full CFG",
        }
    successors = {
        e["block"]: set(e["successors"]) or {virtual} for e in owner["exits"] if e["block"] in nodes
    }
    successors[virtual] = set()
    can_finish = {virtual}
    while expanded := {n for n, targets in successors.items() if targets & can_finish} - can_finish:
        can_finish |= expanded
    if can_finish != nodes:
        return {
            "state": "partial",
            "edges": [],
            "frontier": sorted(nodes - can_finish),
            "policy": "nonterminating region is unresolved",
        }
    post = {n: ({n} if n == virtual else set(nodes)) for n in nodes}
    changed = True
    while changed:
        changed = False
        for node in sorted(nodes - {virtual}):
            value = {node} | set.intersection(*(post[s] for s in successors[node]))
            if value != post[node]:
                post[node] = value
                changed = True
    edges = sorted(
        {
            (branch, successor, target)
            for branch, targets in successors.items()
            if len(targets) > 1
            for successor in targets
            for target in post[successor] - post[branch]
            if target != virtual
        }
    )
    return {
        "state": "complete",
        "edges": edges,
        "policy": "full retained CFG including unwind; conditional on reaching a terminal exit; no nontermination guarantee",
        "frontier": [],
    }


def _cfg(owner: dict) -> tuple[dict[int, dict], dict[int, list[dict]]]:
    exits = {item["block"]: item for item in owner["exits"]}
    if not exits or len(exits) != len(owner["exits"]) or len(exits) > _MAX_BLOCKS or 0 not in exits:
        message = "MIR analysis requires a nonempty bounded CFG with unique block identities"
        raise CollectionError(message)
    if any(target not in exits for item in exits.values() for target in item["successors"]):
        message = "MIR successor leaves the declared owner universe"
        raise CollectionError(message)
    events: dict[int, list[dict]] = {block: [] for block in exits}
    for event in owner["events"]:
        if event["block"] not in events:
            message = "MIR event leaves the declared owner universe"
            raise CollectionError(message)
        events[event["block"]].append(event)
    return exits, events
