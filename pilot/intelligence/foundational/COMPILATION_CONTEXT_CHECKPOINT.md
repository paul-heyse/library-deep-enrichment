# Observed compilation context checkpoint — 2026-09-13

The new compilation analysis reconciles retained Cargo metadata, Cargo messages and original compiler invocation witnesses through the existing coordinator, supervised analysis worker and portable corpus. This advances FB01/FB02/FB16. Only G0 is accepted; compiled availability, general instance binding and the remaining G1–G7 obligations are still open.

`compilation_requests` and `compilation_populations` use the separate model `library-guides.observed-compilation-correspondence.v1`. Existing contexts, declaration products and behavioral summaries keep their meaning. Every selected executable capture has a unit disposition, including historical captures without an original invocation witness. A normalizer's process receipt cannot supply the original compiler's missing working directory or producer identity.

The decoder reproduces the pinned Rust wrapper's legacy and current identity preimages. The current identity includes its observed working directory, wire schema, original producer digest and selected-package setting. Argument interpretation preserves repeated options and opaque response files. An unfamiliar option's unknown arity leaves the remaining suffix uninterpreted; an option value cannot inject another flag. `--check-cfg` describes allowed cfg values and never enables a feature.

Cargo joins use opaque package IDs, observed package/manifest context, exact target source paths, witnessed input bytes, target edition/crate type and an observed output recipe. Different feature contexts remain separate. Declared feature definitions, metadata-resolved features, compiled message features and explicit compiler feature cfgs remain distinct. Requested Cargo settings retain their external observer attribution and are not treated as native process attestations. Missing request witnesses do not imply default features.

The first real Arrow Schema 58.4.0 context contains one compiler unit, 13 Cargo package observations and 14 Cargo messages. Its primary source input has retained matching bytes. The compiler and Cargo artifact observations agree on an empty enabled feature set; four available feature definitions remain separately recorded. The resulting candidate establishes target/output-recipe correspondence, with explicit limits on process co-observation, binary outputs, dependency bytes, generated inputs, effective target defaults and build-script effects. It cannot certify all-feature coverage or consumer availability.

The admission changed the separate context-development corpus from `2dcf4a2f7d25109b93a41590cc2590eb2009983e12b3cf226b66b5b342681e2d` to `34226c2f5dadf8e57592f4c08c08593e4f5d42ffcb98bf5c64cad75e92f6d826`. It did not change either complete development behavior corpus or the original production corpus/releases. The Serde JSON transfer holdout remains unevaluated.

The first supervised stage took 1.58 seconds including admission; an unchanged request reused the result in 0.08 seconds. Its portable archive contains 540 records across 13 families, with exact restoration and analysis replay in 1.82 seconds. These are shared-workspace diagnostic timings, not final isolated resource guarantees.

Five new controls use the real pinned Cargo/compiler workers. They cover two feature configurations, two simultaneous dependency versions with the same package name, explicit feature conflicts, wrong output recipes, unrelated opaque package IDs, missing/wrong source witnesses, original-identity mutation, unsupported execution schemas, legacy capture, stable row ordering, invented populations and export/replay after moving the acquisition source tree. Thirteen related compilation/callable/MIR tests passed in 13.37 seconds. The full tooling suite passed **430 tests in 145.72 seconds** with the two existing dependency warnings. Ruff passed the plan-specified scope and Pyrefly reported zero errors.

Evidence under `.cache/library-guides-foundational/20260913T101230Z`:

- `context-reconciliation-v1.json` and `.log`: exact request, unit/candidate/settings, predecessor/current head, cold/warm results and portable receipt.
- `context-portable-v1` and `context-restored-v1`: export and restored view.
- `compilation-regression-tests.log`, `compilation-full-suite.log`, `compilation-ruff.log`, `compilation-pyrefly.log`: current executable checks.
- The preceding `context-arrow-v2-admission.json` and `context-cargo-admission.json` retain acquisition provenance. The initial development test diagnostics are preserved separately; they are not passing receipts.

Remaining context work includes instance/substitution specialization, complete registry/re-export membership dependencies, Python runtime binding and stub/import reconciliation, target/build-script observation, exact binary dependency closure and cross-language binding. The finite observed correspondences above supply reusable fundamental facts for that work rather than closing those obligations by inference.
