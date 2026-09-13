# Consume Python query results through a documented stream

Profile: `python-installed-54-25`.

Comparison: `0cc7b70d2f4ae4e9c14fb20994c4def02011a789ef413bcc501da86f87959892`. Universe: `0eca5d1542b98330a97237f851b902439917caa6b07b9638c95e2afc4775eabf`.

Candidates are drawn from the admitted interface universe. Retrieval rank does not exclude alternatives.

## pyarrow.dataset.dataset

Disposition: **conditional**.

Interface: `def dataset(source, schema=None, format=None, filesystem=None,
            partitioning=None, partition_base_dir=None,
            exclude_invalid_files=None, ignore_prefixes=None):`.

- `documented_result_delivery = incremental`: **unknown**. No adequate applicable support or refutation.

## datafusion.dataframe.DataFrame.collect

Disposition: **rejected**.

Interface: `def collect(self) -> list[pa.RecordBatch]:`.

- `documented_result_delivery = incremental`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `843820df82c797547ef9965ee818b7ca7c1c79e335a019d73042e2dbbe0459c6`.

Re-evaluation triggers:

- Re-evaluate 2d9beb8e1a8cf239ff303ce62a8261c982962b62abe669c11040a8ace47683f2 when required value or applicability changes.

## datafusion.dataframe.DataFrame.execute_stream

Disposition: **eligible**.

Interface: `def execute_stream(self) -> RecordBatchStream:`.

- `documented_result_delivery = incremental`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `47af7058f7a75cfe34ee02949b32e822cdb14f080758f71e92c79d88ed6ba2cf`.

Re-evaluation triggers:

- Re-evaluate 2d9beb8e1a8cf239ff303ce62a8261c982962b62abe669c11040a8ace47683f2 when required value or applicability changes.

## Unresolved scope

- No universal optimum is asserted; preferences and incomplete semantic coverage are explicit.
- Candidate membership digest: e975ef53c0b9b7ab889258e1b9b3af859e07a4466a3a28d5cccb4cf745c027ad.
