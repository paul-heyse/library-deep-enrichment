"""Unified-fabric commands mounted on the existing product facade during cutover."""

from __future__ import annotations

import json
from pathlib import Path

import typer


def _corpus(ctx: typer.Context) -> object:
    """Resolve the explicitly selected corpus root.

    Returns:
        The configured corpus handle.

    Raises:
        BadParameter: The command has no configured root.

    """
    from library_guides.corpus.store import Corpus

    if not isinstance(ctx.obj, Path):
        message = "select the corpus using --collection"
        raise typer.BadParameter(message)
    return Corpus(ctx.obj)


def mount(app: typer.Typer) -> None:
    """Mount fabric commands; imports stay inside commands for cheap CLI startup."""
    app.command("fabric-import")(_import_collection)
    app.command("fabric-status")(_status)
    app.command("semantic-build")(_build)
    app.command("fabric-export")(_export)
    app.command("fabric-restore")(_restore)


def _import_collection(ctx: typer.Context, source: Path) -> None:
    from attrs import asdict

    from library_guides.corpus.migration import import_collection
    from library_guides.corpus.store import Corpus

    corpus = _corpus(ctx)
    assert isinstance(corpus, Corpus)
    result = import_collection(corpus, source, expected=corpus.reader().manifest_id)
    typer.echo(json.dumps(asdict(result), indent=2))


def _status(ctx: typer.Context, head: str = "analysis") -> None:
    from attrs import asdict

    from library_guides.corpus.store import Corpus

    corpus = _corpus(ctx)
    assert isinstance(corpus, Corpus)
    reader = corpus.reader(head)
    typer.echo(
        json.dumps(
            {
                "manifest": reader.manifest_id,
                "families": {}
                if reader.manifest is None
                else {
                    binding.family: sum(1 for _ in reader.members(binding.family))
                    for binding in reader.manifest.bindings
                },
                "jobs": [asdict(item) for item in reader.records("jobs")],
            },
            indent=2,
        )
    )


def _build(ctx: typer.Context) -> None:
    from attrs import asdict

    from library_guides.corpus.store import Corpus
    from library_guides.workflows.semantics import build

    corpus = _corpus(ctx)
    assert isinstance(corpus, Corpus)
    typer.echo(json.dumps(asdict(build(corpus)), indent=2))


def _export(ctx: typer.Context, destination: Path, head: str = "release") -> None:
    from attrs import asdict

    from library_guides.corpus.store import Corpus
    from library_guides.publication.export import export_view

    corpus = _corpus(ctx)
    assert isinstance(corpus, Corpus)
    typer.echo(json.dumps(asdict(export_view(corpus.reader(head), destination)), indent=2))


def _restore(ctx: typer.Context, source: Path, head: str = "release") -> None:
    from library_guides.corpus.store import Corpus
    from library_guides.publication.export import import_view

    corpus = _corpus(ctx)
    assert isinstance(corpus, Corpus)
    typer.echo(json.dumps({"manifest": import_view(corpus, source, head=head)}, indent=2))
