"""Generate reconciliation targets from lifelib's BasicTerm models.

Run with the separate lifelib environment (it needs lifelib, modelx, pandas, openpyxl):

    python -m venv .venv-lifelib
    .venv-lifelib/Scripts/python -m pip install lifelib pandas openpyxl
    .venv-lifelib/Scripts/python tools/make_lifelib_reference.py

It copies lifelib's BasicTerm inputs to CSV and records lifelib's own results:
* BasicTerm_M (vectorised) for all 10,000 policies: premium per policy, present values,
  and portfolio cash flows by month.
* BasicTerm_S (seriatim, one policy at a time) for a sample of policies, to confirm S and M
  agree before using M as the reference.

lifelib is MIT-licensed; see python/meridian/models/data/lifelib_basicterm/NOTICE.md.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import lifelib
import modelx as mx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = ROOT / "lifelib_work"
OUT = ROOT / "python" / "meridian" / "validation_data" / "lifelib_basicterm"  # lifelib's results (targets)
INPUTS = ROOT / "python" / "meridian" / "models" / "data" / "lifelib_basicterm"  # model inputs


def main() -> None:
    WORK.mkdir(exist_ok=True)
    lib = WORK / "basiclife"
    if not lib.exists():
        lifelib.create("basiclife", str(lib))
    OUT.mkdir(parents=True, exist_ok=True)
    INPUTS.mkdir(parents=True, exist_ok=True)

    # ---- inputs -------------------------------------------------------------------------
    mp = pd.read_excel(lib / "BasicTerm_M" / "model_point_table.xlsx")
    mort = pd.read_excel(lib / "BasicTerm_M" / "mort_table.xlsx")
    disc = pd.read_excel(lib / "BasicTerm_M" / "disc_rate_ann.xlsx")
    mp.to_csv(INPUTS / "model_point_table.csv", index=False)
    mort.to_csv(INPUTS / "mort_table.csv", index=False)
    disc.to_csv(INPUTS / "disc_rate_ann.csv", index=False)

    # ---- BasicTerm_M: full portfolio ------------------------------------------------------
    m = mx.read_model(str(lib / "BasicTerm_M"))
    p = m.Projection
    start = time.perf_counter()
    prem_pp = np.asarray(p.premium_pp())
    pv = {
        "premium_pp": prem_pp,
        "pv_premiums": np.asarray(p.pv_premiums()),
        "pv_claims": np.asarray(p.pv_claims()),
        "pv_expenses": np.asarray(p.pv_expenses()),
        "pv_commissions": np.asarray(p.pv_commissions()),
        "pv_net_cf": np.asarray(p.pv_net_cf()),
        "pv_pols_if": np.asarray(p.pv_pols_if()),
        "net_premium_pp": np.asarray(p.net_premium_pp()),
    }
    n_steps = int(p.max_proj_len())
    cf = {
        name: np.array([np.asarray(getattr(p, name)(t)).sum() for t in range(n_steps)])
        for name in ["premiums", "claims", "expenses", "commissions", "net_cf", "pols_if", "pols_death", "pols_lapse"]
    }
    m_seconds = time.perf_counter() - start

    per_policy = pd.DataFrame({"point_id": mp["point_id"], **pv})
    per_policy.to_csv(OUT / "lifelib_M_per_policy.csv", index=False, float_format="%.17g")
    pd.DataFrame({"t": np.arange(n_steps), **cf}).to_csv(
        OUT / "lifelib_M_cashflows.csv", index=False, float_format="%.17g")

    # ---- BasicTerm_S: sample of seriatim points --------------------------------------------
    s_model = mx.read_model(str(lib / "BasicTerm_S"))
    sample_ids = [1, 2, 3, 100, 777, 2500, 5000, 9999, 10000]
    rows = []
    start = time.perf_counter()
    for pid in sample_ids:
        sp = s_model.Projection[pid]
        rows.append({"point_id": pid, "premium_pp": sp.premium_pp(), "pv_net_cf": sp.pv_net_cf(),
                     "pv_claims": sp.pv_claims(), "pv_premiums": sp.pv_premiums()})
    s_seconds = time.perf_counter() - start
    s_df = pd.DataFrame(rows)
    s_df.to_csv(OUT / "lifelib_S_sample.csv", index=False, float_format="%.17g")

    # S and M must agree before M is used as the reference.
    joined = s_df.merge(per_policy, on="point_id", suffixes=("_S", "_M"))
    worst = max(
        float(np.max(np.abs(joined[f"{c}_S"] - joined[f"{c}_M"]) / np.maximum(1.0, np.abs(joined[f"{c}_M"]))))
        for c in ["premium_pp", "pv_net_cf", "pv_claims", "pv_premiums"]
    )
    meta = {
        "lifelib_version": lifelib.__version__,
        "modelx_version": mx.__version__,
        "n_policies": int(len(mp)),
        "n_steps": n_steps,
        "basicterm_m_seconds_all_policies": round(m_seconds, 3),
        "basicterm_s_seconds_for_sample": round(s_seconds, 3),
        "basicterm_s_sample_size": len(sample_ids),
        "s_vs_m_worst_relative_diff": worst,
        "portfolio_pv_net_cf": float(pv["pv_net_cf"].sum()),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
