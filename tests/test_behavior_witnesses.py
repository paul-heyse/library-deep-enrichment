"""Independent executions, adversarial summaries, and bounded concrete witness semantics."""

from __future__ import annotations

import operator

import pytest
from attrs import evolve

from library_deep_enrichment.analyses.behavior.builder import GraphBuilder, Origin
from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorSummary,
    Guard,
    Language,
    Limits,
    Outcome,
    Term,
)
from library_deep_enrichment.analyses.behavior.engine import Interpreter
from library_deep_enrichment.analyses.behavior.witness_checks import check
from library_deep_enrichment.analyses.behavior.witness_contracts import (
    Cell,
    Input,
    Observation,
    Verdict,
)
from library_deep_enrichment.analyses.behavior.witness_eval import Evaluation
from library_deep_enrichment.analyses.behavior.witness_generation import (
    GeneratedInput,
    GenerationLimits,
    run,
)
from library_deep_enrichment.analyses.behavior.witness_values import Concrete, decode, equality
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.schemas import revision_of


def identity() -> tuple[BehaviorProgram, BehaviorSummary]:
    """Build a typed identity fixture for independent mutation tests.

    Returns:
        The program and its ordinary source-model summary.

    """
    builder = GraphBuilder(
        Origin(
            request="r",
            owner="o",
            artifact="a",
            context="c",
            profile="p",
            symbol="identity",
            language=Language.PYTHON,
        ),
        "control",
    )
    value = builder.term("local", value="x", ty="python:int")
    builder.emit("return", value=value)
    program = builder.finish(("x",))
    return program, Interpreter(Limits()).summarize(program)


def observed(summary: BehaviorSummary, value: int, result: int) -> Observation:
    """Represent a concrete input/output pair outside the abstract value machinery.

    Returns:
        One independently supplied observation.

    """
    return Observation(
        case=str(value),
        summary=revision_of(summary),
        values=(Cell(kind="int", scalar=str(value)), Cell(kind="int", scalar=str(result))),
        inputs=(Input(parameter="x", value=0),),
        outcome=Outcome.RETURN,
        result=1,
    )


def test_unknown_result_and_no_compatible_result_are_distinct() -> None:
    """An opaque result cannot pass a check just because it permits arbitrary outputs."""
    program, summary = identity()
    assert check(program, summary, observed(summary, 3, 3)).verdict == Verdict.MATCHED
    assert check(program, summary, observed(summary, 3, 4)).verdict == Verdict.DISAGREEMENT
    opaque = evolve(summary, terms=(Term(op="unknown", value="open-call"),))
    assert check(program, opaque, observed(opaque, 3, 4)).verdict == Verdict.INCONCLUSIVE
    nonreturn = evolve(summary, clauses=(evolve(summary.clauses[0], outcome=Outcome.UNKNOWN),))
    assert check(program, nonreturn, observed(nonreturn, 3, 4)).verdict == Verdict.INCONCLUSIVE


def test_hypothesis_finds_and_shrinks_an_unsound_constant_transfer() -> None:
    """A deliberately faulty identity summary disagrees with a separately executed callable."""
    program, summary = identity()
    faulty = evolve(summary, terms=(Term(op="literal", value="0", ty="python:int"),))

    def oracle(value: GeneratedInput) -> Observation:
        argument = int(value.values[0].scalar)
        actual = operator.pos(argument)
        return observed(faulty, argument, actual)

    limits = GenerationLimits(examples=40, calls=100)
    campaign = run(program, faulty, oracle, seed=109, limits=limits)
    assert campaign.state == "minimized_disagreement"
    assert campaign.counterexample is not None
    assert abs(int(campaign.counterexample.values[0].scalar)) == 1
    assert campaign.calls <= limits.calls


def test_reversed_guard_rejects_the_independent_outcome() -> None:
    """Guard polarity controls eligibility of each observed return relationship."""
    program, summary = identity()
    terms = (
        *summary.terms,
        Term(op="literal", value="0", ty="python:int"),
        Term(op="gt", args=(0, 1), ty="model:bool"),
    )
    clause = evolve(summary.clauses[0], guards=(Guard(term=2, positive=True),))
    guarded = evolve(summary, terms=terms, clauses=(clause,))
    assert check(program, guarded, observed(guarded, 3, 3)).verdict == Verdict.MATCHED
    reversed_summary = evolve(
        guarded, clauses=(evolve(clause, guards=(Guard(term=2, positive=False),)),)
    )
    assert (
        check(program, reversed_summary, observed(reversed_summary, 3, 3)).verdict
        == Verdict.DISAGREEMENT
    )


def test_shared_concrete_dag_does_not_expand_exponentially() -> None:
    """Deep repeated references are compared once per node pair."""
    cells = [Cell(kind="int", scalar="3")]
    cells.extend(Cell(kind="tuple", children=(index - 1, index - 1)) for index in range(1, 60))
    first, second = decode(tuple(cells)), decode(tuple(cells))
    assert equality(first[-1], second[-1]) is True


def test_address_identity_does_not_prove_equal_payload_or_lifetime() -> None:
    """Reference identity and observed referent contents are separate checks."""
    one = Concrete(kind="reference", identity="a", children=(Concrete(kind="int", scalar="1"),))
    other = evolve(one, identity="b")
    assert equality(one, other) is False
    assert equality(one, evolve(one, identity="")) is None
    opaque = evolve(one, children=(Concrete(kind="opaque"),))
    assert equality(opaque, opaque) is None


@pytest.mark.parametrize(
    "cells",
    [
        (Cell(kind="tuple", children=(0,)),),
        (Cell(kind="bool", scalar="yes"),),
        (Cell(kind="variant", variant="Some"),),
    ],
)
def test_malformed_concrete_values_are_rejected(cells: tuple[Cell, ...]) -> None:
    """Malformed witness transport does not become a false disagreement or a pass."""
    with pytest.raises(CorpusError):
        decode(cells)


def test_concrete_evaluation_keeps_mutable_identity_out_of_value_equality() -> None:
    """The evaluator never consults abstract Values or a library-specific transfer."""
    evaluation = Evaluation({"x": Concrete(kind="int", scalar="255")}, ())
    values = evaluation.run(
        (
            Term(op="argument", value="x", ty="rust:u8"),
            Term(op="literal", value="1", ty="rust:u8"),
            Term(op="add", args=(0, 1), ty="rust:u8"),
        )
    )
    assert values[-1] == Concrete(kind="int", scalar="0")
