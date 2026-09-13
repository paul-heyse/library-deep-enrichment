"""Initialize the finite schema catalog before opening a corpus."""

from __future__ import annotations

from importlib import import_module


def load_schemas() -> None:
    """Load the product's registered typed families exactly once per process."""
    import_module("library_deep_enrichment.semantics.schemas")
    import_module("library_deep_enrichment.discovery.schemas")
    import_module("library_deep_enrichment.workflows.schemas")
    import_module("library_deep_enrichment.semantics.enrichment_schemas")
    import_module("library_deep_enrichment.corpus.native_schemas")
    import_module("library_deep_enrichment.semantics.decision_schemas")
    import_module("library_deep_enrichment.semantics.shape_schema")
    import_module("library_deep_enrichment.analyses.fabric_schemas")
    import_module("library_deep_enrichment.analyses.callable_schemas")
    import_module("library_deep_enrichment.analyses.compilation_schemas")
    import_module("library_deep_enrichment.analyses.characterization.schemas")
    import_module("library_deep_enrichment.analyses.call_graph.schemas")
    import_module("library_deep_enrichment.analyses.behavior.schemas")
    import_module("library_deep_enrichment.analyses.behavior.typing_schemas")
    import_module("library_deep_enrichment.analyses.behavior.witness_schemas")
    import_module("library_deep_enrichment.corpus.identities")
