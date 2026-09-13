"""Current Python source interfaces from retained native syntax and exact contexts."""

from __future__ import annotations

import ast
import json
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from attrs import frozen

from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.contracts import Argument, Context, Gap, Operation
from library_guides.corpus.declarations import raw_selection
from library_guides.corpus.evidence import resolve_bytes, select
from library_guides.corpus.native_contracts import NativeArtifact, NativeFact
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.contracts import Record, Selection
    from library_guides.corpus.store import CorpusReader

MAX_INTERFACES = 10_000
MAX_OWNER_DEPTH = 32
PREFIX = "python-source-interface:"


@frozen(kw_only=True)
class Signature:
    """Source-declared slots; annotations and defaults are never evaluated."""

    name: str
    parameters: tuple[Argument, ...]
    returns: str
    asynchronous: bool


def parse_signature(source: str) -> Signature:
    """Parse a retained function header without importing or executing library code.

    Returns:
        Ordered positional-only, keyword-only, variadic, and symbolic default declarations.

    Raises:
        CorpusError: The header is not exactly one function declaration.

    """
    nodes = ast.parse(source + "\n    pass\n").body
    if len(nodes) != 1 or not isinstance(nodes[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
        message = "Python interface requires one source function header"
        raise CorpusError(message)
    node = nodes[0]
    arguments = node.args
    positional = (*arguments.posonlyargs, *arguments.args)
    defaults = (None,) * (len(positional) - len(arguments.defaults)) + tuple(arguments.defaults)
    pairs = [
        (
            argument,
            default,
            "positional_only" if index < len(arguments.posonlyargs) else "positional_or_keyword",
        )
        for index, (argument, default) in enumerate(zip(positional, defaults, strict=True))
    ]
    if arguments.vararg:
        pairs.append((arguments.vararg, None, "variadic_positional"))
    pairs.extend(
        (argument, default, "keyword_only")
        for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True)
    )
    if arguments.kwarg:
        pairs.append((arguments.kwarg, None, "variadic_keyword"))
    return Signature(
        name=node.name,
        asynchronous=isinstance(node, ast.AsyncFunctionDef),
        returns="" if node.returns is None else ast.unparse(node.returns),
        parameters=tuple(
            Argument(
                name=argument.arg,
                kind=kind,
                type_expression=""
                if argument.annotation is None
                else ast.unparse(argument.annotation),
                default_expression="" if default is None else ast.unparse(default),
                required=default is None and not kind.startswith("variadic_"),
            )
            for argument, default, kind in pairs
        ),
    )


def _owners(
    reader: CorpusReader, artifact: NativeArtifact, fact: NativeFact
) -> tuple[str, tuple[Selection, ...]]:
    names, support, seen = [], [], set()
    owner = fact.owner
    while owner:
        if owner in seen or len(seen) >= MAX_OWNER_DEPTH:
            message = "Python declaration owner chain is cyclic or exceeds its bound"
            raise CorpusError(message)
        seen.add(owner)
        parent = reader.lookup(
            "native_facts", f"native-fact:{artifact.external_id}:{owner}", fact.profile
        )
        if not isinstance(parent, NativeFact) or parent.artifact != fact.artifact:
            message = "Python declaration owner is unresolved in its exact source artifact"
            raise CorpusError(message)
        names.append(parent.symbol)
        support.append(select(parent, "/symbol", "lexical-owner"))
        owner = parent.owner
    return ".".join(reversed(names)), tuple(support)


def normalize(reader: CorpusReader, fact: NativeFact) -> Operation | None:
    """Normalize one source declaration, retaining public-route and dispatch uncertainty.

    Returns:
        A contextual source interface, or no callable for a different syntax family.

    Raises:
        CorpusError: A source or context cannot establish the declared interface.

    """
    if PurePosixPath(fact.file).suffix not in {".py", ".pyi"} or fact.kind != "definition":
        return None
    raw = json.loads(resolve_bytes(reader, fact.original, max_bytes=1_000_000))
    body = raw.get("payload", {})
    if body.get("node_kind") != "function_definition":
        return None
    artifact = reader.get("native_artifacts", fact.artifact)
    if not isinstance(artifact, NativeArtifact) or artifact.lane != "syntax":
        message = "Python normalization requires an exact syntax artifact"
        raise CorpusError(message)
    context = reader.get("contexts", artifact.context)
    if not isinstance(context, Context) or context.profile != fact.profile:
        message = "Python interface context escaped its native artifact profile"
        raise CorpusError(message)
    source = body.get("signature")
    if not isinstance(source, str) or body.get("syntax_valid") is not True:
        message = "Python source function has no valid retained header"
        raise CorpusError(message)
    signature = parse_signature(source)
    owner, evidence = _owners(reader, artifact, fact)
    module = ".".join(PurePosixPath(fact.file).with_suffix("").parts).removesuffix(".__init__")
    symbol = ".".join(item for item in (module, owner, signature.name) if item)
    return Operation(
        logical_id=f"{PREFIX}{fact.artifact}:{fact.native_id}",
        profile=fact.profile,
        symbol=symbol,
        package=context.package,
        version=context.version,
        language="python",
        kind="stub-declaration"
        if fact.file.endswith(".pyi")
        else "async-function"
        if signature.asynchronous
        else "function",
        signature=source,
        parameters=signature.parameters,
        returns=signature.returns,
        routes=(),
        resolution="source-declared; public-route-and-runtime-dispatch-unresolved",
        evidence=(
            raw_selection(fact, "/payload/signature", source),
            select(fact, "/file", "source-module"),
            select(fact, "/owner", "source-owner"),
            select(context, "/package", "source-package"),
            select(context, "/version", "source-version"),
            *evidence,
        ),
    )


def project(reader: CorpusReader, artifact_revision: str) -> Iterator[Record]:
    """Enumerate the finite current source interface population through sanctioned reads.

    Yields:
        Source interfaces and their explicit unqualified runtime-availability frontier.

    Raises:
        BudgetExceededError: The declared finite callable boundary is exceeded.
        CorpusError: The requested artifact is not a syntax observation.

    """
    artifact = reader.get("native_artifacts", artifact_revision)
    if not isinstance(artifact, NativeArtifact) or artifact.lane != "syntax":
        message = "select a current native syntax artifact"
        raise CorpusError(message)
    count = 0
    for fact in reader.filtered_records(
        "native_facts", (("artifact", artifact_revision), ("kind", "definition"))
    ):
        if not isinstance(fact, NativeFact) or fact.artifact != artifact_revision:
            continue
        operation = normalize(reader, fact)
        if operation is None:
            continue
        count += 1
        if count > MAX_INTERFACES:
            message = "Python source normalization exceeds its 10000-interface boundary"
            raise BudgetExceededError(message)
        yield operation
        yield Gap(
            logical_id=f"python-source-frontier:{operation.logical_id}",
            profile=operation.profile,
            subject=revision_of(operation),
            predicate="",
            reason="Source declarations preserve symbolic defaults and annotations; decorators, public facades, runtime dispatch, and native effects require separate evidence",
            next_evidence="Reconcile current runtime/stub/registry routes and selected native boundaries",
            evidence=operation.evidence,
        )


def validate(reader: CorpusReader, record: Operation) -> None:
    """Recompute every projected source field before it can enter the current corpus.

    Raises:
        CorpusError: An interface changes a slot, wrapper, source identity, or availability claim.

    """
    if not record.logical_id.startswith(PREFIX):
        return
    selected = [
        item
        for item in record.evidence
        if item.family == "native_facts" and item.field == "/raw/payload/signature"
    ]
    if len(selected) != 1:
        message = "Python source interface requires one exact native header"
        raise CorpusError(message)
    fact = reader.get("native_facts", selected[0].revision)
    if not isinstance(fact, NativeFact) or normalize(reader, fact) != record:
        message = "Python interface differs from exact source normalization"
        raise CorpusError(message)
