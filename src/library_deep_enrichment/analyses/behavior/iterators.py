"""Private builtin sequence iterators; dynamic protocol calls keep their open call frontier."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import evolve

from library_deep_enrichment.analyses.behavior.contracts import Region, Term
from library_deep_enrichment.analyses.behavior.values import scalar

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.state import State
    from library_deep_enrichment.analyses.behavior.values import Values


def create(values: Values, state: State, source: int, point: str) -> int | None:
    """Acquire a builtin iterator only from a known tuple or exact private list allocation.

    Returns:
        A distinct stateful iterator, the existing iterator, or an unqualified receiver.

    """
    region = state.regions.get(source)
    term = values.terms[source]
    if region is not None and region.kind == "sequence_iterator" and not region.escaped:
        return source
    if term.op != "tuple" and (region is None or region.kind != "list" or region.escaped):
        return None
    event = values.unknown("sequence_iterator:" + point, fresh=True)
    root = values.add(
        Term(op="allocation", args=(event,), value="sequence_iterator", ty="python:iterator")
    )
    zero = values.add(Term(op="literal", value="0", ty="python:int"))
    contents = values.add(Term(op="tuple", args=(source, zero)))
    extent = (
        region.extent
        if region is not None
        else values.add(Term(op="literal", value=str(len(term.args)), ty="python:int"))
    )
    state.regions[root] = Region(
        root=root,
        contents=contents,
        extent=extent,
        kind="sequence_iterator",
        owner=point,
        unique=True,
        escaped=False,
    )
    state.effect("descriptor_allocation", str(root), point)
    state.assumptions = tuple(dict.fromkeys((*state.assumptions, "runtime:allocation_succeeds")))
    return root


def advance(values: Values, state: State, root: int, point: str) -> int | None:
    """Advance a private iterator cursor against its sequence's current contents.

    Returns:
        The next value or a StopIteration sentinel with state.flow set to error.
        None means the actual iteration protocol or mutation state is unqualified.

    """
    region = state.regions.get(root)
    if region is None or region.kind != "sequence_iterator" or region.escaped:
        return None
    descriptor = values.terms[region.contents]
    arity = 2
    if descriptor.op != "tuple" or len(descriptor.args) != arity:
        return None
    source, cursor = descriptor.args
    index = scalar(values.terms[cursor])
    parent = state.regions.get(source)
    sequence = values.terms[parent.contents if parent else source]
    if type(index) is not int or sequence.op not in {"tuple", "list"}:
        return None
    if index < 0 or index >= len(sequence.args):
        completed = values.add(Term(op="literal", value="-1", ty="python:int"))
        zero = values.add(Term(op="literal", value="0", ty="python:int"))
        state.regions[root] = evolve(
            region, contents=values.add(Term(op="tuple", args=(source, completed))), extent=zero
        )
        state.effect("iterator_exhausted", str(root), point)
        error = values.add(Term(op="literal", value="StopIteration", ty="python:builtin_exception"))
        state.locals["$exception"] = error
        state.flow = "error"
        return error
    next_index = values.add(Term(op="literal", value=str(index + 1), ty="python:int"))
    remaining = values.add(
        Term(op="literal", value=str(len(sequence.args) - index - 1), ty="python:int")
    )
    state.regions[root] = evolve(
        region, contents=values.add(Term(op="tuple", args=(source, next_index))), extent=remaining
    )
    state.effect("iterator_advance", str(root), point)
    state.flow = "returned"
    return sequence.args[index]
