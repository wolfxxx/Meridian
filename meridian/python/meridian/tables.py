"""Assumption tables and text categories.

A :class:`Table` is an N-dimensional array of values whose dimensions are keyed either by
an integer range (``start``, e.g. ages from 18) or by a list of category labels (e.g. product
codes, sex). Lookups in a model are written ``tb.name[key1, key2, ...]``:

* range keys are floored and clamped to the table (ages beyond the last row use the last
  row; NaN keys use the first row);
* category keys must match a label exactly; an unknown label gives NaN, so it cannot pass
  silently into results.

Keys outside the table follow the table's ``fill`` setting: ``fill=None`` (default) clamps
range keys and gives NaN for unknown categories; ``fill=x`` returns ``x`` for *any* key outside
the table (out-of-range, NaN or unknown category), e.g. ``fill=0.0`` like a pandas reindex
with ``fill_value=0``.

Text values (model-point columns such as ``sex = "F"``, labels in category tables, and string
literals in formulas such as ``mp.sex == "F"``) are converted to numeric codes by
:func:`category_code`, a deterministic hash. No category list has to be declared in advance.
"""

from __future__ import annotations

import hashlib
from typing import Iterable, Sequence, Union

import numpy as np

_CODE_CACHE: dict[str, float] = {}


def category_code(label: str) -> float:
    """Deterministic numeric code for a text label.

    The code is a negative integer below -2**52 (exactly representable in float64), so it
    cannot be confused with an ordinary numeric input such as an age or a sum assured.
    """
    code = _CODE_CACHE.get(label)
    if code is None:
        h = int.from_bytes(hashlib.blake2b(label.encode("utf-8"), digest_size=6).digest(), "big")
        code = -float(2 ** 52 + h % (2 ** 48))  # exact in float64 (< 2**53)
        _CODE_CACHE[label] = code
    return code


def is_text_array(a: np.ndarray) -> bool:
    return a.dtype.kind in ("U", "S", "O")


def encode_column(values) -> np.ndarray:
    """Model-point column -> float64; text columns become category codes."""
    a = np.asarray(values)
    if is_text_array(a):
        uniques, inverse = np.unique(a.astype(str), return_inverse=True)
        codes = np.array([category_code(u) for u in uniques], dtype=np.float64)
        return codes[inverse].reshape(a.shape)
    return np.ascontiguousarray(a, dtype=np.float64)


DimSpec = Union[int, float, Sequence[str]]


class Table:
    """N-dimensional assumption table.

    ``values``: array of shape ``(n1, n2, ...)``.
    ``dims``: one entry per dimension; an int/float is the first integer key of a range
    dimension (default 0), a sequence of strings is the category labels of that dimension.

    Example — select & ultimate mortality, ages 18.. by durations 0..5::

        mort = Table(q_values, dims=[18, 0])      # q_values.shape == (103, 6)
        lapse = Table([0.10, 0.06], dims=[["TERM10", "TERM20"]])
    """

    def __init__(self, values, dims: Iterable[DimSpec] | None = None, fill: float | None = None):
        self.fill = None if fill is None else float(fill)
        arr = np.asarray(values, dtype=np.float64)
        if arr.ndim == 0:
            arr = arr.reshape(1)
        dims = list(dims) if dims is not None else [0] * arr.ndim
        if len(dims) != arr.ndim:
            raise ValueError(f"table has {arr.ndim} dimension(s) but {len(dims)} dim spec(s)")
        self.values = arr
        self.dims: list[tuple] = []
        for d, (spec, length) in enumerate(zip(dims, arr.shape)):
            if isinstance(spec, (int, float, np.integer, np.floating)):
                self.dims.append(("range", float(spec), int(length)))
            else:
                labels = [str(x) for x in spec]
                if len(labels) != length:
                    raise ValueError(f"dimension {d}: {len(labels)} labels for {length} entries")
                if len(set(labels)) != len(labels):
                    raise ValueError(f"dimension {d}: duplicate category labels")
                self.dims.append(("categories", labels))

    @property
    def ndim(self) -> int:
        return self.values.ndim

    def engine_dims(self) -> list[tuple[float, int, list[float]]]:
        """Dimensions in the engine's format: ``(start, len, category_codes)``."""
        out = []
        for d in self.dims:
            if d[0] == "range":
                out.append((d[1], d[2], []))
            else:
                out.append((0.0, len(d[1]), [category_code(x) for x in d[1]]))
        return out

    def flat_values(self) -> np.ndarray:
        return np.ascontiguousarray(self.values.reshape(-1), dtype=np.float64)

    def lookup(self, keys: Sequence[np.ndarray]) -> np.ndarray:
        """Vectorised lookup with the engine's semantics (used by the NumPy reference)."""
        if len(keys) != self.ndim:
            raise ValueError(f"table has {self.ndim} dimension(s), lookup gave {len(keys)} key(s)")
        flat = np.zeros(np.shape(keys[0]), dtype=np.float64)
        for d, (spec, key) in enumerate(zip(self.dims, keys)):
            stride = int(np.prod(self.values.shape[d + 1:], dtype=np.int64))
            key = np.asarray(key, dtype=np.float64)
            if spec[0] == "range":
                k = np.floor(key) - spec[1]
                if self.fill is None:
                    k = np.where(np.isnan(k), 0.0, k)
                    pos = np.clip(k, 0, spec[2] - 1)
                else:
                    pos = np.where((k >= 0) & (k <= spec[2] - 1), k, np.nan)
            else:
                codes = np.array([category_code(x) for x in spec[1]])
                match = key[..., None] == codes
                pos = np.where(match.any(axis=-1), match.argmax(axis=-1), np.nan)
            flat = flat + pos * stride
        out = np.full(flat.shape, np.nan if self.fill is None else self.fill)
        ok = ~np.isnan(flat)
        out[ok] = self.values.reshape(-1)[flat[ok].astype(np.int64)]
        return out

    def __repr__(self) -> str:
        parts = [f"range from {d[1]:g} ({d[2]})" if d[0] == "range" else f"categories {d[1]}"
                 for d in self.dims]
        fill = "" if self.fill is None else f", fill={self.fill:g}"
        return f"Table(shape={self.values.shape}, dims=[{'; '.join(parts)}]{fill})"


def as_table(x) -> Table:
    return x if isinstance(x, Table) else Table(x)
