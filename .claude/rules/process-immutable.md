---
paths:
  - "AGENTS.md"
  - "CLAUDE.md"
  - ".claude/rules/**"
  - ".claude/settings.json"
  - "scripts/hooks/**"
  - "scripts/env.sh"
  - "docs/design/**"
  - "docs/reviews/**"
  - "docs/history/**"
---

# The enforcement layer is not part of the work

`AGENTS.md`, `CLAUDE.md`, `.claude/rules/`, `.claude/settings.json`, `scripts/hooks/` and
`scripts/env.sh` are the rules an agent works under. **An agent that can edit its own
guardrails does not have guardrails.** Both the pre-edit and pre-bash hooks deny writes here,
shell redirects included.

`docs/design/`, `docs/reviews/` and `docs/history/` are frozen provenance: the design and
review record as it was delivered from the monorepo, with a migration header and nothing
else changed. If a design is wrong, that is an ADR in `docs/adr/`, not an edit.

When a guardrail fires and it is genuinely wrong, say so and stop. Do not route around it,
do not add a narrow exemption, do not disable a hook. Propose the change in `docs/adr/` and
let the operator apply it.

Everything else is yours: `justfile`, `scripts/*.sh` (except `hooks/` and `env.sh`),
`rules/` and `rule-tests/` (growing the ast-grep corpus is encouraged), `.claude/agents/`,
`.claude/commands/`, `.claude/skills/`, `src/`, `crates/`, `tests/`, `pilot/`.
