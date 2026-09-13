"""Finite date-string strictness contrast; no universal coercion claim."""

import json
import sys
from datetime import date
from importlib.metadata import version

from pydantic import TypeAdapter, ValidationError

adapter = TypeAdapter(date)
try:
    adapter.validate_python("2000-01-01", strict=True)
except ValidationError:
    python_accepts = False
else:
    python_accepts = True
json_accepts = adapter.validate_json('"2000-01-01"', strict=True) == date(2000, 1, 1)
assert not python_accepts
assert json_accepts
sys.stdout.write(
    json.dumps(
        {
            "environment": {"pydantic": version("pydantic")},
            "python_accepts": python_accepts,
            "json_accepts": json_accepts,
        }
    )
    + "\n"
)
