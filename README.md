# library-deep-enrichment

A library knowledge compiler. It extracts **exact-release facts** about the libraries a
project depends on and compiles them into an immutable, queryable corpus that a coding agent
can ask *what can this library do, what evidence supports it, and what remains unknown?*

Facts come from code, not from prose: rustdoc JSON and `cargo metadata` for Rust; Griffe,
Sphinx inventories and a pyrefly-based typing worker for Python; tree-sitter and Ruff for
source structure; a `rustc_public` MIR worker for behaviour. Library *documentation* is
looked up live through the [Context7](https://github.com/upstash/context7) MCP tools during
development and never copied into this repository as reference manuals.

## Status

See [`STATUS.md`](STATUS.md) for measured counts and [`docs/adr/`](docs/adr/) for every
decision that departs from the frozen design record under [`docs/design/`](docs/design/).
This repository was migrated on 2026-09-13 from a monorepo sub-project; ADR 0001 and 0002
record what changed. The foundational behaviour-characterization work is paused at the
migration checkpoint: only FB00/G0 is accepted, and
[`docs/design/foundational_behavior_characterization_status_and_repo_handover_2026-09-13.md`](docs/design/foundational_behavior_characterization_status_and_repo_handover_2026-09-13.md)
records every remaining package and gate.

## How it fits together

```
                 ┌────────────── crates/ (Rust workers, one binary per lane) ──────────────┐
  docs.rs        │ lde-rustdoc-facts   rustdoc JSON, public API, cargo metadata (stable)     │
  PyPI / wheels  │ lde-source-facts    tree-sitter coordinates + Ruff semantic facade        │
  source trees ─►│ lde-python-semantics pyrefly types, calls, TSP queries                    │──► framed JSON
                 │ lde-mir-facts       rustc_public bodies, lifecycle, callables (nightly)   │    on stdout
                 └──────────────────────────────────────────────────────────────────────────┘
                                                   │  bwrap-sandboxed, budgeted
                                                   ▼
                 src/library_deep_enrichment/  admission → typed families → semantics →
                 discovery / comparison / composition → publication (LanceDB / Arrow corpus)
                                                   │
                                                   ▼
                 library-deep-enrichment CLI: status · discover · match-task · compose ·
                 explain · evidence · release · export / import · extract-native · runtime
```

Workers never execute the code they analyse and never open the network. The Python side
supervises them with explicit read and write roots and budgets, admits complete validated
artifacts only, and keeps every fact's provenance (source digest, producer identity, request).

## Quick start

```sh
just setup          # toolchain check, uv sync (all groups and extras), dev state, doctor
direnv allow        # optional: puts .venv/bin and .dev-state/bin on PATH
just native-build   # bootstrap the pinned ruff/pyrefly clones and build the four workers
just ci             # the gate: fmt, lint, check, tests, pyrefly, deny, rules, hooks
just test-native    # worker canaries (requires the build above)
just corpus-status  # family counts for the default corpus
```

Requirements: the pinned stable Rust toolchain (`rust-toolchain.toml`, installed by rustup
automatically), `nightly-2026-08-18` with `rustc-dev`, `rust-src`, `llvm-tools` for the MIR
worker, `uv`, `just`, and `/usr/bin/bwrap` (bubblewrap) for the worker sandbox. `just doctor`
reports what is present.

## Service state

Nothing is written inside a working repository. All state resolves from one root:

| Variable | Default | Holds |
|---|---|---|
| `LDE_HOME` | `~/.cache/library-deep-enrichment` | everything below |
| `LDE_CORPUS` | `$LDE_HOME/intelligence/pilot-v4/corpus` | the corpus the CLI binds |
| `LDE_RUNTIME_ROOT` | `$LDE_HOME/runtime` | embedding model snapshot, tools, lifecycle receipts |

Agent sessions get `LDE_HOME=.dev-state/` (gitignored) from the session hook, so an agent can
never mutate the real corpora. See `src/library_deep_enrichment/paths.py`.

The optional embedding runtime is a pinned vLLM container serving Qwen3-Embedding-8B on
loopback port 18080: `just runtime provision --apply`, `just runtime start --apply`,
`just runtime status`. Discovery works without it through an explicit lexical fallback.

## Layout

| Path | Contents |
|---|---|
| `src/library_deep_enrichment/` | The Python package: corpus, semantics, discovery, publication, worker supervision, CLI |
| `crates/` | Four worker crates; `protocol` and `rustdoc-facts` form the root Cargo workspace, the other three are standalone workspaces (see `crates/README.md`) |
| `tests/` | Python suite; `tests/support/` shared helpers; worker-dependent tests report `blocked` when unbuilt |
| `pilot/` | Qualification scripts, task catalog, recorded receipts and status documents from the pilots |
| `docs/design/`, `docs/reviews/`, `docs/history/` | Frozen design and review record, migrated verbatim with provenance headers |
| `docs/adr/` | Decisions and deviations |
| `vendor/` | The metadata-patched `scikit-mine` wheel with its rebuild script and receipt |
| `scripts/` | `env.sh` (the one environment definition), gate scripts, `hooks/` for the agent harness |
| `rules/`, `rule-tests/` | ast-grep rules that encode review findings as executable checks |
| `.claude/`, `.codex/`, `.agents/` | Agent configuration; `AGENTS.md` is the canonical instruction source |

## Development

`just --list` is the command surface. `AGENTS.md` states the binding decisions: Rust produces
facts, Python owns the corpus; Context7 for documentation, exact-release facts for anything a
test or pin depends on; pyrefly as the Python semantic engine; `uv` with exact pins; four
Cargo workspaces on purpose; zero lint or type suppressions.

CI (`.github/workflows/ci.yml`) runs `just ci` on every push and pull request; the worker
workspaces build weekly and on demand (`native.yml`) because the vendored ruff and pyrefly
trees take tens of minutes cold.

## License

Dual-licensed under either [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your option.
Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion
in this work by you, as defined in the Apache-2.0 license, shall be dual licensed as above,
without any additional terms or conditions.
