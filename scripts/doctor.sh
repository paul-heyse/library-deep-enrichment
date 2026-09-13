#!/usr/bin/env bash
# Report which tools this repository needs, and which are actually present.
# A missing hard requirement FAILS; reporting a tool as present when it is not is exactly the
# kind of untruthful claim the gate discipline exists to prevent.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hard_missing=0
req() { if command -v "$2" >/dev/null 2>&1; then printf '  %-18s %s\n' "$1" "$("$2" --version 2>&1 | head -1)"; else printf '  %-18s MISSING (required) -- %s\n' "$1" "$3"; hard_missing=$((hard_missing+1)); fi; }
opt() { if command -v "$2" >/dev/null 2>&1; then printf '  %-18s %s\n' "$1" "$("$2" --version 2>&1 | head -1)"; else printf '  %-18s absent -- %s\n' "$1" "$3"; fi; }

echo "core:"
req rustc   rustc   "the fact workers are Rust"
req cargo   cargo   "workspace build"
req uv      uv      "the only supported Python package manager"
req just    just    "the task surface"
req python3 python3 "scripts"
req git     git     "upstream bootstrap and provenance"

echo; echo "python engine (from the project environment after \`just sync\`):"
for t in pyrefly ruff pytest; do
  if [ -x "$ROOT/.venv/bin/$t" ]; then printf '  %-18s %s\n' "$t" "$("$ROOT/.venv/bin/$t" --version 2>&1 | head -1)"
  else printf '  %-18s MISSING -- run just sync\n' "$t"; hard_missing=$((hard_missing+1)); fi
done

echo; echo "worker isolation:"
# worker_runtime.py refuses to run isolated workers without /usr/bin/bwrap: hard requirement.
if [ -x /usr/bin/bwrap ]; then printf '  %-18s present\n' bwrap; else printf '  %-18s MISSING (required) -- isolated workers cannot run\n' bwrap; hard_missing=$((hard_missing+1)); fi
for s in podman docker; do command -v "$s" >/dev/null 2>&1 && printf '  %-18s present (embedding runtime container)\n' "$s" || printf '  %-18s absent\n' "$s"; done

echo; echo "built workers (.dev-state/bin or crates/*/target/debug):"
for w in rustdoc-facts source-facts python-semantics mir-facts; do
  if [ -x "$ROOT/.dev-state/bin/lde-$w" ] || [ -x "$ROOT/crates/$w/target/debug/lde-$w" ]; then printf '  %-18s built\n' "lde-$w"
  else printf '  %-18s not built -- just native-build (native_lanes tests are blocked)\n' "lde-$w"; fi
done

echo; echo "optional tooling:"
for t in cargo-nextest cargo-deny ast-grep taplo typos direnv sccache mold bacon; do
  cmd="$t"; case "$t" in cargo-*) cmd="cargo-${t#cargo-}";; esac
  command -v "$cmd" >/dev/null 2>&1 && printf '  %-18s present\n' "$t" || printf '  %-18s absent\n' "$t"
done

echo; echo "toolchain pin:"
"$ROOT/scripts/toolchain-check.sh" || hard_missing=$((hard_missing+1))

echo; echo "service state: LDE_HOME=${LDE_HOME:-<unset: defaults to ~/.cache/library-deep-enrichment>}"
echo
if [ "$hard_missing" -gt 0 ]; then echo "doctor: ${hard_missing} hard requirement(s) missing." >&2; exit 1; fi
echo "doctor: all hard requirements present"
