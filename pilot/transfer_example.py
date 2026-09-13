"""A second-library behavioral check for Python-object and JSON validation."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError


class Reading(BaseModel):
    """A small explicitly typed payload used by the transfer pilot."""

    count: int


def main() -> None:
    """Exercise successful decoding and strict-mode error behavior.

    Raises:
        AssertionError: If strict integer validation incorrectly accepts text.

    """
    expected_count = 3
    assert Reading.model_validate({"count": 3}).count == expected_count
    assert Reading.model_validate_json('{"count":3}').count == expected_count
    try:
        Reading.model_validate({"count": "3"}, strict=True)
    except ValidationError as error:
        error_type = error.errors()[0]["type"]
    else:
        message = "strict integer validation accepted text"
        raise AssertionError(message)
    assert error_type == "int_type"


if __name__ == "__main__":
    main()
