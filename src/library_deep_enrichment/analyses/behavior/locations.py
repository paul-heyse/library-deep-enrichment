"""Structural destinations and immutable record lenses, separate from loaded values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import frozen

from library_deep_enrichment.analyses.behavior.contracts import Term

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram
    from library_deep_enrichment.analyses.behavior.values import Values

_PROJECTIONS = frozenset({"field", "index", "downcast"})


@frozen(kw_only=True)
class Destination:
    """A stack-rooted path; a pointer dereference deliberately breaks this proof."""

    local: str
    path: tuple[Term, ...]


def stack_destination(program: BehaviorProgram, index: int) -> Destination | None:
    """Find a directly owned Rust place without assuming input reference separation.

    Returns:
        A finite by-value path, or no uniqueness proof for indirect/Python locations.

    """
    if program.language != "rust":
        return None
    path = []
    while True:
        term = program.terms[index]
        if term.op == "local":
            return Destination(local=term.value, path=tuple(reversed(path)))
        if term.op not in _PROJECTIONS or not term.args:
            return None
        if term.op == "index":
            offset = program.terms[term.args[1]]
            if offset.op != "literal" or not offset.value.isdecimal():
                return None
        path.append(term)
        index = term.args[0]


def replace_path(values: Values, original: int, path: tuple[Term, ...], replacement: int) -> int:
    """Reconstruct only the modified path while forwarding untouched siblings.

    Returns:
        The new root value; each field/index update is explicit in its expression DAG.

    """
    ancestors = []
    current = original
    for step in path:
        ancestors.append(current)
        current = values.add(
            Term(op=step.op, args=(current, *step.args[1:]), value=step.value, ty=step.ty)
        )
    for parent, step in reversed(tuple(zip(ancestors, path, strict=True))):
        replacement = values.add(
            Term(
                op="update_" + step.op,
                args=(parent, replacement, *step.args[1:]),
                value=step.value,
                ty=values.terms[parent].ty,
            )
        )
    return replacement


def overlaps(values: Values, first: int, second: int) -> bool:
    """Compare exact structural location prefixes, never address-valued equality.

    Returns:
        Whether one retained location is an ancestor of the other.

    """

    def ancestors(index: int) -> set[int]:
        result = {index}
        while values.terms[index].args and values.terms[index].op == "location":
            index = values.terms[index].args[0]
            result.add(index)
        return result

    return first in ancestors(second) or second in ancestors(first)
