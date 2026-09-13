"""Normalize retained D0 interfaces and recursive contract neighborhoods into the fabric."""

from __future__ import annotations

from typing import Protocol

from library_guides.corpus.contracts import (
    Argument,
    ByteRange,
    Entity,
    LegacyRecord,
    Operation,
    Passage,
    Record,
    Relation,
    Selection,
    TypeNode,
    TypeUse,
)
from library_guides.corpus.encoding import canonical, digest
from library_guides.corpus.native_contracts import NativeFact
from library_guides.corpus.schemas import codec_for, revision_of
from library_guides.corpus.signature_syntax import return_clause


class DeclarationSink(Protocol):
    """Finite staging shared by archival imports and current native producers."""

    def add(self, record: Record) -> str:
        """Stage a typed immutable record."""
        ...

    def blob(self, data: bytes, media_type: str) -> ByteRange:
        """Retain original bytes in the corpus."""
        ...


def source_id(alias: LegacyRecord | NativeFact) -> str:
    """Return the producer identity within its separately retained artifact context.

    Returns:
        The native identity, with contextual scope retained separately.

    """
    return (
        alias.legacy_id
        if isinstance(alias, LegacyRecord)
        else f"{alias.artifact}:{alias.native_id}"
    )


PARAMETER_PAIR_SIZE = 2


def raw_selection(alias: LegacyRecord | NativeFact, field: str, value: object) -> Selection:
    """Address one field of retained original normalized-record bytes.

    Returns:
        A verified migration selector independent of shard paths or offsets.

    """
    return Selection(
        family=codec_for(alias).family,
        revision=revision_of(alias),
        field=f"/raw{field}",
        digest=digest(value),
        role="declaration",
    )


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _sequence(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def nominal_uses(
    alias: LegacyRecord | NativeFact, raw: dict[str, object], owner: str
) -> tuple[TypeUse, ...]:
    """Normalize exact native nominal occurrence roles without flattening wrappers.

    Returns:
        Contextual resolved or unresolved nominal occurrences with field-specific support.

    """
    records: list[TypeUse] = []
    for index, value in enumerate(_sequence(raw.get("type_occurrences"))):
        occurrence = _mapping(value)
        resolved = occurrence.get("resolved_symbol")
        records.append(
            TypeUse(
                logical_id=f"type-use:{source_id(alias)}:{index}",
                profile=alias.profile,
                owner=owner,
                nominal=resolved if isinstance(resolved, str) else str(occurrence.get("path", "")),
                nominal_scope=alias.artifact,
                role=str(occurrence.get("role", "unknown")),
                position=int(str(occurrence.get("position", 0))),
                direct=occurrence.get("direct") is True,
                selector=str(occurrence.get("selector", "")),
                resolution="exact" if isinstance(resolved, str) and resolved else "unresolved",
                evidence=tuple(
                    raw_selection(alias, f"/type_occurrences/{index}/{field}", occurrence[field])
                    for field in (
                        "path",
                        "resolved_symbol",
                        "role",
                        "position",
                        "direct",
                        "selector",
                    )
                    if field in occurrence
                ),
            )
        )
    return tuple(records)


def _type_tree(
    importer: DeclarationSink,
    value: object,
    alias: LegacyRecord,
    *,
    owner: str,
    path: str,
) -> str:
    evidence = raw_selection(alias, path, value)
    if isinstance(value, dict):
        kind = next(iter(value), "empty") if len(value) == 1 else "type-structure"
        name = str(value.get("path", value.get("name", "")))
        children = tuple(value.items())
    elif isinstance(value, list):
        kind, name = "ordered-types", ""
        children = tuple((str(position), item) for position, item in enumerate(value))
    else:
        kind, name, children = "type-atom", canonical(value).decode(), ()
    node = TypeNode(
        logical_id=f"type:{alias.legacy_id}:{path}",
        profile=alias.profile,
        owner=owner,
        kind=kind,
        name=name,
        resolution="contextual-syntax",
        evidence=(evidence,),
    )
    revision = importer.add(node)
    for position, (role, child) in enumerate(children):
        child_path = path + "/" + role.replace("~", "~0").replace("/", "~1")
        target = _type_tree(importer, child, alias, owner=owner, path=child_path)
        importer.add(
            Relation(
                logical_id=f"type-link:{alias.legacy_id}:{child_path}",
                profile=alias.profile,
                source=revision,
                target=target,
                kind=role,
                position=position,
                resolution="contextual-syntax",
                evidence=(raw_selection(alias, child_path, child),),
            )
        )
    return revision


def _interface(
    alias: LegacyRecord | NativeFact, raw: dict[str, object], version: str
) -> Operation | Entity:
    symbol = str(raw.get("symbol", ""))
    item = _mapping(raw.get("item"))
    function = _mapping(_mapping(item.get("inner")).get("function"))
    signature = str(raw.get("signature", ""))
    if not function:
        return Entity(
            logical_id=f"entity:d0:{source_id(alias)}",
            profile=alias.profile,
            symbol=symbol,
            package=symbol.split("::", maxsplit=1)[0],
            version=version,
            kind=str(raw.get("kind", "unknown")),
            routes=tuple(str(route) for route in _sequence(raw.get("public_routes"))),
            resolution=str(raw.get("route_state", "unresolved")),
            evidence=(raw_selection(alias, "/signature", signature),),
        )
    sig = _mapping(function.get("sig"))
    parameters: list[Argument] = []
    for argument in _sequence(sig.get("inputs")):
        values = _sequence(argument)
        if len(values) == PARAMETER_PAIR_SIZE:
            parameters.append(
                Argument(
                    name=str(values[0]),
                    kind="positional",
                    type_expression=canonical(values[1]).decode(),
                    default_expression="",
                    required=True,
                )
            )
    return Operation(
        logical_id=f"operation:d0:{source_id(alias)}",
        profile=alias.profile,
        symbol=symbol,
        package=symbol.split("::", maxsplit=1)[0],
        version=version,
        language="rust",
        kind=str(raw.get("kind", "unknown")),
        signature=signature,
        parameters=tuple(parameters),
        returns=return_clause(signature),
        routes=tuple(str(route) for route in _sequence(raw.get("public_routes"))),
        resolution=str(raw.get("route_state", "unresolved")),
        evidence=(raw_selection(alias, "/signature", signature),),
    )


def normalize_declaration(
    importer: DeclarationSink,
    alias: LegacyRecord,
    raw: dict[str, object],
    *,
    version: str,
) -> None:
    """Retain callable signatures, ordered type/owner contracts, routes, and documentation."""
    interface = _interface(alias, raw, version)
    owner = importer.add(interface)
    if isinstance(interface, Operation):
        for occurrence in nominal_uses(alias, raw, owner):
            importer.add(occurrence)
    for field in ("item/inner", "owner_contract", "type_occurrences"):
        value = _mapping(raw.get("item")).get("inner") if field == "item/inner" else raw.get(field)
        if value is None:
            continue
        target = _type_tree(importer, value, alias, owner=owner, path=f"/{field}")
        importer.add(
            Relation(
                logical_id=f"contract:{alias.legacy_id}:{field}",
                profile=alias.profile,
                source=owner,
                target=target,
                kind=field,
                position=0,
                resolution="contextual-syntax",
                evidence=(raw_selection(alias, f"/{field}", value),),
            )
        )
    documentation = _mapping(raw.get("item")).get("docs")
    if isinstance(documentation, str) and documentation:
        source = importer.blob(canonical(documentation), "application/json")
        importer.add(
            Passage(
                logical_id=f"passage:d0:{alias.legacy_id}",
                profile=alias.profile,
                owner=owner,
                role="upstream-documentation",
                text=documentation,
                language="en",
                source=source,
                evidence=(raw_selection(alias, "/item/docs", documentation),),
                owner_family="operations" if isinstance(interface, Operation) else "entities",
            )
        )


def normalize_native_declaration(
    sink: DeclarationSink, fact: NativeFact, raw: dict[str, object], *, version: str
) -> None:
    """Project interfaces and nominal graph while retaining whole ordered contracts.

    Structured declaration roots retain exact JSON syntax and field selections.
    Nested field traversal uses the evidence resolver; arbitrary JSON scalar leaves
    need not each become two graph records to preserve the declaration graph.
    """
    interface = _interface(fact, raw, version)
    owner = sink.add(interface)
    if isinstance(interface, Operation):
        for occurrence in nominal_uses(fact, raw, owner):
            sink.add(occurrence)
    item = _mapping(raw.get("item"))
    for field, value in (
        ("/item/inner", item.get("inner")),
        ("/owner_contract", raw.get("owner_contract")),
        ("/item/links", item.get("links")),
    ):
        if value is None:
            continue
        evidence = (raw_selection(fact, field, value),)
        target = sink.add(
            TypeNode(
                logical_id=f"declaration-contract:{source_id(fact)}:{field}",
                profile=fact.profile,
                owner=owner,
                kind="structured-declaration",
                name=canonical(value).decode(),
                resolution="contextual-syntax",
                evidence=evidence,
            )
        )
        sink.add(
            Relation(
                logical_id=f"declaration-edge:{source_id(fact)}:{field}",
                profile=fact.profile,
                source=owner,
                target=target,
                kind=field,
                position=0,
                resolution="contextual-syntax",
                evidence=evidence,
            )
        )
    documentation = item.get("docs")
    if isinstance(documentation, str) and documentation:
        sink.add(
            Passage(
                logical_id=f"native-documentation:{source_id(fact)}",
                profile=fact.profile,
                owner=owner,
                role="upstream-documentation",
                text=documentation,
                language="en",
                source=sink.blob(canonical(documentation), "application/json"),
                evidence=(raw_selection(fact, "/item/docs", documentation),),
                owner_family=codec_for(interface).family,
            )
        )
