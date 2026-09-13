"""Immutable acquisition, interface, provenance, and lifecycle records.

Application revisions address canonical typed content. Neither physical table
versions nor local source paths participate in an evidence identifier.
"""

from __future__ import annotations

from enum import StrEnum

from attrs import frozen


class Disposition(StrEnum):
    """An explicit outcome, independent of retrieval confidence."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@frozen(kw_only=True)
class Record:
    """Common contextual identity for a family-specific immutable revision."""

    logical_id: str
    profile: str = ""


@frozen(kw_only=True)
class Selection:
    """A field of an admitted record, with its expected canonical value digest."""

    family: str
    revision: str
    field: str
    digest: str
    role: str


@frozen(kw_only=True)
class ByteRange:
    """An interval in original bytes, independent of physical chunk layout."""

    blob: str
    start: int
    end: int
    digest: str


@frozen(kw_only=True)
class Blob(Record):
    """A complete byte object whose chunks are separately stored and verified."""

    digest: str
    size: int
    media_type: str
    chunks: tuple[str, ...]
    chunk_sizes: tuple[int, ...]


@frozen(kw_only=True)
class BlobChunk(Record):
    """A bounded content-addressed byte chunk."""

    data: bytes
    digest: str


@frozen(kw_only=True)
class SourceFile(Record):
    """A source artifact within a frozen acquisition context."""

    blob: str
    package: str
    path: str
    locator: str
    license: str
    acquisition: str


@frozen(kw_only=True)
class RawObservation(Record):
    """Original producer bytes retained alongside their normalized typed projection."""

    producer: str
    kind: str
    context: str
    original: ByteRange


@frozen(kw_only=True)
class RegistryEntry(Record):
    """A runtime-registered surface with its calling protocol and upstream metadata."""

    operation: str
    namespace: str
    kind: str
    arity: str
    argument_names: tuple[str, ...]
    options_class: str
    options_required: bool
    summary: str
    description: str
    input_domain: str
    phase: str
    evidence: tuple[Selection, ...]


@frozen(kw_only=True)
class RegistryKernel(Record):
    """One observed kernel signature; computed outputs remain explicitly unresolved."""

    operation: str
    registry_entry: str
    kind: str
    signature: str
    inputs: tuple[str, ...]
    output: str
    resolution: str
    evidence: tuple[Selection, ...]


@frozen(kw_only=True)
class Context(Record):
    """A concrete environment, package, or compilation context."""

    language: str
    package: str
    version: str
    toolchain: str
    target: str
    features: tuple[str, ...]
    components: tuple[str, ...]
    evidence: tuple[Selection, ...] = ()


@frozen(kw_only=True)
class Argument:
    """An ordered callable slot, preserving symbolic defaults and type identity."""

    name: str
    kind: str
    type_expression: str
    default_expression: str
    required: bool


@frozen(kw_only=True)
class Entity(Record):
    """A contextual declaration, including non-callable interface and extension items."""

    symbol: str
    package: str
    version: str
    kind: str
    routes: tuple[str, ...]
    resolution: str
    evidence: tuple[Selection, ...]


@frozen(kw_only=True)
class Operation(Record):
    """A contextual operation; a declaration is not a behavioral guarantee."""

    symbol: str
    package: str
    version: str
    language: str
    kind: str
    signature: str
    parameters: tuple[Argument, ...]
    returns: str
    routes: tuple[str, ...]
    resolution: str
    evidence: tuple[Selection, ...]


@frozen(kw_only=True)
class TypeNode(Record):
    """A recursive type represented by a node and separately ordered links."""

    owner: str
    kind: str
    name: str
    resolution: str
    evidence: tuple[Selection, ...]


@frozen(kw_only=True)
class TypeUse(Record):
    """A resolved nominal occurrence with its direct/nested and input/output role."""

    owner: str
    nominal: str
    nominal_scope: str
    role: str
    position: int
    direct: bool
    selector: str
    resolution: str
    evidence: tuple[Selection, ...]


@frozen(kw_only=True)
class Relation(Record):
    """A contextual structural edge with explicit resolution and ordering."""

    source: str
    target: str
    kind: str
    position: int
    resolution: str
    evidence: tuple[Selection, ...]


@frozen(kw_only=True)
class Passage(Record):
    """An exact documentation passage, not an automatically accepted claim."""

    owner: str
    role: str
    text: str
    language: str
    source: ByteRange
    evidence: tuple[Selection, ...] = ()
    owner_family: str = "operations"


@frozen(kw_only=True)
class LegacyRecord(Record):
    """Verified original normalized bytes for an import-only legacy alias."""

    artifact: str
    legacy_id: str
    kind: str
    original: ByteRange
    normalized_family: str
    normalized_revision: str


@frozen(kw_only=True)
class LegacySelection(Record):
    """An independently verified old selector and its retained exact selected bytes."""

    source_blob: str
    selector: str
    expected_digest: str
    selected: ByteRange
    legacy_subject: str


@frozen(kw_only=True)
class Scope(Record):
    """A finite universe and its explicit completeness frontier."""

    owner: str
    query: str
    members: tuple[str, ...]
    sources: tuple[Selection, ...]
    disposition: Disposition
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class Policy(Record):
    """Independently admitted policy, including rule and coverage authority."""

    kind: str
    subject: str
    authority: str
    rationale: str
    allowed_predicates: tuple[str, ...]
    required_scopes: tuple[str, ...]


@frozen(kw_only=True)
class Review(Record):
    """An attributed interpretation review bound to exact subject revisions."""

    subject: str
    reviewer: str
    outcome: str
    rationale: str
    selections: tuple[Selection, ...]
    inherited_from: str = ""


@frozen(kw_only=True)
class Job(Record):
    """The latest requested job outcome, including unsuccessful requests."""

    stage: str
    request: str
    inputs: tuple[Selection, ...]
    universes: tuple[str, ...]
    outputs: tuple[str, ...]
    disposition: Disposition
    reason: str
    previous_success: str = ""


@frozen(kw_only=True)
class Gap(Record):
    """Unsettled work and the smallest proposed evidence needed to settle it."""

    subject: str
    predicate: str
    reason: str
    next_evidence: str
    evidence: tuple[Selection, ...] = ()


@frozen(kw_only=True)
class Qualification(Record):
    """An exact consequence or interpretation qualification receipt."""

    subject: str
    method: str
    authority: str
    support: tuple[str, ...]
    disposition: Disposition
    reason: str


@frozen(kw_only=True)
class Release(Record):
    """A qualified selection within the corpus, never a copied source tree."""

    source_manifest: str
    subjects: tuple[str, ...]
    qualifications: tuple[str, ...]
    universes: tuple[str, ...]
    renderer: str
    guide_blob: str


@frozen(kw_only=True)
class Binding:
    """A physical table version selected by one manifest."""

    family: str
    version: int


@frozen(kw_only=True)
class Member:
    """Exact selected revision for a contextual logical record."""

    family: str
    logical_id: str
    profile: str
    revision: str


@frozen(kw_only=True)
class AdmissionBatch:
    """A finite update plus explicit withdrawal from the new view, retaining history."""

    records: tuple[Record, ...]
    retire: tuple[Member, ...] = ()


@frozen(kw_only=True)
class Manifest:
    """Portable logical identity plus local physical bindings."""

    digest: str
    predecessor: str
    members_digest: str
    membership_version: int
    bindings: tuple[Binding, ...]
    count: int


@frozen(kw_only=True)
class Head:
    """An atomically committed named view with its exact manifest table version."""

    name: str
    sequence: int
    manifest: str
    manifest_version: int
    predecessor: str


@frozen(kw_only=True)
class RegistryProperty(Record):
    """An exact nullable registry declaration, distinct from inferred behavioral effects."""

    owner: str
    owner_family: str
    name: str
    value_kind: str
    value_text: str
    evidence: tuple[Selection, ...]
