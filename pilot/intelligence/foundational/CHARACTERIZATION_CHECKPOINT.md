# Dependency, resource and local cost checkpoint

The new `library-guides.guarded-dependency-resource-characterization.v1` model derives reusable dimensions from admitted executable programs and guarded summaries. FB14 is in progress; G1–G7 remain open. This increment does not classify services by their names or supply unproved runtime, memory, termination or concurrency guarantees.

Every selected behavior owner receives a profile, including owners with normalization or interpretation budget outcomes. Expression ancestry relates ambient bindings and unresolved call results to guards, return values, memory effects and region extents. Each occurrence retains its own expression identity. Local instruction, call, write, drop and suspension counts have a structural upper bound for acyclic reachable control flow. Reachable cycles retain an unknown upper bound pending an invariant. These count normalized local instructions, excluding callee internals and implicit runtime work. Region extents preserve argument dependencies where the underlying model has them; escape is not a retention-duration bound. Mutation, release, suspension and opaque effects produce ordering and interference obligations.

Admission checks exact references and replays derivation. Requests have independent owner, term and total-work bounds. The ordinary supervised workflow, unchanged reuse, invalidation and portable closure include both new families. Four focused characterization/projection controls pass, including ordinary Python execution, ambient mutation, input-dependent list extent, shared writes, symbol renaming, fabricated-profile rejection, exhausted owners and portable restoration. The full tooling suite passes **444 tests in 164.55 seconds**, with two existing dependency warnings. Plan-scope Ruff/format and Pyrefly pass.

## Retained population experiments

Run root: `/home/paul/smartref/.cache/library-guides-foundational/20260913T101230Z`.

`python -m pilot.intelligence.foundational.qualify_characterization` imports an existing portable archive into a new corpus, characterizes the selected behavior request, verifies unchanged reuse without new producer or characterization calls, exports and restores the complete result, and compares exact profiles. Each output directory contains `report.json`, `profiles.json` and both corpus copies. Original corpora remain untouched.

| Library | Profiles | Summary / budget | Ambient-dependent owners | Cyclic local cost | Cold stage / warm planning / archive replay |
| --- | ---: | ---: | ---: | ---: | --- |
| Arrow Schema 58.4.0 | 79 | 75 / 4 | 0 | 7 | 5.798 / 0.715 / 10.874 seconds |
| Pydantic 2.13.4 | 44 | 31 / 13 | 26 | 6 | 3.003 / 0.294 / 12.068 seconds |
| Serde JSON 1.0.149 | 46 | 46 / 0 | 0 | 0 | 2.304 / 0.116 / 10.029 seconds |

Directories are `characterization-arrow-v1`, `characterization-pydantic-v1` and `characterization-serde-v1`. Their resulting heads are respectively `e4946030a06adb0fb43346a18ba98d6c5eef3527bde7dee4eb17477ce7041174`, `add2ab9fdeb1323f66436124b10a76c29721bbfab39f52358604e5842bcb6050` and `6dc3b7f21a11e05e53a899cb703204328e7e22e5ac2a203aa31d775a414dbb03`. All three archives replay exactly and all three warm requests invoke zero producers and zero characterization analyses. Measured coordinator process-lifetime RSS high-water values are 1,415,909,376, 1,307,750,400 and 1,866,584,064 bytes; these are not isolated per-stage peaks.

The eight model/workflow files were frozen in `characterization-model-freeze-v1.json` after the development runs and before Serde evaluation. All hashes remained unchanged afterward. No transfer was tuned from this Serde result. This is an additional bounded characterization experiment over the existing reservation, not a new untouched behavioral holdout.

## Open obligations

All 190 reserved candidates remain accounted for: these profiles cover 169 mapped owners, including 17 budget outcomes; 21 unresolved source mappings remain in the callable populations. **No real reserved-library profile yet has a demonstrated input-dependent region extent.** The execution fixture establishes the mechanism, while richer library allocation/retention relationships require deeper call and region interpretation. Ambient binding names retain their unresolved semantics. Local counts need callee/loop invariants for stronger bounds, and lexical event obligations need qualified synchronization and lifecycle evidence. These bounded runs do not close G5 or substitute for six-family, discovery or consumer qualification.
