"""Bounded sequence-expression laws over ordered elements and symbolic segments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.behavior.contracts import Term

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.values import Values

_CONCRETE = frozenset({"tuple", "list"})


def fold(values: Values, term: Term) -> Term | int | None:
    """Preserve segment order without expanding an unbounded or unknown iterable.

    Returns:
        A valid sequence simplification, or no applicable law.

    """
    if term.op in {"sequence_snapshot", "list_from_sequence"} and len(term.args) == 1:
        source = values.terms[term.args[0]]
        if source.op in _CONCRETE:
            kind = "tuple" if term.op == "sequence_snapshot" else "list"
            return Term(op=kind, args=source.args, ty="python:" + kind)
        if term.op == "sequence_snapshot" and source.op == "list_from_sequence":
            return source.args[0]
    if term.op == "sequence_concat":
        sources = tuple(values.terms[index] for index in term.args)
        if (
            all(source.op in _CONCRETE for source in sources)
            and sum(len(source.args) for source in sources) <= values.limit
        ):
            return Term(
                op="tuple",
                args=tuple(index for source in sources for index in source.args),
                ty="python:tuple",
            )
    if term.op == "length" and len(term.args) == 1:
        source = values.terms[term.args[0]]
        if source.op in {"sequence_snapshot", "list_from_sequence"}:
            return values.add(Term(op="length", args=source.args, ty="python:int"))
        if source.op == "sequence_concat":
            result = values.add(Term(op="literal", value="0", ty="python:int"))
            for segment in source.args:
                length = values.add(Term(op="length", args=(segment,), ty="python:int"))
                result = values.add(Term(op="add", args=(result, length), ty="python:int"))
            return result
    return None
