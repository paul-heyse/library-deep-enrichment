---
paths:
  - "crates/**"
  - "Cargo.toml"
  - "Cargo.lock"
  - "deny.toml"
  - "clippy.toml"
  - "rust-toolchain.toml"
  - "scripts/native-build.sh"
  - "scripts/bootstrap-upstream.sh"
---

# Rust workers

Each worker is a standalone binary that reads one input, emits length-prefixed JSON frames
(`lde-protocol`: header, records, terminal) on stdout, and exits. It never opens a network
connection, never writes outside the directory it is handed, and never executes the code it
analyses. `crates/protocol/src/lib.rs` is the contract; the Python side mirrors it in
`facts/protocol.py`. Change both in the same commit.

Four separate Cargo workspaces are deliberate. `crates/protocol` and `crates/rustdoc-facts`
form the root workspace on the pinned stable toolchain. `crates/source-facts` and
`crates/python-semantics` are their own workspaces because they path-depend into vendored
ruff and pyrefly clones (`scripts/bootstrap-upstream.sh`; the clones are gitignored and the
owned `upstream.patch` is the only permitted edit). `crates/mir-facts` pins
`nightly-2026-08-18` in its own `rust-toolchain.toml` and links `rustc_private`; its
`build.rs` asserts the compiler commit. Do not merge them, and do not add a second nightly.

Schema markers such as `library-guides.declaration.v1` are on-disk corpus formats and keep
their historical spelling; renaming one invalidates every admitted artifact.

`unwrap`/`expect` are clippy warnings and `just lint` runs with `-D warnings`. Edition 2024,
`unsafe_code = "forbid"`. Exact pins for `rustdoc-types` (one per supported `format_version`),
`public-api`, `cargo_metadata`, `schemars`. `deny.toml` is the dependency-policy oracle.

`cargo nextest` does not run doctests; `just test-rust` adds `cargo test --doc`.
