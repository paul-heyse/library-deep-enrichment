"""Initialize the finite schema catalog before opening a corpus."""

from __future__ import annotations

from importlib import import_module


def load_schemas() -> None:
    """Load the product's registered typed families exactly once per process."""
    import_module("library_guides.semantics.schemas")
    import_module("library_guides.discovery.schemas")
    import_module("library_guides.workflows.schemas")
    import_module("library_guides.semantics.enrichment_schemas")
    import_module("library_guides.corpus.native_schemas")
    import_module("library_guides.semantics.decision_schemas")
    import_module("library_guides.semantics.shape_schema")
    import_module("library_guides.analyses.fabric_schemas")
    import_module("library_guides.analyses.callable_schemas")
    import_module("library_guides.analyses.compilation_schemas")
    import_module("library_guides.analyses.characterization.schemas")
    import_module("library_guides.analyses.call_graph.schemas")
    import_module("library_guides.analyses.behavior.schemas")
    import_module("library_guides.analyses.behavior.typing_schemas")
    import_module("library_guides.analyses.behavior.witness_schemas")
    import_module("library_guides.corpus.identities")
