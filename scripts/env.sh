#!/usr/bin/env bash
# Single definition of this repository's working environment.
#
# Sourced by BOTH .envrc (interactive shells, via direnv) and scripts/hooks/session_env.sh
# (agent sessions, via CLAUDE_ENV_FILE). Defining it once is the point: if the two drifted, an
# agent and a human would run different commands against different state.
#
# Requires LDE_ROOT to be set by the caller.

: "${LDE_ROOT:?scripts/env.sh requires LDE_ROOT}"

# --- Service state -----------------------------------------------------------------------
# Corpora, acquired sources, model snapshots and tool runtimes live OUTSIDE the repository.
# Humans get the XDG location; agent sessions override LDE_HOME to $LDE_ROOT/.dev-state in
# scripts/hooks/session_env.sh so a session can never mutate the real corpora.
export LDE_HOME="${LDE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/library-deep-enrichment}"

# --- Rust --------------------------------------------------------------------------------
export RUST_BACKTRACE=1
export CARGO_TERM_COLOR=never
# rust-toolchain.toml is the single toolchain authority. An inherited RUSTUP_TOOLCHAIN would
# override it, and this workstation's rustup default is nightly.
unset RUSTUP_TOOLCHAIN
# Each worker workspace keeps its own target/ on purpose; do not set CARGO_TARGET_DIR.
command -v sccache >/dev/null 2>&1 && export RUSTC_WRAPPER=sccache
command -v mold >/dev/null 2>&1 && export CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUSTFLAGS="-C link-arg=-fuse-ld=mold"

# --- Python ------------------------------------------------------------------------------
export UV_PROJECT_ENVIRONMENT="${LDE_ROOT}/.venv"
# Do not re-resolve on every `uv run`; `just sync` is the explicit resolution step.
export UV_NO_SYNC=1
export PYTHONDONTWRITEBYTECODE=1

# --- PATH --------------------------------------------------------------------------------
# So `pyrefly`, `ruff`, `pytest`, `python`, the CLI and the built workers work WITHOUT a
# `uv run` or ./target/debug prefix. Fewer modifiers means fewer ways to run the wrong thing.
lde_path_add() { case ":${PATH}:" in *":$1:"*) ;; *) PATH="$1:${PATH}" ;; esac; }
lde_path_add "${LDE_ROOT}/.venv/bin"
lde_path_add "${LDE_ROOT}/.dev-state/bin"
lde_path_add "${LDE_ROOT}/scripts"
export PATH
unset -f lde_path_add
