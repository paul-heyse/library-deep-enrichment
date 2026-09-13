"""A concrete, non-executing value model for comparing external observations."""

from __future__ import annotations

from attrs import evolve, frozen

from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.behavior.witness_contracts import Cell

_MAX_DEPTH = 64
_MAX_SCALAR_BYTES = 16384
_MAX_INTEGER_DIGITS = 1024
_MAX_EQUALITY_PAIRS = 100_000

KINDS = frozenset(
    {
        "bool",
        "int",
        "str",
        "none",
        "float_bits",
        "bytes",
        "record",
        "variant",
        "tuple",
        "list",
        "reference",
        "opaque",
    }
)


@frozen(kw_only=True)
class Concrete:
    """A finite observed value; opaque values are not wildcard matches."""

    kind: str
    scalar: str = ""
    children: tuple[Concrete, ...] = ()
    labels: tuple[str, ...] = ()
    definition: str = ""
    variant: str = ""
    identity: str = ""


@frozen(kw_only=True)
class Unresolved:
    """An unsupported evaluation is an inconclusive comparison, never a concrete value."""

    reason: str


type Value = Concrete | Unresolved


def decode(cells: tuple[Cell, ...]) -> tuple[Concrete, ...]:
    """Validate and decode a bounded concrete DAG without invoking user objects.

    Returns:
        Owned values, retaining sharing identities only where observed explicitly.

    """
    result: list[Concrete] = []
    depths: list[int] = []
    for index, cell in enumerate(cells):
        require("unknown concrete witness kind", condition=cell.kind in KINDS)
        require(
            "witness value graph is not acyclic",
            condition=all(0 <= item < index for item in cell.children),
        )
        depth = 1 + max((depths[item] for item in cell.children), default=0)
        require("concrete witness value depth exhausted", condition=depth <= _MAX_DEPTH)
        require(
            "witness field labels repeat or omit values",
            condition=not cell.labels
            or (
                len(cell.labels) == len(cell.children) and len(set(cell.labels)) == len(cell.labels)
            ),
        )
        require(
            "witness scalar exceeds finite bound", condition=len(cell.scalar) <= _MAX_SCALAR_BYTES
        )
        require(
            "invalid witness boolean",
            condition=cell.kind != "bool" or cell.scalar in {"true", "false"},
        )
        require(
            "invalid witness integer",
            condition=cell.kind != "int"
            or (
                cell.scalar.removeprefix("-").isdecimal()
                and len(cell.scalar) <= _MAX_INTEGER_DIGITS
            ),
        )
        require(
            "witness reference lacks one observed referent",
            condition=cell.kind != "reference" or len(cell.children) == 1,
        )
        require(
            "witness variant lacks contextual identity",
            condition=cell.kind != "variant" or bool(cell.definition and cell.variant),
        )
        require(
            "scalar witness cannot contain fields",
            condition=cell.kind in {"record", "variant", "tuple", "list", "reference"}
            or not cell.children,
        )
        result.append(
            Concrete(
                kind=cell.kind,
                scalar=cell.scalar,
                children=tuple(result[item] for item in cell.children),
                labels=cell.labels,
                definition=cell.definition,
                variant=cell.variant,
                identity=cell.identity,
            )
        )
        depths.append(depth)
    return tuple(result)


def equality(left: Value, right: Value) -> bool | None:
    """Compare observed structural values without treating uncertainty as equality.

    Returns:
        True/False when decidable in this observation model, otherwise None.

    """
    pending = [(left, right)]
    seen: set[tuple[int, int]] = set()
    uncertain = False
    while pending:
        a, b = pending.pop()
        key = (id(a), id(b))
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > _MAX_EQUALITY_PAIRS:
            return None
        same = _shallow_equal(a, b)
        if same is False:
            return False
        if same is None:
            uncertain = True
        elif isinstance(a, Concrete) and isinstance(b, Concrete):
            pending.extend(zip(a.children, b.children, strict=True))
    return None if uncertain else True


def _shallow_equal(left: Value, right: Value) -> bool | None:
    if isinstance(left, Unresolved) or isinstance(right, Unresolved):
        return None
    if left.kind == "opaque" or right.kind == "opaque":
        return None
    if (left.kind, left.scalar, left.definition, left.variant, left.labels) != (
        right.kind,
        right.scalar,
        right.definition,
        right.variant,
        right.labels,
    ):
        return False
    if left.kind == "reference":
        if not left.identity or not right.identity:
            return None
        if left.identity != right.identity:
            return False
    return len(left.children) == len(right.children)


def field(value: Value, name: str) -> Value:
    """Select a concrete logical field; omitted observations remain unresolved.

    Returns:
        The field value or an explicit missing-observation reason.

    """
    if isinstance(value, Unresolved):
        return value
    if value.labels and name in value.labels:
        return value.children[value.labels.index(name)]
    if not value.labels and name.isdecimal() and int(name) < len(value.children):
        return value.children[int(name)]
    return Unresolved(reason="unobserved logical field: " + name)


def replace_field(value: Value, name: str, replacement: Value) -> Value:
    """Apply a concrete field lens without reusing the abstract memory transfer.

    Returns:
        A new structural value or an unresolved projection.

    """
    if isinstance(value, Unresolved) or isinstance(replacement, Unresolved):
        return Unresolved(reason="unresolved concrete field update")
    if value.labels and name in value.labels:
        index = value.labels.index(name)
    elif not value.labels and name.isdecimal():
        index = int(name)
    else:
        return Unresolved(reason="unobserved update field: " + name)
    if index >= len(value.children):
        return Unresolved(reason="unobserved update index")
    children = list(value.children)
    children[index] = replacement
    return evolve(value, children=tuple(children))
