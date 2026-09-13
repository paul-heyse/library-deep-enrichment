#!/usr/bin/env bash
# Build the four standalone fact workers and install them under a prefix.
#
#   scripts/native-build.sh [--plan|--apply] [--prefix DIR]     (default prefix: .dev-state/bin)
#
# rustdoc-facts builds in the root workspace on the pinned stable toolchain. source-facts and
# python-semantics are their own workspaces (vendored ruff / pyrefly). mir-facts builds on the
# dated nightly its own rust-toolchain.toml pins; cargo selects it automatically.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:---plan}"; [[ $# -gt 0 ]] && shift
prefix="$ROOT/.dev-state/bin"
if [[ "${1:-}" == --prefix && $# == 2 ]]; then prefix="$2"; shift 2; fi
[[ $# == 0 && ( "$mode" == --plan || "$mode" == --apply ) ]] || { printf '%s\n' 'Usage: native-build.sh [--plan|--apply] [--prefix DIRECTORY]' >&2; exit 2; }
unset RUSTUP_TOOLCHAIN
printf '%s\n' "Build lde-rustdoc-facts, lde-source-facts, lde-python-semantics and lde-mir-facts into $prefix." \
  "Stable workers use rust-toolchain.toml; mir-facts uses crates/mir-facts/rust-toolchain.toml (nightly-2026-08-18 with rustc-dev, rust-src, llvm-tools)."
[[ "$mode" == --plan ]] && exit 0
"$ROOT/scripts/bootstrap-upstream.sh" ruff --apply
"$ROOT/scripts/bootstrap-upstream.sh" pyrefly --apply
cargo build --locked --manifest-path "$ROOT/Cargo.toml" -p lde-rustdoc-facts
cargo build --locked --manifest-path "$ROOT/crates/source-facts/Cargo.toml"
cargo build --locked --manifest-path "$ROOT/crates/python-semantics/Cargo.toml"
( cd "$ROOT/crates/mir-facts" && cargo build --locked )
mkdir -p -- "$prefix"
install -m755 "$ROOT/target/debug/lde-rustdoc-facts" "$prefix/lde-rustdoc-facts"
for worker in source-facts python-semantics mir-facts; do
  install -m755 "$ROOT/crates/$worker/target/debug/lde-$worker" "$prefix/lde-$worker"
done
sha256sum "$prefix"/lde-*
