"""Explicit abstract execution state; cloning preserves independent guarded paths."""

from __future__ import annotations

from attrs import define, evolve, field, frozen

from library_deep_enrichment.analyses.behavior.contracts import (
    Effect,
    Frontier,
    Guard,
    Outcome,
    Region,
)


@define
class State:
    """One abstract path with separated locals, reachable memory and uncertainty."""

    locals: dict[str, int] = field(factory=dict)
    memory: dict[int, int] = field(factory=dict)
    strong: set[int] = field(factory=set)
    regions: dict[int, Region] = field(factory=dict)
    guards: tuple[Guard, ...] = ()
    effects: tuple[Effect, ...] = ()
    assumptions: tuple[str, ...] = ()
    frontier: tuple[Frontier, ...] = ()
    flow: str = "normal"
    phase: str = "invoke"
    opaque_heap: bool = False

    def copy(self) -> State:
        """Clone mutable locations while retaining immutable evidence values.

        Returns:
            An independently mutable abstract path.

        """
        return evolve(
            self,
            locals=dict(self.locals),
            memory=dict(self.memory),
            strong=set(self.strong),
            regions=dict(self.regions),
        )

    def key(self) -> tuple:
        """Identify convergence using state contents, not object identity.

        Returns:
            An immutable key for exact abstract-state deduplication.

        """
        return (
            tuple(sorted(self.locals.items())),
            tuple(sorted(self.memory.items())),
            tuple(sorted(self.strong)),
            tuple(sorted(self.regions.items())),
            self.guards,
            self.effects,
            self.assumptions,
            self.frontier,
            self.flow,
            self.phase,
            self.opaque_heap,
        )

    def effect(self, kind: str, target: str, point: str) -> None:
        """Record a may-effect; repeated events do not imply a multiplicity bound."""
        item = Effect(kind=kind, target=target, point=point, phase=self.phase)
        if item not in self.effects:
            self.effects = (*self.effects, item)

    def unknown(self, code: str, dimension: str, point: str, detail: str) -> None:
        """Retain a precision loss in the affected path."""
        item = Frontier(code=code, dimension=dimension, point=point, detail=detail)
        if item not in self.frontier:
            self.frontier = (*self.frontier, item)


@frozen(kw_only=True)
class Result:
    """One terminal or suspended value with its full abstract path state."""

    outcome: Outcome
    value: int
    state: State
