# library-deep-enrichment operational API.
#
# This is the first command surface an agent should inspect. Recipes express intent, not tool
# flags, so implementations can change without invalidating what callers know.
#
#   1. Mutating recipes are never dependencies of a validation recipe.
#   2. A gate whose prerequisite is absent reports it and fails; it never fakes a pass.
#
# direnv puts .venv/bin and .dev-state/bin on PATH (see .envrc and scripts/env.sh), so
# `pyrefly`, `ruff`, `pytest`, the CLI and the built workers run without a `uv run` prefix.

set positional-arguments
set dotenv-load := false

root := justfile_directory()

# Put the project environment on PATH for every recipe, so `just` works identically with
# direnv, without direnv, and in CI. A bare tool name can never resolve to a different copy on
# the system, which matters most for pyrefly: this workstation also has a global one.
export PATH := justfile_directory() / ".venv/bin" + ":" + justfile_directory() / ".dev-state/bin" + ":" + env_var("PATH")
export LDE_ROOT := justfile_directory()
export RUSTUP_TOOLCHAIN := ""

[private]
default:
    @just --list --unsorted

# ---------------------------------------------------------------------------- environment

[doc("Full first-time setup: toolchain check, Python environment, dev state, doctor.")]
[group('environment')]
setup:
    @echo "==> rust toolchain (pinned by rust-toolchain.toml)"
    rustc --version
    @echo "==> python environment"
    just sync
    @echo "==> dev state"
    mkdir -p .dev-state/bin
    @command -v direnv >/dev/null && echo "==> run: direnv allow" || echo "==> direnv not installed (optional)"
    @just doctor

[doc("Install Python dependencies exactly as locked (dev group included, no extras).")]
[group('environment')]
sync:
    uv sync --frozen --all-groups --all-extras

[doc("Also install the `embed` extra (tokenizer + model snapshot acquisition; pulls torch).")]
[group('environment')]
sync-embed:
    uv sync --frozen --all-groups --extra embed

[doc("Report which required tools, workers and runtimes are present. Fails on a missing hard requirement.")]
[group('environment')]
doctor:
    @"{{ root }}/scripts/doctor.sh"

[doc("Acquire and verify the qualified Souffle 2.5 rule runtime under $LDE_HOME/runtime (network).")]
[group('environment')]
souffle-provision:
    python -c "from library_deep_enrichment.paths import runtime_root; from library_deep_enrichment.runtime import provision_souffle; print(provision_souffle(runtime_root()))"

[doc("Delete the agent-session state sandbox (.dev-state/). Real corpora under LDE_HOME are untouched.")]
[group('mutating')]
state-reset:
    rm -rf .dev-state
    mkdir -p .dev-state/bin
    @echo "state-reset: .dev-state/ recreated empty"

# ---------------------------------------------------------------------------- native workers

[doc("Acquire and verify the pinned ruff and pyrefly upstream clones the worker crates build against.")]
[group('native')]
native-bootstrap:
    @"{{ root }}/scripts/bootstrap-upstream.sh" ruff --apply
    @"{{ root }}/scripts/bootstrap-upstream.sh" pyrefly --apply

[doc("Build all four fact workers (stable + the dated-nightly MIR worker) into .dev-state/bin.")]
[group('native')]
native-build:
    @"{{ root }}/scripts/native-build.sh" --apply

[doc("Clippy with -D warnings on each standalone worker workspace.")]
[group('native')]
native-check:
    cargo clippy --locked --no-deps --manifest-path crates/source-facts/Cargo.toml --all-targets -- -D warnings
    cargo clippy --locked --no-deps --manifest-path crates/python-semantics/Cargo.toml --all-targets -- -D warnings
    cd crates/mir-facts && cargo clippy --locked --no-deps --all-targets -- -D warnings

# ---------------------------------------------------------------------------- validation

[doc("Assert the active toolchain is the pinned one, not this workstation's nightly default.")]
[group('gate')]
toolchain-check:
    @"{{ root }}/scripts/toolchain-check.sh"

[doc("Run the hook behaviour tests. The hooks are the enforcement layer and need regression cover.")]
[group('gate')]
hooks-test:
    @"{{ root }}/scripts/test-hooks.sh"

[doc("Run the ast-grep rule corpus against its fixtures.")]
[group('gate')]
rules-test:
    ast-grep test

[doc("Scan src/, tests/ and crates/ with the ast-grep rule corpus.")]
[group('gate')]
rules-scan:
    ast-grep scan src tests crates/protocol crates/rustdoc-facts

[doc("Compile-check the root Rust workspace.")]
[group('gate')]
check:
    cargo check --workspace --all-targets

[doc("Lint everything: clippy, ruff, taplo, typos.")]
[group('gate')]
lint:
    cargo clippy --workspace --all-targets --all-features -- -D warnings
    ruff check src tests pilot/*.py pilot/intelligence
    @command -v taplo >/dev/null && taplo check || echo "lint: taplo absent (skipped)"
    @command -v typos >/dev/null && typos || echo "lint: typos absent (skipped)"

[doc("Check formatting without modifying anything.")]
[group('gate')]
fmt-check:
    cargo fmt --all -- --check
    ruff format --check src tests pilot/*.py pilot/intelligence

[doc("Type-check with pyrefly, this project's Python semantic engine.")]
[group('gate')]
typecheck:
    pyrefly check --min-severity warn --output-format min-text

[doc("Run the Rust test suite for the root workspace, including doctests.")]
[group('gate')]
test-rust:
    cargo nextest run --workspace
    cargo test --doc --workspace

# Tests that drive a built worker report `blocked` (skipped with the prerequisite named) when
# the binary is absent, so this recipe is honest without the native build. `just test-native`
# requires every worker and fails instead.
[doc("Run the Python test suite (worker-dependent tests are blocked, not faked, if unbuilt).")]
[group('gate')]
test-python:
    pytest -m "not native_lanes"

[doc("Run every test tier that does not require the network.")]
[group('gate')]
test: test-rust test-python

[doc("Run the pinned upstream extraction canaries and every worker-dependent test; workers must be built.")]
[group('gate')]
test-native:
    LDE_REQUIRE_WORKERS=1 pytest

[doc("Assert dependency policy for the root workspace: bans, licenses, sources.")]
[group('gate')]
deps-policy:
    cargo deny check bans licenses sources

# Kept in the same order as .github/workflows/ci.yml so a local run and a CI run check the
# same things. If you add a step to one, add it to the other.
[doc("Everything that must hold on every change.")]
[group('gate')]
ci: toolchain-check hooks-test rules-test fmt-check lint check test typecheck deps-policy
    @echo "ci: complete"

# ---------------------------------------------------------------------------- corpus

[doc("Report family counts and job currentness for the default corpus ($LDE_CORPUS or LDE_HOME/intelligence/pilot-v4/corpus).")]
[group('corpus')]
corpus-status:
    library-deep-enrichment status

[doc("Plan or apply an embedding-runtime lifecycle action: provision | start | stop | status | canary.")]
[group('corpus')]
runtime action="status" *args:
    library-deep-enrichment runtime --action "$1" "${@:2}"

# ---------------------------------------------------------------------------- mutating

[doc("Format Rust and Python in place.")]
[group('mutating')]
fmt:
    cargo fmt --all
    ruff format src tests pilot/*.py pilot/intelligence
    ruff check --fix src tests pilot/*.py pilot/intelligence
    @command -v taplo >/dev/null && taplo fmt || true
