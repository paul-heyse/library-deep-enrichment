"""Explicit machine integer and IEEE literal semantics shared by abstract transfers."""

from __future__ import annotations

import struct

_WIDTHS = {"8": 8, "16": 16, "32": 32, "64": 64, "128": 128}
_IEEE = {"rust:f32": ("!f", 4), "rust:f64": ("!d", 8), "python:float_bits": ("!d", 8)}


def integer_width(ty: str) -> int | None:
    """Read a target-independent explicit integer width.

    Returns:
        None for pointer-sized integers or an unmodeled type.

    """
    return _WIDTHS.get(ty[6:]) if ty.startswith(("rust:i", "rust:u")) else None


def bounds(ty: str) -> tuple[int, int] | None:
    """Find the inclusive range of a modeled machine integer.

    Returns:
        Bounds without assuming the interpreter host's pointer width.

    """
    bits = integer_width(ty)
    if bits is None:
        return None
    signed = ty.startswith("rust:i")
    return (-(1 << (bits - 1)) if signed else 0, (1 << (bits - int(signed))) - 1)


def wrap(value: int, ty: str) -> tuple[int, bool] | None:
    """Compute a modular result and the separate mathematical overflow predicate.

    Returns:
        The represented integer and whether the unbounded result lies outside its range.

    """
    limits = bounds(ty)
    if limits is None:
        return None
    lower, upper = limits
    return ((value - lower) % (upper - lower + 1) + lower, not lower <= value <= upper)


def ieee_literal(value: str, ty: str) -> float | None:
    """Decode an exact native bit-pattern literal; arithmetic rounding is separate.

    Returns:
        A Python float preserving f32/f64 values, infinities, signed zero and NaN.

    """
    encoding = _IEEE.get(ty)
    if encoding is None:
        return None
    format_string, size = encoding
    try:
        data = int(value).to_bytes(size, "big")
    except ValueError, OverflowError:
        return None
    result = struct.unpack(format_string, data)[0]
    return result if isinstance(result, float) else None
