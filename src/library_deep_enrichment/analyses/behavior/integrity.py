"""Structural checks for finite executable graphs; behavioral proof is a separate check."""

from attrs import fields

from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, Limits, Term
from library_deep_enrichment.corpus.backend import CorpusError

OPERATIONS = frozenset(
    {
        "assign",
        "call",
        "evaluate",
        "return",
        "raise",
        "unwind",
        "abort",
        "suspend",
        "drop",
        "storage_live",
        "storage_dead",
        "write",
        "unknown",
        "assert",
        "effect",
        "nop",
    }
)
EXPRESSIONS = frozenset(
    {
        "unknown",
        "local",
        "argument",
        "global",
        "literal",
        "function",
        "field",
        "index",
        "slice",
        "deref",
        "borrow",
        "address",
        "tuple",
        "set",
        "truth",
        "positive",
        "deferred",
        "slice_descriptor",
        "list",
        "dict",
        "aggregate",
        "downcast",
        "set_variant",
        "discriminant",
        "length",
        "not",
        "neg",
        "invert",
        "eq",
        "ne",
        "lt",
        "le",
        "gt",
        "ge",
        "is",
        "is_not",
        "in",
        "not_in",
        "add",
        "sub",
        "mul",
        "div",
        "floor_div",
        "mod",
        "pow",
        "bit_and",
        "bit_or",
        "bit_xor",
        "shl",
        "shr",
        "and",
        "or",
        "cast",
        "call",
        "allocation",
        "sequence_append",
        "sequence_snapshot",
        "sequence_concat",
        "list_from_sequence",
        "location",
        "update_field",
        "update_index",
        "update_downcast",
        "exception_matches",
        "join",
        "checked_add",
        "checked_sub",
        "checked_mul",
        "overflow_add",
        "overflow_sub",
        "overflow_mul",
    }
)


def require(message: str, *, condition: bool) -> None:
    """Reject an invalid evidence contract.

    Raises:
        CorpusError: The evidence violates an explicit invariant.

    """
    if not condition:
        raise CorpusError(message)


HARD_LIMITS = Limits(
    owners=5000,
    steps=10_000_000,
    states=100_000,
    clauses=10_000,
    terms=1_000_000,
    call_depth=64,
    solver_ms=30_000,
    solver_queries=10_000,
    widen_after=100,
)
MAX_LITERAL_BYTES = 65536
_ZERO = frozenset({"local", "argument", "literal", "function", "unknown"})
_UNARY = frozenset(
    {
        "field",
        "deref",
        "borrow",
        "address",
        "length",
        "discriminant",
        "truth",
        "not",
        "neg",
        "positive",
        "invert",
        "downcast",
        "set_variant",
        "cast",
        "sequence_snapshot",
        "list_from_sequence",
    }
)
_BINARY = frozenset(
    {
        "eq",
        "ne",
        "lt",
        "le",
        "gt",
        "ge",
        "is",
        "is_not",
        "in",
        "not_in",
        "exception_matches",
        "add",
        "sub",
        "mul",
        "div",
        "floor_div",
        "mod",
        "pow",
        "bit_and",
        "bit_or",
        "bit_xor",
        "shl",
        "shr",
        "and",
        "or",
        "checked_add",
        "checked_sub",
        "checked_mul",
        "overflow_add",
        "overflow_sub",
        "overflow_mul",
        "index",
        "update_field",
        "update_downcast",
    }
)
_ARITY = {
    **dict.fromkeys(_ZERO, 0),
    **dict.fromkeys(_UNARY, 1),
    **dict.fromkeys(_BINARY - {"exception_matches"}, 2),
    "slice": 3,
    "update_index": 3,
}


def limits_valid(limits: Limits) -> None:
    """Check independent resource limits before allocating analysis state."""
    for item in fields(Limits):
        require(
            f"behavior {item.name} is outside its independent bound",
            condition=0 < getattr(limits, item.name) <= getattr(HARD_LIMITS, item.name),
        )


def terms_valid(terms: tuple[Term, ...], limits: Limits) -> None:
    """Check expression vocabulary and acyclic, bounded term references."""
    require("behavior term table exceeds limit", condition=len(terms) <= limits.terms)
    for index, term in enumerate(terms):
        require("unknown behavior expression opcode", condition=term.op in EXPRESSIONS)
        require(
            "behavior expression has invalid arity",
            condition=term.op not in _ARITY or len(term.args) == _ARITY[term.op],
        )
        if term.op == "exception_matches":
            require("exception predicate has invalid operands", condition=len(term.args) in {1, 2})
        require(
            "behavior expressions must form a DAG",
            condition=all(0 <= child < index for child in term.args),
        )
        require(
            "behavior literal exceeds limit",
            condition=len(term.value.encode()) <= MAX_LITERAL_BYTES,
        )


def program_valid(program: BehaviorProgram, limits: Limits) -> None:
    """Validate graph/source coordinates without mistaking structure for semantic closure."""
    limits_valid(limits)
    require("unknown executable phase", condition=program.phase in {"invoke", "activate"})
    terms_valid(program.terms, limits)
    blocks = set(program.blocks)
    require(
        "behavior blocks must be unique and nonempty",
        condition=bool(blocks) and len(blocks) == len(program.blocks),
    )
    require("behavior entry is outside its body", condition=program.entry in blocks)
    require(
        "behavior instruction limit exceeded", condition=len(program.instructions) <= limits.steps
    )
    require(
        "duplicate behavior parameters",
        condition=len(set(program.parameters)) == len(program.parameters),
    )
    points = set()
    terminal_blocks = set()
    for item in program.instructions:
        require(
            "behavior instruction follows a terminal in the same block",
            condition=item.block not in terminal_blocks,
        )
        if item.op in {"return", "raise", "unwind", "abort"}:
            terminal_blocks.add(item.block)
        require("unknown behavior instruction opcode", condition=item.op in OPERATIONS)
        require(
            "behavior instruction has invalid program point",
            condition=item.block in blocks and item.index >= 0,
        )
        require("duplicate behavior instruction identity", condition=item.index not in points)
        points.add(item.index)
        require("invalid behavior source range", condition=0 <= item.start <= item.end)
        require("invalid behavior value reference", condition=-1 <= item.value < len(program.terms))
        if item.op in {"assign", "write", "evaluate", "return"}:
            require(
                "behavior value-producing instruction lacks its input", condition=item.value >= 0
            )
        if item.op == "evaluate" and item.target == "sequence_expansion":
            require(
                "sequence expansion requires a snapshot expression",
                condition=program.terms[item.value].op == "sequence_snapshot",
            )
        if item.op == "write":
            require(
                "behavior write requires exactly one destination",
                condition=len(item.arguments) == 1,
            )
        require(
            "invalid behavior call argument",
            condition=all(0 <= arg < len(program.terms) for arg in item.arguments),
        )
    for edge in program.edges:
        require(
            "behavior terminal block has a successor", condition=edge.source not in terminal_blocks
        )
        require(
            "behavior edge escaped the body",
            condition=edge.source in blocks and edge.target in blocks,
        )
        require(
            "invalid behavior guard reference", condition=-1 <= edge.condition < len(program.terms)
        )
        if edge.condition >= 0:
            ty = program.terms[edge.condition].ty
            require(
                "behavior guard has a non-boolean type",
                condition=ty == "unknown" or ty.endswith(":bool"),
            )
        require(
            "unknown behavior edge kind",
            condition=edge.kind in {"normal", "error", "unwind", "resume", "cancel"},
        )
    require("behavior control-edge limit exceeded", condition=len(program.edges) <= limits.steps)
