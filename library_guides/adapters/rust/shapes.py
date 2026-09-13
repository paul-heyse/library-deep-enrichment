"""Typed views of fields consumed after rustdoc-types validates the whole document."""

from __future__ import annotations

from typing import TypedDict


class RustPath(TypedDict):
    """A compiler-resolved path reference."""

    id: int
    path: str


class RustSignature(TypedDict):
    """A callable signature, retaining compiler type expressions."""

    inputs: list[tuple[str, object]]
    output: object


RustBody = TypedDict(
    "RustBody",
    {
        "items": list[int],
        "variants": list[int],
        "for": object,
        "trait": RustPath | None,
        "is_glob": bool,
        "id": int | None,
        "name": str,
        "sig": RustSignature,
        "generics": dict[str, object],
        "header": dict[str, object],
    },
    total=False,
)


class RustItem(TypedDict):
    """One item whose full source remains the evidence authority."""

    crate_id: int
    name: str | None
    visibility: str | dict[str, object]
    inner: dict[str, RustBody]
    docs: str | None
    links: dict[str, int]
    attrs: list[object]


class PathEntry(TypedDict):
    """A named local or dependency-crate type path."""

    path: list[str]
    crate_id: int
    kind: str


class RustDocument(TypedDict):
    """The parts of the validated compiler document used by normalization."""

    index: dict[str, RustItem]
    paths: dict[str, PathEntry]
    root: int
    crate_version: str
