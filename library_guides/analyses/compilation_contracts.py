"""Finite compilation observations, separate from declaration and consumer availability."""

from attrs import frozen

from library_guides.corpus.contracts import Record, Selection


@frozen(kw_only=True)
class CompilationRequest(Record):
    """Exact compiler, Cargo resolution and message catalogs for contextual reconciliation."""

    executables: tuple[str, ...]
    metadata: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()
    max_facts: int = 100_000
    max_bytes: int = 128 * 1024 * 1024


@frozen(kw_only=True)
class ContextSetting:
    """An observed value set, an attributed request, or an explicit unknown."""

    name: str
    values: tuple[str, ...]
    state: str


@frozen(kw_only=True)
class ContextInput:
    """A compiler input with a retained byte witness or an attributed acquisition gap."""

    path: str
    digest: str
    source: str
    state: str


@frozen(kw_only=True)
class CargoCommand:
    """An attributed external observation; never a native process attestation."""

    artifact: str
    source: str
    observer: str
    settings: tuple[ContextSetting, ...]
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class CargoCandidate:
    """An opaque package ID and target joined by source, unit settings and output recipe."""

    metadata: str
    message: str
    package_id: str
    target_source: str
    declared_features: tuple[ContextSetting, ...]
    resolved_features: tuple[str, ...]
    compiled_features: tuple[str, ...]
    state: str
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class CompilationUnit:
    """One selected executable capture, including unresolved or historical captures."""

    artifact: str
    context: str
    invocation: str
    invocation_source: str
    compiler: str
    producer: str
    working_directory: str
    inputs: tuple[ContextInput, ...]
    settings: tuple[ContextSetting, ...]
    candidates: tuple[CargoCandidate, ...]
    state: str
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class CompilationPopulation(Record):
    """Replayable unit reconciliation with finite membership and exact observed provenance."""

    request: str
    model: str
    units: tuple[CompilationUnit, ...]
    commands: tuple[CargoCommand, ...]
    frontier: tuple[str, ...]
    support: tuple[Selection, ...]
