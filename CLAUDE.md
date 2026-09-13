@AGENTS.md

# Claude harness notes

`AGENTS.md` is the canonical instruction source; this file only adds harness specifics.
Start from `STATUS.md`.

The `SessionStart` hooks export `scripts/env.sh` into the session (with `LDE_HOME` redirected
to `.dev-state/`) and print a short environment summary. They do not install tools or run CI.

`PreToolUse` hooks deny the mistakes that are visible in the tool call alone: unpinned tool
execution, a bare `cargo +nightly`, reading the retired monolithic reference corpus in
smartref, shell-redirect writes to the enforcement layer or frozen provenance, and writes
outside the repository, `LDE_HOME`, or the scratch directory. A denial says why; read it
rather than working around it. `PostToolUse` format-checks, lints, and rule-scans the single
edited file and flags suppressions. `Stop` checks the diff for suppressions, ignore-list
growth, and service state inside the repository.

Detailed constraints are in `.claude/rules/`, scoped with `paths:` frontmatter so they load
when you touch matching files rather than every session.

Library documentation comes from the **Context7** plugin (`context7@claude-plugins-official`,
enabled in `.claude/settings.json`); the tools are allow-listed. Exact-release facts come from
the workers and `cargo metadata`.

Subagents: `upstream-verifier` (dated evidence for a library claim), `boundary-reviewer`
(diff review for couplings, suppressions, protocol drift). Commands: `/verify-upstream`,
`/adr`, `/native-build`, `/handoff`.

Skills are discovered from `.claude/skills` (development skills, currently none); Codex and
other agents read the same directory through the `.codex/skills` and `.agents/skills`
symlinks.
