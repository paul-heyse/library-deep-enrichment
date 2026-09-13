"""Independent, reusable discovery stages whose inputs and receipts live in the corpus."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from attrs import evolve

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.encoding import bytes_digest, digest
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.discovery.contracts import DiscoveryScope, EmbeddingRecipe
from library_deep_enrichment.discovery.reuse import embed_current
from library_deep_enrichment.discovery.scopes import prefix
from library_deep_enrichment.workflows.contracts import FamilySelector, InputFamily, StageDefinition
from library_deep_enrichment.workflows.engine import StageResult, run_stage
from library_deep_enrichment.workflows.remote import RemoteProducer

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus
    from library_deep_enrichment.discovery.embeddings import EmbeddingClient


def definition(
    name: str,
    inputs: dict[str, tuple[str, ...]],
    outputs: tuple[str, ...],
    modules: tuple[str, ...],
    *,
    dependencies: tuple[str, ...] = (),
) -> StageDefinition:
    """Fingerprint the finite producer implementation without hashing unrelated tooling.

    Returns:
        A typed stage contract with explicit resource boundaries and model inputs.

    """
    root = Path(__file__).parents[1]
    fingerprint = digest(
        [
            (module, bytes_digest((root / module).read_bytes()))
            for module in (
                *modules,
                "workflows/remote.py",
                "workflows/worker.py",
                "workflows/inputs.py",
                "workflows/engine.py",
                "workflows/failure_records.py",
                "worker_runtime.py",
                "worker_resources.py",
                "worker_observations.py",
                "_worker_entry.py",
            )
        ]
    )
    return StageDefinition(
        logical_id=name,
        inputs=tuple(
            InputFamily(family=family, fields=fields) for family, fields in inputs.items()
        ),
        outputs=(*outputs, "stage_executions"),
        dependencies=dependencies,
        implementation=fingerprint,
        max_records=100_000,
        max_bytes=256 * 1024 * 1024,
        max_seconds=600.0,
    )


def stage_name(name: str, scope: DiscoveryScope | None) -> str:
    """Namespace stage ownership by the declared selector identity.

    Returns:
        A stable job key whose request fingerprint still includes the exact selectors.

    """
    return name if scope is None else f"{name}:scope:{digest(scope.logical_id)}"


def _scoped(stage: StageDefinition, scope: DiscoveryScope | None) -> StageDefinition:
    if scope is None:
        return stage
    return evolve(
        stage,
        logical_id=stage_name(stage.logical_id, scope),
        implementation=digest([stage.implementation, revision_of(scope)]),
        inputs=(
            *stage.inputs,
            InputFamily(
                family="discovery_scopes",
                fields=("/profiles", "/packages", "/artifacts", "/max_units"),
            ),
        ),
        dependencies=tuple(stage_name(name, scope) for name in stage.dependencies),
    )


def _selectors(stage: StageDefinition, scope: DiscoveryScope | None) -> tuple[FamilySelector, ...]:
    if scope is None:
        return ()
    result = []
    for item in stage.inputs:
        if item.family == "discovery_scopes":
            result.append(FamilySelector(family=item.family, logical_ids=(scope.logical_id,)))
        elif item.family == "retrieval_units":
            result.append(FamilySelector(family=item.family, prefix=prefix(scope)))
        elif item.family == "concepts":
            result.append(
                FamilySelector(family=item.family, prefix=f"scoped:{digest(scope.logical_id)}:")
            )
        elif (
            item.family
            in {
                "operations",
                "passages",
                "relations",
                "type_uses",
                "native_facts",
                "assertions",
                "qualifications",
            }
            and scope.profiles
        ):
            result.append(FamilySelector(family=item.family, profiles=scope.profiles))
    return tuple(result)


def build_retrieval(corpus: Corpus, scope: DiscoveryScope | None = None) -> StageResult:
    """Construct source views independently of expensive embedding or concept work.

    Returns:
        A current source-view receipt or exact warm reuse.

    """
    stage = definition(
        "retrieval-units.v1",
        {
            "operations": ("/signature", "/returns", "/symbol", "/profile"),
            "passages": ("/owner", "/text", "/role"),
            "native_facts": ("/artifact",),
        },
        ("retrieval_units", "scopes") if scope is not None else ("retrieval_units",),
        ("discovery/units.py", "discovery/scopes.py"),
    )
    if scope is not None:
        reader = corpus.reader()
        Coordinator(corpus, WriterIdentity(principal="discovery-selection")).commit(
            (scope,), expected=reader.manifest_id
        )

    stage = _scoped(stage, scope)
    return run_stage(
        corpus,
        stage,
        RemoteProducer(root=corpus.root, definition=stage, route="retrieval", scope=scope),
        selectors=_selectors(stage, scope),
    )


def build_embeddings(
    corpus: Corpus, client: EmbeddingClient, scope: DiscoveryScope | None = None
) -> StageResult:
    """Request actual vectors for exact current source units and a pinned recipe.

    Returns:
        The embedding stage receipt; unchanged inputs perform no inference.

    """
    reader = corpus.reader()
    Coordinator(corpus, WriterIdentity(principal="embedding-recipe")).commit(
        (client.recipe,), expected=reader.manifest_id
    )
    stage = definition(
        f"embeddings:{client.recipe.logical_id}",
        {
            "retrieval_units": ("/text", "/text_digest"),
            "embedding_recipes": ("/model_revision", "/query_template", "/max_tokens"),
        },
        ("embeddings",),
        ("discovery/embeddings.py", "discovery/reuse.py", "discovery/scopes.py"),
        dependencies=("retrieval-units.v1",),
    )
    stage = _scoped(stage, scope)
    return run_stage(
        corpus,
        stage,
        lambda source: embed_current(source, client, scope),
        selectors=(
            *_selectors(stage, scope),
            FamilySelector(family="embedding_recipes", logical_ids=(client.recipe.logical_id,)),
        ),
    )


def build_graphs(corpus: Corpus, scope: DiscoveryScope | None = None) -> StageResult:
    """Compute graph projections after source-unit and optional embedding admission.

    Returns:
        A recorded structural/semantic/fused graph outcome.

    """
    stage = definition(
        "discovery-graphs.v1",
        {
            "retrieval_units": ("/subject", "/text_digest"),
            "relations": ("/source", "/target", "/kind"),
            "type_uses": ("/owner", "/nominal", "/nominal_scope", "/direct", "/resolution"),
            "embeddings": ("/unit", "/recipe", "/input_digest"),
        },
        ("graph_nodes", "graph_edges", "scopes", "concepts"),
        ("discovery/graphs.py", "discovery/scopes.py"),
        dependencies=("retrieval-units.v1",),
    )
    stage = _scoped(stage, scope)
    return run_stage(
        corpus,
        stage,
        RemoteProducer(root=corpus.root, definition=stage, route="graphs", scope=scope),
        selectors=_selectors(stage, scope),
    )


def build_fca(corpus: Corpus, scope: DiscoveryScope | None = None) -> StageResult:
    """Build observed-support conjunctions after qualification, independent of communities.

    Returns:
        Bounded exact FCA products and their explicit enumeration frontier.

    """
    stage = definition(
        "support-fca.v1",
        {
            "operations": ("/profile",),
            "assertions": ("/state", "/condition", "/value"),
            "qualifications": ("/subject", "/disposition", "/authority"),
        },
        ("attributes", "concepts", "scopes"),
        ("discovery/fca.py", "discovery/scopes.py"),
    )
    stage = _scoped(stage, scope)
    return run_stage(
        corpus,
        stage,
        RemoteProducer(root=corpus.root, definition=stage, route="fca", scope=scope),
        selectors=_selectors(stage, scope),
    )


def build_labels(corpus: Corpus, scope: DiscoveryScope | None = None) -> StageResult:
    """Refresh display descriptors without extraction or base-vector inference.

    Returns:
        A descriptor-only receipt preserving concept membership identity.

    """
    stage = definition(
        "concept-labels.v1",
        {"retrieval_units": ("/text",), "concepts": ("/members",)},
        ("descriptors",),
        ("discovery/labels.py", "discovery/scopes.py"),
    )
    stage = _scoped(stage, scope)
    return run_stage(
        corpus,
        stage,
        RemoteProducer(root=corpus.root, definition=stage, route="labels", scope=scope),
        selectors=_selectors(stage, scope),
    )


def qwen_recipe() -> EmbeddingRecipe:
    """Return the initial locally qualified embedding-space contract.

    Returns:
        The pinned Qwen3 document/query and numerical recipe, without a service location.

    """
    revision = "1d8ad4ca9b3dd8059ad90a75d4983776a23d44af"
    return EmbeddingRecipe(
        logical_id="qwen3-embedding-8b.v1",
        model="Qwen/Qwen3-Embedding-8B",
        model_revision=revision,
        tokenizer="Qwen/Qwen3-Embedding-8B",
        tokenizer_revision=revision,
        dimension=4096,
        dtype="float32",
        pooling="last-token",
        normalization="l2",
        max_tokens=4096,
        document_prefix="",
        query_template="Instruct: Given a programming task, retrieve library operations and their relevant documented contracts.\nQuery: {query}",
        runtime="vllm/vllm-openai@sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1;bf16;pooling;max_model_len=4096",
    )
