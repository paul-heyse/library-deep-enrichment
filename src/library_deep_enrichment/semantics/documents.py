"""Lossless documentation intervals and static parameter specialization."""

from __future__ import annotations

import ast
import re
import struct
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.contracts import Operation, Passage
from library_deep_enrichment.corpus.evidence import select
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.semantics.contracts import Value, ValueKind
from library_deep_enrichment.semantics.enrichment_contracts import DocumentStatement, ParameterMode

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader

QUALIFIERS = re.compile(
    r"\b(?:not|never|unless|except|may|might|could|if|when|depending|typically|usually|only|must)\b",
    re.IGNORECASE,
)
MAX_LITERAL_CHARACTERS = 2048
MAX_ANNOTATION_CHARACTERS = 4096
SECTIONS = {
    "args": "parameter",
    "arguments": "parameter",
    "parameters": "parameter",
    "returns": "return",
    "yields": "yield",
    "raises": "exception",
    "errors": "exception",
    "panics": "exception",
    "safety": "safety",
    "examples": "example",
    "example": "example",
    "see also": "related",
    "notes": "note",
    "warnings": "warning",
}


def scalar(value: object) -> Value | None:
    """Convert a concrete scalar, preserving literal null separately from absent evidence.

    Returns:
        A canonical scalar, or no result for a compound or unsupported value.

    """
    if value is None:
        return Value(kind=ValueKind.NULL, text="")
    if type(value) is bool:
        return Value(kind=ValueKind.BOOLEAN, text=str(value).lower())
    if type(value) is int:
        return Value(kind=ValueKind.INTEGER, text=str(value))
    if isinstance(value, float):
        return Value(kind=ValueKind.FLOAT_BITS, text=struct.pack(">d", value).hex())
    if isinstance(value, str):
        return Value(kind=ValueKind.TEXT, text=value)
    return None


def literal(expression: str) -> Value | None:
    """Recognize only literal syntax; names, calls, and containers remain symbolic.

    Returns:
        A literal value without executing a default expression.

    """
    if expression in {"true", "false"}:
        return Value(kind=ValueKind.BOOLEAN, text=expression)
    if not expression or len(expression) > MAX_LITERAL_CHARACTERS:
        return None
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError, RecursionError:
        return None
    if isinstance(node, ast.Constant):
        return scalar(node.value)
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
        and not isinstance(node.operand.value, bool)
    ):
        return scalar(-node.operand.value)
    return None


def _domain(annotation: str) -> tuple[Value, ...]:
    if annotation in {"bool", "builtins.bool"}:
        return (
            Value(kind=ValueKind.BOOLEAN, text="false"),
            Value(kind=ValueKind.BOOLEAN, text="true"),
        )
    if len(annotation) > MAX_ANNOTATION_CHARACTERS:
        return ()
    try:
        node = ast.parse(annotation, mode="eval").body
    except SyntaxError, RecursionError:
        return ()
    if not isinstance(node, ast.Subscript) or ast.unparse(node.value) not in {
        "Literal",
        "typing.Literal",
    }:
        return ()
    values = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
    converted = tuple(literal(ast.unparse(item)) for item in values)
    return (
        tuple(item for item in converted if item is not None)
        if all(item is not None for item in converted)
        else ()
    )


def parameters(operation: Operation) -> Iterator[ParameterMode]:
    """Project every declared argument, including variadics and unresolved defaults.

    Yields:
        Static source-qualified argument modes; a symbolic expression is never a default value.

    """
    owner = revision_of(operation)
    for position, argument in enumerate(operation.parameters):
        value = literal(argument.default_expression)
        status = (
            "literal"
            if value is not None
            else "symbolic"
            if argument.default_expression
            else "absent"
        )
        yield ParameterMode(
            logical_id=f"parameter-mode:{operation.logical_id}:{position}",
            profile=operation.profile,
            operation=owner,
            position=position,
            name=argument.name,
            kind=argument.kind,
            required=argument.required,
            default_expression=argument.default_expression,
            default_status=status,
            default_value=value or Value(kind=ValueKind.TEXT, text=""),
            domain=_domain(argument.type_expression),
            support=(select(operation, f"/parameters/{position}", "declared-parameter"),),
        )


def statements(passage: Passage) -> Iterator[DocumentStatement]:
    """Retain Markdown/RST/NumPy/Google section and directive context without paraphrase.

    Yields:
        Exact paragraph intervals with inherited section and document qualifiers.

    """
    section = "summary"
    role = "purpose"
    source = passage.text
    inherited = tuple(sorted({match.group().lower() for match in QUALIFIERS.finditer(source)}))
    for match in re.finditer(r"\S(?:[^\n]|\n(?!\s*\n))*", source):
        text = match.group()
        lines = text.splitlines()
        heading = lines[0].strip().strip("# :").lower()
        if heading in SECTIONS:
            section, role = heading, SECTIONS[heading]
        if lines[0].lstrip().startswith((".. warning::", ".. note::", ".. deprecated::")):
            role = "admonition"
        subject_match = re.match(r"\s*:(?:param|type|raises?)\s+([^:]+):", text)
        subject = subject_match.group(1) if subject_match else ""
        if subject_match:
            role = "exception" if text.lstrip().startswith(":raise") else "parameter"
        links = tuple(
            re.findall(r"\[[^\]]+\]\(([^)]+)\)|:?(?:class|meth|func|attr):`([^`]+)`", text)
        )
        yield DocumentStatement(
            logical_id=f"document-statement:{passage.logical_id}:{match.start()}:{match.end()}",
            profile=passage.profile,
            owner=passage.owner,
            passage=revision_of(passage),
            start=match.start(),
            end=match.end(),
            text=text,
            section=section,
            role=role,
            subject=subject,
            qualifiers=inherited,
            links=tuple(first or second for first, second in links),
            interpretation="attributed-source-structure-not-behavioral-proof",
            support=(select(passage, "/text", "original-document-context"),),
        )


def project(reader: CorpusReader) -> Iterator[Record]:
    """Produce source and declaration projections without a generative interpreter.

    Yields:
        Exact document statements and static parameter-mode records.

    """
    for operation in reader.records("operations"):
        if isinstance(operation, Operation):
            yield from parameters(operation)
    for passage in reader.records("passages"):
        if isinstance(passage, Passage) and passage.owner_family == "operations":
            yield from statements(passage)
