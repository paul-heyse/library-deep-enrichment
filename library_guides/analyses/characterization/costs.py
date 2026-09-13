"""Local structural traversal bounds with explicit cycle and external-work limitations."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import networkx as nx

from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.characterization.contracts import LocalCost

if TYPE_CHECKING:
    from library_guides.analyses.behavior.contracts import BehaviorProgram

METRICS = {
    "instructions": None,
    "calls": "call",
    "writes": "write",
    "drops": "drop",
    "suspensions": "suspend",
}
FRONTIER = (
    "counts_only_original_local_instructions_excluding_callee_and_implicit_runtime_work",
    "zero_lower_bound_allows_external_nonreturn_and_abandonment",
    "guards_are_relaxed_for_the_structural_upper_bound",
    "count_bounds_do_not_establish_time_memory_termination_or_scheduler_guarantees",
)


def analyze(program: BehaviorProgram) -> tuple[LocalCost, ...]:
    """Bound visits for a single local graph traversal when its reachable graph is acyclic.

    Returns:
        Structural upper bounds, or explicit unresolved cycle multiplicities.

    """
    graph = nx.DiGraph()
    graph.add_nodes_from(program.blocks)
    graph.add_edges_from((edge.source, edge.target) for edge in program.edges)
    reachable = {program.entry}
    for node in nx.descendants(graph, program.entry):
        require("characterization CFG has a noninteger node", condition=isinstance(node, int))
        assert isinstance(node, int)
        reachable.add(node)
    graph = graph.subgraph(reachable)
    acyclic = nx.is_directed_acyclic_graph(graph)
    order = tuple(nx.topological_sort(graph)) if acyclic else ()
    result = []
    for metric, opcode in METRICS.items():
        weights = Counter(
            item.block for item in program.instructions if opcode is None or item.op == opcode
        )
        bounds: dict[int, int] = {}
        for block in order:
            require(
                "characterization CFG contains a noninteger block", condition=isinstance(block, int)
            )
            assert isinstance(block, int)
            predecessors = tuple(graph.predecessors(block))
            bounds[block] = weights[block] + max((bounds[item] for item in predecessors), default=0)
        result.append(
            LocalCost(
                metric=metric,
                lower=0,
                upper=(max(bounds.values(), default=0),) if acyclic else (),
                basis="acyclic_local_cfg_relaxation" if acyclic else "cyclic_local_cfg",
                frontier=(
                    *FRONTIER,
                    *(
                        ("cycle_multiplicity_requires_loop_or_protocol_invariant",)
                        if not acyclic
                        else ()
                    ),
                ),
            )
        )
    return tuple(result)
