"""Recompute source projections and finite observations at the admission boundary."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Operation, Passage, Policy, Scope
from library_deep_enrichment.corpus.evidence import field_value, resolve_bytes
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.semantics import enrichment_contracts as c
from library_deep_enrichment.semantics.contracts import Capability, Composition
from library_deep_enrichment.semantics.documents import parameters, scalar, statements

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Describe all typed links for validation, portable closure, and explanations.

    Returns:
        Exact foreign keys; empty optional references are omitted.

    """
    pairs: list[tuple[str, str]] = []
    if isinstance(record, c.DocumentStatement):
        pairs.extend((("operations", record.owner), ("passages", record.passage)))
    if isinstance(record, (c.ParameterMode, c.TransferMapping, c.WitnessObservation)):
        pairs.append(("operations", record.operation))
    if isinstance(record, c.TransferMapping):
        pairs.extend(
            (
                ("transfer_models", record.model),
                ("expressions", record.condition),
                ("scopes", record.scope),
            )
        )
    if isinstance(record, c.TransferModel):
        pairs.append(("expressions", record.condition))
    if isinstance(record, c.StateTransfer):
        pairs.extend((("transfer_mappings", record.mapping), ("scopes", record.scope)))
    if isinstance(record, c.WitnessRun):
        pairs.extend((("witness_recipes", record.recipe), ("contexts", record.context)))
    if isinstance(record, c.WitnessObservation):
        pairs.extend((("witness_runs", record.run), ("scopes", record.scope)))
    pairs.extend(_composition_references(record))
    return tuple(pair for pair in pairs if pair[1])


def _composition_references(record: Record) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    if isinstance(record, c.InvocationContract):
        pairs.extend((("capabilities", record.capability), ("transfer_mappings", record.mapping)))
    if isinstance(record, c.CompositionGoal):
        pairs.append(("tasks", record.task))
    if isinstance(record, c.CompositionEvaluation):
        pairs.extend((("compositions", record.composition), ("composition_goals", record.goal)))
        pairs.extend(("invocation_contracts", item) for item in record.invocations)
        pairs.extend(("state_transfers", item) for item in record.transfers)
    if isinstance(record, Composition):
        pairs.extend((("tasks", record.task), ("scopes", record.universe)))
        pairs.extend(("capabilities", step.capability) for step in record.steps)
    if isinstance(record, c.CompositionProgram):
        pairs.append(("compositions", record.composition))
    if isinstance(record, c.CompositionWitness):
        pairs.extend(
            (
                ("composition_evaluations", record.evaluation),
                ("composition_programs", record.program),
                ("witness_runs", record.run),
            )
        )
    return tuple(pairs)


def _observation(reader: CorpusReader, observation: c.WitnessObservation) -> None:
    run = reader.get("witness_runs", observation.run)
    if not isinstance(run, c.WitnessRun) or run.returncode != 0 or run.disposition != "complete":
        message = "a failed witness cannot support successful observations"
        raise CorpusError(message)
    recipe = reader.get("witness_recipes", run.recipe)
    scope = reader.get("scopes", observation.scope)
    if not isinstance(recipe, c.WitnessRecipe) or observation.field not in recipe.fields:
        message = "witness observation is outside its approved output protocol"
        raise CorpusError(message)
    output = json.loads(resolve_bytes(reader, run.stdout))
    value = scalar(field_value(output, observation.field))
    if (
        value != observation.value
        or not isinstance(scope, Scope)
        or scope.members != (revision_of(run),)
        or scope.owner != revision_of(run)
    ):
        message = (
            "witness observation changed the retained result or escaped its finite execution scope"
        )
        raise CorpusError(message)
    if not any(
        isinstance(policy, Policy)
        and policy.kind == "witness-recipe-approval"
        and policy.subject == revision_of(recipe)
        for policy in reader.records("policies")
    ):
        message = "witness observation lacks independent recipe authority"
        raise CorpusError(message)


def _model(record: Record) -> None:
    if isinstance(record, c.TransferModel):
        outputs = [rule.output for rule in record.rules]
        if len(outputs) != len(set(outputs)):
            message = "a transfer model cannot silently overwrite an output property"
            raise CorpusError(message)
    elif isinstance(record, c.TransferMapping) and (
        not record.support or record.interpretation != "modeled"
    ):
        message = (
            "library transfer mappings require exact support and retain modeled interpretation"
        )
        raise CorpusError(message)


def _composition(reader: CorpusReader, record: Record) -> None:
    from library_deep_enrichment.semantics.composition_models import evaluate_composition
    from library_deep_enrichment.semantics.composition_programs import validate_program, witness_disposition

    if isinstance(record, c.InvocationContract):
        capability = reader.get("capabilities", record.capability)
        mapping = reader.get("transfer_mappings", record.mapping)
        if (
            not isinstance(capability, Capability)
            or not isinstance(mapping, c.TransferMapping)
            or mapping.operation != capability.operation
            or record.profile != capability.profile
            or not all((record.support, record.expression, record.frontier))
        ):
            message = "invocation specialization requires matching exact support and explicit qualifications"
            raise CorpusError(message)
    if isinstance(record, c.CompositionProgram):
        validate_program(reader, record)
    if (
        isinstance(record, c.CompositionWitness)
        and witness_disposition(reader, record) != record.disposition
    ):
        message = "composition witness contradicts the retained generated program execution"
        raise CorpusError(message)
    if isinstance(record, c.CompositionEvaluation):
        composition = reader.get("compositions", record.composition)
        goal = reader.get("composition_goals", record.goal)
        if (
            not isinstance(composition, Composition)
            or not isinstance(goal, c.CompositionGoal)
            or evaluate_composition(reader, composition, goal)[0] != record
        ):
            message = "composition semantics differ from replayed intermediate states"
            raise CorpusError(message)


def validate(reader: CorpusReader, record: Record) -> None:
    """Verify that citations entail the actual normalized or evaluated record.

    Raises:
        CorpusError: An emitted record differs from a replay of its retained inputs.

    """
    if isinstance(record, c.DocumentStatement):
        passage = reader.get("passages", record.passage)
        if not isinstance(passage, Passage) or record not in tuple(statements(passage)):
            message = "document projection changed source text, interval, or qualifiers"
            raise CorpusError(message)
    elif isinstance(record, c.ParameterMode):
        operation = reader.get("operations", record.operation)
        if not isinstance(operation, Operation) or record not in tuple(parameters(operation)):
            message = "parameter mode is not entailed by its original declaration"
            raise CorpusError(message)
    elif isinstance(record, c.WitnessObservation):
        _observation(reader, record)
    elif isinstance(record, c.StateTransfer):
        from library_deep_enrichment.semantics.transfers import evaluate

        mapping = reader.get("transfer_mappings", record.mapping)
        if (
            not isinstance(mapping, c.TransferMapping)
            or evaluate(reader, mapping, record.inputs) != record
        ):
            message = "state transfer is not entailed by the approved mapping and exact input state"
            raise CorpusError(message)
    _model(record)
    _composition(reader, record)
