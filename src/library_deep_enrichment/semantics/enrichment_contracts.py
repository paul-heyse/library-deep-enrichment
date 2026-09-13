"""Source projections and bounded experiments share the admitted semantic fabric."""

from attrs import frozen

from library_deep_enrichment.corpus.contracts import ByteRange, Record, Selection
from library_deep_enrichment.semantics.contracts import Assignment, Slot, State, Value


@frozen(kw_only=True)
class DocumentStatement(Record):
    """An exact source interval with syntax-level qualifiers, never inferred truth."""

    owner: str
    passage: str
    start: int
    end: int
    text: str
    section: str
    role: str
    subject: str
    qualifiers: tuple[str, ...]
    links: tuple[str, ...]
    interpretation: str
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class ParameterMode(Record):
    """A captured declaration default and finite literal domain without evaluating code."""

    operation: str
    position: int
    name: str
    kind: str
    required: bool
    default_expression: str
    default_status: str
    default_value: Value
    domain: tuple[Value, ...]
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class TransferRule:
    """One state assignment in a finite approved transition model."""

    output: str
    operator: str
    inputs: tuple[str, ...]
    value: Value


@frozen(kw_only=True)
class TransferModel(Record):
    """Reusable state transfer semantics; a model alone does not map any library API."""

    name: str
    condition: str
    rules: tuple[TransferRule, ...]
    description: str


@frozen(kw_only=True)
class TransferMapping(Record):
    """An independently approved contextual operation-to-model association."""

    operation: str
    model: str
    condition: str
    interpretation: str
    scope: str
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class StateTransfer(Record):
    """An evaluated transition with unknown/conflicting inputs retained."""

    mapping: str
    inputs: tuple[Assignment, ...]
    outputs: tuple[Assignment, ...]
    condition_state: State
    interpretation: str
    scope: str
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class WitnessRecipe(Record):
    """A reviewed finite program and observation protocol, executable only by build work."""

    name: str
    language: str
    program: ByteRange
    manifest: ByteRange
    packages: tuple[str, ...]
    toolchain: str
    description: str
    fields: tuple[str, ...]


@frozen(kw_only=True)
class WitnessRun(Record):
    """Exact worker execution inputs and outputs, separate from their interpretation."""

    recipe: str
    context: str
    command: tuple[str, ...]
    stdout: ByteRange
    stderr: ByteRange
    lockfile: ByteRange
    returncode: int
    isolation: str
    disposition: str


@frozen(kw_only=True)
class WitnessObservation(Record):
    """A single source field observed in a finite run, not a universal API assertion."""

    operation: str
    run: str
    field: str
    value: Value
    scope: str
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class EvidenceRequest(Record):
    """An unresolved requirement's next useful finite evidence action, without execution."""

    subject: str
    predicate: str
    lane: str
    query: str
    expected_information: str
    reason: str
    dependencies: tuple[Selection, ...]


@frozen(kw_only=True)
class InvocationContract(Record):
    """An approved concrete specialization; the original declaration retains all wrappers."""

    capability: str
    mapping: str
    inputs: tuple[Slot, ...]
    outputs: tuple[Slot, ...]
    expression: str
    support: tuple[Selection, ...]
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class CompositionGoal(Record):
    """Consumer requirements on the final value's modeled semantic properties."""

    task: str
    required: tuple[Assignment, ...]


@frozen(kw_only=True)
class CompositionEvaluation(Record):
    """Replayed intermediate transitions; a modeled result still needs an invocation witness."""

    composition: str
    goal: str
    invocations: tuple[str, ...]
    transfers: tuple[str, ...]
    outputs: tuple[Assignment, ...]
    disposition: str
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class CompositionProgram(Record):
    """Exact generated source with retained input expressions and wrapper handling."""

    composition: str
    inputs: tuple[Assignment, ...]
    prologue: ByteRange
    epilogue: ByteRange
    program: ByteRange


@frozen(kw_only=True)
class CompositionWitness(Record):
    """A finite compiler/execution result tied to the exact generated semantic plan."""

    evaluation: str
    program: str
    run: str
    fields: tuple[Assignment, ...]
    disposition: str
