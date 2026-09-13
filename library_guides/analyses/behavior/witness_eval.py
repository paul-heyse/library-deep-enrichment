"""Interpret summary expressions against concrete observations, without abstract transfers."""

from __future__ import annotations

import operator
from collections.abc import Callable

from attrs import define, field

from library_guides.analyses.behavior.contracts import NominalIdentity, Term
from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.behavior.witness_context import Invocation
from library_guides.analyses.behavior.witness_contracts import Projection
from library_guides.analyses.behavior.witness_operators import Operators
from library_guides.analyses.behavior.witness_values import (
    Concrete,
    Unresolved,
    Value,
    replace_field,
)
from library_guides.analyses.behavior.witness_values import field as concrete_field

_BINARY_ARITY = 2
_MAX_INTEGER_DIGITS = 1024
_MAX_INTEGER_BITS = 4096
_MAX_PROJECTION_DEPTH = 16
_MAX_SEQUENCE_ITEMS = 100_000

_ARITHMETIC: dict[str, Callable[[int, int], int]] = {
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "bit_and": operator.and_,
    "bit_or": operator.or_,
    "bit_xor": operator.xor,
}
_ORDER: dict[str, Callable[[int, int], bool]] = {
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
}


def boolean(*, value: bool) -> Concrete:
    """Construct an owned boolean.

    Returns:
        The exact finite boolean value.

    """
    return Concrete(kind="bool", scalar=str(value).lower())


def literal(term: Term) -> Value:
    """Read a concrete literal with explicit language semantics.

    Returns:
        An owned scalar or an unsupported literal reason.

    """
    if term.ty.endswith(":bool") and term.value in {"true", "false", "True", "False", "0", "1"}:
        return boolean(value=term.value in {"true", "True", "1"})
    if term.ty == "python:none":
        return Concrete(kind="none")
    if term.ty in {"python:str", "python:bytes"}:
        return Concrete(kind=term.ty.removeprefix("python:"), scalar=term.value)
    if (
        (term.ty == "python:int" or term.ty.startswith(("rust:i", "rust:u")))
        and term.value.removeprefix("-").isdecimal()
        and len(term.value) <= _MAX_INTEGER_DIGITS
    ):
        return Concrete(kind="int", scalar=str(int(term.value)))
    return Unresolved(reason="unsupported concrete literal: " + term.ty)


@define
class Evaluation:
    """Evaluate one bounded term DAG using independently captured concrete input values."""

    inputs: dict[str, Concrete]
    nominals: tuple[NominalIdentity, ...]
    values: list[Value] = field(factory=list)
    invocation: Invocation = field(factory=lambda: Invocation({}, {}), kw_only=True)
    category_identity: bool = field(default=True, kw_only=True)
    operators: Operators | None = field(default=None, kw_only=True)
    primitive_unary: bool = field(default=False, kw_only=True)

    def project(self, value: Value, path: tuple[Projection, ...]) -> Value:
        """Select only the returned dimensions that the concrete harness actually observed.

        Returns:
            A projected value or explicit unsupported/missing field information.

        """
        require(
            "witness output projection exceeds its bound",
            condition=len(path) <= _MAX_PROJECTION_DEPTH,
        )
        for step in path:
            require(
                "unsupported witness observation projection",
                condition=step.kind in {"field", "deref", "discriminant", "length", "identity"},
            )
            value = self._projection(Term(op=step.kind, value=step.key), value)
        return value

    def run(self, terms: tuple[Term, ...]) -> tuple[Value, ...]:
        """Evaluate each node once; never evaluate library source or arbitrary callbacks.

        Returns:
            Concrete values and explicit per-expression unknowns.

        """
        for index, term in enumerate(terms):
            if any(item < 0 or item >= index for item in term.args):
                self.values.append(Unresolved(reason="malformed summary DAG"))
            else:
                result = self._term(term, tuple(self.values[item] for item in term.args))
                if isinstance(result, Unresolved) and self.operators is not None:
                    result = self.operators.resolve(index, self.values)
                self.values.append(result)
        return tuple(self.values)

    def _nominal(self, value: Concrete) -> NominalIdentity | None:
        candidates = [item for item in self.nominals if item.definition == value.definition]
        return (
            candidates[0]
            if candidates and all(item.variants == candidates[0].variants for item in candidates)
            else None
        )

    def _field_name(self, value: Value, name: str) -> str:
        if isinstance(value, Unresolved) or not name.isdecimal():
            return name
        nominal = self._nominal(value)
        if nominal is None:
            return name
        variants = [
            item
            for item in nominal.variants
            if item.name == value.variant or nominal.kind == "struct"
        ]
        if len(variants) == 1:
            names = [item.name for item in variants[0].fields if item.index == int(name)]
            if len(names) == 1:
                return names[0]
        return name

    def _aggregate(self, term: Term, args: tuple[Value, ...]) -> Value:
        if term.op in {"sequence_snapshot", "sequence_concat", "list_from_sequence"}:
            return sequence(term, args)
        if any(isinstance(item, Unresolved) for item in args):
            return Unresolved(reason="unresolved constructor operand")
        children = tuple(item for item in args if isinstance(item, Concrete))
        if term.op in {"tuple", "list"}:
            return Concrete(kind=term.op, children=children)
        name, marker, index = term.value.rpartition("#variant:")
        candidates = [item for item in self.nominals if item.name == name]
        definitions = {item.definition for item in candidates}
        if not marker or not index.isdecimal() or len(definitions) != 1:
            return Unresolved(reason="constructor lacks one contextual nominal binding")
        variants = [item for item in candidates[0].variants if item.index == int(index)]
        if len(variants) != 1 or len(variants[0].fields) != len(children):
            return Unresolved(reason="constructor member mismatch")
        variant = variants[0]
        return Concrete(
            kind="record" if candidates[0].kind == "struct" else "variant",
            children=children,
            labels=tuple(item.name for item in variant.fields),
            definition=candidates[0].definition,
            variant=variant.name,
        )

    def _term(self, term: Term, args: tuple[Value, ...]) -> Value:
        if term.op in {"argument", "global"}:
            bindings = self.inputs if term.op == "argument" else self.invocation.globals
            return bindings.get(term.value, Unresolved(reason="unobserved " + term.op))
        if term.op == "call" and args:
            return self.invocation.call(term, args[1:])
        if term.op in {
            "aggregate",
            "tuple",
            "list",
            "sequence_snapshot",
            "sequence_concat",
            "list_from_sequence",
        }:
            return self._aggregate(term, args)
        if term.op == "update_field" and len(args) == _BINARY_ARITY:
            return replace_field(args[0], self._field_name(args[0], term.value), args[1])
        if len(args) == 1:
            return self._projection(term, args[0])
        return (
            literal(term)
            if term.op == "literal"
            else operation(term, args, category_identity=self.category_identity)
        )

    def _projection(self, term: Term, value: Value) -> Value:
        if term.op == "field":
            return concrete_field(value, self._field_name(value, term.value))
        if isinstance(value, Unresolved):
            return value
        if term.op in {"borrow", "address"}:
            return Concrete(kind="reference", children=(value,), identity=value.identity)
        if term.op == "deref" and value.kind == "reference":
            return value.children[0]
        if term.op in {"discriminant", "downcast"}:
            return self._variant(term, value)
        return (
            integer_unary(term, value)
            if self.primitive_unary and term.op in {"neg", "positive", "invert"}
            else unary(term, value)
        )

    def _variant(self, term: Term, value: Concrete) -> Value:
        nominal = self._nominal(value)
        variants = (
            [item for item in nominal.variants if item.name == value.variant] if nominal else []
        )
        if len(variants) == 1:
            variant = variants[0]
            if term.op == "discriminant" and variant.discriminant:
                return Concrete(kind="int", scalar=variant.discriminant)
            if term.op == "downcast" and str(variant.index) == term.value:
                return value
        return Unresolved(reason="unknown contextual variant")


def integer_unary(term: Term, value: Concrete) -> Value:
    """Check finite integer unary arithmetic independently of the abstract transfer routines.

    Returns:
        The exact integer, or an explicit unsupported type/overflow result.

    """
    if value.kind != "int" or len(value.scalar) > _MAX_INTEGER_DIGITS:
        return Unresolved(reason="unobserved or oversized integer unary operand")
    original = int(value.scalar)
    operations: dict[str, Callable[[int], int]] = {
        "neg": operator.neg,
        "positive": operator.pos,
        "invert": operator.invert,
    }
    result = operations[term.op](original)
    if result.bit_length() > _MAX_INTEGER_BITS:
        return Unresolved(reason="integer unary result exceeds witness budget")
    if term.ty == "python:int":
        return Concrete(kind="int", scalar=str(result))
    name = term.ty.removeprefix("rust:")
    if (
        not term.ty.startswith("rust:")
        or name[:1] not in {"u", "i"}
        or name[1:] not in {"8", "16", "32", "64", "128"}
    ):
        return Unresolved(reason="integer unary lacks exact machine width")
    width = int(name[1:])
    modulus = 2**width
    signed = name.startswith("i")
    lower, upper = (-(modulus // 2), modulus // 2 - 1) if signed else (0, modulus - 1)
    if not lower <= original <= upper:
        return Unresolved(reason="integer unary operand outside its machine type")
    if term.op == "invert":
        result %= modulus
        if signed and result > upper:
            result -= modulus
    return (
        Concrete(kind="int", scalar=str(result))
        if lower <= result <= upper
        else Unresolved(reason="integer unary overflow requires its control outcome")
    )


def unary(term: Term, value: Concrete) -> Value:
    """Evaluate non-dispatching operations on fully observed builtin values.

    Returns:
        A concrete result or explicit unsupported operation.

    """
    if term.op == "identity":
        return (
            Concrete(kind="str", scalar=value.identity)
            if value.identity
            else Unresolved(reason="object identity was not observed")
        )
    if term.op == "length" and value.kind in {"list", "tuple", "str", "bytes"}:
        length = len(value.scalar) if value.kind in {"str", "bytes"} else len(value.children)
        return Concrete(kind="int", scalar=str(length))
    if term.op == "not" and value.kind == "bool":
        return boolean(value=value.scalar == "false")
    if term.op == "truth" and value.kind in {"none", "bool", "int", "str", "list", "tuple"}:
        result = value.kind != "none"
        if value.kind == "bool":
            result = value.scalar == "true"
        elif value.kind == "int":
            result = int(value.scalar) != 0
        elif value.kind in {"list", "tuple"}:
            result = bool(value.children)
        elif value.kind == "str":
            result = bool(value.scalar)
        return boolean(value=result)
    return Unresolved(reason="unsupported concrete unary operation: " + term.op)


def sequence(term: Term, args: tuple[Value, ...]) -> Value:
    """Independently check ordered sequence segments under a finite expansion bound.

    Returns:
        Concrete contents, or uncertainty for an unobserved iterable or exhausted budget.

    """
    if term.op != "sequence_concat" and len(args) != 1:
        return Unresolved(reason="malformed sequence conversion")
    if any(not isinstance(item, Concrete) or item.kind not in {"list", "tuple"} for item in args):
        return Unresolved(reason="sequence contents not observed")
    sequences = tuple(item for item in args if isinstance(item, Concrete))
    if sum(len(item.children) for item in sequences) > _MAX_SEQUENCE_ITEMS:
        return Unresolved(reason="witness sequence budget exhausted")
    return Concrete(
        kind="list" if term.op == "list_from_sequence" else "tuple",
        children=tuple(child for item in sequences for child in item.children),
    )


def operation(term: Term, args: tuple[Value, ...], *, category_identity: bool = True) -> Value:
    """Evaluate bounded primitive relations using ordinary host integer arithmetic.

    Returns:
        A concrete relation, or an unknown when dispatch/rounding is not represented.

    """
    if any(isinstance(item, Unresolved) for item in args):
        return Unresolved(reason="unresolved operand: " + term.op)
    values = tuple(item for item in args if isinstance(item, Concrete))
    if len(values) != _BINARY_ARITY:
        return Unresolved(reason="unsupported concrete operation: " + term.op)
    left, right = values
    if term.op in {"is", "is_not"}:
        return identity_operation(term, left, right, category_identity=category_identity)
    if left.kind == right.kind == "bool" and term.op in {"eq", "ne", "and", "or"}:
        a, b = left.scalar == "true", right.scalar == "true"
        return boolean(
            value=a == b
            if term.op == "eq"
            else a != b
            if term.op == "ne"
            else a and b
            if term.op == "and"
            else a or b
        )
    if left.kind == right.kind == "int":
        return integer_operation(term, int(left.scalar), int(right.scalar))
    return Unresolved(reason="unsupported concrete operation: " + term.op)


def identity_operation(
    term: Term, left: Concrete, right: Concrete, *, category_identity: bool
) -> Value:
    """Compare finite object identities and builtin singleton categories.

    Returns:
        A boolean or uncertainty when the observation conceals the required identity.

    """
    known = left.kind in {"bool", "none"} and right.kind in {"bool", "none"}
    disjoint_none = (
        "none" in {left.kind, right.kind}
        and left.kind != right.kind
        and not {left.kind, right.kind} & {"opaque", "reference"}
    )
    if category_identity and disjoint_none:
        return boolean(value=term.op == "is_not")
    if known or (left.identity and right.identity):
        same = (
            (left.kind, left.scalar) == (right.kind, right.scalar)
            if known
            else left.identity == right.identity
        )
        return boolean(value=same if term.op == "is" else not same)
    return Unresolved(reason="object identity was not observed")


def integer_operation(term: Term, left: int, right: int) -> Value:
    """Use bounded ordinary arithmetic as the independent scalar comparison semantics.

    Returns:
        A scalar with explicit width conversion, or an unknown unsupported result.

    """
    if max(left.bit_length(), right.bit_length()) > _MAX_INTEGER_BITS:
        return Unresolved(reason="concrete arithmetic budget")
    if term.op in _ORDER:
        return boolean(value=_ORDER[term.op](left, right))
    if term.op not in _ARITHMETIC:
        return Unresolved(reason="unsupported concrete integer operation: " + term.op)
    result = _ARITHMETIC[term.op](left, right)
    if result.bit_length() > _MAX_INTEGER_BITS:
        return Unresolved(reason="concrete arithmetic result budget")
    if term.ty.startswith(("rust:i", "rust:u")):
        width = term.ty[6:]
        if width not in {"8", "16", "32", "64", "128"}:
            return Unresolved(reason="unknown machine width")
        bits = int(width)
        result %= 2**bits
        if term.ty.startswith("rust:i") and result >= 2 ** (bits - 1):
            result -= 2**bits
    return Concrete(kind="int", scalar=str(result))
