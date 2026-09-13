#!/usr/bin/env bash
# Shared helpers for the harness hooks. Both Claude Code and Codex deliver a JSON object on
# stdin with (at least) hook_event_name, cwd, and for tool hooks tool_name + tool_input.
# Sourced by each hook. Keep this fast and dependency-free: it runs on every matching call.

hook_read_input() {
  HOOK_INPUT="$(cat 2>/dev/null || true)"
  local py
  py='import json,sys
try:
    d = json.loads(sys.argv[1] or "{}")
except Exception:
    d = {}
ti = d.get("tool_input") or {}
cmd = ti.get("command", "")
if isinstance(cmd, list):
    cmd = " ".join(str(c) for c in cmd)
paths = []
p = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
if p:
    paths.append(str(p))
# Codex apply_patch payloads carry paths as "*** Add File: x" etc.
patch = ti.get("patch") or ti.get("input") or (ti.get("content") if isinstance(ti.get("content"), str) and "*** Begin Patch" in ti.get("content", "") else "")
if isinstance(patch, str) and "***" in patch:
    import re
    paths += re.findall(r"^\*\*\* (?:Add|Update|Delete|Move to) File: (.+)$", patch, re.M)
print(json.dumps({"event": d.get("hook_event_name", ""), "cwd": d.get("cwd", ""),
                  "source": d.get("source", ""), "tool": d.get("tool_name", ""),
                  "command": cmd, "paths": paths,
                  "stop_hook_active": bool(d.get("stop_hook_active", False))}))'
  HOOK_JSON="$(python3 -c "$py" "$HOOK_INPUT" 2>/dev/null || echo '{}')"
  HOOK_EVENT="$(hook_field event)"; HOOK_CWD="$(hook_field cwd)"; HOOK_SOURCE="$(hook_field source)"
  HOOK_TOOL="$(hook_field tool)"; HOOK_COMMAND="$(hook_field command)"
  HOOK_STOP_ACTIVE="$(hook_field stop_hook_active)"
}

hook_field() { python3 -c 'import json,sys; v=json.loads(sys.argv[1]).get(sys.argv[2], ""); print(v if not isinstance(v,(list,dict)) else json.dumps(v))' "$HOOK_JSON" "$1" 2>/dev/null; }
hook_paths() { python3 -c 'import json,sys; [print(p) for p in json.loads(sys.argv[1]).get("paths", [])]' "$HOOK_JSON" 2>/dev/null; }

# Repository root: Claude sets CLAUDE_PROJECT_DIR; Codex sends cwd; otherwise git.
hook_root() {
  local r="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$r" ] && [ -n "${HOOK_CWD:-}" ] && r="$(git -C "$HOOK_CWD" rev-parse --show-toplevel 2>/dev/null)"
  [ -z "$r" ] && r="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  printf '%s' "$r"
}

# Emit a PreToolUse deny decision (both harnesses accept this shape) and exit.
hook_deny() {
  python3 - "$1" <<'PY'
import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                         "permissionDecision": "deny",
                                         "permissionDecisionReason": sys.argv[1]}}))
PY
  exit 0
}
