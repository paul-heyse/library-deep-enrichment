---
paths:
  - "src/**"
  - "tests/**"
  - "pilot/**/*.py"
  - "pyproject.toml"
  - "pyrefly.toml"
  - "uv.lock"
---

# Python core

Python owns the corpus (LanceDB/Arrow), admission, semantics, discovery, publication and the
worker supervisor. It never reimplements a fact producer: extraction that belongs to a Rust
worker is added to `crates/`, not to `src/`.

**pyrefly is the Python semantic engine.** It is pinned in `[dependency-groups] dev` and run
from `.venv/bin`. pyright is installed on this workstation and globally plugin-enabled; it is
not this project's engine and its findings are not gates.

`uv` only. Exact pins everywhere (`==`), lockfile committed, `uv sync --frozen`. No `uvx
...@latest`, no `pip install`, no floors or ranges.

**No module in `src/` may name a specific library** (`datafusion`, `pyarrow`, ...) except the
storage backend it is built on; `tests/test_reuse_contract.py` enforces it. Library-specific
knowledge lives in the corpus, in `assets/packs`, or in a registry adapter resolved by
identifier.

Zero suppressions: no `# noqa`, no `# type: ignore`, no `# pyrefly: ignore`, and no growth of
`[tool.ruff.lint.ignore]`, `per-file-ignores`, or the pyrefly `[errors]` block. Fix the cause
or record an ADR. `post_edit.sh` and `stop_guard.sh` check mechanically.

Workers are spawned through `worker_runtime.py` inside `bwrap` with explicit read and write
roots; `/usr/bin/bwrap` is a hard requirement, not an optional sandbox. Stdout of a worker is
the framed fact channel; never `print()` inside `_worker_entry.py` or a worker workflow.

Service state (corpora, acquired sources, model snapshots, tool runtimes) resolves through
`library_deep_enrichment.paths` from `LDE_HOME`. Never hard-code a home-relative path.
