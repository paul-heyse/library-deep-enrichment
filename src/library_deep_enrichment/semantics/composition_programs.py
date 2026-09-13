"""Generate ordinary compiler inputs and qualify only their exact finite observations."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.evidence import field_value, resolve_bytes
from library_deep_enrichment.semantics.composition_models import invocations
from library_deep_enrichment.semantics.contracts import Composition, Task, ValueKind
from library_deep_enrichment.semantics.documents import scalar
from library_deep_enrichment.semantics.enrichment_contracts import (
    CompositionEvaluation,
    CompositionGoal,
    CompositionProgram,
    CompositionWitness,
    WitnessRecipe,
    WitnessRun,
)

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader
    from library_deep_enrichment.semantics.contracts import Assignment


def render(
    reader: CorpusReader,
    composition: Composition,
    inputs: tuple[Assignment, ...],
    prologue: str,
    epilogue: str,
) -> bytes:
    """Generate one Rust program from approved templates and explicit typed input expressions.

    Returns:
        Actual source bytes to compile in the ordinary consumer environment.

    Raises:
        CorpusError: Bindings are incomplete or a specialization exceeds the generator's scope.

    """
    task = reader.get("tasks", composition.task)
    if not isinstance(task, Task) or not composition.steps:
        message = "program generation requires a nonempty plan and an admitted task"
        raise CorpusError(message)
    bindings = {item.variable: item.value.text for item in inputs}
    if (
        set(bindings) != {slot.role for slot in task.inputs}
        or len(bindings) != len(inputs)
        or any(item.value.kind != ValueKind.TEXT for item in inputs)
    ):
        message = "program input expressions must exactly cover the task input roles"
        raise CorpusError(message)
    names = {
        f"input:{index}:{slot.role}": f"input_{index}" for index, slot in enumerate(task.inputs)
    }
    statements = [prologue]
    statements.extend(
        f"let input_{index}: {slot.type_expression} = {bindings[slot.role]};"
        for index, slot in enumerate(task.inputs)
    )
    concrete = invocations(reader)
    for index, step in enumerate(composition.steps):
        contract = concrete.get(step.capability)
        if contract is None or len(contract.outputs) != 1 or len(step.outputs) != 1:
            message = "Rust generation requires one explicit result and an approved invocation"
            raise CorpusError(message)
        arguments = {
            slot.role: names[key] for key, slot in zip(step.inputs, contract.inputs, strict=True)
        }
        expression = contract.expression.format_map(arguments)
        name = f"value_{index}"
        statements.append(f"let {name}: {contract.outputs[0].type_expression} = {expression};")
        names[step.outputs[0]] = name
    statements.append(epilogue.replace("$RESULT", names[composition.steps[-1].outputs[0]]))
    return ("\n".join(statements) + "\n").encode()


def validate_program(reader: CorpusReader, program: CompositionProgram) -> None:
    """Verify that retained source is exactly generated from its admitted plan.

    Raises:
        CorpusError: A purported generated program changes its plan or input expressions.

    """
    composition = reader.get("compositions", program.composition)
    if not isinstance(composition, Composition) or render(
        reader,
        composition,
        program.inputs,
        resolve_bytes(reader, program.prologue).decode(),
        resolve_bytes(reader, program.epilogue).decode(),
    ) != resolve_bytes(reader, program.program):
        message = "retained program differs from its generated composition"
        raise CorpusError(message)


def witness_disposition(reader: CorpusReader, witness: CompositionWitness) -> str:
    """Compare modeled outputs only with the execution of this exact generated program.

    Returns:
        Corroborated, contradicted, or unresolved for the finite retained inputs.

    Raises:
        CorpusError: The claimed witness executes a different program or task plan.

    """
    evaluation = reader.get("composition_evaluations", witness.evaluation)
    program = reader.get("composition_programs", witness.program)
    run = reader.get("witness_runs", witness.run)
    if not isinstance(evaluation, CompositionEvaluation) or not isinstance(
        program, CompositionProgram
    ):
        message = "composition witness requires an admitted evaluation and generated program"
        raise CorpusError(message)
    if not isinstance(run, WitnessRun) or run.returncode or run.disposition != "complete":
        return "unresolved"
    recipe = reader.get("witness_recipes", run.recipe)
    if (
        not isinstance(recipe, WitnessRecipe)
        or recipe.program != program.program
        or evaluation.composition != program.composition
        or recipe.profile != evaluation.profile
    ):
        message = "witness program or context differs from the generated semantic composition"
        raise CorpusError(message)
    data = json.loads(resolve_bytes(reader, run.stdout))
    expected = {item.variable: item.value for item in evaluation.outputs}
    goal = reader.get("composition_goals", evaluation.goal)
    if not isinstance(goal, CompositionGoal):
        return "unresolved"
    required = {item.variable for item in goal.required}
    observed = {item.variable for item in witness.fields}
    if not required <= observed or any(item.variable not in expected for item in witness.fields):
        return "unresolved"
    if any(item.value.text not in recipe.fields for item in witness.fields):
        message = "composition witness field is outside its approved observation protocol"
        raise CorpusError(message)
    return (
        "corroborated"
        if all(
            scalar(field_value(data, item.value.text)) == expected[item.variable]
            for item in witness.fields
        )
        else "contradicted"
    )
