---
description: Bootstrap the pinned upstream clones and build all four fact workers, then run the native lane canaries
---

Run, in order, reporting each result truthfully:

1. `just toolchain-check` — the stable pin must be active and `nightly-2026-08-18` present.
2. `just native-bootstrap` — acquires and verifies the ruff and pyrefly clones (network).
3. `just native-build` — builds `lde-rustdoc-facts`, `lde-source-facts`,
   `lde-python-semantics`, `lde-mir-facts` into `.dev-state/bin` and prints their sha256.
4. `just test-native` — the pinned upstream extraction canaries with `LDE_REQUIRE_WORKERS=1`.

If a step fails, stop and report the step, the command, and the last 30 lines of output. A
worker that did not build makes the native tests `blocked`, never skipped silently.
