"""Logical compiler type members and observed target widths, independent of API names."""

from __future__ import annotations

from library_deep_enrichment.analyses.behavior.contracts import (
    MemberIdentity,
    NominalIdentity,
    VariantIdentity,
)
from library_deep_enrichment.analyses.behavior.numeric import integer_width

_MAX_DEPTH = 32


def type_name(raw: dict | None, depth: int = 0) -> str:
    """Preserve case-sensitive nominal names and structural type arguments.

    Returns:
        A diagnostic type expression; exact nominal identities are retained separately.

    """
    if not raw or depth > _MAX_DEPTH:
        return "unknown"
    name = str(raw.get("nominal") or raw["kind"])
    if raw["kind"] in {"integer", "unsigned", "float"}:
        name = name.lower()
    arguments = tuple(type_name(child, depth + 1) for child in raw.get("args", ()))
    return "rust:" + name + ("<" + ",".join(arguments) + ">" if arguments else "")


def target_types(value: object, pointer_bits: int) -> object:
    """Normalize pointer-sized scalar labels only with the compiler's actual machine facts.

    Returns:
        A new owned tree; original native bytes and schema meaning remain unchanged.

    """
    if isinstance(value, list):
        return [target_types(item, pointer_bits) for item in value]
    if isinstance(value, dict):
        result = {key: target_types(item, pointer_bits) for key, item in value.items()}
        if (
            result.get("kind") in {"integer", "unsigned"}
            and pointer_bits in {16, 32, 64, 128}
            and result.get("nominal") in {"Isize", "Usize"}
        ):
            name = str(result["nominal"])
            result["nominal"] = name[0] + str(pointer_bits)
        return result
    return value


def _variant(raw: dict) -> VariantIdentity:
    ty = type_name(raw.get("discriminant_type"))
    value = raw.get("discriminant_bits")
    bits = integer_width(ty)
    if value is not None and bits is not None:
        integer = int(value) % (1 << bits)
        if ty.startswith("rust:i") and integer >= (1 << (bits - 1)):
            integer -= 1 << bits
        value = str(integer)
    fields = tuple(
        MemberIdentity(
            index=item["index"],
            name=item["name"],
            definition=item["definition"],
            type_name=type_name(item["ty"]),
        )
        for item in raw["fields"]
    )
    return VariantIdentity(
        index=raw["index"],
        name=raw["name"],
        discriminant=value or "",
        discriminant_type=ty,
        fields=fields,
    )


def nominals(raw: dict) -> tuple[NominalIdentity, ...]:
    """Retain logical fields/variants and evaluated tags under exact compiler definitions.

    Returns:
        Contextual definition shapes with generic substitution obligations still visible.

    """
    return tuple(
        NominalIdentity(
            definition=item["definition"],
            name=item["name"],
            kind=item["kind"],
            member_type_policy=item["member_type_policy"],
            variants=tuple(_variant(variant) for variant in item["variants"]),
        )
        for item in raw.get("nominals", ())
    )
