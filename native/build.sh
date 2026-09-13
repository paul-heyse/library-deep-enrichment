#!/usr/bin/env bash
set -euo pipefail
native_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mode="${1:---plan}"
worker_prefix="$native_dir/bin"
if [[ $# -gt 0 ]]; then shift; fi
if [[ "${1:-}" == --prefix && $# == 2 ]]; then
  worker_prefix="$2"
  shift 2
fi
[[ $# == 0 && ( "$mode" == --plan || "$mode" == --apply ) ]] || { printf '%s\n' 'Usage: build.sh [--plan|--apply] [--prefix DIRECTORY]' >&2; exit 2; }
printf '%s\n' "Build standalone declaration, source, Python semantic and MIR workers into $worker_prefix." 'Stable workers use the installed stable toolchain; MIR requires nightly-2026-08-18 with rustc-dev, rust-src and llvm-tools-preview.'
if [[ "$mode" == --plan ]]; then exit 0; fi
bash "$native_dir/source-facts/bootstrap.sh" --apply
bash "$native_dir/python-semantics/bootstrap.sh" --apply
cargo +stable build --locked --manifest-path "$native_dir/../rustdoc-helper/Cargo.toml"
cargo +stable build --locked --manifest-path "$native_dir/source-facts/Cargo.toml"
cargo +stable build --locked --manifest-path "$native_dir/python-semantics/Cargo.toml"
cargo +nightly-2026-08-18 build --locked --manifest-path "$native_dir/mir-facts/Cargo.toml"
mkdir -p -- "$worker_prefix"
install -m755 "$native_dir/../rustdoc-helper/target/debug/library-guides-rustdoc" "$worker_prefix/library-guides-rustdoc"
for worker in source-facts python-semantics mir-facts; do
  install -m755 "$native_dir/$worker/target/debug/library-guides-$worker" "$worker_prefix/library-guides-$worker"
done
sha256sum "$worker_prefix"/library-guides-*
