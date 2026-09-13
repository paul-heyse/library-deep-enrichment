"""Counterexamples for bounded owner flow and recursive may-effect summaries."""

from __future__ import annotations

from library_deep_enrichment.analyses.effects import summarize
from library_deep_enrichment.analyses.flow import analyze, control_dependence


def _place(local: int, *, projected: bool = False) -> dict:
    """Build a plain local or abstract field location.

    Returns:
        A normalized fixture node.

    """
    return {"local": local, "projection": [{"kind": "deref"}] if projected else []}


def _value(local: int) -> dict:
    """Build a copy operand.

    Returns:
        A normalized fixture node.

    """
    return {"mode": "copy", "place": _place(local), "ty": None}


def _event(block: int, destination: int, source: int, *, projected: bool = False) -> dict:
    """Build one ordered transfer.

    Returns:
        A normalized fixture node.

    """
    return {
        "block": block,
        "statement": 0,
        "kind": "use",
        "destination": _place(destination, projected=projected),
        "values": [_value(source)],
    }


def _exit(block: int, kind: str, successors: tuple[int, ...] = ()) -> dict:
    """Build a control-flow terminator.

    Returns:
        A normalized fixture node.

    """
    return {
        "block": block,
        "kind": kind,
        "successors": list(successors),
        "args": [],
        "unwind_block": None,
    }


def _owner(events: list[dict], exits: list[dict]) -> dict:
    """Build a bounded body with a return, argument and temporary local.

    Returns:
        A normalized fixture node.

    """
    return {
        "locals": [
            {"index": i, "role": role} for i, role in enumerate(("return", "argument", "local"))
        ],
        "events": events,
        "exits": exits,
        "frontier": [],
    }


def test_only_values_reaching_return_and_projected_writes() -> None:
    """An unused assignment does not reach return; heap writes retain uncertainty."""
    body = _owner(
        [
            _event(0, 2, 1),
            {
                "block": 0,
                "statement": 1,
                "kind": "use",
                "destination": _place(0),
                "values": [{"mode": "constant", "place": None}],
            },
        ],
        [_exit(0, "return")],
    )
    assert analyze(body).return_dependencies == ("constant",)
    body["events"].insert(0, _event(0, 1, 2, projected=True))
    assert analyze(body).projected_writes
    assert any("write" in f for f in analyze(body).frontier)


def test_conditional_assignment_preserves_uninitialized_path() -> None:
    """A value assigned on only one branch cannot look initialized on every path."""
    body = _owner(
        [_event(1, 2, 1), _event(3, 0, 2)],
        [
            _exit(0, "switch", (1, 2)),
            _exit(1, "goto", (3,)),
            _exit(2, "goto", (3,)),
            _exit(3, "return"),
        ],
    )
    assert analyze(body).return_dependencies == ("argument:1", "unknown:uninitialized")
    assert control_dependence(body, analyze(body).reachable)["edges"] == [(0, 1, 1), (0, 2, 2)]


def test_dominating_branch_does_not_control_rejoined_call() -> None:
    """A common successor is post-dominated, even though the initial branch dominates it."""
    body = _owner(
        [],
        [
            _exit(0, "switch", (1, 2)),
            _exit(1, "goto", (3,)),
            _exit(2, "goto", (3,)),
            _exit(3, "return"),
        ],
    )
    common_successor = 3
    edges = control_dependence(body, (0, 1, 2, 3))["edges"]
    assert isinstance(edges, list)
    assert not any(edge[2] == common_successor for edge in edges)
    body["exits"][2] = _exit(2, "goto", (2,))
    assert control_dependence(body, (0, 1, 2, 3))["state"] == "partial"


def test_indirect_callable_flow_does_not_resolve_dispatch() -> None:
    """A cast retains a callable candidate; the invocation still has an effect frontier."""
    transfer = {
        "block": 0,
        "statement": 0,
        "kind": "cast",
        "destination": _place(2),
        "values": [
            {
                "mode": "constant",
                "place": None,
                "ty": {"kind": "function_definition", "nominal": "fixture::callback"},
            }
        ],
    }
    call = {**_exit(0, "call", (1,)), "callee": _value(2), "destination": _place(0)}
    result = analyze(_owner([transfer], [call, _exit(1, "return")]))
    assert result.indirect_candidates == ((0, ("fixture::callback",)),)
    assert "bb0:callee_effects" in result.frontier


def test_recursive_effects_propagate_with_separate_support_dag() -> None:
    """Recursion reaches a finite may-write result; missing a callee keeps an open frontier."""

    def record(name: str, target: str, events: list[dict]) -> dict:
        call = {
            **_exit(0, "call", (1,)),
            "callee": {"mode": "constant", "place": None},
            "destination": _place(0),
            "instance": {"kind": "item", "local_definition": target},
        }
        return {"id": "mir:unit:" + name, "payload": _owner(events, [call, _exit(1, "return")])}

    a = record("a", "b", [])
    b = record("b", "a", [_event(0, 1, 1, projected=True)])
    result = summarize((a, b))
    assert all(
        r["may_effects"] == ["projected_memory_write"] and r["closed"] for r in result.values()
    )
    partial = summarize((a,))
    assert not partial["mir:unit:a"]["closed"]
    assert partial["mir:unit:a"]["frontier"]
