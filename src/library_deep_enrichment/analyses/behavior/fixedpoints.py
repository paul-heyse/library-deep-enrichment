"""Finite interprocedural value/effect envelopes with checked post-fixed points."""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx
from attrs import define, frozen

from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, Effect, Outcome, Term
from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.corpus.backend import BudgetExceededError
from library_deep_enrichment.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.contracts import Instruction, Limits


@frozen(kw_only=True)
class Atom:
    """An exact formal argument/literal, or top for all values; absence is bottom."""

    kind: str
    value: str = ""
    ty: str = "unknown"


TOP = frozenset({Atom(kind="top")})
type Domain = frozenset[Atom]


def join(first: Domain, second: Domain, limit: int) -> Domain:
    """Join a finite value domain, widening excess alternatives to absorbing top.

    Returns:
        A finite over-approximation of both operands.

    """
    result = first | second
    return TOP if result >= TOP or len(result) > limit else result


@frozen(kw_only=True)
class Envelope:
    """A path-insensitive result that may safely replace exhausted relational depth."""

    values: Domain = frozenset()
    effects: frozenset[Effect] = frozenset()
    outcomes: frozenset[Outcome] = frozenset()


@frozen(kw_only=True)
class Solution:
    """A complete finite model and execution-derived convergence counters."""

    envelopes: dict[str, Envelope]
    dependencies: dict[str, tuple[str, ...]]
    recursive: frozenset[str]
    iterations: int
    steps: int
    checked: bool


def _expression(program: BehaviorProgram, index: int, locals_: dict[str, Domain]) -> Domain:
    if index < 0:
        return TOP
    term = program.terms[index]
    if term.op == "literal":
        return frozenset({Atom(kind="literal", value=term.value, ty=term.ty)})
    if term.op == "local":
        return locals_.get(term.value, frozenset())
    return TOP


def _ambient(program: BehaviorProgram) -> set[Effect]:
    return {
        Effect(
            kind="ambient_read", target=term.value, phase="invoke_or_cleanup", point=program.owner
        )
        for term in program.terms
        if term.op == "global"
    }


def _substitute(values: Domain, arguments: tuple[Domain, ...], limit: int) -> Domain:
    result: Domain = frozenset()
    for atom in values:
        if atom.kind == "parameter":
            position = int(atom.value)
            selected = arguments[position] if position < len(arguments) else TOP
        else:
            selected = frozenset({atom})
        result = join(result, selected, limit)
    return result


@define
class Transfers:
    """Monotone transfers over finite owner/call and local-value populations."""

    limits: Limits
    targets: dict[str, str]
    steps: int = 0

    def body(
        self, program: BehaviorProgram, summaries: dict[str, Envelope], *, recursive: bool
    ) -> Envelope:
        """Reach a finite local envelope for the current callee approximations.

        Returns:
            May-values, may-effects and possible outcomes including termination uncertainty.

        Raises:
            BudgetExceededError: The bounded fixed-point transfer work is exhausted.

        """
        locals_ = {
            name: frozenset({Atom(kind="parameter", value=str(index))})
            for index, name in enumerate(program.parameters)
        }
        effects = _ambient(program)
        outcomes: set[Outcome] = set()
        returned: Domain = frozenset()
        if recursive:
            outcomes.update(
                (Outcome.DIVERGE, Outcome.ABORT if program.language == "rust" else Outcome.RAISE)
            )
        graph = nx.DiGraph()
        graph.add_nodes_from(program.blocks)
        graph.add_edges_from((edge.source, edge.target) for edge in program.edges)
        if not nx.is_directed_acyclic_graph(graph):
            outcomes.add(Outcome.DIVERGE)
        while True:
            before = dict(locals_)
            for instruction in program.instructions:
                self.steps += 1
                if self.steps > self.limits.steps:
                    message = "behavior fixed-point work budget exhausted; no solution admitted"
                    raise BudgetExceededError(message)
                value, extra = self._instruction(program, instruction, locals_, summaries)
                effects.update(extra.effects)
                outcomes.update(extra.outcomes)
                if instruction.destination:
                    locals_[instruction.destination] = join(
                        locals_.get(instruction.destination, frozenset()),
                        value,
                        self.limits.clauses,
                    )
                if instruction.op == "return":
                    returned = join(returned, value, self.limits.clauses)
            if before == locals_:
                break
        return Envelope(values=returned, effects=frozenset(effects), outcomes=frozenset(outcomes))

    def _instruction(
        self,
        program: BehaviorProgram,
        instruction: Instruction,
        locals_: dict[str, Domain],
        summaries: dict[str, Envelope],
    ) -> tuple[Domain, Envelope]:
        value = _expression(program, instruction.value, locals_)
        if instruction.op == "call":
            key = self.targets.get(instruction.target)
            if key is not None:
                callee = summaries[key]
                arguments = tuple(
                    _expression(program, index, locals_) for index in instruction.arguments
                )
                return _substitute(callee.values, arguments, self.limits.clauses), callee
            return TOP, Envelope(
                values=TOP,
                effects=frozenset({self._effect(program, instruction, "unknown_call")}),
                outcomes=frozenset(Outcome),
            )
        if instruction.op in {"return", "raise", "unwind", "abort", "suspend"}:
            return value, Envelope(outcomes=frozenset({Outcome(instruction.op)}))
        if instruction.op == "evaluate":
            return value if instruction.target == "local_lookup" else TOP, Envelope(
                effects=frozenset({self._effect(program, instruction, "unknown_dispatch")})
                if instruction.target != "local_lookup"
                else frozenset(),
                outcomes=frozenset({Outcome.RAISE, Outcome.UNKNOWN})
                if instruction.target != "local_lookup"
                else frozenset({Outcome.RAISE}),
            )
        kind = {
            "write": "memory_write",
            "drop": "release",
            "unknown": "unknown",
            "effect": instruction.target,
        }.get(instruction.op)
        effects = frozenset({self._effect(program, instruction, kind)}) if kind else frozenset()
        extra = (
            frozenset({Outcome.UNKNOWN}) if instruction.op in {"unknown", "drop"} else frozenset()
        )
        return value, Envelope(effects=effects, outcomes=extra)

    @staticmethod
    def _effect(program: BehaviorProgram, instruction: Instruction, kind: str) -> Effect:
        return Effect(
            kind=kind,
            target=instruction.target,
            phase="invoke_or_cleanup",
            point=f"{program.owner}:{instruction.index}",
        )


def _node(value: object) -> str:
    require("fixed-point graph returned a non-string owner", condition=isinstance(value, str))
    assert isinstance(value, str)
    return value


def solve(
    programs: tuple[BehaviorProgram, ...], targets: dict[str, BehaviorProgram], limits: Limits
) -> Solution:
    """Compute recursive SCC envelopes and independently reapply transfers to check closure.

    Returns:
        A checked post-fixed point; exhaustion is a failed analysis, never an empty solution.

    Raises:
        BudgetExceededError: The dynamic-call dependency graph exceeds the finite work bound.

    """
    bodies = {revision_of(program): program for program in programs}
    target_ids = {name: revision_of(program) for name, program in targets.items()}
    require(
        "fixed-point target escaped the selected population",
        condition=all(key in bodies for key in target_ids.values()),
    )
    graph = nx.DiGraph()
    graph.add_nodes_from(bodies)
    graph.add_edges_from(
        (key, target_ids[item.target])
        for key, body in bodies.items()
        for item in body.instructions
        if item.op == "call" and item.target in target_ids
    )
    # Value-sensitive execution can reach an item passed in by a caller. The fallback
    # envelope deliberately retains top; its dependency/SCC scope must include every
    # selected body, even when no static explicit call edge points at that body.
    dynamic = tuple(
        key
        for key, body in bodies.items()
        if any(
            item.op == "call" and not item.target and item.value >= 0 for item in body.instructions
        )
    )
    if len(dynamic) * len(bodies) > limits.steps:
        message = "callable fixed-point dependency edge budget exhausted before graph growth"
        raise BudgetExceededError(message)
    graph.add_edges_from((key, target) for key in dynamic for target in bodies)
    components = tuple(
        frozenset(_node(value) for value in component)
        for component in nx.strongly_connected_components(graph)
    )
    recursive = frozenset(
        key
        for component in components
        for key in component
        if len(component) > 1 or graph.has_edge(key, key)
    )
    summaries = dict.fromkeys(bodies, Envelope())
    transfers = Transfers(limits, target_ids)
    iterations = 0
    # NetworkX emits sink SCCs before their callers for this depth-first component traversal.
    # Repeating the complete finite set makes convergence independent of that traversal order.
    while True:
        previous = dict(summaries)
        for component in components:
            for key in sorted(component):
                summaries[key] = transfers.body(bodies[key], summaries, recursive=key in recursive)
        iterations += 1
        if summaries == previous:
            break
    checked = all(
        transfers.body(body, summaries, recursive=key in recursive) == summaries[key]
        for key, body in sorted(bodies.items())
    )
    require("behavior fixed-point postcondition failed", condition=checked)
    dependencies = {
        key: tuple(sorted({key, *(_node(value) for value in nx.descendants(graph, key))}))
        for key in bodies
    }
    return Solution(
        envelopes=summaries,
        dependencies=dependencies,
        recursive=recursive,
        iterations=iterations,
        steps=transfers.steps,
        checked=checked,
    )


def instantiate(atom: Atom, arguments: tuple[int, ...]) -> Term | int:
    """Instantiate a checked envelope's finite value atom at one contextual call.

    Returns:
        The actual argument identity, an exact literal, or explicit value top.

    """
    if atom.kind == "parameter" and int(atom.value) < len(arguments):
        return arguments[int(atom.value)]
    if atom.kind == "literal":
        return Term(op="literal", value=atom.value, ty=atom.ty)
    return Term(op="unknown", value="fixed_point_value_top")
