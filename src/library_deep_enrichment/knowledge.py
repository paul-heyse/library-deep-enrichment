"""Versioned knowledge contracts shared by extraction, review and retrieval."""

from __future__ import annotations

from typing import Literal

from attrs import frozen


@frozen(kw_only=True)
class Profile:
    """A version/feature/target scope or an explicitly declared composition of scopes."""

    id: str
    description: str
    components: tuple[str, ...] = ()


@frozen(kw_only=True)
class Source:
    """Immutable source artifact with its acquisition scope."""

    id: str
    path: str
    digest: str
    locator: str
    profile: str
    origin: Literal[
        "compiler_api",
        "static_api",
        "runtime_api",
        "documentation",
        "registry",
        "behavior",
        "source_code",
        "fact",
        "derived",
    ]
    attribution: str
    acquisition: str = ""


@frozen(kw_only=True)
class Evidence:
    """An exact, independently resolvable selection inside a source."""

    id: str
    source: str
    selector: str
    digest: str
    subject: str
    kind: Literal["api", "statement", "registry", "behavior", "source", "fact", "receipt"]


@frozen(kw_only=True)
class Parameter:
    """One callable parameter without losing kind, annotation or default."""

    name: str
    type: str
    kind: str = "positional"
    default: str | None = None
    documented_type: str = ""


@frozen(kw_only=True)
class Binding:
    """A language-specific public interface under a coherent profile."""

    id: str
    symbol: str
    package: str
    version: str
    profile: str
    language: Literal["rust", "python"]
    kind: str
    evidence: tuple[str, ...]
    parameters: tuple[Parameter, ...] = ()
    returns: str = ""
    generics: str = ""
    aliases: tuple[str, ...] = ()
    owner: str = ""
    conditions: tuple[str, ...] = ()
    families: tuple[str, ...] = ()
    resolution: Literal["resolved", "candidate", "ambiguous", "unresolved"] = "resolved"
    signature: str = ""
    documented_returns: str = ""


@frozen(kw_only=True)
class Relation:
    """A compiler or static-analysis relationship, never a behavioral inference."""

    source: str
    target: str
    kind: str
    evidence: str
    resolution: Literal["resolved", "external", "unresolved", "ambiguous"]
    source_symbol: str = ""
    target_symbol: str = ""


@frozen(kw_only=True)
class Facet:
    """An applicable semantic dimension supported by specific claims."""

    name: str
    value: str
    claims: tuple[str, ...]


@frozen(kw_only=True)
class Claim:
    """A behavioral assertion whose acceptance lives in a review receipt."""

    id: str
    profile: str
    statement: str
    mechanism: str
    evidence: tuple[str, ...]
    conditions: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    verification: Literal["documented", "source_reviewed", "behavior_tested"] = "documented"
    category: Literal["structural", "behavioral", "comparative"] = "behavioral"


@frozen(kw_only=True)
class Realization:
    """Conditional causal application of a shared principle."""

    principle: str
    mechanism: str
    conditions: tuple[str, ...]
    claims: tuple[str, ...]


@frozen(kw_only=True)
class Principle:
    """A reusable decision heuristic, with explicit limits rather than a library guarantee."""

    id: str
    statement: str
    exceptions: tuple[str, ...]


@frozen(kw_only=True)
class Capability:
    """A task-level behavior, separate from its concrete bindings."""

    id: str
    title: str
    intent: str
    profile: str
    family: str
    bindings: tuple[str, ...]
    claims: tuple[str, ...]
    facets: tuple[Facet, ...]
    synonyms: tuple[str, ...] = ()
    realizations: tuple[Realization, ...] = ()


@frozen(kw_only=True)
class Candidate:
    """One option and the claim supporting its applicability."""

    capability: str
    when: str
    claims: tuple[str, ...]


@frozen(kw_only=True)
class Decision:
    """Comparison of a complete declared candidate family for a task."""

    id: str
    stack: str
    profile: str
    task: str
    requirements: tuple[str, ...]
    candidates: tuple[Candidate, ...]
    comparison: str
    claims: tuple[str, ...]
    reversing_conditions: tuple[str, ...]
    family: str
    examples: tuple[str, ...] = ()


@frozen(kw_only=True)
class Integration:
    """A directed composition with an explicit boundary contract."""

    id: str
    profile: str
    producer: str
    consumer: str
    representation: str
    ownership: str
    lifecycle: str
    failures: tuple[str, ...]
    claims: tuple[str, ...]
    examples: tuple[str, ...]


@frozen(kw_only=True)
class Obligation:
    """An independently declared coverage denominator member."""

    id: str
    axis: Literal["surface", "use_case", "decision", "composition"]
    profile: str
    target: str
    required_facets: tuple[str, ...] = ()
    disposition: Literal["required", "reference_only", "excluded"] = "required"
    reason: str = ""


@frozen(kw_only=True)
class Review:
    """Reviewer disposition bound to a record and its dependency closure."""

    subject: str
    reviewer: str
    rationale: str
    digest: str
    disposition: Literal["accepted", "needs_review", "rejected"]


@frozen(kw_only=True)
class Example:
    """A bounded executable verification job and the contract it exercises."""

    id: str
    profile: str
    argv: tuple[str, ...]
    inputs: tuple[str, ...]
    claims: tuple[str, ...]
    timeout_seconds: int = 60
    requirements: tuple[tuple[str, str], ...] = ()
    cacheable: bool = False


@frozen(kw_only=True)
class Knowledge:
    """Portable source of truth; indexes and rendered briefs are derived."""

    schema_version: Literal["library-guides.knowledge.v2", "library-guides.knowledge.v3"]
    collection_id: str
    sources: tuple[Source, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    bindings: tuple[Binding, ...] = ()
    claims: tuple[Claim, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    decisions: tuple[Decision, ...] = ()
    integrations: tuple[Integration, ...] = ()
    obligations: tuple[Obligation, ...] = ()
    reviews: tuple[Review, ...] = ()
    examples: tuple[Example, ...] = ()
    relations: tuple[Relation, ...] = ()
    profiles: tuple[Profile, ...] = ()
    principles: tuple[Principle, ...] = ()
