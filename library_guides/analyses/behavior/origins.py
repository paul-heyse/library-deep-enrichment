"""Instruction-level origins for derived values, separate from value equality and effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import define, field, frozen

from library_guides.analyses.behavior.contracts import Guard
from library_guides.corpus.backend import BudgetExceededError
from library_guides.corpus.contracts import Record, Selection
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_guides.analyses.behavior.contracts import (
        BehaviorProgram,
        BehaviorSummary,
        Instruction,
    )
    from library_guides.analyses.behavior.state import State

MODEL = "source-instruction-value-origins.v1"


@frozen(kw_only=True)
class OriginValue:
    """An already-evaluated result and operands at one transfer boundary."""

    result: int
    arguments: tuple[int, ...]
    mode: str


@frozen(kw_only=True)
class ValueOrigin:
    """A guarded evaluated value at an instruction in an exact contextual body."""

    program: str
    instruction: int
    operation: str
    mode: str
    result: int
    arguments: tuple[int, ...]
    phase: str
    guards: tuple[Guard, ...]
    assumptions: tuple[str, ...]


@frozen(kw_only=True)
class BehaviorOrigins(Record):
    """Origins address the referenced summary's DAG; they do not strengthen its semantics."""

    request: str
    summary: str
    model: str
    entries: tuple[ValueOrigin, ...]
    support: tuple[Selection, ...]


@define
class Origins:
    """Bounded recorder that does not re-evaluate expressions to recover their operands."""

    limit: int
    entries: dict[ValueOrigin, None] = field(factory=dict)
    programs: dict[int, tuple[BehaviorProgram, str]] = field(factory=dict)

    def observe(
        self,
        program: BehaviorProgram,
        instruction: Instruction,
        state: State,
        *,
        value: OriginValue,
    ) -> None:
        """Record one already-evaluated relationship without altering state or term identity.

        Raises:
            BudgetExceededError: The finite provenance budget is exhausted.

        """
        key = id(program)
        if key not in self.programs:
            self.programs[key] = (program, revision_of(program))
        operation = (
            program.terms[instruction.value].op if instruction.value >= 0 else instruction.op
        )
        entry = ValueOrigin(
            program=self.programs[key][1],
            instruction=instruction.index,
            operation=operation,
            mode=value.mode,
            result=value.result,
            arguments=value.arguments,
            phase=state.phase,
            guards=state.guards,
            assumptions=state.assumptions,
        )
        if entry not in self.entries and len(self.entries) >= self.limit:
            message = "behavior value origin budget exhausted"
            raise BudgetExceededError(message)
        self.entries[entry] = None

    def record(self, summary: BehaviorSummary) -> BehaviorOrigins:
        """Bind recorded origins to the completed summary's exact expression table.

        Returns:
            One independently addressable analysis consequence, including an empty table.

        """
        return BehaviorOrigins(
            logical_id="behavior-origins:" + summary.logical_id,
            profile=summary.profile,
            request=summary.request,
            summary=revision_of(summary),
            model=MODEL,
            entries=tuple(self.entries),
            support=summary.support,
        )


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Retain every contextual instruction owner and the exact summary value table.

    Returns:
        Typed prerequisites for admission, invalidation and portable closure.

    """
    if not isinstance(record, BehaviorOrigins):
        return ()
    return (
        ("behavior_requests", record.request),
        ("behavior_summaries", record.summary),
        *(
            ("behavior_programs", item)
            for item in sorted({entry.program for entry in record.entries})
        ),
    )
