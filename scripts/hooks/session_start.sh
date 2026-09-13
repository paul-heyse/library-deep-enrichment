#!/usr/bin/env bash
# SessionStart. Environment truth, hard-capped at ~25 lines: this output is prepended to every
# session and re-injected after every compaction.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
hook_read_input
root="$(hook_root)"
cd "$root" 2>/dev/null || exit 0
{
  [ -f STATUS.md ] && sed -n '1,8p' STATUS.md
  echo
  echo "toolchain: $(rustc --version 2>/dev/null || echo 'rustc UNAVAILABLE')  (pin: $(grep -m1 '^channel' rust-toolchain.toml 2>/dev/null | cut -d'"' -f2))"
  if [ -x .venv/bin/pyrefly ]; then echo "pyrefly:   $(.venv/bin/pyrefly --version 2>/dev/null | head -1) (project engine)"
  else echo "pyrefly:   NOT INSTALLED -- run: just sync"; fi
  built=""; missing=""
  for w in rustdoc-facts source-facts python-semantics mir-facts; do
    if [ -x ".dev-state/bin/lde-$w" ] || [ -x "crates/$w/target/debug/lde-$w" ] || [ -x "target/debug/lde-$w" ]; then built="$built $w"; else missing="$missing $w"; fi
  done
  echo "workers:   built:${built:- none}${missing:+  | not built:$missing (just native-build)}"
  echo "state:     LDE_HOME=${LDE_HOME:-$root/.dev-state} (session sandbox; real corpora stay under ~/.cache/library-deep-enrichment)"
  echo "lookup:    library docs via Context7 MCP; exact facts via lde-rustdoc-facts / cargo metadata / Griffe. No monolithic reference documents."
} 2>/dev/null | head -25
exit 0
