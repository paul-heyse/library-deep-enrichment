"""Owned, typed contracts for immutable extraction and claim support."""

from __future__ import annotations

from typing import Literal

from attrs import frozen

type Outcome = Literal["complete", "partial", "failed", "unsupported", "not_requested"]
type Purpose = Literal["documentation", "check", "mir", "doctest", "python", "metadata", "source"]


@frozen(kw_only=True)
class FileEntry:
    """Exact immutable bytes and their language/source role."""

    path: str
    digest: str
    size: int
    kind: str


@frozen(kw_only=True)
class SourceSnapshot:
    """Acquired source universe; unsupported languages remain inventoried."""

    id: str
    package: str
    version: str
    origin: str
    files: tuple[FileEntry, ...]
    attribution: str
    source_digest: str


@frozen(kw_only=True)
class Setting:
    """A captured configuration input; absent values are explicit unknowns."""

    name: str
    value: str | None
    origin: Literal["requested", "observed", "unknown"]


@frozen(kw_only=True)
class SemanticProfile:
    """Evidence-backed settings, separate from a descriptive profile label."""

    id: str
    purpose: Purpose
    package: str
    version: str
    source_digest: str
    toolchain: str
    target: str | None
    settings: tuple[Setting, ...] = ()
    dependency_digests: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@frozen(kw_only=True)
class Budget:
    """Enforced process, frame, source and query resource limits."""

    wall_seconds: int = 180
    cpu_seconds: int = 180
    memory_bytes: int = 4_000_000_000
    frame_bytes: int = 32_000_000
    output_bytes: int = 2_000_000_000
    stderr_bytes: int = 1_000_000
    input_bytes: int = 1_000_000_000
    max_records: int = 1_000_000


@frozen(kw_only=True)
class FactShard:
    """A canonical indexed record stream; its bytes are independently verified."""

    path: str
    digest: str
    records: int


@frozen(kw_only=True)
class FactArtifact:
    """Immutable extraction product with independently verifiable provenance."""

    id: str
    schema: str
    profile: str
    producer: str
    input_path: str
    input_digest: str
    header_path: str
    receipt_path: str
    receipt_digest: str
    shards: tuple[FactShard, ...]
    outcome: Outcome
    artifact_kind: Literal[
        "declarations",
        "cargo",
        "syntax",
        "execution",
        "lexical",
        "types",
        "mir",
        "mir_execution",
        "mir_instances",
        "mir_callables",
        "mir_lifecycle",
        "mir_memory",
        "derived",
    ]
    job: str = ""
    context: str = ""
    snapshots: tuple[str, ...] = ()
    acquisition_path: str = ""
    acquisition_digest: str = ""
    witnesses: tuple[FileEntry, ...] = ()
    dependencies: tuple[FactSelection, ...] = ()


@frozen(kw_only=True)
class FactHead:
    """The requested job head, including failures that cannot reuse older facts."""

    job: str
    profile: str
    request: str
    artifact: str | None
    outcome: Outcome
    reason: str = ""


@frozen(kw_only=True)
class SourceSegment:
    """A generated interval mapped exactly to host bytes or synthetic text."""

    generated_start: int
    generated_end: int
    host_start: int | None
    host_end: int | None


@frozen(kw_only=True)
class SourceAnchor:
    """Exact byte coordinates including disjoint and transformed source segments."""

    snapshot: str
    file: str
    digest: str
    role: str
    segments: tuple[SourceSegment, ...]
    encoding: Literal["utf-8", "raw"] = "utf-8"


@frozen(kw_only=True)
class FactSelection:
    """A specific assertion-supporting field, never an entire corpus."""

    artifact: str
    record: str
    selector: str
    digest: str
    role: Literal["declaration", "statement", "mechanism", "execution", "context"]


@frozen(kw_only=True)
class AnalysisScope:
    """A retained relevant universe required for bounded negative assertions."""

    predicate: str
    profile: str
    owners: tuple[str, ...]
    receipts: tuple[str, ...]
    model: str
    frontier: tuple[str, ...]
    closed: bool
    mode: Literal["inventory", "conservative", "heuristic"]


@frozen(kw_only=True)
class ClaimSupport:
    """Assertion-specific support; extraction never grants an entailment review."""

    id: str
    claim: str
    assertion: str
    kind: Literal[
        "signature",
        "upstream_statement",
        "shape",
        "trait_obligation",
        "public_route",
        "availability",
        "mechanism",
        "behavior",
        "comparison",
        "bounded_absence",
    ]
    facts: tuple[FactSelection, ...]
    assumptions: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    scope: AnalysisScope | None = None
    dependency_mode: Literal["declaration", "documentation", "body", "universe"] = "declaration"


@frozen(kw_only=True)
class ReviewRevalidation:
    """Recorded equivalence without rewriting a review's historical evidence."""

    subject: str
    previous_digest: str
    current_digest: str
    policy: str
    checks: tuple[str, ...]
    outcome: Literal["equivalent", "needs_review"]
    prior_knowledge: FileEntry | None = None
    prior_inputs: tuple[FileEntry, ...] = ()


@frozen(kw_only=True)
class FacetSeed:
    """Unreviewed generated value or a concrete evidence gap."""

    capability: str
    dimension: str
    value: str | None
    facts: tuple[FactSelection, ...]
    missing: tuple[str, ...]
    recipe: str


@frozen(kw_only=True)
class ExampleDiscovery:
    """Located examples keep parsing, typing and execution separate."""

    id: str
    anchor: SourceAnchor
    language: str
    code: str
    directives: tuple[str, ...]
    status: Literal["located", "parsed", "names_resolved", "type_checked", "executed"]
    limitations: tuple[str, ...] = ()
    facts: tuple[FactSelection, ...] = ()
    display_code: str = ""
    display_segments: tuple[SourceSegment, ...] = ()


@frozen(kw_only=True)
class CandidateUniverse:
    """Independently authored declaration query; generated nominations cannot shrink it."""

    id: str
    profile: str
    jobs: tuple[str, ...]
    nominal: str
    role: Literal["any", "input", "output"] = "any"


@frozen(kw_only=True)
class UniverseDependency:
    """A reviewed choice depends on all candidates, including newly acquired ones."""

    subject: str
    universe: str
