"""JSON Schema generated from the same attrs contracts used at runtime."""

from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Literal, TypeAliasType, Union, get_args, get_origin, get_type_hints

import attrs
from jsonschema import Draft202012Validator

from library_guides.knowledge import Knowledge
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.store.digests import canonical_bytes
from library_guides.store.staging import write_atomic


def schema_for(annotation: object) -> dict[str, object]:
    """Derive a strict schema while preserving fixed tuples and literal vocabularies.

    Returns:
        A strict JSON Schema derived from the annotation.

    Raises:
        TypeError: If the annotation is outside the supported contract vocabulary.

    """
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    origin, arguments = get_origin(annotation), get_args(annotation)
    primitives = {
        str: "string",
        int: "integer",
        bool: "boolean",
        float: "number",
        type(None): "null",
    }
    if annotation in primitives:
        return {"type": primitives[annotation]}
    if origin is Literal:
        return {"enum": list(arguments)}
    if origin in {types.UnionType, Union}:
        return {"anyOf": [schema_for(item) for item in arguments]}
    if origin is tuple:
        variable_tuple_arity = 2
        if len(arguments) == variable_tuple_arity and arguments[1] is Ellipsis:
            return {"type": "array", "items": schema_for(arguments[0])}
        return {
            "type": "array",
            "prefixItems": [schema_for(item) for item in arguments],
            "minItems": len(arguments),
            "maxItems": len(arguments),
        }
    if isinstance(annotation, type) and attrs.has(annotation):
        hints = get_type_hints(annotation)
        fields = attrs.fields(annotation)
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {field.name: schema_for(hints[field.name]) for field in fields},
            "required": [field.name for field in fields if field.default is attrs.NOTHING],
        }
    message = f"unsupported schema annotation: {annotation}"
    raise TypeError(message)


def write_schema(path: Path) -> None:
    """Write the portable schema owned by the current knowledge contracts."""
    write_atomic(
        path,
        canonical_bytes(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "library-guides.knowledge.v2",
                **schema_for(Knowledge),
                "allOf": [
                    {
                        "properties": {
                            "schema_version": {"const": "library-guides.knowledge.v2"},
                            "sources": {
                                "items": {
                                    "properties": {
                                        "origin": {
                                            "enum": [
                                                "compiler_api",
                                                "static_api",
                                                "runtime_api",
                                                "documentation",
                                                "registry",
                                                "behavior",
                                            ]
                                        }
                                    }
                                }
                            },
                            "evidence": {
                                "items": {
                                    "properties": {
                                        "kind": {
                                            "enum": ["api", "statement", "registry", "behavior"]
                                        }
                                    }
                                }
                            },
                        }
                    }
                ],
            }
        ),
    )


def validate_document(document: object) -> None:
    """Reject coercions and unknown fields before structuring YAML or model output."""
    version = (
        "v3"
        if isinstance(document, dict)
        and document.get("schema_version") == "library-guides.knowledge.v3"
        else "v2"
    )
    path = Path(__file__).parent / "assets" / "schemas" / f"knowledge.{version}.schema.json"
    validator = Draft202012Validator(json.loads(path.read_bytes()))
    validator.validate(document)


def write_v3_schema(path: Path) -> None:
    """Write the strict source-evidence schema without modifying V2's schema."""
    write_atomic(
        path,
        canonical_bytes(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "library-guides.knowledge.v3",
                "allOf": [
                    schema_for(KnowledgeV3),
                    {"properties": {"schema_version": {"const": "library-guides.knowledge.v3"}}},
                ],
            }
        ),
    )
