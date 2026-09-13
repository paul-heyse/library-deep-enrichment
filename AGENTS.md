# library-deep-enrichment agent instructions

A library knowledge compiler. Rust workers extract exact-release facts (rustdoc JSON, cargo
metadata, source structure, Python typing, MIR behaviour); Python admits them into an
immutable LanceDB/Arrow corpus and answers discovery, comparison and composition questions
over it with evidence attached. Current state is [`STATUS.md`](STATUS.md). The design record
is under [`docs/design/`](docs/design/) (frozen); decisions and deviations are ADRs under
[`docs/adr/`](docs/adr/).

## Binding decisions

| Decision | Requirement |
|---|---|
| Fact production | Rust workers (`crates/`), one binary per lane, framed JSON on stdout, no network, sandboxed by `bwrap`. |
| Corpus and semantics | Python (`src/`): admission, typed families, discovery, comparison, publication, worker supervision. Never a fact producer. |
| Library documentation | **Context7 MCP** (`resolve-library-id`, `query-docs`). A discovery lead, never exact-version proof. |
| Exact-release facts | `lde-rustdoc-facts` over docs.rs rustdoc JSON, `cargo metadata`, Griffe (`allow_inspection=False`), Sphinx inventories. |
| Monolithic reference documents | **Retired.** Not read, not written, not reconstructed. `pre_bash.sh` denies the smartref corpus. |
| Python semantics | **pyrefly**, pinned in the lockfile. Not pyright, not mypy, not ty. |
| Packaging | `uv` only; exact pins; `uv sync --frozen`; `uv_build` backend; src layout. |
| Toolchains | Stable `1.98.1` pinned at the root; `nightly-2026-08-18` pinned only inside `crates/mir-facts`. |
| Workspaces | Four Cargo workspaces on purpose (root, source-facts, python-semantics, mir-facts). Do not merge them. |
| Storage | LanceDB 0.38 / pylance 11 / pyarrow 25, exact. One Arrow type universe. |
| Service state | Under `LDE_HOME` (`~/.cache/library-deep-enrichment`), never inside a working repository. |

Do **not** add: a graph database, a vector database beyond LanceDB's own index, an
in-process model, an RPC server, a workflow engine, automatic edits to any repository under
study, or a prose reference corpus.

## Library lookup

1. Context7 for what a library is and how its API is meant to be used.
2. Exact-release facts for anything a test, a pin, or a design claim depends on.
3. Primary sources (docs.rs, doc.rust-lang.org, crates.io, PyPI, the project repository),
   cited with URL and retrieval date.

Use `/verify-upstream <library> <version> <claim>` before pinning or asserting. Date every
verification claim. "Verified 2026-09-13" is useful a month later; "verified" is not.

## The boundary rule

Corpora, acquired sources, model snapshots and tool runtimes live under `LDE_HOME`. Agent
sessions get `LDE_HOME=.dev-state/` (gitignored) from `scripts/hooks/session_env.sh`, so a
session can never mutate the real corpora. Moving or deleting anything under
`~/.cache/library-deep-enrichment` is an operator action.

The upstream ruff and pyrefly clones under `crates/*/upstream` are gitignored, re-acquired
by `scripts/bootstrap-upstream.sh`, and may differ from upstream only by the crate's owned
`upstream.patch`.

## Command surface

Start with `just --list`. Do not run the full suite before every edit.

| Change | Useful checks |
|---|---|
| Python core | `ruff check`, `pyrefly check`, `pytest tests/<file>` |
| A worker crate | `cargo clippy` in that workspace, then `just test-native` |
| The protocol | both `crates/protocol` and `facts/protocol.py`, then `just test-native` |
| Dependencies | `uv lock` / `cargo update -p`, then `just deps-policy` and an ADR if a pin moved |
| Rules, hooks, agents | `just rules-test`, `just hooks-test` |
| Anything frozen | stop; `/adr` |

`just ci` is the pre-commit surface and matches `.github/workflows/ci.yml` step for step.
`just native-build` + `just test-native` cover the worker workspaces.

## Truthful reporting

Four states: `passed`, `failed`, `blocked`, `not_run`. A test that needs an unbuilt worker,
an absent Souffle runtime or a stopped embedding container is `blocked` with the prerequisite
named; `tests/support/workers.py` reports it as a skip with that reason and
`LDE_REQUIRE_WORKERS=1` turns it into a failure. Never report a pass from a mock of a worker,
the sandbox or the corpus backend. Numbers in `STATUS.md` come from a command that ran.

## Deviations

When a frozen design and reality disagree, record it with `/adr`: the boundary it touches,
primary-source evidence with dates, the tests that prove the new behaviour, consequences.
Preserve the binding decisions. Do not silently reinterpret the design.

## Conventions

`just`, never `make`. Recipe names are kebab-case and outcome-shaped, with `[doc]` and
`[group]`. Mutating recipes are never dependencies of a validation recipe.

Zero suppressions: no `# noqa`, `# type: ignore`, `# pyrefly: ignore`, `#[allow(...)]`, and
no growth of any ignore list. Fix the cause or record an ADR. `post_edit.sh` and
`stop_guard.sh` check mechanically.

Git is observational for agents except `git add`, `git commit`, `git branch`, `git restore`
of your own changes. No force pushes, no history rewrites, no `reset --hard`.

Ruff `line-length = 100`, the rule set in `pyproject.toml` is the gate. Rust edition 2024,
resolver 3, `unsafe_code = "forbid"`, `unwrap`/`expect` warn and the lint gate denies
warnings. Schema markers (`library-guides.*.v1`, `library_guides_public_api`) are on-disk
formats and keep their spelling.

Detailed, path-scoped constraints live in [`.claude/rules/`](.claude/rules/):
`library-lookup`, `python-core`, `rust-workers`, `evidence-truthfulness`, `process-immutable`.
Enforcement has four tiers: a **hook** when the mistake is visible in the tool call alone, an
**ast-grep rule** in `rules/` when it is a code shape, a **`just` gate** when it needs the
whole repository, prose only when there is no mechanical oracle. Review findings are supposed
to land in `rules/`; adding a rule is frictionless on purpose.
