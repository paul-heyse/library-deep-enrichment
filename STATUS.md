# Status

Migrated from `smartref/tooling/library_guides` on 2026-09-13 (ADR 0001, 0002). Every number
below was printed by the named command in that session; re-measure before carrying one forward.

| Measure | Value | Command |
|---|---|---|
| Python suite (workers built) | 306 passed, 0 skipped | `pytest -m "not native_lanes"` |
| Native lane canaries | 22 passed | `LDE_REQUIRE_WORKERS=1 pytest -m native_lanes` |
| Root Rust workspace | check, clippy `-D warnings`, fmt, nextest (1), doctests (0) clean | `just check lint fmt-check test-rust` |
| pyrefly | 0 diagnostics (`implicit-any` deferred, ADR 0003) | `just typecheck` |
| Corpus (`pilot-v4`) | 52 families, entities 70261, native_facts 672073; identical to pre-move baseline | `library-deep-enrichment status` |
| Workers | all four built into `.dev-state/bin` | `just native-build` |

## What the corpus holds

The `pilot-v4` corpus under `$LDE_HOME/intelligence` is the live qualification corpus for
the DataFusion / Arrow / PyArrow stack (see `pilot/intelligence/STATUS.md` and
`pilot/intelligence/COMPLETION.md` for the qualification narrative and its gaps). The
foundational behaviour-characterization work (`docs/design/foundational_behavior_*`) is in
progress: G0 accepted, G1 to G7 open, per its implementation plan.

## Known gaps

- The Souffle 2.5 runtime and the embedding container are external prerequisites; tests
  that need them are `blocked` (skipped with the reason) when absent.
- `implicit-any` typing strictness is deferred (ADR 0003).
- The worker workspaces are not built on every CI run; `native.yml` covers them weekly.
