# Choose element-wise addition with an explicit preference for overflow errors

Profile: `python-installed-54-25`.

Comparison: `93790284aba98c6c1d7805836c2b23b23956f4344ec186b8fd31e99dce942743`. Universe: `6b495f99916026d857add2e7930ec2bff7f24b40ec72e1e0de193e3d26bc53d5`.

Candidates are drawn from the admitted interface universe. Retrieval rank does not exclude alternatives.

Compared 890 admitted operations: 882 conditional, 2 eligible, 6 rejected.

Eligibility addresses the stated semantic requirements. Native invocation and unmodeled properties remain separate checks.

## compute-registry:add

Disposition: **eligible**.

Interface: ``.

- `documented_elementwise_operation = add`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `d57c63de7a5884467a1459245e3ac08f542a692446ae1344be2a661647f17bfb`.

Re-evaluation triggers:

- Re-evaluate f55ae4479ebf9cc0e175de94fb2d8c7983d855c3a2ca6591dedfac3f9030664d when required value or applicability changes.

## compute-registry:add_checked

Disposition: **eligible**.

Interface: ``.

- `documented_elementwise_operation = add`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `c1767ea0f81aad87ae80e660cdb008cbc39af30cad0e36d86b76afcc370cdcea`.

Re-evaluation triggers:

- Re-evaluate f55ae4479ebf9cc0e175de94fb2d8c7983d855c3a2ca6591dedfac3f9030664d when required value or applicability changes.

## compute-registry:hash_count_distinct

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## sql:ln

Disposition: **conditional**.

Interface: `ln(numeric_expression)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## sql:covar_samp

Disposition: **conditional**.

Interface: `covar_samp(expression1, expression2)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## sql:array_except

Disposition: **conditional**.

Interface: `array_except(array1, array2)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## sql:dot_product

Disposition: **conditional**.

Interface: `inner_product(array1, array2)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.greater

Disposition: **conditional**.

Interface: `(x, y, /, *, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## sql:coalesce

Disposition: **conditional**.

Interface: `coalesce(expression1[, ..., expression_n])`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## sql:substring_index

Disposition: **conditional**.

Interface: `substr_index(str, delim, count)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## compute-registry:utf8_length

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## sql:trim

Disposition: **conditional**.

Interface: `btrim(str[, trim_str])`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.round_binary

Disposition: **conditional**.

Interface: `(x, s, /, round_mode='half_to_even', *, options=None, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.utf8_is_title

Disposition: **conditional**.

Interface: `(strings, /, *, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## sql:var_pop

Disposition: **conditional**.

Interface: `var_pop(expression)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## compute-registry:hash_kurtosis

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## compute-registry:utf8_rtrim

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## sql:string_to_array

Disposition: **conditional**.

Interface: `string_to_array(str, delimiter[, null_str])`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## compute-registry:hash_any

Disposition: **conditional**.

Interface: ``.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

## pyarrow.compute.dictionary_decode

Disposition: **conditional**.

Interface: `(dictionary_array, /, *, memory_pool=None)`.

- `documented_elementwise_operation = add`: **unknown**. No adequate applicable support or refutation.

The remaining 870 alternatives and all individual assessments are retained in the comparison record `93790284aba98c6c1d7805836c2b23b23956f4344ec186b8fd31e99dce942743`. This display limit does not narrow the candidate universe.

## Consumer preferences

Strategy: **lexicographic**. Policy: `c70a604e6963c2fc1afaad0da6bf47db76fc9d90048be7787babba5031ee7bd7`.

For this demonstration both overflow policies are permitted; the consumer explicitly prefers a reported error. This is a consumer choice, not a measured speed or memory claim.

- `documented_integer_overflow_policy`: ordered (error → wrap).

Retained preference frontier: `compute-registry:add_checked`.

Candidates with unresolved objective values remain on the frontier. Preference does not establish invocation compatibility or a universal optimum.

- `compute-registry:add_checked`: `documented_integer_overflow_policy = error`, **supported**, upstream_contract; assertion `5bb05aa0ff51f0b16bd02a727d587538b23f99c110080a633e42111fe80aeae8`.
- `compute-registry:add`: `documented_integer_overflow_policy = wrap`, **supported**, upstream_contract; assertion `aef6d3744890fe67cf1258d37109687453d3df766f3760beb73d1aed789a9377`.

## Unresolved scope

- No universal optimum is asserted; preferences and incomplete semantic coverage are explicit.
- Candidate membership digest: 28ff314407222c606ed933b020e9834c0e142e8e84baabafb0ab4cb204160674.
