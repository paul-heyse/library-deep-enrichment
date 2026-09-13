"""Finite CFG indexing and explicit propagation of normal, exceptional and cyclic paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx
from attrs import frozen

from library_deep_enrichment.analyses.behavior.contracts import Outcome
from library_deep_enrichment.analyses.behavior.predicates import PredicateChecks, assume
from library_deep_enrichment.analyses.behavior.state import Result

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.contracts import (
        BehaviorProgram,
        Edge,
        Instruction,
    )
    from library_deep_enrichment.analyses.behavior.memory import Locations
    from library_deep_enrichment.analyses.behavior.state import State

_ERROR_EDGES = frozenset({"error", "unwind", "cancel"})
_FINAL_FLOW = {
    "abort": Outcome.ABORT,
    "suspend": Outcome.SUSPEND,
    "unknown": Outcome.UNKNOWN,
    "diverge": Outcome.DIVERGE,
}


@frozen(kw_only=True)
class Graph:
    """An indexed disposable view over one admitted executable graph."""

    instructions: dict[int, tuple[Instruction, ...]]
    edges: dict[int, tuple[Edge, ...]]
    cyclic: frozenset[int]


def index(program: BehaviorProgram) -> Graph:
    """Index instructions and identify SCCs that can contain a control cycle.

    Returns:
        A finite execution view; cyclic membership is not a nontermination proof.

    Raises:
        TypeError: The graph provider returns a node outside the integer node contract.

    """
    graph = nx.DiGraph()
    graph.add_nodes_from(program.blocks)
    graph.add_edges_from((edge.source, edge.target) for edge in program.edges)
    cycles = set()
    for raw_component in nx.strongly_connected_components(graph):
        component: set[int] = set()
        for member in raw_component:
            if not isinstance(member, int):
                message = "behavior graph contains a non-integer node"
                raise TypeError(message)
            component.add(member)
        if len(component) > 1 or any(graph.has_edge(node, node) for node in component):
            cycles.update(component)
    return Graph(
        instructions={
            block: tuple(item for item in program.instructions if item.block == block)
            for block in program.blocks
        },
        edges={
            block: tuple(item for item in program.edges if item.source == block)
            for block in program.blocks
        },
        cyclic=frozenset(cycles),
    )


def cycle(locations: Locations, state: State, block: int) -> Result:
    """Retain a repeated abstract cycle as possible divergence.

    Returns:
        An explicit termination frontier, not a definite infinite-loop claim.

    """
    result = state.copy()
    result.unknown(
        "abstract_cycle", "termination", str(block), "repeated abstract state on a CFG cycle"
    )
    return Result(
        outcome=Outcome.DIVERGE, value=locations.values.unknown("cycle:" + str(block)), state=result
    )


def _edge_allowed(state: State, edge: Edge) -> bool:
    if state.flow == "error":
        return edge.kind in _ERROR_EDGES
    if state.flow == "returned":
        return edge.kind not in _ERROR_EDGES
    return True


def route(
    locations: Locations, state: State, edges: tuple[Edge, ...], checks: PredicateChecks
) -> tuple[list[tuple[int, State]], list[Result]]:
    """Route outcomes without erasing an unhandled error or assuming a call returns.

    Returns:
        Feasible successor states and any unhandled terminal outcomes.

    """
    if state.flow in _FINAL_FLOW:
        return [], [
            Result(
                outcome=_FINAL_FLOW[state.flow],
                value=locations.values.unknown(state.flow),
                state=state,
            )
        ]
    successors = []
    eligible = tuple(edge for edge in edges if _edge_allowed(state, edge))
    for edge in eligible:
        following = state.copy()
        if edge.condition >= 0:
            value = locations.resolve(edge.condition, following)
            guards = assume(locations.values, following.guards, value, positive=edge.positive)
            if guards is None:
                continue
            following.guards = guards
            if not checks.possible(locations.values, following):
                continue
        following.flow = "normal"
        if edge.kind in {"resume", "unwind", "cancel"}:
            following.phase = edge.kind
        successors.append((edge.target, following))
    if eligible:
        return successors, []
    if state.flow == "error":
        outcome = Outcome.UNWIND if locations.program.language == "rust" else Outcome.RAISE
        value = state.locals.get("$exception", locations.values.unknown("unhandled_error"))
        return [], [Result(outcome=outcome, value=value, state=state)]
    state.unknown(
        "unterminated_block", "control", locations.program.owner, "no modeled terminal or successor"
    )
    return [], [
        Result(outcome=Outcome.UNKNOWN, value=locations.values.unknown("no_exit"), state=state)
    ]
