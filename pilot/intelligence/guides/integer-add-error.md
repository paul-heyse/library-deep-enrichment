# Choose element-wise integer addition with documented overflow behavior: error

Profile: `python-installed-54-25`.

Comparison: `9bc832f102bca3ce9f9f875bf76345e1f415707e3c09f3dcfd8c1dfc1ed8e963`. Universe: `d9a27feb86443805ab900e0fba72332b54836f64f3bb781e15d50835aabeb565`.

Candidates are drawn from the admitted interface universe. Retrieval rank does not exclude alternatives.

Compared 890 admitted operations: 880 conditional, 1 eligible, 9 rejected.

Eligibility addresses the stated semantic requirements. Native invocation and unmodeled properties remain separate checks.

## compute-registry:add_checked

Disposition: **eligible**.

Interface: ``.

- `documented_elementwise_operation = add`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `c1767ea0f81aad87ae80e660cdb008cbc39af30cad0e36d86b76afcc370cdcea`.
- `documented_integer_overflow_policy = error`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `5bb05aa0ff51f0b16bd02a727d587538b23f99c110080a633e42111fe80aeae8`.

Re-evaluation triggers:

- Re-evaluate f55ae4479ebf9cc0e175de94fb2d8c7983d855c3a2ca6591dedfac3f9030664d when required value or applicability changes.
- Re-evaluate b1ec9d65234efc5166c38d1b26412c545bcad69d8396b6e3892419417e16776f when required value or applicability changes.

## compute-registry:abs_checked

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `fde4986250b99cd58e681fd94aa38053d74a344e6be5153495eb2deadf7b271b`.

Re-evaluation triggers:

- Re-evaluate b1ec9d65234efc5166c38d1b26412c545bcad69d8396b6e3892419417e16776f when required value or applicability changes.

## compute-registry:negate_checked

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `482db18523fb3c74233ff4a644ae59977d51e33290e4c70d19b2b837792660dd`.

Re-evaluation triggers:

- Re-evaluate b1ec9d65234efc5166c38d1b26412c545bcad69d8396b6e3892419417e16776f when required value or applicability changes.

## compute-registry:hash_count_distinct

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## sql:ln

Disposition: **conditional**.

Interface: `ln(numeric_expression)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## sql:covar_samp

Disposition: **conditional**.

Interface: `covar_samp(expression1, expression2)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## sql:array_except

Disposition: **conditional**.

Interface: `array_except(array1, array2)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## sql:dot_product

Disposition: **conditional**.

Interface: `inner_product(array1, array2)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.greater

Disposition: **conditional**.

Interface: `(x, y, /, *, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## sql:coalesce

Disposition: **conditional**.

Interface: `coalesce(expression1[, ..., expression_n])`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## sql:substring_index

Disposition: **conditional**.

Interface: `substr_index(str, delim, count)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## compute-registry:utf8_length

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## sql:trim

Disposition: **conditional**.

Interface: `btrim(str[, trim_str])`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.round_binary

Disposition: **conditional**.

Interface: `(x, s, /, round_mode='half_to_even', *, options=None, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.utf8_is_title

Disposition: **conditional**.

Interface: `(strings, /, *, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## sql:var_pop

Disposition: **conditional**.

Interface: `var_pop(expression)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## compute-registry:hash_kurtosis

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## compute-registry:utf8_rtrim

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## sql:string_to_array

Disposition: **conditional**.

Interface: `string_to_array(str, delimiter[, null_str])`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

## compute-registry:hash_any

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.
- `documented_integer_overflow_policy = error`: **unknown**. No adequate applicable support or refutation.

The remaining 870 alternatives and all individual assessments are retained in the comparison record `9bc832f102bca3ce9f9f875bf76345e1f415707e3c09f3dcfd8c1dfc1ed8e963`. This display limit does not narrow the candidate universe.

## Unresolved scope

- No universal optimum is asserted; preferences and incomplete semantic coverage are explicit.
- Candidate membership digest: 28ff314407222c606ed933b020e9834c0e142e8e84baabafb0ab4cb204160674.
