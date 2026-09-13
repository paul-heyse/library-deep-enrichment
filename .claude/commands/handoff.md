---
description: Write a handoff note for the next session - what is done, what is verified, what is blocked
---

Write `docs/handoffs/<YYYY-MM-DD>-<topic>.md` (create the directory if needed) with:

- **Done**: commits since the last handoff (`git log --oneline`), one line each.
- **Verified**: each gate that was run this session with its command and result
  (`just ci`, `just test-native`, `just corpus-status`), dated. Blocked gates say why.
- **Open**: what remains, ordered; the first item is the one to start with.
- **Decisions pending**: anything that needs the operator (an ADR, a corpus migration, a
  dependency bump).

Then refresh the top eight lines of `STATUS.md` so `session_start.sh` shows the new state.
No number in the handoff may come from memory; every count is the output of a command run
in this session.
