"""Bounded expression ancestry and source use, independent of function names or tasks."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.characterization.contracts import DependencySource, DependencyUse
from library_deep_enrichment.corpus.backend import BudgetExceededError

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, BehaviorSummary, Term

SOURCE_KINDS = {"global": "module_binding", "call": "unresolved_call_result"}


class Ancestry:
    """Finite ancestry queries with a shared visit budget and no exponential DAG expansion."""

    def __init__(self, terms: tuple[Term, ...], limit: int) -> None:
        """Bind exact table indices and a finite number of visited dependency nodes."""
        self.terms = terms
        self.limit = limit
        self.visits = 0

    def sources(self, root: int, kinds: frozenset[str]) -> tuple[int, ...]:
        """Find reachable source expressions without conflating separate observed reads.

        Returns:
            Sorted indices in this exact expression table.

        Raises:
            BudgetExceededError: The shared ancestry-work limit is exhausted.

        """
        pending = [root] if root >= 0 else []
        seen, result = set(), []
        while pending:
            index = pending.pop()
            if index in seen:
                continue
            seen.add(index)
            self.visits += 1
            if self.visits > self.limit:
                message = "characterization expression ancestry budget exhausted"
                raise BudgetExceededError(message)
            term = self.terms[index]
            if term.op in kinds:
                result.append(index)
            pending.extend(term.args)
        return tuple(sorted(result))


def summary_sources(summary: BehaviorSummary, ancestry: Ancestry) -> tuple[DependencySource, ...]:
    """Locate ambient/result dependencies of values, guards and region contents/extents.

    Returns:
        Attributed expression uses; unsupported transfer precision remains in the source summary.

    """
    uses: dict[int, set[DependencyUse]] = defaultdict(set)
    effects: dict[str, set[DependencyUse]] = defaultdict(set)
    for ordinal, clause in enumerate(summary.clauses):
        roots = (
            ("result", clause.result),
            *(("guard", guard.term) for guard in clause.guards),
            *(("memory_value", item.term) for item in clause.memory),
            *(("region_contents", item.contents) for item in clause.regions),
            *(("region_extent", item.extent) for item in clause.regions),
        )
        for kind, root in roots:
            for index in ancestry.sources(root, frozenset(SOURCE_KINDS)):
                uses[index].add(DependencyUse(kind=kind, clause=ordinal, term=root, point=-1))
        for effect in clause.effects:
            if effect.kind == "ambient_read":
                effects[effect.target].add(
                    DependencyUse(kind="may_effect", clause=ordinal, term=-1, point=-1)
                )
    return (
        *_records(summary.terms, uses, "summary"),
        *(
            DependencySource(
                kind="module_binding",
                name=name,
                space="effect",
                term=-1,
                uses=tuple(sorted(rows, key=lambda item: item.clause)),
                qualification="may_effect_name; not_joined_to_a_particular_read_event",
            )
            for name, rows in sorted(effects.items())
        ),
    )


def program_sources(program: BehaviorProgram, ancestry: Ancestry) -> tuple[DependencySource, ...]:
    """Retain syntactic executable source uses even when interpretation lost their lineage.

    Returns:
        Original instruction dependencies, without asserting that the point is feasible.

    """
    uses: dict[int, set[DependencyUse]] = defaultdict(set)
    for instruction in program.instructions:
        for root in (instruction.value, *instruction.arguments):
            for index in ancestry.sources(root, frozenset(SOURCE_KINDS)):
                uses[index].add(
                    DependencyUse(
                        kind="instruction:" + instruction.op,
                        clause=-1,
                        term=root,
                        point=instruction.index,
                    )
                )
    return _records(program.terms, uses, "program")


def _records(
    terms: tuple[Term, ...], uses: dict[int, set[DependencyUse]], space: str
) -> tuple[DependencySource, ...]:
    return tuple(
        DependencySource(
            kind=SOURCE_KINDS[terms[index].op],
            name=terms[index].value,
            space=space,
            term=index,
            uses=tuple(
                sorted(rows, key=lambda item: (item.clause, item.point, item.kind, item.term))
            ),
            qualification="expression_dependency_under_source_model; runtime_binding_and_external_effects_unqualified",
        )
        for index, rows in sorted(uses.items())
    )
