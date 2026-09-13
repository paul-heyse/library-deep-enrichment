"""Bounded generation and shrinking from admitted scalar input types and guard constants."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import frozen

from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.behavior.witness_checks import check
from library_guides.analyses.behavior.witness_contracts import Cell, Input, Observation, Verdict

if TYPE_CHECKING:
    from collections.abc import Callable

    from hypothesis.strategies import SearchStrategy

    from library_guides.analyses.behavior.contracts import BehaviorProgram, BehaviorSummary


_MAX_CALLS = 10_000


@frozen(kw_only=True)
class GenerationLimits:
    """Independent bounds for generated examples and actual oracle invocations."""

    examples: int = 100
    calls: int = 1000


@frozen(kw_only=True)
class GeneratedInput:
    """Concrete generated scalar arguments, retaining the original parameter identities."""

    values: tuple[Cell, ...]
    inputs: tuple[Input, ...]


@frozen(kw_only=True)
class Campaign:
    """Finite executed observations; minimization failures never erase the first disagreement."""

    seed: int
    calls: int
    state: str
    observations: tuple[Observation, ...]
    counterexample: Observation | None
    detail: str


class _BudgetError(Exception):
    """The actual oracle invocation bound, including shrinking, has been exhausted."""


def run(
    program: BehaviorProgram,
    summary: BehaviorSummary,
    oracle: Callable[[GeneratedInput], Observation],
    *,
    seed: int,
    limits: GenerationLimits = GenerationLimits(),
) -> Campaign:
    """Generate and shrink with Hypothesis; the caller supplies an independent executor.

    Returns:
        All executed observations and a minimized disagreement when one is found.

    """
    import random

    from hypothesis import find, settings
    from hypothesis.errors import NoSuchExample

    require(
        "invalid witness generation budget",
        condition=0 < limits.examples <= limits.calls <= _MAX_CALLS,
    )
    strategy = _strategy(program)
    observations: list[Observation] = []
    failures: dict[GeneratedInput, Observation] = {}

    def disagrees(value: GeneratedInput) -> bool:
        if len(observations) >= limits.calls:
            raise _BudgetError
        observation = oracle(value)
        observations.append(observation)
        result = check(program, summary, observation)
        if result.verdict == Verdict.DISAGREEMENT:
            failures[value] = observation
            return True
        return False

    try:
        minimum = find(
            strategy,
            disagrees,
            settings=settings(max_examples=limits.examples, database=None, deadline=None),
            random=random.Random(seed),
        )
    except NoSuchExample:
        return Campaign(
            seed=seed,
            calls=len(observations),
            state="no_disagreement_found",
            observations=tuple(observations),
            counterexample=None,
            detail="finite generated inputs only; inconclusive comparisons remain in observations",
        )
    except _BudgetError:
        return Campaign(
            seed=seed,
            calls=len(observations),
            state="oracle_budget_exhausted",
            observations=tuple(observations),
            counterexample=next(iter(failures.values()), None),
            detail="generation and shrinking share the actual invocation bound",
        )
    return Campaign(
        seed=seed,
        calls=len(observations),
        state="minimized_disagreement",
        observations=tuple(observations),
        counterexample=failures[minimum],
        detail="minimal under the selected Hypothesis strategy and bounded search, not a global minimum proof",
    )


def _strategy(program: BehaviorProgram) -> SearchStrategy[GeneratedInput]:
    from hypothesis import strategies as st

    choices: list[SearchStrategy[Cell]] = []
    for name in program.parameters:
        types = {
            item.ty
            for item in program.terms
            if item.op in {"argument", "local"} and item.value == name and item.ty != "unknown"
        }
        require(
            "automatic witnesses require one admitted scalar type or a constructor binding",
            condition=len(types) == 1,
        )
        ty = next(iter(types))
        if ty.endswith(":bool"):
            choices.append(
                st.booleans().map(lambda value: Cell(kind="bool", scalar=str(value).lower()))
            )
        else:
            choices.append(_integers(program, ty))
    return st.tuples(*choices).map(
        lambda cells: GeneratedInput(
            values=cells,
            inputs=tuple(
                Input(parameter=name, value=index) for index, name in enumerate(program.parameters)
            ),
        )
    )


def _integers(program: BehaviorProgram, ty: str) -> SearchStrategy[Cell]:
    from hypothesis import strategies as st

    require(
        "automatic witness type needs a qualified constructor/representation binding",
        condition=ty == "python:int"
        or (ty.startswith(("rust:i", "rust:u")) and ty[6:] in {"8", "16", "32", "64", "128"}),
    )
    if ty == "python:int":
        low, high = -1024, 1024
    else:
        bits, signed = int(ty[6:]), ty.startswith("rust:i")
        low, high = (-(2 ** (bits - 1)) if signed else 0), 2 ** (bits - int(signed)) - 1
    landmarks = {low, high, 0}
    for item in program.terms:
        if item.op == "literal" and item.ty == ty and item.value.removeprefix("-").isdecimal():
            value = int(item.value)
            landmarks.update(
                point for point in (value - 1, value, value + 1) if low <= point <= high
            )
    return st.one_of(
        st.integers(low, high),
        st.sampled_from(sorted(landmarks, key=lambda value: (abs(value), value))),
    ).map(lambda value: Cell(kind="int", scalar=str(value)))
