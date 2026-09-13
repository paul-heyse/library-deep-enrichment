"""Allocation-site identities, private contents and conservative reachable escape."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import evolve

from library_guides.analyses.behavior.contracts import Region, Term

if TYPE_CHECKING:
    from library_guides.analyses.behavior.state import State
    from library_guides.analyses.behavior.values import Values


def allocate(values: Values, state: State, term: Term, owner: str) -> int:
    """Create a fresh builtin collection region without equating it to its payload.

    Returns:
        An allocation reference whose contents can change independently of its identity.

    """
    event = values.unknown("allocation:" + owner + ":" + term.value, fresh=True)
    kind = "list" if term.op == "list_from_sequence" else term.op
    root = values.add(Term(op="allocation", args=(event,), value=kind, ty="python:" + kind))
    contents = values.add(term)
    extent = (
        values.add(Term(op="length", args=(contents,), ty="python:int"))
        if kind == "list"
        else values.unknown("distinct_cardinality:" + str(root), "python:int")
    )
    state.regions[root] = Region(
        root=root,
        contents=contents,
        extent=extent,
        kind=kind,
        owner=owner,
        unique=True,
        escaped=False,
    )
    state.effect("descriptor_allocation", str(root), owner + ":" + term.value)
    state.assumptions = tuple(dict.fromkeys((*state.assumptions, "runtime:allocation_succeeds")))
    return root


def escape(values: Values, state: State, roots: tuple[int, ...]) -> None:
    """Expose every reachable allocation, including objects retained by container elements."""
    pending = list(roots)
    visited = set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        pending.extend(values.terms[current].args)
        region = state.regions.get(current)
        if region is not None:
            state.regions[current] = evolve(region, unique=False, escaped=True)
            pending.append(region.contents)


def havoc(values: Values, state: State, point: str) -> None:
    """Forget contents and extents only for allocations exposed to unknown code."""
    for root, region in tuple(state.regions.items()):
        if region.escaped:
            state.regions[root] = evolve(
                region,
                contents=values.unknown("region_contents:" + point, fresh=True),
                extent=values.unknown("region_extent:" + point, "python:int", fresh=True),
            )


def append(values: Values, state: State, arguments: tuple[int, ...], point: str) -> int | None:
    """Apply the compiler's private list accumulator operation to a proven builtin receiver.

    Returns:
        None only when its receiver/arity is unqualified; otherwise the Python None result.

    """
    arity = 2
    if len(arguments) != arity:
        return None
    root, value = arguments
    region = state.regions.get(root)
    if region is None or region.kind != "list" or not region.unique:
        return None
    previous = values.terms[region.contents]
    contents = (
        values.add(Term(op="list", args=(*previous.args, value), value=previous.value))
        if previous.op == "list"
        else values.add(Term(op="sequence_append", args=(region.contents, value)))
    )
    one = values.add(Term(op="literal", value="1", ty="python:int"))
    extent = values.add(Term(op="add", args=(region.extent, one), ty="python:int"))
    state.regions[root] = evolve(region, contents=contents, extent=extent)
    state.effect("memory_write", str(root), point)
    return values.add(Term(op="literal", value="None", ty="python:none"))
