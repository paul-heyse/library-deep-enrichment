#!/usr/bin/env bash
# Hook behaviour tests. The hooks are the enforcement layer, so they need the same regression
# discipline as the code they guard. Run by `just hooks-test` and by CI.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export CLAUDE_PROJECT_DIR="$ROOT"
export LDE_HOME="$ROOT/.dev-state"
pass=0; fail=0
_json() { python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$1"; }
_report() { if [ "$2" = "$3" ]; then pass=$((pass+1)); printf '  ok   %-5s %s\n' "$2" "$1"; else fail=$((fail+1)); printf '  FAIL want=%s got=%s  %s\n' "$3" "$2" "$1"; fi; }
bash_case() {  # desc, command, expect(deny|allow)
  local out got
  out=$(printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","cwd":"%s","tool_input":{"command":%s}}' "$ROOT" "$(_json "$2")" | "$ROOT/scripts/hooks/pre_bash.sh" 2>/dev/null)
  got=allow; printf '%s' "$out" | grep -q '"deny"' && got=deny
  _report "$1" "$got" "$3"
}
edit_case() {  # desc, path, expect(deny|allow)
  local out got
  out=$(printf '{"hook_event_name":"PreToolUse","tool_name":"Write","cwd":"%s","tool_input":{"file_path":%s}}' "$ROOT" "$(_json "$2")" | "$ROOT/scripts/hooks/pre_edit.sh" 2>/dev/null)
  got=allow; printf '%s' "$out" | grep -q '"deny"' && got=deny
  _report "$1" "$got" "$3"
}

echo "pre_bash: pinning and toolchain"
bash_case "uvx @latest"            'uvx ruff@latest check'                                   deny
bash_case "uvx unpinned"           'uvx cowsay hello'                                        deny
bash_case "uvx pinned"             'uvx --from ruff==0.16.7 ruff check'                      allow
bash_case "npx unpinned"           'npx @upstash/context7-mcp'                               deny
bash_case "npx pinned"             'npx -y @upstash/context7-mcp@4.1.0'                      allow
bash_case "bare +nightly"          'cargo +nightly build'                                    deny
bash_case "dated nightly"          'cargo +nightly-2026-08-18 build --locked'                allow
bash_case "stable cargo"           'cargo clippy --workspace -- -D warnings'                 allow

echo "pre_bash: monolithic documents"
bash_case "smartref library_ref"   'cat /home/paul/smartref/docs/library_ref/lancedb.md'     deny
bash_case "smartref skills"        'rg lancedb /home/paul/smartref/.claude/skills'           deny
bash_case "context7 is fine"       'echo use context7'                                       allow

echo "pre_bash: enforcement layer via shell"
bash_case "redirect AGENTS.md"     'echo x > AGENTS.md'                                      deny
bash_case "sed -i hook"            'sed -i s/a/b/ scripts/hooks/pre_bash.sh'                 deny
bash_case "tee settings"           'tee .claude/settings.json < x'                           deny
bash_case "redirect design doc"    'echo x >> docs/design/foo.md'                            deny
bash_case "redirect src ok"        'echo x > src/library_deep_enrichment/paths.py'           allow
bash_case "read AGENTS.md"         'cat AGENTS.md'                                           allow

echo "pre_bash: repository boundary"
bash_case "rm outside"             'rm -rf /home/paul/smartref/build'                        deny
bash_case "redirect outside"       'echo x > /home/paul/other/file.txt'                      deny
bash_case "mv real corpus"         'mv /home/paul/.cache/library-deep-enrichment/x /tmp/y'   deny
bash_case "read outside"           'cat /home/paul/library-enrichment/justfile'              allow
bash_case "dev-state write"        'mkdir -p .dev-state/bin'                                 allow
bash_case "LDE_HOME write"         "mkdir -p $ROOT/.dev-state/cache"                         allow
bash_case "scratch write"          'echo x > /tmp/claude-1000/s/x.txt'                       allow
bash_case "plain ls"               'ls -la docs/'                                            allow
bash_case "just"                   'just ci'                                                 allow

echo "pre_edit: path classification"
edit_case "AGENTS.md"              "$ROOT/AGENTS.md"                                         deny
edit_case "CLAUDE.md"              "CLAUDE.md"                                               deny
edit_case "rules"                  ".claude/rules/python-core.md"                            deny
edit_case "settings"               ".claude/settings.json"                                   deny
edit_case "hook"                   "scripts/hooks/pre_edit.sh"                               deny
edit_case "env.sh"                 "scripts/env.sh"                                          deny
edit_case "design doc"             "docs/design/x.md"                                        deny
edit_case "review doc"             "docs/reviews/x.md"                                       deny
edit_case "vendored wheel"         "vendor/scikit_mine-1.0.0+lde.1-py3-none-any.whl"         deny
edit_case "dev-state"              ".dev-state/bin/x"                                        deny
edit_case "outside repo"           "/home/paul/smartref/x.py"                                deny
edit_case "adr ok"                 "docs/adr/0002-x.md"                                      allow
edit_case "src ok"                 "src/library_deep_enrichment/cli.py"                      allow
edit_case "crate ok"               "crates/protocol/src/lib.rs"                              allow
edit_case "justfile ok"            "justfile"                                                allow
edit_case "gate script ok"         "scripts/doctor.sh"                                       allow
edit_case "rule ok"                "rules/new-rule.yml"                                      allow
edit_case "agent ok"               ".claude/agents/x.md"                                     allow
edit_case "settings.local ok"      ".claude/settings.local.json"                             allow
edit_case "plan file ok"           "$HOME/.claude/plans/x.md"                                allow

echo
echo "hooks-test: ${pass} passed, ${fail} failed"
[ "$fail" -eq 0 ]
