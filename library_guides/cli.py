"""One admitted-corpus facade for acquisition, semantics, decisions, and publication."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus
    from library_guides.discovery.contracts import DiscoveryScope, SearchSelection
    from library_guides.discovery.embeddings import EmbeddingClient
    from library_guides.semantics.contracts import Task

app = typer.Typer(
    no_args_is_help=True, help="Build and query grounded library capabilities in one corpus."
)
MAX_PAGE_ROWS = 200


@app.callback()
def configure(
    ctx: typer.Context,
    corpus: Annotated[
        Path,
        typer.Option(
            "--corpus",
            "--collection",
            help="Explicit admitted corpus root; legacy collections are import inputs.",
        ),
    ],
    runtime_root: Path | None = None,
    runtime_port: int = 18080,
    max_records: int = 2_500_000,
) -> None:
    """Bind an explicit corpus without workspace inference or legacy generation fallback."""
    ctx.obj = corpus.resolve()
    ctx.meta.update(runtime_root=runtime_root, runtime_port=runtime_port, max_records=max_records)


def _corpus(ctx: typer.Context) -> Corpus:
    from library_guides.corpus.store import Corpus

    if not isinstance(ctx.obj, Path):
        message = "select an admitted --corpus root"
        raise typer.BadParameter(message)
    return Corpus(ctx.obj, max_rows=int(ctx.meta["max_records"]))


def _embedding_client(ctx: typer.Context) -> EmbeddingClient | None:
    from library_guides.runtime import RuntimeConfig, embedding_client

    root = ctx.meta.get("runtime_root")
    return (
        embedding_client(RuntimeConfig(root=root, port=ctx.meta["runtime_port"]))
        if isinstance(root, Path)
        else None
    )


def _emit(value: object) -> None:
    from library_guides.application import encode

    typer.echo(encode(value).decode())


def _task(path: Path) -> Task:
    from library_guides.corpus.encoding import CONVERTER
    from library_guides.semantics.contracts import Task

    return CONVERTER.structure(json.loads(path.read_bytes()), Task)


def _discovery_scope(path: Path | None) -> DiscoveryScope | None:
    from library_guides.corpus.encoding import CONVERTER
    from library_guides.discovery.contracts import DiscoveryScope

    return (
        None if path is None else CONVERTER.structure(json.loads(path.read_bytes()), DiscoveryScope)
    )


@app.command()
def scan(
    ctx: typer.Context,
    family: str,
    continuation: str = "",
    limit: int = 20,
    head: str = "analysis",
) -> None:
    """Read an ordered bounded page with exact counts and a manifest-pinned continuation."""
    _emit(
        _corpus(ctx)
        .reader(head)
        .page(
            family,
            continuation=continuation,
            max_rows=limit,
        )
    )


@app.command()
def candidate_results(
    ctx: typer.Context,
    comparison: str,
    continuation: str = "",
    limit: int = 20,
    head: str = "analysis",
) -> None:
    """Inspect a complete comparison through bounded candidate pages."""
    from library_guides.corpus.sequence_pages import SequenceRequest, read

    _emit(
        read(
            _corpus(ctx).reader(head),
            SequenceRequest(
                family="comparisons",
                revision=comparison,
                field="/candidates",
                continuation=continuation,
                max_rows=limit,
            ),
        )
    )


@app.command()
def sequence(ctx: typer.Context, request: Path, head: str = "analysis") -> None:
    """Page an exact nested sequence using a typed JSON request and pinned continuation."""
    from library_guides.corpus.encoding import CONVERTER
    from library_guides.corpus.sequence_pages import SequenceRequest, read

    specification = CONVERTER.structure(json.loads(request.read_bytes()), SequenceRequest)
    _emit(read(_corpus(ctx).reader(head), specification))


@app.command()
def status(ctx: typer.Context, head: str = "analysis") -> None:
    """Report selected family counts and actual job currentness."""
    from library_guides.application import status as report

    _emit(report(_corpus(ctx).reader(head)))


@app.command()
def build(ctx: typer.Context, stage: str = "semantics", scope: Path | None = None) -> None:
    """Build structure, semantics, retrieval, graphs, concepts, or labels.

    Raises:
        BadParameter: The stage is not in the executable catalog.

    """
    from library_guides.workflows import discovery, enrichment, semantics, shapes

    selection = _discovery_scope(scope)
    if selection is not None and stage not in {
        "retrieval",
        "embeddings",
        "graphs",
        "concepts",
        "labels",
    }:
        message = "explicit scopes support retrieval, embeddings, graphs, concepts, and labels"
        raise typer.BadParameter(message)
    if stage == "embeddings":
        client = _embedding_client(ctx)
        if client is None:
            message = "embedding builds require an explicit --runtime-root"
            raise typer.BadParameter(message)
        _emit(discovery.build_embeddings(_corpus(ctx), client, selection))
        return

    scoped_builders = {
        "retrieval": discovery.build_retrieval,
        "graphs": discovery.build_graphs,
        "concepts": discovery.build_fca,
        "labels": discovery.build_labels,
    }
    if stage in scoped_builders:
        _emit(scoped_builders[stage](_corpus(ctx), selection))
        return

    builders = {
        "structure": enrichment.build,
        "shapes": shapes.build,
        "semantics": semantics.build,
    }
    if stage not in builders:
        message = f"select one of {', '.join(builders)}"
        raise typer.BadParameter(message)
    _emit(builders[stage](_corpus(ctx)))


@app.command()
def discover(
    ctx: typer.Context, query: str, profile: str = "", limit: int = 20, head: str = "analysis"
) -> None:
    """Find source-grounded operations with explicit offline lexical fallback."""
    from library_guides.discovery.contracts import SearchSelection

    _discover(ctx, query, SearchSelection(profiles=(profile,) if profile else ()), limit, head)


@app.command("discover-scoped")
def discover_scoped(
    ctx: typer.Context, query: str, scope: Path, limit: int = 20, head: str = "analysis"
) -> None:
    """Search an exact built profile/package/native-artifact population."""
    from library_guides.discovery.contracts import SearchSelection

    _discover(ctx, query, SearchSelection(scope=_discovery_scope(scope)), limit, head)


def _discover(
    ctx: typer.Context, query: str, selection: SearchSelection, limit: int, head: str
) -> None:
    from attrs import evolve

    from library_guides.application import discover as search

    failure = ""
    try:
        client = _embedding_client(ctx)
    except (OSError, ValueError, RuntimeError) as error:
        client = None
        failure = f"Lexical fallback; embedding initialization failed: {type(error).__name__}"
    result = search(
        _corpus(ctx).reader(head),
        query,
        selection=selection,
        limit=limit,
        client=client,
    )
    _emit(evolve(result, frontier=(failure, *result.frontier)) if failure else result)


@app.command("match-task")
@app.command("compare")
def match_task(ctx: typer.Context, task: Path, *, save: bool = False) -> None:
    """Compare independent candidates; --save admits the typed result."""
    from library_guides.application import match_task as match

    _emit(match(_corpus(ctx), _task(task), save=save))


@app.command()
def compose(ctx: typer.Context, task: Path, max_steps: int = 3, max_plans: int = 20) -> None:
    """Plan bounded multi-input compositions and expose required witnesses."""
    from library_guides.application import compose_task
    from library_guides.semantics.planning import PlanBudget

    _emit(
        compose_task(
            _corpus(ctx).reader(), _task(task), PlanBudget(max_steps=max_steps, max_plans=max_plans)
        )
    )


@app.command("plan-evidence")
@app.command("why-unknown")
def plan_evidence(ctx: typer.Context, task: Path, offset: int = 0, limit: int = 20) -> None:
    """Return next-evidence questions without executing probes.

    Raises:
        BadParameter: The requested page boundary is invalid.

    """
    from library_guides.application import match_task as match
    from library_guides.application import plan_evidence as plan

    if offset < 0 or not 0 < limit <= MAX_PAGE_ROWS:
        message = "invalid evidence page bounds"
        raise typer.BadParameter(message)
    corpus = _corpus(ctx)
    requests = plan(corpus.reader(), match(corpus, _task(task)))
    _emit(
        {
            "manifest": corpus.reader().manifest_id,
            "requests": requests[offset : offset + limit],
            "total": len(requests),
        }
    )


@app.command()
def explore(ctx: typer.Context, text: str = "", limit: int = 20) -> None:
    """Navigate concepts with their structural or positive-support meaning."""
    from library_guides.application import explore as navigate

    _emit(navigate(_corpus(ctx).reader(), text, limit=limit))


@app.command()
def records(
    ctx: typer.Context, family: str, offset: int = 0, limit: int = 20, head: str = "analysis"
) -> None:
    """Inspect a finite typed record page and its continuation offset."""
    from library_guides.application import page

    _emit(page(_corpus(ctx).reader(head), family, offset=offset, limit=limit))


@app.command()
def explain(
    ctx: typer.Context, family: str, revision: str, limit: int = 20, head: str = "analysis"
) -> None:
    """Expand exact record, rule, and evidence relationships."""
    from library_guides.application import explain as expand

    _emit(expand(_corpus(ctx).reader(head), family, revision, limit=limit))


@app.command()
def evidence(
    ctx: typer.Context, family: str, revision: str, field: str, head: str = "analysis"
) -> None:
    """Resolve one exact logical field from a pinned corpus view."""
    from library_guides.corpus.evidence import read_field

    reader = _corpus(ctx).reader(head)
    _emit(
        {
            "manifest": reader.manifest_id,
            "revision": revision,
            "field": field,
            "value": read_field(reader, family, revision, field),
        }
    )


@app.command()
def release(ctx: typer.Context, comparison: str, head: str = "release") -> None:
    """Recheck and publish an admitted comparison and its exact evidence closure.

    Raises:
        BadParameter: The selected revision is not a comparison.

    """
    from library_guides.publication.releases import publish
    from library_guides.semantics.contracts import Comparison

    corpus = _corpus(ctx)
    record = corpus.reader().get("comparisons", comparison)
    if not isinstance(record, Comparison):
        message = "release requires an admitted comparison revision"
        raise typer.BadParameter(message)
    _emit(
        {"manifest": publish(corpus, record, expected=corpus.reader(head).manifest_id, head=head)}
    )


@app.command("export")
def export_release(ctx: typer.Context, destination: Path, head: str = "release") -> None:
    """Export selected families and original bytes as verified portable Parquet."""
    from library_guides.publication.export import export_view

    _emit(export_view(_corpus(ctx).reader(head), destination))


@app.command("import")
def import_release(
    ctx: typer.Context, source: Path, head: str = "release", historical_checker: str = ""
) -> None:
    """Restore a verified portable corpus selection."""
    from library_guides.publication.export import import_view

    _emit(
        {
            "manifest": import_view(
                _corpus(ctx), source, head=head, historical_checker=historical_checker
            )
        }
    )


@app.command("import-legacy")
def import_legacy(ctx: typer.Context, source: Path) -> None:
    """Import a predecessor collection without retaining its write authority."""
    from library_guides.corpus.migration import import_collection

    corpus = _corpus(ctx)
    _emit(import_collection(corpus, source, expected=corpus.reader().manifest_id))


@app.command("import-declarations")
def import_declarations(ctx: typer.Context, source: Path, artifact: str) -> None:
    """Admit a verified native declaration artifact and its original bytes."""
    from library_guides.corpus.lanes import import_declarations as ingest

    corpus = _corpus(ctx)
    _emit(ingest(corpus, source, artifact, expected=corpus.reader().manifest_id))


@app.command("probe-registry")
def probe_registry(ctx: typer.Context, adapter: str, profile: str) -> None:
    """Capture an explicitly selected loaded registry.

    Raises:
        BadParameter: The registry adapter is not in the owned catalog.

    """
    from library_guides.registry_adapters.fabric import adapters

    available = adapters()
    if adapter not in available:
        message = f"select an installed registry adapter: {', '.join(sorted(available))}"
        raise typer.BadParameter(message)
    _emit(available[adapter](_corpus(ctx), profile=profile))


@app.command("admit")
def admit_records(
    ctx: typer.Context, source: Path, authority: str, expected: str, role: str = "producer"
) -> None:
    """Admit authoring records with attribution and an exact expected predecessor."""
    from library_guides.application import admit
    from library_guides.corpus.encoding import CONVERTER
    from library_guides.corpus.schemas import REGISTRY

    corpus = _corpus(ctx)
    rows = json.loads(source.read_bytes())
    proposed = tuple(
        CONVERTER.structure(row["record"], REGISTRY[row["family"]].record_type) for row in rows
    )
    _emit({"manifest": admit(corpus, proposed, authority=authority, role=role, expected=expected)})


@app.command("install-pack")
def install_pack(
    ctx: typer.Context, source: Path, authority: str, *, approve: bool = False
) -> None:
    """Admit reusable model data; --approve attributes approval of the exact revisions."""
    from library_guides.semantic_packs import install

    _emit(install(_corpus(ctx), source, authority=authority, approve=approve))


@app.command("runtime")
def runtime(ctx: typer.Context, action: str = "status", *, apply: bool = False) -> None:
    """Plan explicit runtime setup and lifecycle; --apply executes the displayed action.

    Raises:
        BadParameter: Runtime management requires an explicit owned cache root.

    """
    from library_guides.runtime import RuntimeConfig, lifecycle

    root = ctx.meta.get("runtime_root")
    if not isinstance(root, Path):
        message = "runtime management requires an explicit --runtime-root"
        raise typer.BadParameter(message)
    _emit(lifecycle(RuntimeConfig(root=root, port=ctx.meta["runtime_port"]), action, apply=apply))


@app.command("run-witness")
def run_witness(ctx: typer.Context, recipe: str, bindings: Path) -> None:
    """Execute an approved finite witness against exact operation revision bindings.

    Raises:
        BadParameter: The recipe or operation binding map is malformed.

    """
    from library_guides.semantics.enrichment_contracts import WitnessRecipe
    from library_guides.semantics.experiments import run_witness

    corpus = _corpus(ctx)
    selected = corpus.reader().get("witness_recipes", recipe)
    mapping = json.loads(bindings.read_bytes())
    if (
        not isinstance(selected, WitnessRecipe)
        or not isinstance(mapping, dict)
        or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in mapping.items()
        )
    ):
        message = (
            "a witness recipe revision and a string-to-operation-revision JSON map are required"
        )
        raise typer.BadParameter(message)
    _emit({"manifest": run_witness(corpus, selected, mapping)})


@app.command("counterfactuals")
def counterfactuals(ctx: typer.Context, task: Path, limit: int = 16, *, save: bool = False) -> None:
    """Recompute adjacent finite task contexts and expose exact eligibility changes."""
    from library_guides.corpus.admission import Coordinator, WriterIdentity
    from library_guides.semantics.comparison import counterfactuals
    from library_guides.semantics.decision_contracts import Counterfactual

    corpus = _corpus(ctx)
    reader = corpus.reader()
    records = tuple(counterfactuals(reader, _task(task), limit=limit))
    if save:
        Coordinator(corpus, WriterIdentity(principal="counterfactual-compiler")).commit(
            records, expected=reader.manifest_id
        )
    _emit(tuple(record for record in records if isinstance(record, Counterfactual)))


@app.command("extract-native")
def extract_native(
    ctx: typer.Context, source: Path, transport: Path, catalog: Path | None = None
) -> None:
    """Execute pinned native jobs directly into the corpus; catalog supplies frozen snapshots."""
    from library_guides.workflows.native import build

    _emit(build(_corpus(ctx), source, transport, catalog=catalog))


@app.command("analyze-native")
def analyze_native(ctx: typer.Context, source: Path) -> None:
    """Run bounded MIR flow/effect analysis from an exact artifact/owner request JSON."""
    from library_guides.analyses.fabric_contracts import AnalysisRequest
    from library_guides.corpus.encoding import CONVERTER
    from library_guides.workflows.source_analysis import build

    request = CONVERTER.structure(json.loads(source.read_bytes()), AnalysisRequest)
    _emit(build(_corpus(ctx), request))


@app.command("normalize-python")
def normalize_python(ctx: typer.Context, artifact: str) -> None:
    """Normalize one exact retained syntax artifact; runtime availability stays explicit."""
    from library_guides.workflows.python_interfaces import build

    _emit(build(_corpus(ctx), artifact))


@app.command("analyze-python")
def analyze_python(ctx: typer.Context, source: Path) -> None:
    """Reconcile a retained Python syntax owner with exact same-source typed call candidates."""
    from library_guides.analyses.fabric_contracts import PythonBoundaryRequest
    from library_guides.corpus.encoding import CONVERTER
    from library_guides.workflows.python_boundaries import build

    request = CONVERTER.structure(json.loads(source.read_bytes()), PythonBoundaryRequest)
    _emit(build(_corpus(ctx), request))


@app.command("document-python")
def document_python(ctx: typer.Context, artifact: str) -> None:
    """Attach exact docstring literals to source-normalized Python interfaces."""
    from library_guides.workflows.python_documents import build

    _emit(build(_corpus(ctx), artifact))


@app.command("import-native")
def import_native(ctx: typer.Context, source: Path, artifact: str = "", lane: str = "") -> None:
    """Migrate a finite verified native scope; archival YAML remains read-only.

    Raises:
        BadParameter: The requested scope has no artifacts.

    """
    from library_guides.collection import load
    from library_guides.knowledge_v3 import KnowledgeV3
    from library_guides.native_admission import NativeInputs, admit_artifacts

    knowledge = load(source)
    selected = (
        tuple(
            item
            for item in knowledge.fact_artifacts
            if (not artifact or item.id == artifact) and (not lane or item.artifact_kind == lane)
        )
        if isinstance(knowledge, KnowledgeV3)
        else ()
    )
    if not selected or not isinstance(knowledge, KnowledgeV3):
        message = "the finite native scope contains no matching V3 artifacts"
        raise typer.BadParameter(message)
    _emit(
        admit_artifacts(
            _corpus(ctx),
            NativeInputs(
                root=source,
                artifacts=selected,
                profiles=knowledge.semantic_profiles,
                snapshots=knowledge.source_snapshots,
                stage=f"migration:{source.name}:{artifact or lane or 'all'}",
            ),
        )
    )
