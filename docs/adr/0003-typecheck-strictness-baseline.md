# 0003. pyrefly strictness baseline: `implicit-any` deferred

Date: 2026-09-13
Status: accepted

## Context

The sub-project's own `pyrefly.toml` had no `[errors]` block. The migration adopted the
stricter error set from the monorepo root (`missing-source`, `implicitly-defined-attribute`,
`implicit-abstract-class`, `assert-type`, `permissive-ignores = false`,
`ignore-errors-in-generated-code = false`, `untyped-def-behavior =
"check-and-infer-return-type"`). With `implicit-any = true` as well, pyrefly 1.3.0 reported
533 diagnostics on 2026-09-13: 451 `implicit-any-type-argument`, 72
`implicit-any-empty-container`, 1 `implicit-any-lambda`, and 9 `missing-import` for optional
extras that were not installed.

## Decision

Enable everything except `implicit-any`. Install all extras in the development environment
(`just sync` runs `uv sync --frozen --all-groups --all-extras`) so `missing-import` is a real
error again. `implicit-any` is a tracked tightening: enabling it requires annotating roughly
520 generic containers across `rust_pipeline`, `analyses/behavior/*`, `analyses/flow`,
`declaration_refresh`, `example_discovery` and the tests, and belongs in its own change with
its own review.

## Evidence

- `pyrefly check --min-severity warn --output-format min-text` on 2026-09-13: 533 diagnostics
  with `implicit-any = true`; 0 diagnostics with it removed and extras installed.

## Consequences

- The type gate is green and honest about what it enforces; the pyrefly.toml comment states
  the deferral so nobody mistakes it for full strictness.
- Adding `implicit-any = true` back is the acceptance test for the tightening.
