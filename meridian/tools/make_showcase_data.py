"""Produce the data behind the showcase page (showcase/showcase_data.json) from real runs.

    .venv/Scripts/python tools/make_showcase_data.py
    .venv/Scripts/python tools/build_showcase.py      # injects the data into the page

Everything on the page comes from this file: reconciliation statistics against lifelib,
monthly cash flows from both engines, per-scenario present values, timings, and full
formula traces for sample policies (the "explain a number" explorer).
"""

from __future__ import annotations

import csv
import json
import os
import platform
import time
from pathlib import Path

import numpy as np

import meridian as mr
from meridian.dsl import references
from meridian.models import lifelib_basicterm as bt
from meridian.models import lifelib_cashvalue as cv
from meridian.models import sa_funeral as fu

ROOT = Path(__file__).resolve().parent.parent
REF_BT = ROOT / "python" / "meridian" / "validation_data" / "lifelib_basicterm"
REF_CV = ROOT / "python" / "meridian" / "validation_data" / "lifelib_cashvalue"
OUT = ROOT / "showcase" / "showcase_data.json"


def sig(x, n=12):
    """Round to n significant digits (keeps the JSON compact; display shows fewer)."""
    if isinstance(x, (list, tuple, np.ndarray)):
        return [sig(v, n) for v in x]
    x = float(x)
    if not np.isfinite(x):
        return None
    return float(f"{x:.{n}g}")


def worst_rel(a, b):
    return float(np.max(np.abs(a - b) / np.maximum(1.0, np.abs(b))))


def best_of(f, n=3):
    times, out = [], None
    for _ in range(n):
        out = f()
        times.append(out.seconds if hasattr(out, "seconds") else out[1])
    return out, min(times)


def read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def model_spec(model: mr.Model) -> list[dict]:
    """Variables in evaluation order with formula text, doc and direct references."""
    order = mr.inspect(model)["order"]
    classes = mr.inspect(model)["classes"]
    spec = []
    for name in order:
        d = model.variables[name]
        refs, inputs = references(d.expr)
        f = d.expr.formula()
        if f.startswith("(") and f.endswith(")"):
            depth, outer = 0, True
            for i, ch in enumerate(f):
                depth += ch == "("
                depth -= ch == ")"
                if depth == 0 and i < len(f) - 1:
                    outer = False
                    break
            if outer:
                f = f[1:-1]
        spec.append({"name": name, "formula": f, "doc": d.doc, "init": d.init,
                     "refs": sorted([list(r) for r in refs]), "inputs": sorted(inputs),
                     "cls": classes[name], "total": d.total, "pv": d.policy_sum})
    return spec


def trace_policy(model, mp_one, tables, scenarios, steps, label, extra=None):
    tr = mr.trace(model, mp_one, tables, scenarios)
    vals = {k: sig(v[:steps], 10) for k, v in tr.values.items()}
    return {"label": label, "inputs": {k: (v if isinstance(v, str) else sig(v)) for k, v in tr.inputs.items()},
            "values": vals, **(extra or {})}


def basicterm() -> dict:
    meta = json.loads((REF_BT / "meta.json").read_text())
    mp, tables = bt.load_model_points(), bt.load_tables()
    bt.run_basicterm({k: v[:10] for k, v in mp.items()}, tables)
    res, secs = best_of(lambda: bt.run_basicterm(mp, tables))
    ref = read_csv(REF_BT / "lifelib_M_per_policy.csv")
    cf = read_csv(REF_BT / "lifelib_M_cashflows.csv")
    ps = res.projection.policy_sums
    big = {k: np.tile(v, 100) for k, v in mp.items()}
    big_res, big_secs = best_of(lambda: bt.run_basicterm(big, tables), n=2)

    checks = [{"item": "Premium per policy", "kind": "exact",
               "value": int(np.sum(res.premium_pp == ref["premium_pp"])), "of": int(len(ref["premium_pp"]))}]
    for k, label in [("pv_premiums", "PV premiums"), ("pv_claims", "PV claims"),
                     ("pv_expenses", "PV expenses"), ("pv_commissions", "PV commissions"),
                     ("pv_net_cf", "PV net cash flow")]:
        checks.append({"item": label, "kind": "rel", "value": worst_rel(ps[k][0], ref[k])})
    cash = {}
    for k in ["premiums", "claims", "expenses", "commissions", "net_cf"]:
        cash[k] = {"meridian": sig(res.projection.totals[k][0], 10), "lifelib": sig(cf[k], 10),
                   "worst_rel": worst_rel(res.projection.totals[k][0], cf[k])}

    m = bt.build(int(np.max(mp["policy_term"])))
    samples = []
    for i in [0, 1, 2, 3, 4, 9]:
        one = {k: v[i:i + 1] for k, v in mp.items()}
        one["premium_pp"] = res.premium_pp[i:i + 1]
        lab = (f"Policy {int(mp['point_id'][i])} · {mp['sex'][i]}, age {int(mp['age_at_entry'][i])} · "
               f"{int(mp['policy_term'][i])}-year term · SA {int(mp['sum_assured'][i]):,}")
        samples.append(trace_policy(m, one, tables, None, m.n_steps, lab,
                                    {"premium_pp": float(res.premium_pp[i]),
                                     "lifelib_premium_pp": float(ref["premium_pp"][i])}))
    pvs = {name: float(ps[k].sum()) for name, k in
           [("Premiums", "pv_premiums"), ("Claims", "pv_claims"), ("Expenses", "pv_expenses"),
            ("Commissions", "pv_commissions"), ("Net cash flow", "pv_net_cf")]}
    return {
        "n_policies": int(len(mp["policy_term"])), "n_steps": int(meta["n_steps"]),
        "lifelib_version": meta["lifelib_version"],
        "portfolio_pv_net_cf": {"meridian": float(ps["pv_net_cf"].sum()), "lifelib": meta["portfolio_pv_net_cf"]},
        "result_pv": pvs, "checks": checks, "cashflows": cash,
        "timing": {"meridian_10k": secs, "lifelib_10k": meta["basicterm_m_seconds_all_policies"],
                   "meridian_1m": big_secs, "n_big": int(len(big["policy_term"]))},
        "model": model_spec(m), "samples": samples, "trace_steps": m.n_steps,
    }


def cashvalue() -> dict:
    meta = json.loads((REF_CV / "meta.json").read_text())
    out = {"sets": {}}
    gross = ["pv_premiums", "pv_inv_income", "pv_claims_death", "pv_claims_lapse",
             "pv_claims_maturity", "pv_expenses", "pv_commissions", "pv_av_change"]
    labels = {"pv_premiums": "PV premiums", "pv_inv_income": "PV investment income",
              "pv_claims_death": "PV death claims", "pv_claims_lapse": "PV surrenders",
              "pv_claims_maturity": "PV maturities", "pv_expenses": "PV expenses",
              "pv_commissions": "PV commissions", "pv_av_change": "PV change in account value"}
    for label, mpfile, ref_file, scen in [("portfolio", "model_point_10000.csv", "portfolio.npz", None),
                                          ("inforce", "model_point_inforce_1000.csv", "inforce.npz", [1, 2, 3])]:
        ref = np.load(REF_CV / ref_file)
        mp = cv.load_model_points(mpfile)
        cv.run_cashvalue({k: v[:5] for k, v in mp.items()}, scenarios=scen)
        res, secs = best_of(lambda: cv.run_cashvalue(mp, scenarios=scen))
        g = sum(np.abs(ref[k]) for k in gross)
        net_vs_gross = float((np.abs(res.policy_sums["pv_net_cf"] - ref["pv_net_cf"]) / np.maximum(g, 1)).max())
        out["sets"][label] = {
            "n_policies": res.n_policies, "n_scenarios": res.n_scenarios, "n_steps": res.n_steps,
            "checks": [{"item": labels[k], "value": worst_rel(res.policy_sums[k], ref[k])} for k in gross]
            + [{"item": "PV net cash flow (vs gross flows)", "value": net_vs_gross}],
            "pv_by_scenario": {"meridian": res.policy_sums["pv_net_cf"].sum(axis=1).tolist(),
                               "lifelib": meta[label]["pv_net_cf_by_scenario"]},
            "timing": {"meridian": secs, "lifelib": float(sum(meta[label]["lifelib_seconds_per_scenario"]))},
        }
        if label == "portfolio":
            spec_ids = mp["spec_id"]
            out["by_product"] = {s: float(res.policy_sums["pv_net_cf"][:, spec_ids == s].sum(axis=1).mean())
                                 for s in ["A", "B", "C", "D"]}
            out["cash_scen1"] = {k: sig(res.totals[k][0], 10) for k in
                                 ["premiums", "claims", "inv_income", "expenses", "net_cf"]}

    # Capacity run: 100 generated scenarios.
    mp = cv.load_model_points()
    tables = cv.load_tables()
    last_age = cv.mort_table_last_age(tables)
    steps = cv.projection_length(mp, tables, last_age)
    model = cv.build(steps, last_age=last_age)
    z = np.random.default_rng(1).standard_normal((100, steps))
    cap = mr.run(model, mp, tables, {"std_norm_rand": z})
    pvn = cap.policy_sums["pv_net_cf"].sum(axis=1)
    out["capacity"] = {"n_scenarios": 100, "n_policies": cap.n_policies, "n_steps": steps,
                       "seconds": cap.seconds, "pv_sorted": sorted(float(x) for x in pvn)}

    # Explorer samples: one new-business policy per product + two in-force policies, scenario 1.
    shown = 240
    samples = []
    nb = cv.load_model_points()
    inf = cv.load_model_points("model_point_inforce_1000.csv")
    picks = [("NB", nb, i) for i in [3, 0, 1, 2]] + [("IF", inf, 5), ("IF", inf, 9)]
    names = {"A": "single-premium endowment", "B": "single premium with surrender charge",
             "C": "level-premium whole life", "D": "level-premium whole life with surrender charge"}
    for kind, src, i in picks:
        one = {k: v[i:i + 1] for k, v in src.items()}
        n = cv.projection_length(one, tables, last_age)
        mdl = cv.build(n, last_age=last_age)
        status = "new business" if kind == "NB" else f"in force, {int(one['duration_mth'][0])} months"
        lab = (f"Policy {int(one['policy_id'][0])} · product {one['spec_id'][0]} ({names[one['spec_id'][0]]}) · "
               f"age {int(one['age_at_entry'][0])} at entry · {status}")
        samples.append(trace_policy(mdl, one, tables, cv.load_scenarios(n, [1]), min(n, shown), lab))
    out.update({
        "lifelib_version": meta["lifelib_version"],
        "model": model_spec(cv.build(240, last_age=last_age)),
        "samples": samples, "trace_steps": shown,
    })
    return out


def funeral(n_policies: int = 20_000) -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    import independent_funeral as ind

    rows = fu.synthetic_lives(n_policies)
    mp = fu.model_points(rows)
    fu.value({k: v[:80] for k, v in mp.items()}, years=5)  # warm-up
    best, secs = None, None
    for _ in range(2):
        r = fu.value(mp)
        if secs is None or r.seconds < secs:
            best, secs = r, r.seconds
    r = best
    base = r.base
    roles, counts = np.unique(rows["role"], return_counts=True)

    # Independent loop implementation on 25 policies under every basis.
    sub_ids = list(dict.fromkeys(rows["policy_id"]))[:25]
    sub = {k: v[np.isin(rows["policy_id"], sub_ids)] for k, v in rows.items()}
    sub_mp = fu.model_points(sub)
    worst = 0.0
    for basis in fu.BASES:
        res = mr.run(fu.build(), sub_mp, fu.tables(basis))
        ours = res.policy_sums["bel"][0].reshape(-1, fu.LIVES).sum(axis=1)
        ref = np.array([ind.check_policy(sub, pid, basis) for pid in sub_ids])
        worst = max(worst, float((np.abs(ours - ref) / np.maximum(1, np.abs(ref))).max()))

    # Explorer: every life of one family policy.
    pids = list(dict.fromkeys(rows["policy_id"]))
    fam = next(pid for pid in pids if {"spouse", "child", "extended"} <= set(rows["role"][rows["policy_id"] == pid]))
    p = pids.index(fam)
    model = fu.build()
    shown = 240
    samples = []
    idx = np.where(rows["policy_id"] == fam)[0]
    for slot, i in enumerate(idx):
        tr = mr.trace(model, mp, fu.tables(), policy=p, life=slot)
        lab = (f"{fam} · life {slot + 1}: {rows['role'][i]} · {rows['sex'][i]}, age {int(rows['age'][i])} · "
               f"cover R{int(rows['cover'][i]):,} · premium R{float(rows['premium'][i]):.2f}/month")
        samples.append({"label": lab,
                        "inputs": {k: (v if isinstance(v, str) else sig(v)) for k, v in tr.inputs.items()},
                        "values": {k: sig(v[:shown], 10) for k, v in tr.values.items()}})
    pols = base.totals["policies_if"][0]
    return {
        "n_policies": n_policies, "n_lives": int(len(rows["policy_id"])), "lanes": int(len(mp["policy_id"])),
        "lives_by_role": {r_: int(c) for r_, c in zip(roles, counts)},
        "n_steps": base.n_steps, "runs": r.runs, "seconds": secs,
        "pv_premiums": float(base.policy_sums["pv_premiums"].sum()),
        "pv_claims": float(base.policy_sums["pv_claims"].sum()),
        "bel": r.bel, "scr": r.scr, "risk_margin": r.risk_margin, "tp": r.technical_provisions,
        "stress_labels": fu.STRESS_LABELS,
        "policies_by_year": [float(pols[12 * y]) for y in range(0, 31)],
        "projected_scr": [float(x) for x in r.projected_scr[:31]],
        "independent_worst": worst, "independent_policies": len(sub_ids),
        "assumptions": {"commission": fu.COMMISSION, "expense_per_policy": fu.EXPENSE_PER_POLICY,
                        "claim_expense": fu.CLAIM_EXPENSE, "expense_inflation": fu.EXPENSE_INFLATION,
                        "mass_lapse": fu.MASS_LAPSE, "coc": fu.COST_OF_CAPITAL,
                        "lapse_by_year": [float(x) for x in fu.tables()["lapse"].values]},
        "model": model_spec(model), "samples": samples, "trace_steps": shown,
    }


def main():
    start = time.perf_counter()
    rust_tests = 25
    data = {
        "generated": time.strftime("%Y-%m-%d"),
        "machine": {"cpu": os.environ.get("SHOWCASE_CPU", platform.processor() or "unknown"),
                    "threads": os.cpu_count(), "os": f"{platform.system()} {platform.release()}"},
        "basicterm": basicterm(),
        "cashvalue": cashvalue(),
        "funeral": funeral(),
        "tests": {"rust": rust_tests, "python": 97},
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB) in {time.perf_counter() - start:.0f}s")


if __name__ == "__main__":
    main()
