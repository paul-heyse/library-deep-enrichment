# Completed reboot continuation and implementation

The reboot continuation and accepted seven-step plan are complete for the retained
pilot. There is no interrupted task-owned writer to resume. The old commands below
are preserved historical context; consult [STATUS.md](STATUS.md), [COMPLETION.md](COMPLETION.md)
and [ACCEPTANCE.md](ACCEPTANCE.md) for the final result.

Final semantic assessment: **4 supported, 4 partial, 16 gaps** across all 24 tasks.
Future semantic expansion should start from [TASK_ASSESSMENT.md](TASK_ASSESSMENT.md),
which records exact generated/baseline evidence and each unresolved obligation.
Do not automatically rerun expensive extraction or treat these gaps as positive guarantees.

Preserve these qualified resources:

- Main corpus: `.cache/library-guides-intelligence/pilot-v4/corpus`, current analysis
  manifest `f61eabbd4fe17866ca3bd5c6a3d7b1d8875e3f53ee32b204a693ce4292fa9913`.
- Main task release: `7e7b42b41bafcfca619a6f5e8856effe6f0a566e21af99259b63fb58abfa1596`,
  named head `completion-task-cohort`.
- Full isolated environment and execution logs:
  `.cache/library-guides-implementation/completion-20260912T220757Z/`.
  Use its `full-environment/bin` tools from `tooling/library_guides`; do not sync
  the root SMARTREF environment.
- Final noneditable wheel: `wheel-final-1788/smartref_library_guides-0.2.0-py3-none-any.whl`
  beneath that run directory. Its Python and asset bytes match the final core.
- Final native binaries: `native-final-bin/` beneath that run directory. Exact
  hashes and five workspace gates are in `reports/completion-packaging-native-verification.json`.
- Existing `library-guides-embeddings` container, pinned model cache and port 18080
  remain active. Driver 615.71.09 and actual inference were verified; do not recreate
  the service or delete its model cache as a routine resume action.

Final core freeze is
`89cb8d1665f7d4e06a2cc48b80a19a936679aa1617500a4c36d8ad3444343b3e`.
Verify `reports/completion-core-freeze.json` before extending the qualification.
A future core change needs a recorded generalization finding and relevant renewed
qualification; prior immutable release receipts keep their original identities.
Full-main analytical workers used an explicit 8 GiB memory budget. The coordinator
has no separate RSS cap and large publication reached approximately 20 GiB.
Never overlap writers to the same corpus.

## Earlier reboot handover

# Continue the unified library intelligence implementation

Checkpoint: 2026-09-12, after reboot. **The NVIDIA runtime is qualified and the implementation has advanced; the complete target remains in progress.** The earlier driver/library mismatch and zero-bulk-shape state are historical, not current blockers.

Active authority: [target design](../../../../docs/library_ref/library_guide_programmatic_semantic_intelligence_target_design_2026-09-12.md). Preserve the user's correction: one coherent evidence, semantic, and publication fabric. Evaluation is attributed and qualitative; no automated generative-model runner or API key is required. [STATUS.md](STATUS.md) records current and historical checkpoints.

## Preserve these paths and boundaries

- Repository: `/home/paul/smartref`.
- Use **`tooling/library_guides/.venv/bin` explicitly**. Do not sync the root environment or incidentally change the tooling dependencies/lockfile.
- Latest main analysis manifest: `9575e2673f0566f30f8a5d7481bd282a021a887d8e4d72e41193b3cab92741d9`; [current status](reports/resume-final-corpus-status.json).
- Main corpus: `.cache/library-guides-intelligence/pilot-v4/corpus`. Direct Python reads require `max_rows=2_500_000`; the CLI already uses that bound. The ordinary constructor defaults to 250,000.
- Runtime cache: `/home/paul/.cache/library-guides-intelligence`.
- Before-reboot source snapshot: `.cache/library-guides-implementation/intelligence-20260912T080026Z/`.
- This continuation's preservation snapshot and command logs: `.cache/library-guides-implementation/resume-20260912T134154Z/`, including `baseline.json` and `source-baseline.tar.gz`.
- The whole tooling directory and target design were already untracked shared work. Do not reset, broadly clean, or infer ownership of everything under them. Concurrent Torch/CUDA and `httpx2` dependency changes were preserved.
- Original transports, source bytes, historical releases, and prior vectors are retained. The 67 current native artifacts are a current-head scope, not historical migration closure.

## What is now verified

1. **Runtime.** RTX 5090 driver **615.71.09** is active. The existing owned service started, provisioning ran, and real two-vector canaries passed. All 17 model files / 15,150,575,778 bytes matched the pinned upstream inventory. Model/tokenizer byte digests enter embedding recipes, lifecycle outcomes are durable, and initialization failures retain lexical search. Real reuse computed 2 initial vectors, 1 added vector, zero warm producer work, and 3 vectors for a changed document-prefix recipe. See [runtime receipt](reports/resume-runtime-canary-verified.json), [provisioning](reports/resume-provision-verified.json), and [reuse](reports/resume-real-embedding-reuse.json).
2. **Bulk shapes and semantics.** Bounded batch reads preserve exact pinned/staged membership. The main corpus admitted **26,358 operation shapes**, then **3,098 assertions, 3,098 qualifications, and 3,014 capabilities**. Both unchanged stages reused. The profiled shape stage took 185.47 seconds; a sanctioned 64-record cold batch took 0.223 seconds versus 2.236 seconds for the earlier individual-read sample. [Shape receipt](reports/resume-bulk-shapes.json), [semantic receipt](reports/resume-shaped-semantics.json).
3. **Generated semantic composition.** Three attributed, manually authored invocation/model mappings connect the existing bounded planner, intermediate transfers, generated Rust programs, and finite witnesses. `Schema::new_with_metadata → project` retains the tested metadata; `Schema::new → project` is modeled as rejected and observed to lose it. Both exact programs compiled and ran. Admission rejects altered model results or generated source. The analysis and released closure restored identically. [Guide](guides/generated-schema-composition.md), [receipt](reports/resume-generated-composition.json). This is one finite specialization, not generic/borrow/availability certification; the same agent authored and reviewed the mappings.
4. **Scoped real discovery.** [This selector](scopes/arrow-schema-native.json) selects **427 native operations** from 854 Arrow Schema profile/package entries. The main corpus has 427 byte-qualified real vectors, 2,535 graph edges, 1,281 projection nodes, and 173 communities for that scope. All three warm stages reused. Exact population receipts and distinct scope output identities prevent silent truncation or overlap merging. Total qualification time, including planning/admission/warm reads, was 434.67 seconds. [Receipt](reports/resume-scoped-discovery.json). Stage read sets and invalidation remain conservative at family granularity; scoped FCA/labels remain open.
5. **Native source analyses through the fabric.** `analyze-native` reuses pure MIR flow/control/effect functions against an explicit artifact plus 1–200 owner revisions. The coordinator admits independently replayed typed results. Five real Arrow Schema owners completed and restored portably; all five retain open effect frontiers. Tests verify retained-source replay after transport removal and reject fabricated consequences. [Receipt](reports/resume-native-source-analysis.json). Python boundary/current-interface normalization and broad Rust joins/availability are still pending.
6. **Decision publication.** Objective evidence and admitted counterfactuals now enter portable closure and generated guides. Lexicographic selection uses the best complete tuple and preserves unknown candidates. Tests restore and recompute preferred comparisons and actual eligibility deltas. The real releases retain four requirement changes and two objective assertions, and both restored identically. [Publication receipt](reports/resume-decision-publication.json), [counterfactual guide](guides/integer-add-with-counterfactuals.md), [preference guide](guides/integer-add-with-preferences.md).
7. **Verification.** **267 tooling tests pass**, Ruff lint/format pass, and Pyrefly reports zero diagnostics at warning severity. The two known FCApy/skmine deprecation warnings remain unsuppressed. The refreshed installed wheel passed offline read/export/reimport for the composition, native source analysis, arithmetic counterfactual, and arithmetic preference artifacts. [Installed-reader receipt](reports/resume-installed-offline-reader-final.json). The environment uses 96 exact pre-existing tooling distributions; complete installation of newly declared runtime dependencies remains a separate gate. No SMARTREF root/native acceptance claim is made.

## Existing managed runtime

Do not recreate or stop this working service merely to continue implementation. Verify current ownership before any lifecycle action:

- Container: `library-guides-embeddings`.
- ID: `d9f62af21210dcf9aa262d494ee31681565f48ac63f6accdf48b7b587e0d306d`.
- Ownership label: `org.smartref.library-guides.runtime=80863571b29f18a21ed3a742a25fe43d0c9f6244adbcaa9a1f8350655de7b5af`.
- Qwen3-Embedding-8B revision: `1d8ad4ca9b3dd8059ad90a75d4983776a23d44af`.
- Image: `vllm/vllm-openai@sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1`.
- Loopback port: 18080; served model: `library-guides-qwen`; vectors: 4,096 dimensions.
- Soufflé: `/home/paul/.cache/library-guides-intelligence/tools/souffle-2.5/runtime/usr/bin/souffle`.

Runtime actions use `runtime --action start` for a plan and add `--apply` to execute. Query paths never start containers or provision models. The owned service remains useful during the remaining work.

## Remaining priorities and acceptance boundaries

1. **Finish source analysis and applicability depth.** Activate Python current-interface/boundary normalization, contextual Rust identity joins, ordinary-consumer feature/target availability, and the mode/error/configuration/lifecycle analyses demanded by the pilot. Reuse pure functions behind typed fabric reads. A MIR may-dependency or a passed finite composition does not settle unmodeled semantic properties.
2. **Complete T5 maintenance and migration.** Inventory superseded artifacts and all historical releases; qualify a real direct `extract-native` producer; retain relevant V2 source gates; complete body/default/stub/bridge/new-candidate invalidation controls. An early Python release with manifest `93f1462edd7bbf5eeb8d51da30f3dfc434eb5fe638fa889dcd68b90b65a1c5f8` fails current semantic admission because it predates capability-schema authority. Its archive is unchanged. Implement a justified historical checker/migration policy; do not bypass validation or label typed Parquet readability as successful semantic restoration. [Observed failure](reports/resume-historical-release-gap.json).
3. **Improve precision and resource enforcement.** Scope identities are implemented, but whole-family stage input recording and invalidation remain costly and broad. Reduce those costs without losing new-candidate dependencies. Scope FCA/labels and explicit resource enforcement separately; keep projection limits finite. Composition witness/policy changes currently require semantic rebuilding under conservative invalidation.
4. **Complete the four-library evidence chains and 24-task evaluation.** Every task in `pilot/tasks.yaml` needs an attributed supported/partial/gap assessment with exact release, inspected evidence, alternatives, reversing conditions, and remaining manual interpretation. The original V2 activation/gap matrix remains independent evidence. Do not convert counts or focused tests into invented accuracy figures.
5. **Freeze the core, then qualify reuse.** Run Pydantic 2.13.4 and serde_json 1.0.151 against a recorded frozen core. Permit new source manifests/profiles/pack data and justified adapters; record every required core change and manual override. This freeze/reuse gate has not been completed.

Main Rust profile: `rust-docsrs-54.1-58.4`. Main Python profile: `python-installed-54-25`. The older task catalog uses `python-installed-54.0-25.0.1`; establish an explicit evidence-backed mapping before using it. Keep `arrow-schema-local-58.4`, feature-reduced builds, rustdoc artifacts, versions, and nominal identities distinct.

## Commands

```bash
tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus status

tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus \
  build --stage retrieval --scope tooling/library_guides/pilot/intelligence/scopes/arrow-schema-native.json

tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus \
  --runtime-root /home/paul/.cache/library-guides-intelligence \
  discover-scoped 'preserve schema metadata' tooling/library_guides/pilot/intelligence/scopes/arrow-schema-native.json

tooling/library_guides/.venv/bin/pytest tooling/library_guides/tests -q --tb=short
tooling/library_guides/.venv/bin/ruff check tooling/library_guides/library_guides tooling/library_guides/tests tooling/library_guides/pilot/intelligence
tooling/library_guides/.venv/bin/ruff format --check tooling/library_guides/library_guides tooling/library_guides/tests tooling/library_guides/pilot/intelligence
```

Run `.venv/bin/pyrefly check --min-severity warn --output-format min-text` from `tooling/library_guides`. The `qualify_*.py` programs alongside this handover record real runtime, composition, discovery, source-analysis, and decision-publication runs. They preserve previous run directories. Consult their receipts before repeating expensive work. [The tooling README](../../README.md) now documents the active corpus workflow.
