---
description: Record an architecture decision or a deviation from a frozen design document
argument-hint: <short title>
---

Create `docs/adr/NNNN-<kebab-title>.md` with the next free number and this structure:

```
# NNNN. <title>

Date: <YYYY-MM-DD>
Status: proposed | accepted | superseded by NNNN

## Context
What forced the decision. Cite the design document section or the failing gate.

## Decision
One paragraph. What changes, what stays.

## Evidence
Primary sources with URL and retrieval date; Context7 library ids; commands that were run
and what they printed. A deviation from a frozen design needs evidence, not preference.

## Consequences
What becomes easier, what becomes harder, which tests prove the new behaviour.
```

Then add a row to `docs/adr/README.md`. Do not edit the design document the ADR deviates
from; it is frozen provenance.
