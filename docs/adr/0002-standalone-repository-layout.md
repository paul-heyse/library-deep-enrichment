# 0002. Standalone repository: naming, layout, four Cargo workspaces, service-state root

Date: 2026-09-13
Status: accepted

## Context

`smartref/tooling/library_guides` was already a self-contained uv project with its own
lockfile and its own Cargo workspaces, but it was never committed to smartref's git and its
tests, pilot scripts and README reached into the monorepo by relative path. The operator asked
for a public standalone repository named `library-deep-enrichment` with best-in-class tooling
designed from scratch.

## Decision

- **Names.** Distribution and CLI `library-deep-enrichment`; import package
  `library_deep_enrichment`; crates and binaries `lde-protocol`, `lde-rustdoc-facts`,
  `lde-source-facts`, `lde-python-semantics`, `lde-mir-facts`; environment variables `LDE_*`;
  container label `io.github.paul-heyse.library-deep-enrichment.runtime`; vendored wheel
  local version `+lde.1`. Schema markers are unchanged (ADR 0001).
- **Layout.** `src/` layout with the `uv_build` backend; `crates/` for the workers;
  `scripts/` for build, bootstrap and hooks; `docs/{design,reviews,history,adr}`; `pilot/`
  and `tests/` in place; `.dev-state/` (gitignored) for session state.
- **Four Cargo workspaces, deliberately.** The root workspace holds `protocol` and
  `rustdoc-facts` on the pinned stable toolchain and is what CI builds on every push.
  `source-facts` and `python-semantics` stay standalone because they path-depend into
  vendored ruff and pyrefly clones that carry their own workspaces and lockfiles;
  `mir-facts` stays standalone because it pins `nightly-2026-08-18` and links `rustc_private`.
  Merging them would either drag two upstream dependency universes into one lockfile or make
  `cargo build --workspace` require nightly.
- **Service state.** One root, `LDE_HOME` (default `~/.cache/library-deep-enrichment`),
  resolved through `library_deep_enrichment.paths`. The corpora were moved there from
  `smartref/.cache/library-guides-*` and `~/.cache/library-guides*` (81 GB, same filesystem).
  Agent sessions redirect `LDE_HOME` to `.dev-state/`.
- **Type checker.** pyrefly (ADR 0003 records the strictness baseline).
- **Optional dependencies.** `embed` (transformers, huggingface-hub) and `pilot` (datafusion,
  pydantic) are extras; `torch` was removed because nothing imports it and the embedding
  model runs in a pinned vLLM container.
- **License.** MIT OR Apache-2.0.

## Evidence

- No `[tool.uv.workspace]`, no `[tool.uv.sources]` entry and no root-`Cargo.toml` member
  referenced the sub-project in smartref (verified 2026-09-13); the only reverse reference was
  `pyrefly.toml`'s `search-path`, now removed.
- `cargo check --workspace --all-targets`, `cargo clippy ... -D warnings`, `cargo fmt --check`
  clean on the root workspace; `scripts/native-build.sh --apply` produced all four workers.
- Worker sandbox: uv-managed virtual environments link `python` through a versioned alias
  directory; binding only the endpoint left `execvp` failing inside `bwrap`.
  `worker_runtime._interpreter_roots` now binds every hop.

## Consequences

- `just native-build` is a separate, slower step; CI runs it weekly and on demand
  (`native.yml`) while `ci.yml` covers the root workspace and the Python suite on every push.
- Tests that need a worker report `blocked` when it is unbuilt (`tests/support/workers.py`);
  `just test-native` turns that into a failure.
