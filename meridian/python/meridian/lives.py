"""Lives within a policy.

A model created with ``Model(..., lives=K)`` treats every K consecutive model-point rows as the
K lives of one policy (main member, spouse, children, ...). Formulas are written per life;
``sum_lives(x)`` gives the policy total of ``x`` (broadcast back to each life) and ``life`` is
the life's slot number 0..K-1. This is the analogue of Prophet's array variables, with each
life a lane of the vectorised engine.

Data usually arrives one row per life. :func:`group_lives` arranges it into policies of K
slots: rows are grouped by a policy key, kept in their original order within the policy, and
unused slots are padded with ``life_active = 0`` and zero-valued columns.
"""

from __future__ import annotations

import numpy as np


def group_lives(columns: dict, policy_key: str, lives: int, *, order_key: str | None = None,
                pad: dict | None = None) -> dict[str, np.ndarray]:
    """Arrange one-row-per-life columns into ``lives`` slots per policy.

    Returns the padded columns plus ``life_active`` (1 for a real life, 0 for padding) and
    ``policy_index`` (0-based policy number). Raises if a policy has more than ``lives`` lives.
    ``pad`` gives the value for unused slots per column (default 0 or ""); choose values that
    keep table lookups valid (e.g. a known sex and a role "none"), so padding never yields NaN.
    """
    pad = pad or {}
    if lives < 1 or lives & (lives - 1):
        raise ValueError("lives must be a power of two")
    keys = np.asarray(columns[policy_key])
    n = len(keys)
    idx = np.arange(n)
    if order_key is not None:
        idx = np.lexsort((np.asarray(columns[order_key]), keys))  # by policy, then order_key
    else:
        _, first = np.unique(keys, return_index=True)
        rank = {k: r for r, k in enumerate(keys[np.sort(first)])}
        idx = np.array(sorted(range(n), key=lambda i: (rank[keys[i]], i)))
    sorted_keys = keys[idx]
    uniq, start, counts = np.unique(sorted_keys, return_index=True, return_counts=True)
    order = np.argsort(start)
    uniq, start, counts = uniq[order], start[order], counts[order]
    if counts.max(initial=0) > lives:
        worst = uniq[np.argmax(counts)]
        raise ValueError(f"policy {worst!r} has {counts.max()} lives; the model allows {lives}")
    n_pol = len(uniq)
    slot_rows = np.full(n_pol * lives, -1)
    for p, (s, c) in enumerate(zip(start, counts)):
        slot_rows[p * lives:p * lives + c] = idx[s:s + c]
    real = slot_rows >= 0
    out = {}
    for name, values in columns.items():
        a = np.asarray(values)
        if a.dtype.kind in ("U", "S", "O"):
            col = np.full(n_pol * lives, pad.get(name, ""), dtype=object)
        else:
            col = np.full(n_pol * lives, float(pad.get(name, 0.0)), dtype=np.float64)
        col[real] = a[slot_rows[real]]
        if name == policy_key:
            col = np.repeat(uniq, lives)
        out[name] = col if col.dtype != object else col.astype(str)
    out["life_active"] = real.astype(np.float64)
    out["policy_index"] = np.repeat(np.arange(n_pol, dtype=np.float64), lives)
    return out
