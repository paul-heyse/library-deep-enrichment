"""Malformed executable evidence cannot become an admitted behavioral guarantee."""

from __future__ import annotations

import pytest
from attrs import evolve
from library_guides.analyses.behavior.builder import GraphBuilder, Origin
from library_guides.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorRequest,
    Edge,
    Instruction,
    Language,
    Limits,
    Term,
)
from library_guides.analyses.behavior.integrity import limits_valid, program_valid
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.encoding import CONVERTER, payload


def program() -> BehaviorProgram:
    """Construct a small body without a library-specific semantic mapping.

    Returns:
        A finite valid executable graph.

    """
    builder = GraphBuilder(
        Origin(
            request="r",
            owner="o",
            artifact="a",
            context="c",
            profile="p",
            symbol="choose",
            language=Language.PYTHON,
        ),
        "test",
    )
    argument = builder.term("argument", value="value", ty="python:int")
    builder.emit("return", value=argument, span=(0, 10))
    return builder.finish(("value",))


def test_behavior_contract_is_strict_and_preserves_enum_meaning() -> None:
    """Strict structuring rejects extra evidence and does not turn bool into an integer."""
    value = program()
    assert CONVERTER.structure(payload(value), BehaviorProgram) == value
    raw = payload(value)
    raw["silently_closed"] = True
    with pytest.raises(ExceptionGroup):
        CONVERTER.structure(raw, BehaviorProgram)
    with pytest.raises(ExceptionGroup):
        CONVERTER.structure(
            {"logical_id": "r", "owners": ["o"], "artifacts": ["a"], "limits": {"steps": True}},
            BehaviorRequest,
        )


@pytest.mark.parametrize(
    "replacement",
    [
        {"terms": (Term(op="eq", args=(0,)),)},
        {"terms": (Term(op="not_a_language_operation"),)},
        {"edges": (Edge(source=0, target=1),)},
        {"edges": (Edge(source=0, target=0, condition=3),)},
        {"instructions": (Instruction(block=0, index=0, op="return", value=7),)},
        {"instructions": (Instruction(block=0, index=0, op="return", start=8, end=2),)},
        {"parameters": ("x", "x")},
        {"blocks": (0, 0)},
    ],
)
def test_malformed_body_graph_is_rejected(replacement: dict) -> None:
    """Invalid references and source coordinates fail before any interpretation."""
    with pytest.raises(CorpusError):
        program_valid(evolve(program(), **replacement), Limits())


@pytest.mark.parametrize(
    "limits",
    [
        Limits(states=0),
        Limits(clauses=-1),
        Limits(call_depth=100),
        Limits(solver_ms=60000),
        Limits(terms=2000000),
    ],
)
def test_limits_are_checked_before_allocating(limits: Limits) -> None:
    """A supplied budget cannot disable independent hard bounds."""
    with pytest.raises(CorpusError):
        limits_valid(limits)


def test_term_interning_and_program_points_are_deterministic() -> None:
    """Repeated structural inputs retain stable values and body identity."""
    value = program()
    program_valid(value, Limits())
    assert value == program()


def test_arrow_codec_retains_guard_and_frontier_fields() -> None:
    """The owned portable schema preserves the whole typed body."""
    from library_guides.analyses.behavior import schemas
    from library_guides.corpus.schemas import REGISTRY

    assert schemas.TERMS is not None
    codec = REGISTRY["behavior_programs"]
    assert codec.decode(codec.encode(program())) == program()
