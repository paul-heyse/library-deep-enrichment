---
description: Verify a library claim against Context7 and exact-release code facts via the upstream-verifier subagent
argument-hint: <library> <version> <claim>
---

Delegate to the `upstream-verifier` subagent with this brief, verbatim:

> Library: $1. Version: $2. Claim: $ARGUMENTS (everything after the version). Follow your
> procedure: Context7 first, exact-release facts second, dated evidence, `unverified` if
> either source is missing. Do not read any monolithic reference document.

Relay the verdict block unchanged. If the verdict is `refuted` or `unverified` and the claim
came from code, docs, or a test in this repository, name the file and line that must change.
