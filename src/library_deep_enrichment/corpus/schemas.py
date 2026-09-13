"""Explicit family Arrow schemas and strict attrs/cattrs boundary codecs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
from attrs import frozen

from library_deep_enrichment.corpus import contracts as c
from library_deep_enrichment.corpus.encoding import CONVERTER, digest, payload

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

TEXT = pa.string()
TEXTS = pa.list_(pa.field("item", TEXT, nullable=False))
NUMBER = pa.int64()
SELECTION = pa.struct(
    [
        pa.field(name, TEXT, nullable=False)
        for name in ("family", "revision", "field", "digest", "role")
    ]
)
SELECTIONS = pa.list_(pa.field("item", SELECTION, nullable=False))
BYTE_RANGE = pa.struct(
    [
        pa.field("blob", TEXT, nullable=False),
        pa.field("start", NUMBER, nullable=False),
        pa.field("end", NUMBER, nullable=False),
        pa.field("digest", TEXT, nullable=False),
    ]
)
ARGUMENT = pa.struct(
    [
        *[
            pa.field(name, TEXT, nullable=False)
            for name in (
                "name",
                "kind",
                "type_expression",
                "default_expression",
            )
        ],
        pa.field("required", pa.bool_(), nullable=False),
    ]
)


@frozen(kw_only=True)
class Codec:
    """One registered immutable record family and its physical schema."""

    family: str
    record_type: type[c.Record]
    schema: pa.Schema

    def encode(self, record: c.Record) -> dict[str, object]:
        """Return an Arrow-ready, content-addressed row.

        Returns:
            An Arrow-ready, content-addressed row.

        Raises:
            TypeError: The caller used a different family.

        """
        if type(record) is not self.record_type:
            message = f"{self.family} cannot encode {type(record).__name__}"
            raise TypeError(message)
        body = payload(record)
        return {"revision": digest([self.family, 1, body]), **body}

    def decode(self, row: Mapping[str, object]) -> c.Record:
        """Return a validated record, rejecting changed content under an ID.

        Returns:
            A validated record, rejecting changed content under an ID.

        Raises:
            ValueError: A stored revision does not match the content.

        """
        body = dict(row)
        revision = body.pop("revision")
        record = CONVERTER.structure(body, self.record_type)
        if self.encode(record)["revision"] != revision:
            message = f"corrupt revision in {self.family}: {revision}"
            raise ValueError(message)
        return record


REGISTRY: dict[str, Codec] = {}


def register(
    family: str,
    record_type: type[c.Record],
    fields: Iterable[tuple[str, pa.DataType]],
) -> None:
    """Register an explicit family schema before any corpus is opened.

    Raises:
        ValueError: A family name is registered twice.

    """
    if family in REGISTRY:
        message = f"duplicate corpus family: {family}"
        raise ValueError(message)
    fields = tuple(fields)
    names = [name for name, _ in fields]
    if set(names) & {"revision", "logical_id", "profile"} or len(names) != len(set(names)):
        message = f"family schema contains reserved or duplicate fields: {family}"
        raise ValueError(message)
    schema = pa.schema(
        [
            pa.field(name, kind, nullable=False)
            for name, kind in [("revision", TEXT), ("logical_id", TEXT), ("profile", TEXT), *fields]
        ],
        metadata={b"library-guides-family": family.encode(), b"schema-version": b"1"},
    )
    REGISTRY[family] = Codec(family=family, record_type=record_type, schema=schema)


def fields(*names: str) -> list[tuple[str, pa.DataType]]:
    """Return explicit non-null text fields for compact schema declarations.

    Returns:
        Explicit non-null text fields for compact schema declarations.

    """
    return [(name, TEXT) for name in names]


def codec_for(record: c.Record) -> Codec:
    """Return the codec for the exact record class.

    Returns:
        The codec for the exact record class.

    Raises:
        TypeError: The producer used an unregistered contract.

    """
    from library_deep_enrichment.corpus.catalog import load_schemas

    load_schemas()
    for codec in REGISTRY.values():
        if type(record) is codec.record_type:
            return codec
    message = f"unregistered record class: {type(record).__name__}"
    raise TypeError(message)


def revision_of(record: c.Record) -> str:
    """Return the immutable application revision of a typed record.

    Returns:
        The immutable application revision of a typed record.

    """
    return str(codec_for(record).encode(record)["revision"])


register(
    "blobs",
    c.Blob,
    [
        *fields("digest", "media_type"),
        ("size", NUMBER),
        ("chunks", TEXTS),
        ("chunk_sizes", pa.list_(NUMBER)),
    ],
)
register("blob_chunks", c.BlobChunk, [("data", pa.binary()), ("digest", TEXT)])
register(
    "source_files",
    c.SourceFile,
    fields("blob", "package", "path", "locator", "license", "acquisition"),
)
register(
    "raw_observations",
    c.RawObservation,
    [*fields("producer", "kind", "context"), ("original", BYTE_RANGE)],
)
register(
    "registry_entries",
    c.RegistryEntry,
    [
        *fields(
            "operation",
            "namespace",
            "kind",
            "arity",
            "options_class",
            "summary",
            "description",
            "input_domain",
            "phase",
        ),
        ("argument_names", TEXTS),
        ("options_required", pa.bool_()),
        ("evidence", SELECTIONS),
    ],
)
register(
    "registry_kernels",
    c.RegistryKernel,
    [
        *fields("operation", "registry_entry", "kind", "signature", "output", "resolution"),
        ("inputs", TEXTS),
        ("evidence", SELECTIONS),
    ],
)
register(
    "contexts",
    c.Context,
    [
        *fields("language", "package", "version", "toolchain", "target"),
        ("features", TEXTS),
        ("components", TEXTS),
        ("evidence", SELECTIONS),
    ],
)
register(
    "entities",
    c.Entity,
    [
        *fields("symbol", "package", "version", "kind", "resolution"),
        ("routes", TEXTS),
        ("evidence", SELECTIONS),
    ],
)
register(
    "operations",
    c.Operation,
    [
        *fields(
            "symbol", "package", "version", "language", "kind", "signature", "returns", "resolution"
        ),
        ("parameters", pa.list_(pa.field("item", ARGUMENT, nullable=False))),
        ("routes", TEXTS),
        ("evidence", SELECTIONS),
    ],
)
register(
    "type_nodes",
    c.TypeNode,
    [*fields("owner", "kind", "name", "resolution"), ("evidence", SELECTIONS)],
)
register(
    "type_uses",
    c.TypeUse,
    [
        *fields("owner", "nominal", "nominal_scope", "role", "selector", "resolution"),
        ("position", NUMBER),
        ("direct", pa.bool_()),
        ("evidence", SELECTIONS),
    ],
)
register(
    "relations",
    c.Relation,
    [
        *fields("source", "target", "kind", "resolution"),
        ("position", NUMBER),
        ("evidence", SELECTIONS),
    ],
)
register(
    "passages",
    c.Passage,
    [
        *fields("owner", "owner_family", "role", "text", "language"),
        ("source", BYTE_RANGE),
        ("evidence", SELECTIONS),
    ],
)
register(
    "legacy_records",
    c.LegacyRecord,
    [
        *fields("artifact", "legacy_id", "kind", "normalized_family", "normalized_revision"),
        ("original", BYTE_RANGE),
    ],
)
register(
    "legacy_selections",
    c.LegacySelection,
    [
        *fields("source_blob", "selector", "expected_digest", "legacy_subject"),
        ("selected", BYTE_RANGE),
    ],
)
register(
    "scopes",
    c.Scope,
    [
        *fields("owner", "query", "disposition"),
        ("members", TEXTS),
        ("sources", SELECTIONS),
        ("frontier", TEXTS),
    ],
)
register(
    "policies",
    c.Policy,
    [
        *fields("kind", "subject", "authority", "rationale"),
        ("allowed_predicates", TEXTS),
        ("required_scopes", TEXTS),
    ],
)
register(
    "reviews",
    c.Review,
    [
        *fields("subject", "reviewer", "outcome", "rationale", "inherited_from"),
        ("selections", SELECTIONS),
    ],
)
register(
    "jobs",
    c.Job,
    [
        *fields("stage", "request", "disposition", "reason", "previous_success"),
        ("inputs", SELECTIONS),
        ("universes", TEXTS),
        ("outputs", TEXTS),
    ],
)
register(
    "gaps",
    c.Gap,
    [
        *fields("subject", "predicate", "reason", "next_evidence"),
        ("evidence", SELECTIONS),
    ],
)
register(
    "qualifications",
    c.Qualification,
    [
        *fields("subject", "method", "authority", "disposition", "reason"),
        ("support", TEXTS),
    ],
)
register(
    "releases",
    c.Release,
    [
        *fields("source_manifest", "renderer", "guide_blob"),
        ("subjects", TEXTS),
        ("qualifications", TEXTS),
        ("universes", TEXTS),
    ],
)
register(
    "registry_properties",
    c.RegistryProperty,
    [
        *fields("owner", "owner_family", "name", "value_kind", "value_text"),
        ("evidence", SELECTIONS),
    ],
)
