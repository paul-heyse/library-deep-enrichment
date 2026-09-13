"""Contextual declaration types retain wrappers and resolve Self without guessing behavior."""

from __future__ import annotations

from itertools import batched
from typing import TYPE_CHECKING

from attrs import frozen

from library_guides.corpus.contracts import Operation, Record, Selection, TypeUse
from library_guides.corpus.encoding import canonical
from library_guides.corpus.evidence import read_field, select
from library_guides.corpus.schemas import revision_of
from library_guides.semantics.contracts import Slot

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.store import CorpusReader

PARAMETER_PAIR_SIZE = 2


@frozen(kw_only=True)
class OperationShape(Record):
    """A typed call shape, preserving context, generic obligations, and nested wrappers."""

    operation: str
    inputs: tuple[Slot, ...]
    outputs: tuple[Slot, ...]
    support: tuple[Selection, ...]
    frontier: tuple[str, ...]


def _normalize(value: object, path: str, uses: dict[str, TypeUse], owner: str) -> object:
    occurrence = uses.get(path)
    if isinstance(value, dict):
        if "resolved_path" in value or (value.get("generic") == "Self" and occurrence is not None):
            original = value.get("resolved_path", {})
            original = original if isinstance(original, dict) else {}
            return {
                "nominal": {
                    "name": occurrence.nominal if occurrence else str(original.get("path", "")),
                    "scope": occurrence.nominal_scope if occurrence else owner,
                    "resolution": occurrence.resolution if occurrence else "unresolved",
                    "arguments": _normalize(
                        original.get("args"), path + "/resolved_path/args", uses, owner
                    ),
                }
            }
        if "generic" in value:
            return {"generic": {"owner": owner, "name": value["generic"]}}
        return {
            key: _normalize(
                child, path + "/" + key.replace("~", "~0").replace("/", "~1"), uses, owner
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [
            _normalize(child, path + f"/{index}", uses, owner) for index, child in enumerate(value)
        ]
    return value


def operation_shape(
    reader: CorpusReader, operation: Operation, uses: tuple[TypeUse, ...]
) -> OperationShape:
    """Recover exact Rust input/output syntax with contextual nominal substitutions.

    Returns:
        A structural call shape. Generic solving, borrowing, and behavior remain separate checks.

    """
    support = [
        select(operation, "/parameters", "declared-inputs"),
        select(operation, "/returns", "declared-output"),
    ]
    uses = tuple(sorted(uses, key=revision_of))
    by_path: dict[str, TypeUse] = {}
    conflicts: set[str] = set()
    for item in uses:
        if item.resolution != "exact":
            continue
        path = item.selector.removeprefix("json:")
        previous = by_path.get(path)
        if previous is not None and (previous.nominal, previous.nominal_scope) != (
            item.nominal,
            item.nominal_scope,
        ):
            conflicts.add(path)
        by_path[path] = item
    for path in conflicts:
        del by_path[path]
    source = next(
        (
            item
            for item in operation.evidence
            if item.family in {"native_facts", "legacy_records"} and item.field == "/raw/signature"
        ),
        None,
    )
    inputs = tuple(
        Slot(
            role=argument.name,
            type_expression=argument.type_expression,
            representation="unknown",
            resource="",
            consumes=False,
        )
        for argument in operation.parameters
        if argument.required
    )
    output = operation.returns
    frontier = [
        "Declaration types do not establish invocation, ownership, or semantic compatibility"
    ]
    frontier.extend(f"Conflicting nominal resolutions at {path}" for path in sorted(conflicts))
    if operation.language == "rust" and source is not None:
        signature = read_field(
            reader, source.family, source.revision, "/raw/item/inner/function/sig"
        )
        if isinstance(signature, dict):
            raw_inputs = signature.get("inputs", [])
            inputs = tuple(
                Slot(
                    role=str(pair[0]),
                    type_expression=canonical(
                        _normalize(
                            pair[1],
                            f"/item/inner/function/sig/inputs/{index}/1",
                            by_path,
                            revision_of(operation),
                        )
                    ).decode(),
                    representation="unknown",
                    resource="",
                    consumes=False,
                )
                for index, pair in enumerate(raw_inputs)
                if isinstance(pair, list) and len(pair) == PARAMETER_PAIR_SIZE
            )
            output = canonical(
                _normalize(
                    signature.get("output"),
                    "/item/inner/function/sig/output",
                    by_path,
                    revision_of(operation),
                )
            ).decode()
            from library_guides.corpus.contracts import LegacyRecord
            from library_guides.corpus.declarations import raw_selection
            from library_guides.corpus.native_contracts import NativeFact

            raw = reader.get(source.family, source.revision)
            if isinstance(raw, (LegacyRecord, NativeFact)):
                support.append(raw_selection(raw, "/item/inner/function/sig", signature))
            support.extend(select(item, "/nominal", "contextual-type-resolution") for item in uses)
            frontier.append(
                "Nominal identities are contextual to the source artifact; no cross-context identity collapse"
            )
    return OperationShape(
        logical_id=f"shape:{operation.logical_id}",
        profile=operation.profile,
        operation=revision_of(operation),
        inputs=inputs,
        outputs=(
            Slot(
                role="result",
                type_expression=output,
                representation="unknown",
                resource="",
                consumes=False,
            ),
        ),
        support=tuple(support),
        frontier=tuple(frontier),
    )


def shapes(reader: CorpusReader) -> Iterator[OperationShape]:
    """Project contextual interfaces without per-operation shape annotations.

    Yields:
        Exact operation-owned type shapes with independent source selections.

    """
    grouped: dict[str, list[TypeUse]] = {}
    for item in reader.records("type_uses"):
        if isinstance(item, TypeUse):
            grouped.setdefault(item.owner, []).append(item)
    for batch in batched(reader.records("operations"), 128, strict=False):
        reader.prefetch(
            (source.family, source.revision)
            for operation in batch
            if isinstance(operation, Operation) and operation.language == "rust"
            for source in operation.evidence
            if source.family in {"native_facts", "legacy_records"}
            and source.field == "/raw/signature"
        )
        for operation in batch:
            if not isinstance(operation, Operation):
                continue
            yield operation_shape(reader, operation, tuple(grouped.get(revision_of(operation), ())))
