"""Typed stage graph with digest-based up-to-date checks.

Stages are pure functions over declared artifact identifiers. A stage key is
computed from its input digests, adapter identity, rule and schema revisions,
configuration, and declared environment facts. Timestamps never participate, so
refreshing an unchanged source does not invalidate downstream work.

Scheduling and semantic invalidation are related but distinct: this module
decides what to *run*; :mod:`library_guides.stages.impact` decides which reviewed
claims a change reopens.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from attrs import evolve, field, frozen

from library_guides.store.digests import canonical_bytes, digest_bytes

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from library_guides.models.records import ExtractionReceipt

__all__ = [
    "CyclicStageGraphError",
    "StageContext",
    "StageDefinition",
    "StageGraph",
    "StagePlan",
    "StageResult",
    "StageRunner",
    "UnknownStageError",
    "stage_key",
]


class UnknownStageError(LookupError):
    """Raised when a stage names an input no registered stage produces."""


class CyclicStageGraphError(ValueError):
    """Raised when the declared stage dependencies contain a cycle."""


@frozen(kw_only=True)
class StageContext:
    """Everything a stage may read, and where it may write."""

    library_id: str | None = field(default=None)
    profile_id: str | None = field(default=None)
    workspace_root: Path = field()
    cache_root: Path = field()
    staging_root: Path = field()
    configuration: Mapping[str, object] = field(factory=dict)
    environment_facts: Mapping[str, str] = field(factory=dict)


@frozen(kw_only=True)
class StageResult:
    """What one stage produced."""

    stage_id: str = field()
    receipt: ExtractionReceipt = field()
    output_digests: Mapping[str, str] = field(factory=dict)


class StageRunner(Protocol):
    """Callable signature every stage implementation satisfies."""

    def __call__(self, context: StageContext) -> StageResult:
        """Execute the stage.

        Returns:
            The stage result, including its receipt.

        """
        ...


@frozen(kw_only=True)
class StageDefinition:
    """One registered stage and its declared dependencies."""

    stage_id: str = field()
    inputs: tuple[str, ...] = field(default=())
    outputs: tuple[str, ...] = field(default=())
    adapter_id: str = field()
    schema_revision: str = field()
    runner: StageRunner = field()


def stage_key(
    definition: StageDefinition,
    *,
    input_digests: Mapping[str, str],
    configuration: Mapping[str, object],
    environment_facts: Mapping[str, str],
) -> str:
    """Return the cache key identifying one stage execution.

    Returns:
        Lowercase hexadecimal digest over every fact that changes the output.

    """
    payload: dict[str, object] = {
        "stage_id": definition.stage_id,
        "adapter_id": definition.adapter_id,
        "schema_revision": definition.schema_revision,
        "inputs": dict(sorted(input_digests.items())),
        "configuration": dict(sorted(configuration.items())),
        "environment": dict(sorted(environment_facts.items())),
    }
    return digest_bytes(canonical_bytes(payload))


@frozen(kw_only=True)
class StagePlan:
    """What a planned run would do, before it does anything."""

    ordered_stage_ids: tuple[str, ...] = field()
    reusable: tuple[str, ...] = field(default=())
    to_run: tuple[str, ...] = field(default=())

    def describe(self) -> str:
        """Return a short human-readable plan summary.

        Returns:
            One line per disposition.

        """
        reuse = ", ".join(self.reusable) or "none"
        run = ", ".join(self.to_run) or "none"
        return f"reuse: {reuse}\nrun:   {run}"


@frozen
class StageGraph:
    """An immutable registry of stages, ordered by their declared artifacts."""

    definitions: tuple[StageDefinition, ...] = field(default=())

    def with_stage(self, definition: StageDefinition) -> StageGraph:
        """Return a copy of this graph with ``definition`` registered.

        Returns:
            A new graph.

        """
        return evolve(self, definitions=(*self.definitions, definition))

    def by_id(self) -> dict[str, StageDefinition]:
        """Return the registered stages keyed by identifier.

        Returns:
            Mapping of stage identifier to definition.

        """
        return {definition.stage_id: definition for definition in self.definitions}

    def topological_order(self, requested: Sequence[str] | None = None) -> tuple[str, ...]:
        """Return stage identifiers in dependency order.

        Args:
            requested: Optional subset to order; defaults to every stage.

        Returns:
            Stage identifiers such that every producer precedes its consumers.

        Raises:
            UnknownStageError: When a declared input has no producer.
            CyclicStageGraphError: When dependencies contain a cycle.

        """
        definitions = self.by_id()
        selected = tuple(requested) if requested is not None else tuple(definitions)
        producers = self._producers()
        ordered: list[str] = []
        visited: set[str] = set()
        on_path: set[str] = set()
        # (stage_id, expanded) - expanded marks the post-order visit.
        pending: list[tuple[str, bool]] = [(stage_id, False) for stage_id in reversed(selected)]
        while pending:
            stage_id, expanded = pending.pop()
            if expanded:
                on_path.discard(stage_id)
                if stage_id not in visited:
                    visited.add(stage_id)
                    ordered.append(stage_id)
                continue
            if stage_id in visited:
                continue
            if stage_id in on_path:
                message = f"stage dependency cycle reaches {stage_id}"
                raise CyclicStageGraphError(message)
            definition = definitions.get(stage_id)
            if definition is None:
                message = f"unknown stage {stage_id}"
                raise UnknownStageError(message)
            on_path.add(stage_id)
            pending.append((stage_id, True))
            for artifact in reversed(definition.inputs):
                producer = producers.get(artifact)
                if producer is None:
                    message = f"stage {stage_id} requires unproduced artifact {artifact}"
                    raise UnknownStageError(message)
                pending.append((producer, False))
        return tuple(ordered)

    def plan(
        self,
        *,
        requested: Sequence[str] | None = None,
        cached_keys: Mapping[str, str],
        current_keys: Mapping[str, str],
    ) -> StagePlan:
        """Return the dispositions a run would take without performing it.

        Args:
            requested: Optional subset of stages to consider.
            cached_keys: Stage keys recorded by the previous successful run.
            current_keys: Stage keys computed from the present inputs.

        Returns:
            The plan.

        """
        ordered = self.topological_order(requested)
        reusable: list[str] = []
        to_run: list[str] = []
        stale_outputs: set[str] = set()
        definitions = self.by_id()
        for stage_id in ordered:
            definition = definitions[stage_id]
            upstream_is_stale = any(artifact in stale_outputs for artifact in definition.inputs)
            key_matches = (
                stage_id in cached_keys
                and stage_id in current_keys
                and cached_keys[stage_id] == current_keys[stage_id]
            )
            if key_matches and not upstream_is_stale:
                reusable.append(stage_id)
                continue
            to_run.append(stage_id)
            stale_outputs.update(definition.outputs)
        return StagePlan(
            ordered_stage_ids=ordered,
            reusable=tuple(reusable),
            to_run=tuple(to_run),
        )

    def _producers(self) -> dict[str, str]:
        producers: dict[str, str] = {}
        for definition in self.definitions:
            for artifact in definition.outputs:
                producers[artifact] = definition.stage_id
        return producers


def build_graph(definitions: Iterable[StageDefinition]) -> StageGraph:
    """Return a graph containing ``definitions``.

    Returns:
        The constructed graph.

    """
    return StageGraph(definitions=tuple(definitions))
