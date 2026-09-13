#!/usr/bin/env bash
# PreToolUse(Edit|Write|NotebookEdit). Pure path classification; no file parsing.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
hook_read_input
root="$(hook_root)"
while read -r p; do
  [ -n "$p" ] || continue
  case "$p" in /*) abs="$p" ;; *) abs="$root/$p" ;; esac
  rel="${abs#"$root"/}"
  case "$abs" in
    "$root"/*) ;;
    "$HOME"/.claude/plans/*) ;;
    /tmp/claude-*/*) ;;
    *) hook_deny "Refusing to edit outside the repository: ${abs}. Service state belongs under \$LDE_HOME (.dev-state/ in a session); scratch files in the session scratch directory." ;;
  esac
  case "$rel" in
    docs/design/*|docs/reviews/*|docs/history/*)
      hook_deny "\`${rel}\` is frozen provenance: a design or review document as it was delivered. If it is wrong, that is a decision to deviate, recorded with /adr in docs/adr/, not an edit to the record." ;;
    vendor/*.whl|vendor/scikit-mine-metadata-patch.json)
      hook_deny "\`${rel}\` is a vendored artifact with a provenance receipt. Regenerate it with vendor/rebuild_scikit_mine.py and commit the receipt it writes; never hand-edit either." ;;
    AGENTS.md|CLAUDE.md|.claude/rules/*|.claude/settings.json|scripts/hooks/*|scripts/env.sh)
      hook_deny "\`${rel}\` is the enforcement layer: the rules an agent works under, not part of the work. An agent that can edit its own guardrails does not have guardrails. If one is genuinely wrong, say so and stop; propose the change in docs/adr/ and let the operator apply it.

What you CAN change without an ADR: the justfile, scripts/ (except hooks/ and env.sh), rules/ and rule-tests/, .claude/agents/, .claude/commands/, .claude/skills/, tests/, src/, crates/." ;;
    .dev-state/*)
      hook_deny "\`${rel}\` is session service state; the code writes it, agents do not hand-edit it. Use \`just state-reset\` to start clean." ;;
  esac
done < <(hook_paths)
exit 0
