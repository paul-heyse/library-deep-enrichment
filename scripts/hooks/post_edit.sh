#!/usr/bin/env bash
# PostToolUse(Edit|Write). Format-check, lint and rule-scan the SINGLE file just edited.
# Scoping to one file is deliberate: a repo-wide scan would fire on pre-existing content and
# get disabled. Exit 2 feeds the message back to the agent.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
hook_read_input
root="$(hook_root)"
problems=""
note() { problems="${problems}$1"$'\n'; }
RUFF="$root/.venv/bin/ruff"; [ -x "$RUFF" ] || RUFF="$(command -v ruff || true)"
while read -r p; do
  [ -n "$p" ] || continue
  case "$p" in /*) f="$p" ;; *) f="$root/$p" ;; esac
  [ -f "$f" ] || continue
  rel="${f#"$root"/}"
  case "$rel" in crates/*/upstream/*|docs/*|pilot/qualified/*|pilot/source_semantics/*) continue ;; esac
  case "$f" in
    *.rs)
      out=$(rustfmt --edition 2024 --check "$f" 2>&1) || note "rustfmt: ${rel} is not formatted. Run \`just fmt\`.
${out}" ;;
    *.py)
      if [ -n "$RUFF" ]; then
        out=$(cd "$root" && "$RUFF" check "$f" 2>&1) || note "ruff: ${rel}
${out}"
        out=$(cd "$root" && "$RUFF" format --check "$f" 2>&1) || note "ruff format: ${rel} is not formatted. Run \`just fmt\`."
      fi ;;
    *.json)
      out=$(python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$f" 2>&1) || note "invalid JSON: ${rel}
${out}" ;;
    *.toml)
      out=$(python3 -c 'import tomllib,sys; tomllib.load(open(sys.argv[1],"rb"))' "$f" 2>&1) || note "invalid TOML: ${rel}
${out}" ;;
    *.sh)
      out=$(bash -n "$f" 2>&1) || note "shell syntax: ${rel}
${out}" ;;
  esac
  case "$f" in
    *.rs|*.py)
      if [ -f "$root/sgconfig.yml" ] && command -v ast-grep >/dev/null 2>&1; then
        out=$(cd "$root" && ast-grep scan --config sgconfig.yml "$f" 2>&1)
        printf '%s' "$out" | grep -qiE '\b(error|warning)\b' && note "rules: ${rel}
${out}"
      fi
      out=$(grep -nE '(#[[:space:]]*noqa|#[[:space:]]*type:[[:space:]]*ignore|#[[:space:]]*pyrefly:[[:space:]]*ignore|#!?\[allow\()' "$f" 2>/dev/null || true)
      [ -n "$out" ] && note "suppression in ${rel}: this repository does not use \`# noqa\`, \`# type: ignore\`, \`# pyrefly: ignore\` or \`#[allow(...)]\`. Fix the cause, or record an ADR if the lint is genuinely wrong.
${out}" ;;
  esac
done < <(hook_paths)
if [ -n "$problems" ]; then printf '%s' "$problems" >&2; exit 2; fi
exit 0
