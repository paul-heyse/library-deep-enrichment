"""Independent numeric boundary and inconclusive-query controls."""

from __future__ import annotations

import math
import struct

import pytest
from hypothesis import given
from hypothesis import strategies as st
from library_guides.analyses.behavior.contracts import Guard, Term
from library_guides.analyses.behavior.numeric import integer_width
from library_guides.analyses.behavior.predicates import PredicateChecks
from library_guides.analyses.behavior.solver import Check, feasible
from library_guides.analyses.behavior.state import State
from library_guides.analyses.behavior.values import Values, integral_type, scalar

_BYTE_MAX = 255


@pytest.mark.parametrize("ty", ["rust:u8", "rust:i8", "python:int"])
def test_solver_proves_order_contradiction_in_the_correct_scalar_domain(ty: str) -> None:
    """Neither signed nor unsigned interpretation permits x > 7 and x < 3."""
    terms = (
        Term(op="argument", value="x", ty=ty),
        Term(op="literal", value="7", ty=ty),
        Term(op="literal", value="3", ty=ty),
        Term(op="gt", args=(0, 1), ty="model:bool"),
        Term(op="lt", args=(0, 2), ty="model:bool"),
    )
    result = feasible(
        terms, (Guard(term=3, positive=True), Guard(term=4, positive=True)), timeout_ms=100
    )
    assert result.state == Check.INFEASIBLE


def test_unsigned_high_bit_is_not_a_negative_integer() -> None:
    """The unsigned byte 255 is greater than zero."""
    terms = (
        Term(op="literal", value="255", ty="rust:u8"),
        Term(op="literal", value="0", ty="rust:u8"),
        Term(op="gt", args=(0, 1), ty="model:bool"),
    )
    assert feasible(terms, (Guard(term=2, positive=True),), timeout_ms=100).state == Check.FEASIBLE
    assert (
        feasible(terms, (Guard(term=2, positive=False),), timeout_ms=100).state == Check.INFEASIBLE
    )


def test_unencoded_dispatch_and_exhaustion_never_mean_infeasible() -> None:
    """An unsupported Python predicate and a node limit retain possible paths."""
    dynamic = (Term(op="argument", value="x"), Term(op="truth", args=(0,), ty="model:bool"))
    guards = (Guard(term=1, positive=True),)
    assert feasible(dynamic, guards, timeout_ms=100).state == Check.UNSUPPORTED
    assert feasible(dynamic, guards, timeout_ms=100, node_limit=1).state == Check.BUDGET
    values = Values(100)
    predicate = values.add(Term(op="argument", value="flag", ty="model:bool"))
    state = State(guards=(Guard(term=predicate, positive=True),))
    checks = PredicateChecks(1, 100)
    assert checks.possible(values, state)
    assert checks.possible(values, state)
    assert checks.calls == 1
    assert any(frontier.code == "predicate_budget_exhausted" for frontier in state.frontier)


@given(a=st.integers(0, 255), b=st.integers(0, 255))
def test_checked_byte_addition_matches_independent_wide_integer_arithmetic(a: int, b: int) -> None:
    """The wrapped result and overflow flag are independent outputs."""
    values = Values(100)
    left = values.add(Term(op="literal", value=str(a), ty="rust:u8"))
    right = values.add(Term(op="literal", value=str(b), ty="rust:u8"))
    pair = values.terms[values.add(Term(op="checked_add", args=(left, right), ty="rust:u8"))]
    assert pair.op == "tuple"
    expected = a + b
    assert scalar(values.terms[pair.args[0]]) == expected % 256
    assert scalar(values.terms[pair.args[1]]) == (expected > _BYTE_MAX)


def test_symbolic_overflow_is_distinct_from_the_wrapped_value() -> None:
    """An increment of the maximal byte overflows even though its result is zero."""
    terms = (
        Term(op="argument", value="x", ty="rust:u8"),
        Term(op="literal", value="255", ty="rust:u8"),
        Term(op="literal", value="1", ty="rust:u8"),
        Term(op="eq", args=(0, 1), ty="model:bool"),
        Term(op="overflow_add", args=(0, 2), ty="model:bool"),
    )
    guards = (Guard(term=3, positive=True), Guard(term=4, positive=False))
    assert feasible(terms, guards, timeout_ms=100).state == Check.INFEASIBLE


@pytest.mark.parametrize("number", [float("nan"), float("inf"), -0.0, 1.25])
def test_ieee_literal_equality_preserves_nan_and_signed_zero_semantics(number: float) -> None:
    """Concrete floating equality differs from integer reflexivity."""
    values = Values(100)
    bits = str(int.from_bytes(struct.pack("!d", number), "big"))
    value = values.add(Term(op="literal", value=bits, ty="rust:f64"))
    equality = values.add(Term(op="eq", args=(value, value), ty="model:bool"))
    assert scalar(values.terms[equality]) == (not math.isnan(number))


@pytest.mark.parametrize("ty", ["rust:u0", "rust:u99999999999999999", "rust:usize", "python:int"])
def test_machine_width_is_finite_and_never_guessed_from_the_host(ty: str) -> None:
    """Pointer width and malformed sizes cannot allocate huge shifts."""
    assert integer_width(ty) is None
    if ty not in {"rust:usize", "python:int"}:
        assert not integral_type(ty)


def test_out_of_range_bitvector_literal_is_rejected_instead_of_wrapped() -> None:
    """Malformed source constants do not silently acquire modular meaning."""
    terms = (
        Term(op="literal", value="256", ty="rust:u8"),
        Term(op="eq", args=(0, 0), ty="model:bool"),
    )
    assert (
        feasible(terms, (Guard(term=1, positive=True),), timeout_ms=100).state == Check.UNSUPPORTED
    )


def test_variant_ordinal_is_not_a_declared_discriminant() -> None:
    """An enum's second variant may have repr(-3), so an ordinal cannot supply its tag."""
    values = Values(100)
    aggregate = values.add(Term(op="aggregate", value="Tag#variant:1", ty="rust:Tag"))
    tag = values.add(Term(op="discriminant", args=(aggregate,), ty="rust:i8"))
    assert values.terms[tag].op == "discriminant"
