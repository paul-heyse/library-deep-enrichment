#!/usr/bin/env bash
# Stop. Single-shot checks for failure modes only visible at the end of a turn. Honours
# stop_hook_active so it never loops.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
hook_read_input
[ "${HOOK_STOP_ACTIVE:-False}" = "True" ] && exit 0
root="$(hook_root)"
cd "$root" 2>/dev/null || exit 0
problems=""

# 1. Suppressions introduced in this session's diff (staged or not).
added=$(git diff HEAD -- 'src/*.py' 'tests/*.py' 'pilot/*.py' 'crates/*.rs' 2>/dev/null \
        | grep -E '^\+' | grep -vE '^\+\+\+' \
        | grep -nE '#[[:space:]]*noqa|#[[:space:]]*type:[[:space:]]*ignore|#[[:space:]]*pyrefly:[[:space:]]*ignore|#!?\[allow\(' | head -5 || true)
[ -n "$added" ] && problems="${problems}Suppressions added in this diff:
${added}
This repository has zero \`# noqa\`, \`# type: ignore\`, \`# pyrefly: ignore\` and \`#[allow(...)]\` in hand-written code. Fix the cause or record an ADR.
"

# 2. Ignore lists must not grow.
grown=$(git diff HEAD -- pyproject.toml pyrefly.toml 2>/dev/null | grep -E '^\+' | grep -vE '^\+\+\+' \
        | grep -nE 'per-file-ignores|extend-ignore|^\+\s*"[A-Z]+[0-9]*",?\s*$|permissive-ignores = true' | head -5 || true)
[ -n "$grown" ] && problems="${problems}The lint or type-check ignore surface grew in pyproject.toml / pyrefly.toml:
${grown}
Growing an ignore list is the same as a suppression. Fix the cause or record an ADR.
"

# 3. Service state must not land inside the repository outside .dev-state/.
leak=$(git status --porcelain --ignored 2>/dev/null | awk '{print $NF}' \
       | grep -E '^(corpus|snapshots|blobs|acquired|models|runtime)/' | head -5 || true)
[ -n "$leak" ] && problems="${problems}Service state inside the repository:
${leak}
Corpora, snapshots and acquired sources belong under \$LDE_HOME (.dev-state/ in a session).
"

if [ -n "$problems" ]; then printf '%s' "$problems" >&2; exit 2; fi
exit 0
