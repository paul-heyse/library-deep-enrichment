#!/usr/bin/env bash
# Assert the active Rust toolchain is the one rust-toolchain.toml pins.
#
# This workstation's rustup default is nightly. If rust-toolchain.toml is missing, ignored, or
# overridden by an inherited RUSTUP_TOOLCHAIN, every stable worker silently builds on nightly.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

want="$(python3 -c 'import tomllib,sys;print(tomllib.load(open(sys.argv[1],"rb"))["toolchain"]["channel"])' "$ROOT/rust-toolchain.toml")"
if [ -n "${RUSTUP_TOOLCHAIN:-}" ]; then
  echo "toolchain-check: FAIL -- RUSTUP_TOOLCHAIN=${RUSTUP_TOOLCHAIN} is set and overrides rust-toolchain.toml." >&2
  echo "                 Unset it; scripts/env.sh does this for direnv and agent sessions." >&2
  exit 1
fi
got="$(cd "$ROOT" && rustc --version | awk '{print $2}')"
if [ "$got" != "$want" ]; then
  echo "toolchain-check: FAIL -- active rustc is ${got}, rust-toolchain.toml pins ${want}." >&2
  echo "                 Run: rustup toolchain install ${want}" >&2
  exit 1
fi
mir="$(python3 -c 'import tomllib,sys;print(tomllib.load(open(sys.argv[1],"rb"))["toolchain"]["channel"])' "$ROOT/crates/mir-facts/rust-toolchain.toml")"
if ! rustup toolchain list | grep -q "^${mir}-"; then
  echo "toolchain-check: WARN -- ${mir} (crates/mir-facts) is not installed; the MIR lane is blocked." >&2
fi
echo "toolchain-check: OK -- rustc ${got} matches the pin; mir-facts pins ${mir}"
