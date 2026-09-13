"""The single registration point for build stages.

Every stage is declared here so the command line, the planner, and the tests all
read one list. A second copy of this list is how target inventories drift.
"""

from __future__ import annotations

from library_deep_enrichment.stages.graph import (
    StageContext,
    StageDefinition,
    StageGraph,
    StageResult,
)

__all__ = ["default_graph", "register"]

_REGISTERED: list[StageDefinition] = []


def register(definition: StageDefinition) -> StageDefinition:
    """Register ``definition`` in the default graph.

    Returns:
        The definition, so registration can decorate a construction site.

    Raises:
        ValueError: When a stage identifier is registered twice.

    """
    if any(existing.stage_id == definition.stage_id for existing in _REGISTERED):
        message = f"stage {definition.stage_id} is already registered"
        raise ValueError(message)
    _REGISTERED.append(definition)
    return definition


def _declare_pipeline() -> None:
    """Declare the stages the build actually runs, in dependency order."""
    if _REGISTERED:
        return
    register(
        StageDefinition(
            stage_id="qualify",
            outputs=("qualification",),
            adapter_id="evidence-qualification@2",
            schema_revision="v2",
            runner=_qualify,
        )
    )
    register(
        StageDefinition(
            stage_id="bundle",
            inputs=("qualification",),
            outputs=("bundle",),
            adapter_id="immutable-bundle@2",
            schema_revision="v2",
            runner=_bundle,
        )
    )


def _qualify(context: StageContext) -> StageResult:
    from library_deep_enrichment.collection import load
    from library_deep_enrichment.qualification import validate
    from library_deep_enrichment.store import ReceiptRequest, build_receipt
    from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes
    from library_deep_enrichment.store.staging import write_atomic

    errors = validate(context.workspace_root, load(context.workspace_root))
    payload = canonical_bytes({"errors": errors})
    write_atomic(context.staging_root / "qualification.json", payload)
    receipt = build_receipt(
        ReceiptRequest(
            stage_id="qualify",
            configuration={},
            enumerated_inputs=1,
            processed_inputs=0 if errors else 1,
            failed=bool(errors),
        )
    )
    return StageResult(
        stage_id="qualify",
        receipt=receipt,
        output_digests={"qualification.json": digest_bytes(payload)},
    )


def _bundle(context: StageContext) -> StageResult:
    from library_deep_enrichment.generations import build, verify
    from library_deep_enrichment.store import ReceiptRequest, build_receipt

    candidate = build(context.workspace_root, context.staging_root)
    receipt = build_receipt(
        ReceiptRequest(stage_id="bundle", configuration={}, enumerated_inputs=1, processed_inputs=1)
    )
    return StageResult(
        stage_id="bundle", receipt=receipt, output_digests={str(candidate): verify(candidate)}
    )


def default_graph() -> StageGraph:
    """Return the graph of every registered stage.

    Returns:
        The stage graph.

    """
    _declare_pipeline()
    return StageGraph(definitions=tuple(_REGISTERED))
