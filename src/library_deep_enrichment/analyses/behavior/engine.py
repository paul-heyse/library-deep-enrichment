"""Bounded guarded interpretation over owned execution graphs and exact body bindings."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from attrs import define, evolve, field

from library_deep_enrichment.analyses.behavior import control, iterators, regions, sequences
from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorSummary,
    Clause,
    Limits,
    Memory,
    Metric,
    Outcome,
    Precision,
    Term,
)
from library_deep_enrichment.analyses.behavior.fixedpoints import Solution, instantiate, solve
from library_deep_enrichment.analyses.behavior.integrity import program_valid
from library_deep_enrichment.analyses.behavior.memory import Locations
from library_deep_enrichment.analyses.behavior.origins import Origins, OriginValue
from library_deep_enrichment.analyses.behavior.predicates import PredicateChecks
from library_deep_enrichment.analyses.behavior.state import Result, State
from library_deep_enrichment.analyses.behavior.values import Values
from library_deep_enrichment.corpus.backend import BudgetExceededError
from library_deep_enrichment.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.contracts import Instruction

MODEL = "guarded-executable-transfer.v1"
_TERMINALS = {
    "return": Outcome.RETURN,
    "raise": Outcome.RAISE,
    "unwind": Outcome.UNWIND,
    "abort": Outcome.ABORT,
    "suspend": Outcome.SUSPEND,
}
_PYTHON_BOOLEAN_EVALUATIONS = frozenset(
    {"truth", "unary:not", "comparison:in", "comparison:not in"}
)


@define
class Interpreter:
    """Interpret a finite contextual population; unknown paths remain observable."""

    limits: Limits
    targets: dict[str, BehaviorProgram] = field(factory=dict)
    solution: Solution | None = None
    steps: int = 0
    states: int = 0
    calls: int = 0
    dependencies: set[str] = field(factory=set)
    values: Values = field(init=False)
    predicates: PredicateChecks = field(init=False)
    origins: Origins = field(init=False)

    def __attrs_post_init__(self) -> None:
        """Allocate a bounded value table for this root interpretation."""
        self.values = Values(self.limits.terms)
        self.predicates = PredicateChecks(self.limits.solver_queries, self.limits.solver_ms)
        self.origins = Origins(self.limits.terms * 4)

    def summarize(self, program: BehaviorProgram) -> BehaviorSummary:
        """Compute guarded outcomes under an explicit finite abstraction.

        Returns:
            A reproducible summary with precision, dependencies and execution counters.

        Raises:
            BudgetExceededError: A finite interpretation or result budget is exhausted.

        """
        if self.solution is None:
            self.solution = solve((program, *self.targets.values()), self.targets, self.limits)
        arguments = tuple(
            self.values.add(Term(op="argument", value=name, ty=self._parameter_type(program, name)))
            for name in program.parameters
        )
        results = self._run(program, arguments, State(phase=program.phase), ())
        if len(results) > self.limits.clauses:
            message = "behavior clause budget exhausted after fixed-point projection"
            raise BudgetExceededError(message)
        clauses = tuple(self._clause(result) for result in results)
        frontier = tuple(dict.fromkeys(item for clause in clauses for item in clause.frontier))
        return BehaviorSummary(
            logical_id=f"behavior-summary:{program.request}:{program.owner}",
            profile=program.profile,
            request=program.request,
            program=revision_of(program),
            model="guarded-executable-transfer.v3"
            if any(
                body.model == "rust-mir-execution.v4" for body in (program, *self.targets.values())
            )
            else "guarded-executable-transfer.v2"
            if any(
                body.model == "rust-mir-execution.v3" for body in (program, *self.targets.values())
            )
            else MODEL,
            terms=tuple(self.values.terms),
            clauses=clauses,
            precision=Precision.CONSERVATIVE if frontier else Precision.CLOSED,
            frontier=frontier,
            dependencies=tuple(sorted(self.dependencies)),
            metrics=(
                Metric(name="instructions", value=self.steps),
                Metric(name="states", value=self.states),
                Metric(name="calls", value=self.calls),
                Metric(name="terms", value=len(self.values.terms)),
                Metric(name="solver_queries", value=self.predicates.calls),
                Metric(name="shared_fixedpoint_steps", value=self.solution.steps),
                Metric(name="shared_fixedpoint_iterations", value=self.solution.iterations),
                *(
                    Metric(name="solver_" + key.value, value=value)
                    for key, value in sorted(self.predicates.outcomes.items())
                ),
            ),
            support=program.support,
        )

    @staticmethod
    def _parameter_type(program: BehaviorProgram, name: str) -> str:
        types = {
            term.ty
            for term in program.terms
            if term.op == "local" and term.value == name and term.ty != "unknown"
        }
        return next(iter(types)) if len(types) == 1 else "unknown"

    def _clause(self, result: Result) -> Clause:
        state = result.state
        return Clause(
            guards=state.guards,
            outcome=result.outcome,
            result=result.value,
            memory=tuple(
                Memory(
                    location=self.values.render(location),
                    term=value,
                    strong=location in state.strong,
                )
                for location, value in sorted(state.memory.items())
            ),
            effects=state.effects,
            assumptions=state.assumptions,
            frontier=state.frontier,
            regions=tuple(value for _, value in sorted(state.regions.items())),
        )

    def _tick(self) -> None:
        self.steps += 1
        if self.steps > self.limits.steps:
            message = "behavior instruction budget exhausted; no completed summary"
            raise BudgetExceededError(message)

    def _run(
        self,
        program: BehaviorProgram,
        arguments: tuple[int, ...],
        inherited: State,
        stack: tuple[str, ...],
    ) -> tuple[Result, ...]:
        program_valid(program, self.limits)
        key = revision_of(program)
        self.dependencies.add(key)
        state = inherited.copy()
        state.locals = dict(zip(program.parameters, arguments, strict=True))
        state.flow = "normal"
        state.frontier = tuple(dict.fromkeys((*state.frontier, *program.frontier)))
        if key in stack or len(stack) >= self.limits.call_depth:
            return self._envelope(program, arguments, state, "recursive_or_depth_projection")
        return self._worklist(program, state, (*stack, key))

    def _envelope(
        self, program: BehaviorProgram, arguments: tuple[int, ...], state: State, reason: str
    ) -> tuple[Result, ...]:
        assert self.solution is not None
        envelope = self.solution.envelopes[revision_of(program)]
        self.dependencies.update(self.solution.dependencies[revision_of(program)])
        result = state.copy()
        result.unknown(
            reason,
            "relation",
            program.owner,
            "checked finite value/effect fixed point; path correlation is widened",
        )
        result.effects = tuple(
            dict.fromkeys(
                (
                    *result.effects,
                    *sorted(
                        envelope.effects,
                        key=lambda effect: (effect.point, effect.kind, effect.target, effect.phase),
                    ),
                )
            )
        )
        if any(
            effect.kind
            in {"memory_write", "unknown_call", "unknown_dispatch", "unknown", "release"}
            for effect in envelope.effects
        ):
            regions.escape(self.values, result, arguments)
            Locations(program, self.values).havoc(result, "fixedpoint:" + program.owner)
        results = []
        for outcome in sorted(envelope.outcomes):
            if outcome == Outcome.RETURN:
                for atom in sorted(
                    envelope.values, key=lambda value: (value.kind, value.value, value.ty)
                ):
                    value = instantiate(atom, arguments)
                    value = value if isinstance(value, int) else self.values.add(value)
                    results.append(Result(outcome=outcome, value=value, state=result.copy()))
            else:
                results.append(
                    Result(
                        outcome=outcome,
                        value=self.values.unknown("fixedpoint:" + outcome.value, fresh=True),
                        state=result.copy(),
                    )
                )
        return tuple(results)

    def _worklist(
        self, program: BehaviorProgram, initial: State, stack: tuple[str, ...]
    ) -> tuple[Result, ...]:
        graph = control.index(program)
        queue = deque([(program.entry, initial)])
        seen: set[tuple] = set()
        visits: dict[int, int] = {}
        results: list[Result] = []
        locations = Locations(program, self.values)
        while queue:
            block, state = queue.popleft()
            identity = (block, state.key())
            if identity in seen:
                if block in graph.cyclic:
                    results.append(control.cycle(locations, state, block))
                continue
            seen.add(identity)
            self._state_tick()
            visits[block] = visits.get(block, 0) + 1
            if block in graph.cyclic and visits[block] > self.limits.widen_after:
                state = self._widen(state, program, block)
                arguments = tuple(initial.locals[name] for name in program.parameters)
                results.extend(
                    self._envelope(program, arguments, state, "loop_fixedpoint_projection")
                )
                continue
            active, terminated = self._block(locations, graph.instructions[block], state, stack)
            results.extend(terminated)
            for current in active:
                successors, outcomes = control.route(
                    locations, current, graph.edges[block], self.predicates
                )
                queue.extend(successors)
                results.extend(outcomes)
            if len(results) > self.limits.clauses:
                message = "behavior clause budget exhausted; no completed summary"
                raise BudgetExceededError(message)
        if not results:
            state = initial.copy()
            state.unknown(
                "no_finite_outcome",
                "termination",
                program.owner,
                "no terminating path was established",
            )
            results.append(
                Result(
                    outcome=Outcome.DIVERGE, value=self.values.unknown("divergence"), state=state
                )
            )
        return tuple(results)

    def _state_tick(self) -> None:
        self.states += 1
        if self.states > self.limits.states:
            message = "behavior state budget exhausted; no completed summary"
            raise BudgetExceededError(message)

    def _widen(self, state: State, program: BehaviorProgram, block: int) -> State:
        widened = state.copy()
        widened.locals = {
            name: self.values.unknown(f"widen:{program.owner}:{block}:{name}")
            for name in state.locals
        }
        widened.memory.clear()
        widened.strong.clear()
        widened.regions = {
            root: evolve(
                region,
                contents=self.values.unknown(f"widen:region:{root}"),
                extent=self.values.unknown(f"widen:extent:{root}", "python:int"),
                unique=False,
                escaped=True,
            )
            for root, region in state.regions.items()
        }
        widened.opaque_heap = True
        widened.guards = ()
        widened.unknown(
            "loop_widening",
            "value",
            str(block),
            "loop state widened; no cardinality or termination guarantee",
        )
        return widened

    def _block(
        self,
        locations: Locations,
        instructions: tuple[Instruction, ...],
        state: State,
        stack: tuple[str, ...],
    ) -> tuple[list[State], list[Result]]:
        active = [state]
        results: list[Result] = []
        for instruction in instructions:
            following: list[State] = []
            for current in active:
                self._tick()
                if instruction.op in _TERMINALS:
                    value = locations.resolve(instruction.value, current)
                    self.origins.observe(
                        locations.program,
                        instruction,
                        current,
                        value=OriginValue(
                            result=value,
                            arguments=locations.resolved_inputs.get(instruction.value, ()),
                            mode=instruction.op,
                        ),
                    )
                    results.append(
                        Result(
                            outcome=_TERMINALS[instruction.op],
                            value=value,
                            state=current.copy(),
                        )
                    )
                    if instruction.op == "suspend":
                        following.append(current)
                elif instruction.op == "call":
                    following.extend(self._call(locations, instruction, current, stack))
                elif instruction.op == "evaluate":
                    following.extend(self._evaluation(locations, instruction, current))
                else:
                    self._instruction(locations, instruction, current)
                    following.append(current)
            active = following
        return active, results

    def _evaluation(
        self, locations: Locations, instruction: Instruction, state: State
    ) -> list[State]:
        if instruction.target == "local_lookup":
            return self._local_load(locations, instruction, state)
        if instruction.target == "sequence_expansion":
            expression = locations.program.terms[instruction.value]
            source = locations.resolve(expression.args[0], state)
            expanded = sequences.expand(self.values, state, source, str(instruction.index))
            if expanded is not None:
                state.locals[instruction.destination] = expanded
                self.origins.observe(
                    locations.program,
                    instruction,
                    state,
                    value=OriginValue(
                        result=expanded, arguments=(source,), mode="sequence_expansion"
                    ),
                )
                return [state]
        ordinary = state.copy()
        value = locations.resolve(instruction.value, ordinary)
        ordinary.locals[instruction.destination] = value
        ordinary.flow = "returned"
        result = self.values.terms[value]
        if instruction.target == "truth" and result.op != "truth" and result.ty.endswith(":bool"):
            self._evaluated_origin(locations, instruction, ordinary, value)
            return [ordinary]
        assumption = "python:ordinary_primitive:" + instruction.target
        ordinary.assumptions = tuple(dict.fromkeys((*ordinary.assumptions, assumption)))
        ordinary.flow = "returned"
        ordinary.unknown(
            "python_dynamic_dispatch",
            "execution",
            str(instruction.index),
            "primitive result is conditional on ordinary runtime semantics",
        )
        self._evaluated_origin(locations, instruction, ordinary, value)
        return [
            ordinary,
            *self._opaque_call(
                locations,
                instruction,
                state.copy(),
                arguments=locations.inputs(instruction.value, state),
            ),
        ]

    def _evaluated_origin(
        self, locations: Locations, instruction: Instruction, state: State, value: int
    ) -> None:
        self.origins.observe(
            locations.program,
            instruction,
            state,
            value=OriginValue(
                result=value,
                arguments=locations.resolved_inputs.get(instruction.value, ()),
                mode="ordinary_evaluation",
            ),
        )

    def _local_load(
        self, locations: Locations, instruction: Instruction, state: State
    ) -> list[State]:
        local = locations.program.terms[instruction.value]
        result = state.copy()
        if local.value in result.locals:
            result.locals[instruction.destination] = result.locals[local.value]
            result.flow = "returned"
        else:
            result.locals["$exception"] = self.values.add(
                Term(op="aggregate", value="UnboundLocalError")
            )
            result.flow = "error"
        self.origins.observe(
            locations.program,
            instruction,
            result,
            value=OriginValue(
                result=result.locals[
                    "$exception" if result.flow == "error" else instruction.destination
                ],
                arguments=(),
                mode="local_" + result.flow,
            ),
        )
        return [result]

    def _instruction(self, locations: Locations, instruction: Instruction, state: State) -> None:
        op = instruction.op
        point = f"{locations.program.owner}:{instruction.index}"
        if op == "assign":
            value = locations.resolve(instruction.value, state)
            state.locals[instruction.destination] = value
            self.origins.observe(
                locations.program,
                instruction,
                state,
                value=OriginValue(
                    result=value,
                    arguments=locations.resolved_inputs.get(instruction.value, ()),
                    mode="assignment",
                ),
            )
        elif op in {"storage_live", "storage_dead"}:
            state.locals.pop(instruction.destination, None)
        elif op == "write":
            locations.write(instruction, state)
        elif op == "drop":
            state.effect(
                "release", self.values.render(locations.resolve(instruction.value, state)), point
            )
            state.unknown(
                "drop_glue",
                "effects",
                point,
                "release target effects require a qualified callee summary",
            )
            locations.havoc(state, point)
        elif op == "effect":
            state.effect(instruction.target, "", point)
        elif op not in {"nop", "assert"}:
            state.effect("unknown", instruction.target, point)
            locations.havoc(state, point)

    def _call(
        self, locations: Locations, instruction: Instruction, state: State, stack: tuple[str, ...]
    ) -> list[State]:
        self.calls += 1
        arguments = tuple(locations.resolve(index, state) for index in instruction.arguments)
        if len(arguments) == 1 and instruction.target in {"implicit:iter", "implicit:next"}:
            operation = (
                iterators.create if instruction.target == "implicit:iter" else iterators.advance
            )
            value = operation(
                self.values, state, arguments[0], f"{locations.program.owner}:{instruction.index}"
            )
            if value is not None:
                state.locals[instruction.destination] = value
                state.flow = "error" if state.flow == "error" else "returned"
                self._intrinsic_origin(locations, instruction, state, arguments)
                return [state]
        if instruction.target == "internal:list_append":
            value = regions.append(
                self.values, state, arguments, f"{locations.program.owner}:{instruction.index}"
            )
            if value is not None:
                state.locals[instruction.destination] = value
                state.flow = "returned"
                self._intrinsic_origin(locations, instruction, state, arguments)
                return [state]
        target = self._call_target(locations, instruction, state)
        if target is None or len(target.parameters) != len(arguments):
            return self._opaque_call(locations, instruction, state, arguments=arguments)
        outputs = self._run(target, arguments, state, stack)
        result = []
        for output in outputs:
            current = output.state.copy()
            current.locals = dict(state.locals)
            if current.opaque_heap:
                locations.havoc(current, f"callee:{target.owner}")
            current.locals[instruction.destination] = output.value
            self.origins.observe(
                locations.program,
                instruction,
                current,
                value=OriginValue(
                    result=output.value,
                    arguments=arguments,
                    mode="callee_" + output.outcome,
                ),
            )
            current.flow = {
                Outcome.RETURN: "returned",
                Outcome.ABORT: "abort",
                Outcome.DIVERGE: "diverge",
                Outcome.SUSPEND: "suspend",
                Outcome.UNKNOWN: "unknown",
            }.get(output.outcome, "error")
            if current.flow == "error":
                current.locals["$exception"] = output.value
            if output.outcome == Outcome.UNKNOWN:
                normal = current.copy()
                normal.flow = "returned"
                result.append(normal)
            result.append(current)
        return result

    def _call_target(
        self, locations: Locations, instruction: Instruction, state: State
    ) -> BehaviorProgram | None:
        target = self.targets.get(instruction.target)
        if target is not None or instruction.target or instruction.value < 0:
            return target
        value = self.values.terms[locations.resolve(instruction.value, state)]
        if value.op == "function" and not value.args:
            target = self.targets.get(value.value)
        if target is None:
            state.unknown(
                "callable_target",
                "call",
                str(instruction.index),
                "evaluated callable is not one exact selected function item",
            )
        return target

    def _intrinsic_origin(
        self,
        locations: Locations,
        instruction: Instruction,
        state: State,
        arguments: tuple[int, ...],
    ) -> None:
        self.origins.observe(
            locations.program,
            instruction,
            state,
            value=OriginValue(
                result=state.locals[instruction.destination],
                arguments=arguments,
                mode="intrinsic_" + state.flow,
            ),
        )

    def _opaque_call(
        self,
        locations: Locations,
        instruction: Instruction,
        state: State,
        *,
        arguments: tuple[int, ...],
    ) -> list[State]:
        point = f"{locations.program.owner}:{instruction.index}"
        regions.escape(self.values, state, arguments)
        state.effect("unknown_call", instruction.target, point)
        locations.havoc(state, point)
        error = state.copy()
        error.flow = "error"
        error.locals["$exception"] = self.values.unknown("exception:" + point, fresh=True)
        other = state.copy()
        other.flow = "unknown"
        other.unknown(
            "opaque_control",
            "termination",
            point,
            "unresolved call can diverge, abort or suspend before returning",
        )
        # Effects occur before the returned value becomes available. Retain which
        # evaluated call produced it, while keeping independent evaluations distinct.
        event = self.values.unknown("call_result:" + point, fresh=True)
        result_type = (
            "model:bool"
            if locations.program.language == "python"
            and instruction.op == "evaluate"
            and instruction.target in _PYTHON_BOOLEAN_EVALUATIONS
            else "unknown"
        )
        state.locals[instruction.destination] = self.values.add(
            Term(
                op="call",
                args=(event, *arguments),
                value=instruction.target or point,
                ty=result_type,
            )
        )
        self.origins.observe(
            locations.program,
            instruction,
            state,
            value=OriginValue(
                result=state.locals[instruction.destination],
                arguments=arguments,
                mode="opaque_call_return",
            ),
        )
        state.flow = "returned"
        return [state, error, other]
