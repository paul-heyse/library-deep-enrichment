---
paths:
  - "src/**"
  - "crates/**"
  - "tests/**"
  - "pilot/**"
  - "docs/**"
  - "pyproject.toml"
  - "Cargo.toml"
---

# Library lookup: Context7 plus code facts, never monolithic documents

When you need to know what a library does, how an API is shaped, or whether a usage is
correct, the evidence sources are, in order:

1. **Context7** (`resolve-library-id`, then `query-docs`) for documentation, concepts and
   worked examples. It is a discovery lead, not exact-version proof.
2. **Exact-release code facts** for anything that must be true of the resolved version:
   `lde-rustdoc-facts` over rustdoc JSON from docs.rs, `cargo metadata` (the `cargo_context`
   module), Griffe for Python APIs, Sphinx `objects.inv` inventories, and the source-facts /
   python-semantics / mir-facts workers for behaviour.
3. Primary sources on docs.rs, doc.rust-lang.org, crates.io, PyPI and the project's own
   repository, fetched directly and cited with URL and retrieval date.

The retired deep-dive corpus in `smartref/docs/library_ref` and the skills that routed to it
are **not** evidence sources here; `pre_bash.sh` denies reading them. Do not reconstruct
monolithic reference documents inside this repository either: the product compiles exact
facts into a corpus, it does not curate prose manuals.

Date every verification claim ("verified 2026-09-13 against lancedb 0.38.0 via Context7 and
the wheel's `objects.inv`"). A claim without a source and a date is an assumption.
