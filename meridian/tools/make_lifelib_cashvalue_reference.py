"""Generate stochastic reconciliation targets from lifelib's CashValue_ME (savings library).

Run with the lifelib environment (see make_lifelib_reference.py):

    .venv-lifelib/Scripts/python tools/make_lifelib_cashvalue_reference.py

Two reference sets:
1. ``portfolio``: lifelib's 10,000 model points (all new business) under each of the 10
   stochastic scenarios in lifelib's ``std_norm_rand`` table.
2. ``inforce``: 1,000 of those policies turned into in-force business (random durations and
   account values), under scenarios 1-3. This exercises lifelib's existing-business logic.

lifelib's model is run unchanged; only ``model_point_table`` and ``scen_id`` are set.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import lifelib
import modelx as mx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "lifelib_work"
OUT = ROOT / "python" / "meridian" / "validation_data" / "lifelib_cashvalue"
INPUTS = ROOT / "python" / "meridian" / "models" / "data" / "lifelib_cashvalue"

PV_ITEMS = {
    "pv_premiums": lambda p: p.pv_premiums(),
    "pv_claims_death": lambda p: p.pv_claims("DEATH"),
    "pv_claims_lapse": lambda p: p.pv_claims("LAPSE"),
    "pv_claims_maturity": lambda p: p.pv_claims("MATURITY"),
    "pv_expenses": lambda p: p.pv_expenses(),
    "pv_commissions": lambda p: p.pv_commissions(),
    "pv_inv_income": lambda p: p.pv_inv_income(),
    "pv_av_change": lambda p: p.pv_av_change(),
    "pv_net_cf": lambda p: p.pv_net_cf(),
    "pv_pols_if": lambda p: p.pv_pols_if(),
}
CF_ITEMS = ["premiums", "claims", "expenses", "commissions", "inv_income", "av_change", "net_cf"]


def run_set(p, n_scen: int, label: str):
    n_pol = len(p.model_point_table)
    pv = {k: np.zeros((n_scen, n_pol)) for k in PV_ITEMS}
    steps = int(p.max_proj_len())
    cf = {k: np.zeros((n_scen, steps)) for k in CF_ITEMS + ["pols_if"]}
    secs = []
    for s in range(n_scen):
        p.scen_id = s + 1
        start = time.perf_counter()
        for k, f in PV_ITEMS.items():
            pv[k][s] = np.asarray(f(p))
        for k in CF_ITEMS:
            cf[k][s] = [float(np.sum(np.asarray(getattr(p, k)(t)))) for t in range(steps)]
        cf["pols_if"][s] = [float(np.sum(np.asarray(p.pols_if(t)))) for t in range(steps)]
        secs.append(time.perf_counter() - start)
        print(f"  {label} scenario {s + 1}: {secs[-1]:.1f}s, sum pv_net_cf {pv['pv_net_cf'][s].sum():,.2f}")
    return pv, cf, steps, secs


def main() -> None:
    WORK.mkdir(exist_ok=True)
    lib = WORK / "savings"
    if not lib.exists():
        lifelib.create("savings", str(lib))
    OUT.mkdir(parents=True, exist_ok=True)
    INPUTS.mkdir(parents=True, exist_ok=True)
    src = lib / "CashValue_ME"

    m = mx.read_model(str(src))
    p = m.Projection
    mp = pd.DataFrame(p.model_point_10000).reset_index()
    mp.to_csv(INPUTS / "model_point_10000.csv", index=False)
    for name in ["product_spec_table", "surr_charge_table", "mort_table", "disc_rate_ann"]:
        df = pd.read_excel(src / f"{name}.xlsx")
        df.to_csv(INPUTS / f"{name}.csv", index=False)
    pd.read_csv(src / "std_norm_rand.csv").to_csv(INPUTS / "std_norm_rand.csv", index=False)
    rand = pd.read_csv(src / "std_norm_rand.csv")
    n_scen = int(rand["scen_id"].nunique())

    # 1. Full portfolio, every scenario.
    p.model_point_table = p.model_point_10000
    pv, cf, steps, secs = run_set(p, n_scen, "portfolio")
    np.savez_compressed(OUT / "portfolio.npz", n_steps=steps, **pv,
                        **{f"cf_{k}": v for k, v in cf.items()})

    # 2. In-force variant: 1,000 policies with durations and account values.
    rng = np.random.default_rng(20261102)
    base = pd.DataFrame(p.model_point_10000).iloc[:1000].copy()
    spec = pd.read_excel(src / "product_spec_table.xlsx").set_index("spec_id")
    last_age = int(p.mort_table_last_age())
    is_wl = spec.loc[base["spec_id"], "is_wl"].to_numpy()
    term = np.where(is_wl, last_age - base["age_at_entry"].to_numpy(), base["policy_term"].to_numpy())
    base["duration_mth"] = rng.integers(1, 12 * term)
    base["av_pp_init"] = np.round(base["sum_assured"].to_numpy() * rng.uniform(0.0, 0.6, len(base)), 0)
    base.reset_index().to_csv(INPUTS / "model_point_inforce_1000.csv", index=False)
    p.model_point_table = base
    pv_i, cf_i, steps_i, secs_i = run_set(p, 3, "inforce")
    np.savez_compressed(OUT / "inforce.npz", n_steps=steps_i, **pv_i,
                        **{f"cf_{k}": v for k, v in cf_i.items()})

    meta = {
        "lifelib_version": lifelib.__version__,
        "modelx_version": mx.__version__,
        "model": "savings/CashValue_ME",
        "portfolio": {"n_policies": int(len(mp)), "n_scenarios": n_scen, "n_steps": steps,
                      "lifelib_seconds_per_scenario": [round(x, 2) for x in secs],
                      "pv_net_cf_by_scenario": [float(x) for x in pv["pv_net_cf"].sum(axis=1)]},
        "inforce": {"n_policies": 1000, "n_scenarios": 3, "n_steps": steps_i,
                    "lifelib_seconds_per_scenario": [round(x, 2) for x in secs_i],
                    "pv_net_cf_by_scenario": [float(x) for x in pv_i["pv_net_cf"].sum(axis=1)]},
        "mort_table_last_age": last_age,
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
