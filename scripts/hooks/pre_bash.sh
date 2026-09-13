#!/usr/bin/env bash
# PreToolUse(Bash). Denies the mistakes that are visible in the command string alone. Anything
# that needs a source file parsed belongs in rules/ (ast-grep) instead.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
hook_read_input
cmd="${HOOK_COMMAND:-}"
[ -n "$cmd" ] || exit 0
root="$(hook_root)"

# 1. Unpinned tool execution.
if printf '%s' "$cmd" | grep -q '@latest'; then
  hook_deny "Unpinned tool execution (\`@latest\`). Resolve dependencies at setup, not per invocation: add the tool to [dependency-groups] dev with an exact pin and run it from .venv/bin, or pin explicitly (\`uvx --from pkg==X.Y.Z\`, \`npx pkg@X.Y.Z\`)."
fi
if printf '%s' "$cmd" | grep -Eq '(^|[^[:alnum:]_-])(uvx|npx)([^[:alnum:]_-]|$)|uv tool run' \
   && ! printf '%s' "$cmd" | grep -Eq '==|@[0-9]'; then
  hook_deny "Unpinned tool execution. Add it to [dependency-groups] dev (exact pin) and use the project environment, or pin the version on the command line."
fi

# 2. Bare +nightly. This workstation's rustup default IS nightly, so a floating +nightly is
#    unpinned and indistinguishable from the default. crates/mir-facts pins nightly-2026-08-18
#    in its own rust-toolchain.toml; run cargo from that directory instead.
if printf '%s' "$cmd" | grep -Eq 'cargo[[:space:]]+\+nightly([[:space:]]|$)'; then
  hook_deny "Bare \`cargo +nightly\` floats. The only nightly this repository uses is the dated pin in crates/mir-facts/rust-toolchain.toml; run cargo inside that crate (or \`cargo +nightly-2026-08-18\`) so the producer identity is reproducible."
fi

# 3. Monolithic reference documents. Library lookup goes through Context7 and code-fact
#    producers; the retired deep-dive corpus in smartref is not an evidence source here.
if printf '%s' "$cmd" | grep -Eq '/smartref/docs/library_ref|/smartref/\.(claude|codex)/skills'; then
  [ "${LDE_ALLOW_SMARTREF_DOCS:-0}" = "1" ] || hook_deny "That path is the retired monolithic reference corpus in smartref. This repository resolves library documentation through the Context7 MCP tools (resolve-library-id, query-docs) and exact-release facts through lde-rustdoc-facts, cargo metadata and Griffe. Set LDE_ALLOW_SMARTREF_DOCS=1 only for an explicitly authorised archaeology task."
fi

# 4. Writing to the enforcement layer or frozen provenance through the shell. pre_edit.sh
#    blocks the same paths for Edit/Write; without this, `cat > AGENTS.md` would bypass it.
if printf '%s' "$cmd" | grep -Eq '([[:space:]]>|[[:space:]]>>|tee[[:space:]]|sed[[:space:]]+-i|dd[[:space:]]+of=)'; then
  for frozen in AGENTS.md CLAUDE.md .claude/rules .claude/settings.json scripts/hooks scripts/env.sh docs/design docs/reviews docs/history vendor; do
    if printf '%s' "$cmd" | grep -Eq "([[:space:]>]|${root}/)${frozen}([[:space:]/]|\"|'|$)"; then
      hook_deny "Refusing to write to \`${frozen}\` through the shell. It is the enforcement layer or frozen provenance; pre_edit.sh blocks the same write for Edit/Write. If a guardrail is wrong, say so and stop; propose the change in docs/adr/ for the operator to apply."
    fi
  done
fi

# 5. Writes outside the repository boundary. Service state lives under LDE_HOME (redirected to
#    .dev-state/ in sessions); temporary files belong in the session scratch directory.
if printf '%s' "$cmd" | grep -Eq '(^|[|;&[:space:]])(rm|mv|cp|tee|install|mkdir|touch|truncate|chmod|chown|ln)([[:space:]])|[[:space:]]>[^>|&]|[[:space:]]>>|sed[[:space:]]+-i'; then
  while read -r p; do
    [ -n "$p" ] || continue
    case "$p" in
      "$root"|"$root"/*) ;;
      "${LDE_HOME:-/nonexistent}"|"${LDE_HOME:-/nonexistent}"/*) ;;
      /tmp/claude-*|/tmp/claude-*/*|/tmp/*) ;;
      /dev/null|/dev/stdout|/dev/stderr) ;;
      "$HOME"/.claude/plans/*) ;;
      *) hook_deny "Write outside the repository boundary: ${p}

Service state (corpora, acquired sources, model snapshots) lives under \$LDE_HOME, which agent sessions redirect to .dev-state/. Temporary files belong in the session scratch directory. Moving or deleting the real corpora under ~/.cache/library-deep-enrichment is an operator action." ;;
    esac
  done < <(printf '%s' "$cmd" | grep -oE '(^|[[:space:]>])(/|~/)[^[:space:]|;&)"'"'"']*' | sed 's/^[[:space:]>]*//' | sed "s|^~|$HOME|")
fi
exit 0
