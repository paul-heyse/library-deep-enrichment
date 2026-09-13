"""Compare external concrete outcomes with guarded summaries, preserving uncertainty."""

from attrs import frozen

from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorSummary,
    Outcome,
)
from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.behavior.origins import BehaviorOrigins
from library_deep_enrichment.analyses.behavior.witness_context import context
from library_deep_enrichment.analyses.behavior.witness_contracts import (
    CaseCheck,
    Observation,
    Verdict,
)
from library_deep_enrichment.analyses.behavior.witness_eval import Evaluation
from library_deep_enrichment.analyses.behavior.witness_inputs import validate as validate_inputs
from library_deep_enrichment.analyses.behavior.witness_operators import context as operator_context
from library_deep_enrichment.analyses.behavior.witness_values import Concrete, decode, equality
from library_deep_enrichment.corpus.schemas import revision_of

MODEL = "finite-guarded-result-observation-check.v1"
CONTEXT_MODEL = "finite-guarded-result-observation-check.v2"
OPERATOR_MODEL = "finite-guarded-result-observation-check.v3"
SCALAR_MODEL = "finite-guarded-result-observation-check.v4"


@frozen(kw_only=True)
class CheckPolicy:
    """Versioned concrete comparison features, separate from abstract summary semantics."""

    contextual: bool = True
    origins: BehaviorOrigins | None = None
    primitive_unary: bool = False


def check(
    program: BehaviorProgram,
    summary: BehaviorSummary,
    observation: Observation,
    *,
    contextual: bool = True,
    origins: BehaviorOrigins | None = None,
) -> CaseCheck:
    """Retain the historical comparison interface and its finite evaluation semantics.

    Returns:
        A concrete comparison with the existing context/operator policy.

    """
    return compare(
        program, summary, observation, CheckPolicy(contextual=contextual, origins=origins)
    )


def compare(
    program: BehaviorProgram,
    summary: BehaviorSummary,
    observation: Observation,
    policy: CheckPolicy,
) -> CaseCheck:
    """Check one input/output observation without changing the summary's evidence status.

    Returns:
        Matching clause indices, a concrete disagreement, or precise inconclusive reasons.

    """
    require(
        "witness summary belongs to another program",
        condition=summary.program == revision_of(program),
    )
    require(
        "witness observation selects another summary",
        condition=observation.summary == revision_of(summary),
    )
    require(
        "witness parameter set differs from the actual invocation",
        condition=len(observation.inputs) == len(program.parameters)
        and {item.parameter for item in observation.inputs} == set(program.parameters),
    )
    require(
        "unknown cannot be a concrete witness outcome",
        condition=observation.outcome != Outcome.UNKNOWN,
    )
    concrete = decode(observation.values)
    require(
        "witness result/input leaves its value table",
        condition=0 <= observation.result < len(concrete)
        and all(0 <= item.value < len(concrete) for item in observation.inputs),
    )
    inputs = {item.parameter: concrete[item.value] for item in observation.inputs}
    validate_inputs(program, inputs)
    evaluator = Evaluation(
        inputs,
        program.nominals,
        invocation=context(program, observation, concrete),
        category_identity=policy.contextual,
        primitive_unary=policy.primitive_unary,
        operators=operator_context(program, summary, observation, concrete, policy.origins)
        if observation.operations
        else None,
    )
    evaluated = evaluator.run(summary.terms)
    matched, uncertain, detail = [], [], []
    for index, clause in enumerate(summary.clauses):
        require(
            "summary guard/result index escapes its DAG",
            condition=0 <= clause.result < len(evaluated)
            and all(0 <= item.term < len(evaluated) for item in clause.guards),
        )
        guards = [
            value.scalar == "true" if isinstance(value, Concrete) and value.kind == "bool" else None
            for value in (evaluated[item.term] for item in clause.guards)
        ]
        if any(
            value is not None and value != guard.positive
            for value, guard in zip(guards, clause.guards, strict=True)
        ):
            continue
        if clause.outcome not in {observation.outcome, Outcome.UNKNOWN}:
            continue
        same = equality(
            evaluator.project(evaluated[clause.result], observation.projection),
            concrete[observation.result],
        )
        open_assumptions = set(clause.assumptions) - set(observation.assumptions)
        if clause.outcome == Outcome.UNKNOWN or None in guards or same is None or open_assumptions:
            uncertain.append(index)
            detail.extend(
                (
                    "open guard/result/outcome or assumption at clause " + str(index),
                    *sorted(open_assumptions),
                )
            )
        elif same:
            matched.append(index)
    verdict = (
        Verdict.MATCHED if matched else Verdict.INCONCLUSIVE if uncertain else Verdict.DISAGREEMENT
    )
    return CaseCheck(
        case=observation.case,
        verdict=verdict,
        clauses=tuple(matched or uncertain),
        detail=tuple(dict.fromkeys(detail)) if not matched else (),
    )
