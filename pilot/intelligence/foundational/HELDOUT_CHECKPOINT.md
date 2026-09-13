# First frozen-model holdout run — 2026-09-13

Serde JSON 1.0.149 has now been evaluated with the transfer implementation frozen before the run. Both reserved guarded relationships match ordinary Rust executions. This supplies held-out evidence for FB09; it does not close G2 or the remaining foundational and delivery packages.

The [pre-evaluation freeze](pre_heldout_freeze_v1.json) pins checkpoint `20260913T172156Z`, its complete manifest, 142 critical source files, three native producer binaries and the unchanged benchmark/expectation reservation. All critical hashes were checked again before interpretation, witness comparison and portable replay. No transfer, frontend or corpus implementation was changed in response to this run. Future transfer changes prompted by its results require treating this cohort as development evidence and selecting a new untouched holdout.

The fresh pinned Cargo build selected only `serde_json@1.0.149` for MIR body capture. Compilation finished in 14.34 seconds and retained 1,090 compiler owners with 17 source witnesses plus the original invocation and build witnesses. The original declaration input was normalized with exact path-to-byte attribution. Contextual semantic declaration identities distinguish macro-generated trait implementations that share one name and source span; the selection adapter initially used an insufficient name/span key, rejected the ambiguity, and was corrected to use the already implemented semantic identities before transfer evaluation.

All 60 reserved candidates remain accounted for. Forty-six have unique source-corresponding bodies and all 46 normalized and produced summaries under the original default budgets. Fourteen generated or unmapped bodies remain unresolved. Thirteen summaries are closed under the model and 33 retain frontiers. The stage admitted 46 programs, 46 summaries, 46 origin tables and 46 coverage records in 3.64 seconds including admission. No per-function semantic override or reduced selection was used.

The ordinary Rust oracle constructs 13 values spanning all six `Value` variants, including both booleans, several numeric/string values, empty/nonempty arrays and objects. It invokes `as_bool` and `as_array` directly. Independent observations check the optional boolean, returned array variant, vector identity and vector length. For arrays, actual pointer comparisons and serialized contents also confirm that the returned vector is the existing receiver payload. Private buffer representation, allocation/lifetime validity beyond the ordinary borrow and other feature configurations remain unqualified.

All **32 result-dimension comparisons matched**, with zero inconclusive comparisons or disagreements. The two relationships are guarded variant/payload or borrow relationships; they are not constant-return detections. No additional semantic transfer was introduced for Serde JSON.

Deliberately incorrect controls remain separate from admitted summaries:

| Control | Disagreements | Inconclusive | Other cases |
| --- | ---: | ---: | --- |
| Reverse `as_bool` guard polarity | 2 | 11 | 0 matches |
| Replace boolean payload with false | 1 | 0 | 12 unchanged matches |
| Reverse `as_array` guard polarity | 3 | 16 | 0 matches |
| Substitute identity of an actually cloned vector | 3 | 0 | 0 matches |

The clone control executes a real copy and observes its distinct vector address and equal contents. The abstract comparison rejects its substituted returned identity. Address correspondence alone is not an ownership or lifetime proof. Inconclusive reversed-guard cases remain inconclusive; they are not counted as disagreements.

The first witness admission correctly rejected contextual invocation IDs in the old v1 observation envelope. The corrected adapter uses the existing v2 wire and direct managed-byte attachments for the oracle, binary, build output and source. The final v3 adapter revision adds the actual clone control while retaining v2 wire semantics. These are acquisition/adapter corrections, not changes to the frozen analyzer. All intermediate diagnostics and observations remain preserved.

Final holdout corpus head: `285b2bc498bb7043d03dfe908c66776b84be8d9b636e7828dbb08bda78ba91e9`. The portable archive contains 23,301 records across 26 families, totaling 10,741,071 bytes. Restoration and exact replay of all 184 behavior products plus 32 witness matches took 8.88 seconds. Unchanged behavior and witness requests reused admitted results in 0.31 seconds combined; guards on producer and analysis calls verified zero new producer, behavior-analysis or witness-analysis calls.

Across the three reserved libraries, all 190 candidates are now accounted for: 152 summaries, 17 interpretation-budget outcomes and 21 unresolved body mappings. This complete denominator and successful finite witnesses do not make every operation supported. Pydantic mutation/dispatched-call qualification, full contextual specialization, failure/recovery handling, protocol/native composition, six-family laws, discovery, consumer reassessment and installed delivery remain in scope. The scope of the last green implementation suite is unchanged: 430 tests and the recorded static checks; no core source changed during this holdout run.

Evidence under `.cache/library-guides-foundational/20260913T101230Z`:

- `pre-heldout-freeze-v1.json`, `heldout-serde-v1-admission.json`, `heldout-serde-cargo-messages.jsonl` and compiler logs/frames.
- `heldout-serde-callable-population-v1.json`, `heldout-serde-interpretation-v1.json` and `heldout-serde-interpretation-v2.log` for exact denominator and summaries.
- `heldout-serde-oracle-v2.json`, `rust-population/src/bin/serde_heldout_oracle_v2.rs`, its binary and build log for ordinary execution and the real copy control.
- `heldout-serde-witness-admission-v3.json` and `.log` for admitted comparisons and all negative outcomes.
- `heldout-serde-portable-v1.json`, `heldout-serde-portable-v1` and `heldout-serde-restored-v1` for export, restore, replay and guarded unchanged reuse.
