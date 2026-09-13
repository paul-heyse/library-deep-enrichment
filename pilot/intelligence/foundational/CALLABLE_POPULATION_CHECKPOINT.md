# Provisional callable population checkpoint — 2026-09-13

Implementation continues under the full FB00–FB18 scope. Only FB00/G0 is accepted. The frozen 190-candidate reservation and Serde JSON transfer holdout are unchanged.

New acquisition receipts retain original witness paths alongside their copied byte identities under `library-guides.witness-origins.v1`. Verification checks the version and exact retained witness denominator. Original paths are attribution only; replay reads managed corpus bytes. Older receipts without these associations remain unattributed rather than receiving inferred mappings. Collection and native admission fingerprints include the new verification implementation.

The `callable_requests` and `callable_populations` families use the existing coordinator, supervised worker, exact prerequisite selection, admission replay and portable closure. Each request selects immutable interface/executable artifacts and an optional exact file scope. Limits bound artifacts, native records and bytes. Every selected catalog member contributes evidence, including records required to resolve declaration ownership or public receiver types. A missing native denominator is rejected.

Rust source correspondence requires an attributed original path, exact source digest and checked UTF-8 owner coordinates. Expansion mappings do not become exact original-body matches. Public routes and trait members on public receiver types remain distinct candidate rules. Local rustdoc IDs resolve only within their own artifact; source identities survive local renumbering, while declaration and compilation contexts remain separate mandatory fields. Multiple matching bodies remain distinct candidates. Correspondence does not establish consumer availability, generic instantiation or runtime dispatch.

Python uses exact native source identities and lexical owners to distinguish public-name/protocol candidates, private names, nested functions and stub interfaces. Source definitions remain candidates before execution normalization, decorator application, overload resolution and descriptor/import binding. An ellipsis-bodied overload is not qualified runtime dispatch merely because its source definition is retained.

The development population was checked against every original reservation entry using retained source digests and coordinates. Rust declarations additionally match their reserved semantic digests. Python's two previously identified comment/declaration extent differences retain their attribution; source bytes, starts and definition names agree.

| Development selection | Reserved candidates recovered | Exact compiler body matches | Additional public candidates |
| --- | ---: | ---: | ---: |
| Arrow Schema 58.4.0 | 86 / 86 | 79; seven unresolved | 0 within selected files |
| Pydantic 2.13.4 | 44 / 44 | Python source definitions remain unqualified | 1 |

Arrow's complete catalog also retains three excluded local callables and 14 unlocated declarations, including 13 public-receiver trait candidates. Pydantic retains eight private-name exclusions and one nested-function exclusion. The additional Python candidate is `ModelPrivateAttr.__getattr__`, declared inside a conditional block at `pydantic/fields.py` bytes 63151–63659. The original reservation traversed direct module/class definitions. This additional structural finding is retained separately; no reserved owner is dropped or silently added to the held-out evaluation denominator. Its definition condition and runtime binding still need characterization.

An actual archive restore exposed backend-order dependence in the provisional evidence list. Model `library-guides.contextual-callable-source-population.v2` orders artifact and fact inputs explicitly. A regression reverses staged native row order and checks identical output. Earlier v1 diagnostic artifacts remain preserved and unqualified; they are not terminal historical-compatibility receipts. The required historical-model policy remains an FB01/FB18 obligation.

Current development heads:

- Arrow: `bdaf07b3d32e40cd28b702fbad9749d006331453d23d9484809fdd5660e820da`.
- Pydantic: `7da5a23de3b10789ff30cf66400df32a86027d0c8b10c66b7860c1683e74faca`.

Both populations restore and replay exactly. Their archives retain 8,454 records across 26 families and 16,589 records across 21 families respectively, including existing behavior evidence. Archive sizes are 5,922,995 and 3,741,121 bytes. Unchanged analysis requests reuse results on the original candidate heads; replay uses the restored release heads. A diagnostic first attempted a writer workflow against an empty restored candidate head; that error was corrected without changing the release/candidate contract. These timings are diagnostic, not isolated G5 performance qualification.

Evidence beneath `.cache/library-guides-foundational/20260913T101230Z`:

- `development-callable-populations-v4.json`: complete catalogs, reservation matches and extra candidates.
- `callable-portable-v3-receipts.json`: exact archive heads, denominators, replay and reuse receipts.
- `callable-full-suite.log`: **425 passed**, two existing dependency warnings, 162.83 seconds, before the final ordering fix.
- `callable-regression-tests.log`: 19 native/admission/origin regression checks passed before that fix.
- `callable-canonical-tests.log`: four focused tests passed after the ordering fix, including real compiler/source, renumbering, changed-source, stub/private/nested, forgery, portable and row-order controls.
- `callable-final-ruff.log`, `callable-final-pyrefly.log`: plan-scope Ruff passed; zero tooling type diagnostics. Formatting checks cover 387 files.

This checkpoint does not complete FB02 or any behavioral gate. Cargo feature/unit reconciliation, native/runtime binding, registry/import membership, owner-level normalization/interruption accounting and full selected behavior interpretation remain open. The six families, lifecycle/native composition, discovery, consumer reassessment and installed terminal delivery remain mandatory.
