"""Exercise a real PyArrow to Rust to PyArrow C Stream ownership boundary."""

from __future__ import annotations

import gc
import importlib.util
import json
import sys
from pathlib import Path

import pyarrow as pa


def main(extension: Path) -> None:
    """Verify schema fidelity, buffer reuse, lifetime transfer and capsule single use.

    Raises:
        AssertionError: If a consumed capsule can be imported again.

    """
    spec = importlib.util.spec_from_file_location("library_guides_interop", extension)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = pa.schema([pa.field("value", pa.int64())], metadata={b"pilot": b"owned"})
    table = pa.Table.from_pydict({"value": [1, None, 3]}, schema=schema)
    buffer_address = table.column(0).chunk(0).buffers()[1].address
    reader = table.to_reader()
    capsule = reader.__arrow_c_stream__()
    result_reader = module.round_trip(capsule)
    del reader, table
    gc.collect()
    result = result_reader.read_all()
    assert result.schema.equals(schema, check_metadata=True)
    assert result.column(0).to_pylist() == [1, None, 3]
    assert result.column(0).chunk(0).buffers()[1].address == buffer_address
    try:
        module.round_trip(capsule)
    except ValueError, OSError:
        pass
    else:
        message = "a consumed capsule was imported twice"
        raise AssertionError(message)
    sys.stdout.write(
        json.dumps(
            {
                "observations": {
                    "fixture": "nullable int64 values [1, null, 3] with schema metadata",
                    "schema_and_metadata_preserved": True,
                    "data_buffer_address_preserved": True,
                    "result_survives_producer_deletion": True,
                    "second_capsule_import_rejected": True,
                }
            },
            sort_keys=True,
        )
        + "\n"
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
