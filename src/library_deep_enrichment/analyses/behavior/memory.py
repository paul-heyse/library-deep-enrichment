"""Location-aware value transfer; opaque callees cannot preserve unobserved heap contents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import define, evolve, field

from library_deep_enrichment.analyses.behavior import regions
from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, Instruction, Term
from library_deep_enrichment.analyses.behavior.locations import overlaps, replace_path, stack_destination

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.state import State
    from library_deep_enrichment.analyses.behavior.values import Values

_ACCESSES = frozenset({"field", "index", "deref", "slice"})


@define
class Locations:
    """Resolve one body's value DAG against an independent abstract path."""

    program: BehaviorProgram
    values: Values
    resolved_inputs: dict[int, tuple[int, ...]] = field(factory=dict, init=False)

    def resolve(self, index: int, state: State, *, load: bool = True) -> int:
        """Substitute locals and load fields without recursive Python stack growth.

        Returns:
            An analysis value, including an explicit unknown on opaque reads.

        """
        if index < 0:
            return self.values.unknown("missing_value")
        ready: dict[int, int] = {}
        pending = [(index, False)]
        while pending:
            key, visited = pending.pop()
            if key in ready:
                continue
            term = self.program.terms[key]
            if not visited:
                pending.append((key, True))
                pending.extend(
                    (child, False) for child in reversed(term.args) if child not in ready
                )
                continue
            args = tuple(ready[child] for child in term.args)
            self.resolved_inputs[key] = args
            ready[key] = self._value(evolve(term, args=args), state, load=load or key != index)
        return ready[index]

    def _value(self, term: Term, state: State, *, load: bool) -> int:
        if term.op in {"list", "dict", "set", "list_from_sequence"}:
            return regions.allocate(self.values, state, term, self.program.owner)
        if term.op == "local":
            if term.value in state.locals:
                return state.locals[term.value]
            state.unknown(
                "uninitialized_local", "value", term.value, "no value established for this local"
            )
            return self.values.unknown("uninitialized:" + term.value, term.ty, fresh=True)
        if term.op == "unknown":
            return self.values.unknown(term.value, term.ty, fresh=True)
        if term.op == "global":
            state.effect("ambient_read", term.value, self.program.owner)
            state.unknown(
                "global_binding",
                "value",
                term.value,
                "runtime binding and mutation require an explicit contract",
            )
            event = self.values.unknown("global_read:" + term.value, fresh=True)
            term = evolve(term, args=(*term.args, event))
        return self._access(term, state, load=load)

    def _access(self, term: Term, state: State, *, load: bool) -> int:
        region = state.regions.get(term.args[0]) if term.args else None
        if region is not None and term.op == "length":
            return region.extent
        if region is not None and term.op in _ACCESSES and load:
            term = evolve(term, args=(region.contents, *term.args[1:]))
        if not load and term.op in _ACCESSES:
            return self.values.add(
                Term(op="location", args=term.args, value=term.op + ":" + term.value, ty=term.ty)
            )
        value = self.values.add(term)
        if term.op in _ACCESSES and load:
            if state.opaque_heap and (region is None or region.escaped):
                return self.values.unknown(f"opaque_heap:{value}", term.ty, fresh=True)
            if self.program.language == "python":
                assumption = "python:ordinary_field_and_index_access"
                if assumption not in state.assumptions:
                    state.assumptions = (*state.assumptions, assumption)
        return value

    def write(self, instruction: Instruction, state: State) -> None:
        """Update proven by-value Rust places strongly; preserve uncertain aliases as weak writes."""
        value = self.resolve(instruction.value, state)
        destination = stack_destination(self.program, instruction.arguments[0])
        if destination is not None and destination.local in state.locals:
            root = self.values.add(
                Term(op="location", value=self.program.owner + ":" + destination.local)
            )
            location = root
            path = []
            for original_step in destination.path:
                indices = tuple(self.resolve(child, state) for child in original_step.args[1:])
                step = evolve(original_step, args=(root, *indices))
                path.append(step)
                location = self.values.add(
                    Term(op="location", args=(location, *indices), value=step.op + ":" + step.value)
                )
            state.locals[destination.local] = replace_path(
                self.values, state.locals[destination.local], tuple(path), value
            )
            for prior in tuple(state.memory):
                if overlaps(self.values, prior, location):
                    state.memory.pop(prior)
                    state.strong.discard(prior)
            state.memory[location] = value
            state.strong.add(location)
            state.effect("memory_write", self.values.render(location), str(instruction.index))
            return
        location = self.resolve(instruction.arguments[0], state, load=False)
        previous = self.values.unknown("weak_previous:" + str(location), fresh=True)
        # A new ambiguous write invalidates every earlier location equality it may alias.
        state.memory.clear()
        state.strong.clear()
        regions.escape(self.values, state, self.inputs(instruction.arguments[0], state))
        regions.havoc(self.values, state, str(instruction.index))
        state.memory[location] = self.values.add(Term(op="join", args=(previous, value)))
        state.effect("memory_write", self.values.render(location), str(instruction.index))
        state.unknown(
            "may_alias_write",
            "memory",
            str(instruction.index),
            "unique target and alias separation not established",
        )
        state.opaque_heap = True

    def havoc(self, state: State, point: str) -> None:
        """Forget reachable mutable contents after an unresolved effect boundary."""
        if self.program.language == "python":
            state.assumptions = tuple(
                dict.fromkeys(
                    (*state.assumptions, "python:separation_excludes_reflective_frame_mutation")
                )
            )
        state.memory.clear()
        state.strong.clear()
        regions.havoc(self.values, state, point)
        state.locals = {
            name: value
            if value in state.regions or self.values.immutable(value)
            else self.values.unknown(
                "reachable:" + point + ":" + name, self.values.terms[value].ty, fresh=True
            )
            for name, value in state.locals.items()
        }
        state.opaque_heap = True
        state.unknown("unknown_effect", "memory", point, "callee may mutate reachable regions")

    def inputs(self, index: int, state: State) -> tuple[int, ...]:
        """Collect evaluated input references without repeating expression evaluation.

        Returns:
            The actual local values reachable through one operation's expression DAG.

        """
        pending, visited, result = [index], set(), set()
        while pending:
            current = pending.pop()
            if current < 0 or current in visited:
                continue
            visited.add(current)
            term = self.program.terms[current]
            if term.op == "local" and term.value in state.locals:
                result.add(state.locals[term.value])
            pending.extend(term.args)
        return tuple(sorted(result))
