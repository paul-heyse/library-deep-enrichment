# Choose element-wise integer addition with documented overflow behavior: wrap

Profile: `python-installed-54-25`.

Comparison: `3e374970b1b5cbc9b52e5ce477c03eebe12779e6a4b8fcbe2745164466379efe`. Universe: `4e4d8e0cd616d9ba4eb304a833dfccc8703d158f3a89b00167a034111e2c3608`.

Candidates are drawn from the admitted interface universe. Retrieval rank does not exclude alternatives.

Compared 890 admitted operations: 880 conditional, 1 eligible, 9 rejected.

Eligibility addresses the stated semantic requirements. Native invocation and unmodeled properties remain separate checks.

## compute-registry:add

Disposition: **eligible**.

Interface: ``.

- `documented_elementwise_operation = add`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `d57c63de7a5884467a1459245e3ac08f542a692446ae1344be2a661647f17bfb`.
- `documented_integer_overflow_policy = wrap`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `aef6d3744890fe67cf1258d37109687453d3df766f3760beb73d1aed789a9377`.

Re-evaluation triggers:

- Re-evaluate f55ae4479ebf9cc0e175de94fb2d8c7983d855c3a2ca6591dedfac3f9030664d when required value or applicability changes.
- Re-evaluate b1ec9d65234efc5166c38d1b26412c545bcad69d8396b6e3892419417e16776f when required value or applicability changes.

## compute-registry:negate

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `dc3ddd2d9427ca53ab8e696eaa2ed11d73d29718a0172103b5b76bd6a68ec5d0`.

Re-evaluation triggers:

- Re-evaluate b1ec9d65234efc5166c38d1b26412c545bcad69d8396b6e3892419417e16776f when required value or applicability changes.

## compute-registry:abs

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `c3a41b496867b42bd16307b4f5c0eff1470939309cad4c39f21cd3f1f19ae873`.

Re-evaluation triggers:

- Re-evaluate b1ec9d65234efc5166c38d1b26412c545bcad69d8396b6e3892419417e16776f when required value or applicability changes.

## compute-registry:hash_count_distinct

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## sql:ln

Disposition: **conditional**.

Interface: `ln(numeric_expression)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## sql:covar_samp

Disposition: **conditional**.

Interface: `covar_samp(expression1, expression2)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## sql:array_except

Disposition: **conditional**.

Interface: `array_except(array1, array2)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## sql:dot_product

Disposition: **conditional**.

Interface: `inner_product(array1, array2)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.greater

Disposition: **conditional**.

Interface: `(x, y, /, *, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## sql:coalesce

Disposition: **conditional**.

Interface: `coalesce(expression1[, ..., expression_n])`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## sql:substring_index

Disposition: **conditional**.

Interface: `substr_index(str, delim, count)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## compute-registry:utf8_length

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## sql:trim

Disposition: **conditional**.

Interface: `btrim(str[, trim_str])`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.round_binary

Disposition: **conditional**.

Interface: `(x, s, /, round_mode='half_to_even', *, options=None, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.utf8_is_title

Disposition: **conditional**.

Interface: `(strings, /, *, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## sql:var_pop

Disposition: **conditional**.

Interface: `var_pop(expression)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## compute-registry:hash_kurtosis

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## compute-registry:utf8_rtrim

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## sql:string_to_array

Disposition: **conditional**.

Interface: `string_to_array(str, delimiter[, null_str])`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

## compute-registry:hash_any

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = wrap`: **unknown**. No adequate applicable support or refutation.

The remaining 870 alternatives and all individual assessments are retained in the comparison record `3e374970b1b5cbc9b52e5ce477c03eebe12779e6a4b8fcbe2745164466379efe`. This display limit does not narrow the candidate universe.

## Unresolved scope

- No universal optimum is asserted; preferences and incomplete semantic coverage are explicit.
- Candidate membership digest: 28ff314407222c606ed933b020e9834c0e142e8e84baabafb0ab4cb204160674.
