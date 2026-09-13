"""Verify projection placement, overflow and the declared Arrow boundary."""

from __future__ import annotations

import importlib.metadata
import tempfile
from pathlib import Path

import pyarrow as pa
from datafusion import SessionContext, col
from pyarrow import compute, dataset, parquet

EXPECTED_VERSIONS = {"datafusion": "54.0.0", "pyarrow": "25.0.1"}


def main() -> None:
    """Exercise actual library behavior with explicit expected values and schemas.

    Raises:
        AssertionError: If the checked addition accepts integer overflow.

    """
    for package, version in EXPECTED_VERSIONS.items():
        assert importlib.metadata.version(package) == version
    schema = pa.schema([pa.field("value", pa.int64())], metadata={b"case": b"pilot"})
    table = pa.Table.from_pydict({"value": [1, None, 3]}, schema=schema)
    reader = table.to_reader(max_chunksize=2)
    assert reader.schema == schema
    assert reader.read_all().equals(table, check_metadata=True)
    context = SessionContext()
    frame = context.from_arrow(table)
    result = frame.select((col("value") + 1).alias("result")).collect()
    observed = pa.Table.from_batches(result).column("result").to_pylist()
    assert observed == [2, None, 4]
    assert (
        compute.call_function("add", [table.column("value"), pa.scalar(1)]).to_pylist() == observed
    )
    maximum = pa.array([127], type=pa.int8())
    one = pa.scalar(1, type=pa.int8())
    assert compute.call_function("add", [maximum, one]).to_pylist() == [-128]
    try:
        compute.call_function("add_checked", [maximum, one])
    except pa.ArrowInvalid:
        pass
    else:
        message = "checked addition did not report integer overflow"
        raise AssertionError(message)
    with tempfile.TemporaryDirectory(prefix="library-guides-dataset-") as temporary:
        path = Path(temporary) / "values.parquet"
        parquet.write_table(table, path)
        scan = dataset.dataset(path).scanner(
            columns=["value"], filter=dataset.field("value") > 1, batch_size=1, batch_readahead=1
        )
        batches = list(scan.to_batches())
        scanned = pa.Table.from_batches(batches)
        materialized = parquet.read_table(path, columns=["value"], filters=[("value", ">", 1)])
        assert scanned.equals(materialized)
        assert scanned.column("value").to_pylist() == [3]
        assert all(batch.num_rows <= 1 for batch in batches)


if __name__ == "__main__":
    main()
