"""Independent state vocabularies for evidence, resolution, and review.

These three axes are deliberately separate. A syntactic occurrence can be fully
extracted yet unresolved to a library symbol, and a reviewed claim can still
depend on an untested upstream assertion. A single numeric confidence would
hide both distinctions.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "Ecosystem",
    "EvidenceOrigin",
    "ResolutionState",
    "ReviewState",
    "StageCompletion",
    "SurfaceKind",
    "VerificationLevel",
]


class EvidenceOrigin(StrEnum):
    """How an observation was produced."""

    COMPILER_API = "compiler_api"
    STATIC_API = "static_api"
    SYNTAX_MATCH = "syntax_match"
    DOCUMENTATION_STATEMENT = "documentation_statement"
    RUNTIME_REGISTRY = "runtime_registry"
    BEHAVIOR_OBSERVATION = "behavior_observation"


class ResolutionState(StrEnum):
    """How well an observation binds to a library identity."""

    RESOLVED = "resolved"
    CANDIDATE = "candidate"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class ReviewState(StrEnum):
    """Whether a reviewed semantic claim may be published."""

    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    SUPERSEDED = "superseded"


class VerificationLevel(StrEnum):
    """What kind of evidence backs a claim, per assessment section 8.2."""

    DOCUMENTED = "documented"
    SOURCE_REVIEWED = "source_reviewed"
    COMPILED_OR_IMPORTED = "compiled_or_imported"
    BEHAVIOR_TESTED = "behavior_tested"
    INTEGRATION_TESTED = "integration_tested"


class StageCompletion(StrEnum):
    """Whether a stage enumerated and processed its whole declared input set."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class Ecosystem(StrEnum):
    """Packaging ecosystem that owns an identity."""

    RUST = "rust"
    PYTHON = "python"


class SurfaceKind(StrEnum):
    """Functionality that is not a callable symbol.

    An API-only denominator misses much of what makes a library useful, so
    these surfaces carry their own coverage denominators.
    """

    SQL_FUNCTION = "sql_function"
    COMPUTE_FUNCTION = "compute_function"
    CONFIGURATION_KEY = "configuration_key"
    CARGO_FEATURE = "cargo_feature"
    PYTHON_EXTRA = "python_extra"
    ENTRY_POINT = "entry_point"
    EXTENSION_TRAIT = "extension_trait"
    LIFECYCLE_HOOK = "lifecycle_hook"
    FILE_FORMAT = "file_format"
    STORAGE_BACKEND = "storage_backend"
    TRANSPORT = "transport"
    PROTOCOL = "protocol"
    CLI_OPTION = "cli_option"
    ENVIRONMENT_VARIABLE = "environment_variable"
