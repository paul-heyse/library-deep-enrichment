# Provisional complete development population run — 2026-09-13

The frozen development selections have now passed through source-owner normalization and guarded interpretation. This is progress on FB09 and FB16; the Serde JSON holdout, remaining foundational obligations and G1–G7 are still open. No task judgment or production release has changed.

All 130 reserved development candidates remain accounted for:

| Library | Reserved candidates | Summaries | Interpretation budget exhausted | Source body unresolved |
| --- | ---: | ---: | ---: | ---: |
| Arrow Schema 58.4.0 | 86 | 75 | 4 | 7 |
| Pydantic 2.13.4 | 44 | 31 | 13 | 0 |

The source-correspondence catalog supplies 79 unique Arrow compiler bodies and 44 Pydantic source definitions. A diagnostic normalization pass handled all 123 bodies without rejection. Its remaining seven rows retain the unresolved Arrow mappings. This diagnostic pass did not itself admit behavior products. The subsequent ordinary behavior stages admitted programs, summaries, coverage, origins and applicable static typing with independent admission replay. Python declaration-shaped overloads remain source-body candidates with runtime-binding frontiers; normalization is not a claim that the exported runtime operation invokes that body.

The analysis used the original default limits, including 256 clauses per owner, 200,000 steps, 10,000 states and 50,000 terms. All 17 interpretation failures are explicit clause-budget exhaustion; completed peers remain present. The Arrow failures are `Field::try_merge`, `Field`'s `Display::fmt`, `SchemaBuilder::try_merge` and `Schema::normalize`. The last is a library operation name, not a failed frontend normalization stage.

Fourteen Arrow summaries are closed under the current model and its assumptions; 61 retain frontiers. All 31 Pydantic summaries retain frontiers. Arrow contributes 1,260 outcome clauses and 36,507 value terms; Pydantic contributes 1,219 clauses and 6,395 terms. These counts characterize the analyzed population, not independent behavioral accuracy. The existing independently checked development relationships retain their earlier finite scope; the newly analyzed operations have not acquired witness qualification merely by sharing a summary model.

The broader run also derives guarded `Field::dict_id` behavior alongside the two reserved dictionary-order methods. This is an additional model-derived candidate relationship, not a newly certified semantic law. Getter/source lineage and conditional methods can now be inspected across the complete development selections.

| Measurement | Arrow | Pydantic |
| --- | ---: | ---: |
| End-to-end first stage | 8.24 s | 51.59 s |
| Supervised worker | 3.24 s | 22.90 s |
| Peak sampled worker-tree RSS | 369,512,448 bytes | 366,829,568 bytes |
| Framed worker output | 16,932,647 bytes | 8,526,415 bytes |
| Unchanged request | 0.21 s | 2.18 s |

The supervisor's actual RSS ceiling is 4,000,000,000 bytes, stricter than the reservation's 8 GiB ceiling. The address-space ceiling is separately 64 GiB. End-to-end time includes coordinator work and admission replay; worker time measures only the supervised producer. These are diagnostic measurements in the shared workspace, not isolated benchmark thresholds or worst-case bounds.

Both unchanged requests reused their admitted stage results. A guarded reuse check rejects any new `RemoteProducer` invocation or in-process summary analysis call; both counters remained zero. These checks do not complete failure injection, interruption, dependency-change invalidation or G5 qualification.

Current heads:

- Arrow: `65079b568114959782f3e43a7b7ae3a24cabfb729d0782d4371f9db381018927`.
- Pydantic: `a68ac7fa30909cf2ea62d0298fd23b80b137fd76c8b20c886d1faa22e2677e22`.

Evidence beneath `.cache/library-guides-foundational/20260913T101230Z`:

- `selected-normalization-probe.jsonl`: every reserved development owner, including unresolved body mappings.
- `arrow-schema-development-population-interpretation-v1.json` and `pydantic-development-population-interpretation-v1.json`: requests, limits, predecessor/current heads, all summaries and coverage outcomes.
- `arrow-development-population-interpretation-v1.log` and `pydantic-development-population-interpretation-v1.log`: actual supervised stage outcomes.
- `development-population-warm-reuse-v1.json`: unchanged reuse counters and retained cold-worker resource receipts.
- `development-population-portable-v1.json`: complete development archive restoration and exact analytical replay. Arrow retains 8,772 records across 26 families (6,380,945 archive bytes) and replays 308 products; Pydantic retains 16,837 records across 21 families (4,688,206 bytes) and replays 238 products. Restoration took 8.34 and 10.77 seconds respectively. Replay uses retained corpus evidence without invoking native/source workers.

The context audit identified a limitation in the older typed Arrow capture: it predates the invocation's working-directory/provider identity fields and does not retain an invocation witness. Those omissions are not backfilled. A new Arrow-only MIR capture using the current pinned worker completed in 11.18 seconds; ordinary Cargo compilation of dependencies did not select the Serde holdout for MIR bodies or transfer evaluation. Its 389 body records, original compiler inputs, invocation receipt and source witnesses are admitted separately under `context-development-corpus`. Thirteen Cargo package facts and 14 Cargo message observations are also retained. `context-arrow-v2-admission.json`, `context-cargo-admission.json`, and their original command/output witnesses record the acquisition. These raw observations still require checked contextual reconciliation before they support compiled availability or cross-unit identity claims.

No core implementation changed after the callable checkpoint to obtain these population results. The subsequent [compilation context checkpoint](COMPILATION_CONTEXT_CHECKPOINT.md) adds checked observed Cargo/compiler correspondence in the separate context corpus. It preserves the earlier acquisition evidence and does not strengthen either behavior population automatically. The broader interpreter populations still require independent controls and the reserved held-out evaluation. Effective target/build context, generalized specialization, lifecycle/native binding, six-family laws, consumer integration and terminal installed delivery remain in scope.
