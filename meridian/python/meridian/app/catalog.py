"""The models the app offers, and everything the app needs to know about each one.

Each :class:`ModelEntry` knows how to load its policy data, which assumption tables it uses,
how to run (including what-if runs with edited tables), how to explain one policy and how to
validate itself. The server only talks to this interface.
"""

from __future__ import annotations

import csv
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from .. import runner as mr_runner
from ..dsl import Model, references
from ..models import lifelib_basicterm as bt
from ..models import lifelib_cashvalue as cv
from ..models import sa_funeral as fu
from ..tables import Table

VALIDATION = Path(__file__).resolve().parents[1] / "validation_data"


# ---- helpers ---------------------------------------------------------------------------------

def clean(x):
    """JSON-safe floats (NaN/inf -> None), numpy -> python."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return v if np.isfinite(v) else None
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.str_):
        return str(x)
    return x


def strip_parens(f: str) -> str:
    if f.startswith("(") and f.endswith(")"):
        depth = 0
        for i, ch in enumerate(f):
            depth += ch == "("
            depth -= ch == ")"
            if depth == 0 and i < len(f) - 1:
                return f
        return f[1:-1]
    return f


def variable_spec(model: Model) -> list[dict]:
    info = mr_runner.inspect(model)
    order, classes = info["order"], info["classes"]
    deps: dict[str, list] = {name: [] for name in model.variables}
    raw = {}
    for name, d in model.variables.items():
        refs, inputs = references(d.expr)
        raw[name] = (refs, inputs)
        for ref, lag in refs:
            if ref in deps and name not in [x[0] for x in deps[ref]]:
                deps[ref].append([name, lag])
    out = []
    for name in order:
        d = model.variables[name]
        refs, inputs = raw[name]
        out.append({
            "name": name, "formula": strip_parens(d.expr.formula()), "doc": d.doc, "init": d.init,
            "refs": sorted([list(r) for r in refs]), "inputs": sorted(inputs),
            "used_by": sorted(deps[name]), "cls": classes[name],
            "total": d.total, "pv": d.policy_sum,
            "tables": sorted({t for t in _tables_in(d.expr)}),
        })
    return out


def _tables_in(expr):
    from ..dsl import TableLookup
    seen, stack, out = set(), [expr], []
    while stack:
        e = stack.pop()
        if id(e) in seen:
            continue
        seen.add(id(e))
        if isinstance(e, TableLookup):
            out.append(e.name)
        stack.extend(e.children())
    return out


def table_json(name: str, tb: Table, *, editable: bool, description: str = "", modified: bool = False) -> dict:
    dims = []
    for d, n in zip(tb.dims, tb.values.shape):
        if d[0] == "range":
            dims.append({"kind": "range", "start": d[1], "labels": [str(int(d[1]) + i) for i in range(n)]})
        else:
            dims.append({"kind": "categories", "labels": list(d[1])})
    return clean({"name": name, "description": description, "shape": list(tb.values.shape), "dims": dims,
                  "values": tb.values.tolist(), "fill": tb.fill, "editable": editable, "modified": modified})


def read_csv_columns(path: Path) -> dict[str, np.ndarray]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def worst_rel(a, b) -> float:
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b)) / np.maximum(1.0, np.abs(np.asarray(b)))))


def kpi(label, value, unit="", note="", fmt="number"):
    return {"label": label, "value": value, "unit": unit, "note": note, "format": fmt}


# ---- the entries ------------------------------------------------------------------------------

@dataclass
class ModelEntry:
    id: str
    name: str
    tagline: str
    description: str
    source: str                       # e.g. "lifelib BasicTerm (MIT)" or "Illustrative"
    currency: str
    table_info: dict[str, dict]       # name -> {"description", "editable"}
    data_columns: list[dict]          # columns shown in the policy grid
    run_options: list[dict]           # options shown before a run
    _model: Model | None = None
    _data: dict | None = None
    overrides: dict[str, Table] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    # subclasses implement these
    def build(self) -> Model: ...
    def load_rows(self) -> dict[str, np.ndarray]: ...
    def base_tables(self) -> dict[str, Table]: ...
    def run(self, options: dict, progress: Callable) -> dict: ...
    def explain(self, policy: int, life: int, options: dict) -> dict: ...
    def validate(self) -> list[dict]: ...
    def policy_label(self, rows: dict, i: int) -> str: ...

    # shared
    @property
    def model(self) -> Model:
        if self._model is None:
            self._model = self.build()
        return self._model

    @property
    def rows(self) -> dict[str, np.ndarray]:
        if self._data is None:
            self._data = self.load_rows()
        return self._data

    def tables(self) -> dict[str, Table]:
        return {**self.base_tables(), **self.overrides}

    def summary(self) -> dict:
        rows = self.rows
        first = next(iter(rows.values()))
        return {"id": self.id, "name": self.name, "tagline": self.tagline, "source": self.source,
                "policies": self.n_policies(), "rows": int(len(first)), "steps": self.model.n_steps,
                "variables": len(self.model.variables), "lives": self.model.lives,
                "modified_tables": sorted(self.overrides)}

    def n_policies(self) -> int:
        return int(len(next(iter(self.rows.values()))))

    def detail(self) -> dict:
        return clean({**self.summary(), "description": self.description, "currency": self.currency,
                      "variables_spec": variable_spec(self.model),
                      "tables": [{"name": n, "description": self.table_info.get(n, {}).get("description", ""),
                                  "editable": self.table_info.get(n, {}).get("editable", False),
                                  "shape": list(t.values.shape), "modified": n in self.overrides}
                                 for n, t in self.tables().items()],
                      "data_columns": self.data_columns, "run_options": self.run_options})

    def table(self, name: str) -> dict:
        t = self.tables()[name]
        info = self.table_info.get(name, {})
        return table_json(name, t, editable=info.get("editable", False),
                          description=info.get("description", ""), modified=name in self.overrides)

    def set_table(self, name: str, values) -> dict:
        info = self.table_info.get(name, {})
        if not info.get("editable"):
            raise ValueError(f"table {name} is not editable")
        base = self.base_tables()[name]
        arr = np.asarray(values, dtype=float)
        if arr.shape != base.values.shape:
            raise ValueError(f"expected shape {base.values.shape}, got {arr.shape}")
        if not np.isfinite(arr).all():
            raise ValueError("all values must be numbers")
        if np.array_equal(arr, base.values):
            self.overrides.pop(name, None)
        else:
            t = Table(arr)
            t.dims, t.fill = base.dims, base.fill
            self.overrides[name] = t
        return self.table(name)

    def reset_tables(self):
        self.overrides.clear()

    def data_page(self, offset: int, limit: int, search: str = "") -> dict:
        rows = self.rows
        n = self.n_policies()
        idx = np.arange(n)
        if search:
            s = search.strip().lower()
            keys = [c["key"] for c in self.data_columns]
            mask = np.zeros(n, dtype=bool)
            for k in keys:
                col = rows[k]
                if col.dtype.kind in ("U", "S", "O"):
                    mask |= np.char.find(np.char.lower(col.astype(str)), s) >= 0
                else:
                    try:
                        mask |= col == float(s)
                    except ValueError:
                        pass
            idx = idx[mask]
        page = idx[offset:offset + limit]
        out = []
        for i in page:
            r = {"_row": int(i)}
            for c in self.data_columns:
                v = rows[c["key"]][i]
                r[c["key"]] = str(v) if isinstance(v, (str, np.str_)) else float(v)
            out.append(r)
        return clean({"total": int(len(idx)), "offset": offset, "rows": out})

    def data_stats(self) -> list[dict]:
        rows = self.rows
        out = []
        for c in self.data_columns:
            col = rows[c["key"]]
            if col.dtype.kind in ("U", "S", "O"):
                vals, counts = np.unique(col.astype(str), return_counts=True)
                order = np.argsort(-counts)[:8]
                out.append({"key": c["key"], "label": c["label"], "kind": "text",
                            "top": [[str(vals[i]), int(counts[i])] for i in order]})
            else:
                hist, edges = np.histogram(col, bins=24)
                out.append({"key": c["key"], "label": c["label"], "kind": "number",
                            "min": float(col.min()), "max": float(col.max()), "mean": float(col.mean()),
                            "hist": hist.tolist(), "edges": edges.tolist()})
        return clean(out)


def _trace_payload(tr, steps: int, label: str, extra: dict | None = None) -> dict:
    return clean({"label": label, "inputs": tr.inputs, "steps": steps,
                  "values": {k: v[:steps] for k, v in tr.values.items()}, **(extra or {})})


# ---- 1. lifelib BasicTerm ----------------------------------------------------------------------

class TermEntry(ModelEntry):
    def build(self):
        return bt.build(20)

    def load_rows(self):
        return bt.load_model_points()

    def base_tables(self):
        return bt.load_tables()

    def policy_label(self, rows, i):
        return (f"Policy {int(rows['point_id'][i])} · {rows['sex'][i]}, age {int(rows['age_at_entry'][i])} · "
                f"{int(rows['policy_term'][i])}-year term · SA {int(rows['sum_assured'][i]):,}")

    def run(self, options, progress):
        progress(0.1, "Pricing pass")
        res = bt.run_basicterm(self.rows, self.tables())
        progress(0.9, "Collecting results")
        p = res.projection
        ps = {k: float(v.sum()) for k, v in p.policy_sums.items()}
        series = {k: p.totals[k][0] for k in ["premiums", "claims", "expenses", "commissions", "net_cf", "pols_if"]}
        prem = ps["pv_premiums"]
        return {
            "kpis": [kpi("PV of net cash flow", ps["pv_net_cf"], self.currency, "portfolio, at the valuation date"),
                     kpi("PV of premiums", prem, self.currency),
                     kpi("Claims ratio (PV)", ps["pv_claims"] / prem, "", "PV claims ÷ PV premiums", "percent"),
                     kpi("Average premium", float(np.mean(res.premium_pp)), self.currency, "per policy per month")],
            "pv_table": [{"label": lab, "value": ps[k], "share": ps[k] / prem} for lab, k in
                         [("Premiums", "pv_premiums"), ("Claims", "pv_claims"), ("Expenses", "pv_expenses"),
                          ("Commissions", "pv_commissions"), ("Net cash flow", "pv_net_cf")]],
            "series": {k: {"values": v, "label": k.replace("_", " ")} for k, v in series.items()},
            "series_unit": "month",
            "seconds": res.seconds,
            "policies": self.n_policies(),
        }

    def explain(self, policy, life, options):
        rows = self.rows
        one = {k: v[policy:policy + 1] for k, v in rows.items()}
        priced = bt.run_basicterm(one, self.tables())
        one["premium_pp"] = priced.premium_pp
        tr = mr_runner.trace(self.model, one, self.tables())
        return _trace_payload(tr, self.model.n_steps, self.policy_label(rows, policy))

    def validate(self):
        res = bt.run_basicterm(self.rows, bt.load_tables())
        ref = read_csv_columns(VALIDATION / "lifelib_basicterm" / "lifelib_M_per_policy.csv")
        cf = read_csv_columns(VALIDATION / "lifelib_basicterm" / "lifelib_M_cashflows.csv")
        meta = json.loads((VALIDATION / "lifelib_basicterm" / "meta.json").read_text())
        p = res.projection
        checks = [{"name": "Premium per policy", "detail": "rounded to the cent, all 10,000 policies",
                   "metric": f"{int(np.sum(res.premium_pp == ref['premium_pp'])):,} of {len(ref['premium_pp']):,} identical",
                   "passed": bool(np.array_equal(res.premium_pp, ref["premium_pp"]))}]
        for k, lab in [("pv_premiums", "PV of premiums"), ("pv_claims", "PV of claims"), ("pv_expenses", "PV of expenses"),
                       ("pv_commissions", "PV of commissions"), ("pv_net_cf", "PV of net cash flow")]:
            w = worst_rel(p.policy_sums[k][0], ref[k])
            checks.append({"name": lab, "detail": "per policy, worst relative difference",
                           "metric": f"{w:.1e}", "passed": w < 1e-11})
        w = max(worst_rel(p.totals[k][0], cf[k]) for k in ["premiums", "claims", "expenses", "commissions", "net_cf"])
        checks.append({"name": "Monthly portfolio cash flows", "detail": f"5 series × {meta['n_steps']} months",
                       "metric": f"{w:.1e}", "passed": w < 1e-12})
        total = float(p.policy_sums["pv_net_cf"].sum())
        checks.append({"name": "Portfolio PV of net cash flow", "detail": "Meridian vs lifelib",
                       "metric": f"{total:,.6f} vs {meta['portfolio_pv_net_cf']:,.6f}",
                       "passed": abs(total - meta["portfolio_pv_net_cf"]) <= 1e-6 * abs(total)})
        sample = [{"policy": int(ref["point_id"][i]), "meridian": float(p.policy_sums["pv_net_cf"][0][i]),
                   "reference": float(ref["pv_net_cf"][i])} for i in range(8)]
        return clean([{"title": f"lifelib {meta['lifelib_version']} BasicTerm, policy by policy",
                       "reference": "lifelib (open-source, MIT), run unchanged", "checks": checks, "sample": sample,
                       "sample_label": "PV of net cash flow"}])


# ---- 2. lifelib CashValue ---------------------------------------------------------------------

class SavingsEntry(ModelEntry):
    def build(self):
        tables = cv.load_tables()
        last = cv.mort_table_last_age(tables)
        return cv.build(cv.projection_length(self.rows, tables, last), last_age=last)

    def load_rows(self):
        return cv.load_model_points()

    def base_tables(self):
        return cv.load_tables()

    def policy_label(self, rows, i):
        names = {"A": "single-premium endowment", "B": "single premium + surrender charge",
                 "C": "level-premium whole life", "D": "level-premium whole life + surrender charge"}
        return (f"Policy {int(rows['policy_id'][i])} · product {rows['spec_id'][i]} ({names[rows['spec_id'][i]]}) · "
                f"age {int(rows['age_at_entry'][i])} · {int(rows['policy_count'][i])} policies")

    def run(self, options, progress):
        n = int(options.get("scenarios") or 0)
        progress(0.1, f"Projecting {'lifelib’s 10' if not n else n} scenarios")
        res = cv.run_cashvalue(self.rows, tables=self.overrides or None, generated_scenarios=n or None)
        progress(0.9, "Collecting results")
        pv = res.policy_sums["pv_net_cf"].sum(axis=1)
        srt = np.sort(pv)
        k = max(1, int(np.ceil(0.3 * len(srt))))
        series = {k2: res.totals[k2].mean(axis=0) for k2 in
                  ["premiums", "claims", "inv_income", "expenses", "commissions", "net_cf", "pols_if"]}
        means = {k2: float(v.sum(axis=1).mean()) for k2, v in res.policy_sums.items()}
        prem = means["pv_premiums"]
        return {
            "kpis": [kpi("Mean PV of net cash flow", float(pv.mean()), self.currency, f"over {len(pv)} scenarios"),
                     kpi("CTE70", float(srt[:k].mean()), self.currency, "mean of the worst 30%"),
                     kpi("Worst scenario", float(srt[0]), self.currency),
                     kpi("Best scenario", float(srt[-1]), self.currency)],
            "pv_table": [{"label": lab, "value": means[k2], "share": means[k2] / prem} for lab, k2 in
                         [("Premiums", "pv_premiums"), ("Investment income", "pv_inv_income"),
                          ("Death claims", "pv_claims_death"), ("Surrenders", "pv_claims_lapse"),
                          ("Maturities", "pv_claims_maturity"), ("Expenses", "pv_expenses"),
                          ("Commissions", "pv_commissions"), ("Change in account value", "pv_av_change"),
                          ("Net cash flow", "pv_net_cf")]],
            "scenarios": pv,
            "series": {k2: {"values": v, "label": k2.replace("_", " ") + " (scenario mean)"} for k2, v in series.items()},
            "series_unit": "month",
            "seconds": res.seconds,
            "policies": self.n_policies(),
        }

    def explain(self, policy, life, options):
        rows = self.rows
        tables = self.tables()
        last = cv.mort_table_last_age(tables)
        one = {k: v[policy:policy + 1] for k, v in rows.items()}
        n = cv.projection_length(one, tables, last)
        model = cv.build(n, last_age=last)
        tr = mr_runner.trace(model, one, tables, cv.load_scenarios(n, [1]))
        return _trace_payload(tr, min(n, 600), self.policy_label(rows, policy) + " · scenario 1")

    def validate(self):
        out = []
        for label, mpfile, ref_file, scen, title in [
                ("portfolio", "model_point_10000.csv", "portfolio.npz", None, "new business, 10,000 policies × 10 scenarios"),
                ("inforce", "model_point_inforce_1000.csv", "inforce.npz", [1, 2, 3], "in force, 1,000 policies × 3 scenarios")]:
            ref = np.load(VALIDATION / "lifelib_cashvalue" / ref_file)
            meta = json.loads((VALIDATION / "lifelib_cashvalue" / "meta.json").read_text())[label]
            res = cv.run_cashvalue(cv.load_model_points(mpfile), scenarios=scen)
            gross = ["pv_premiums", "pv_inv_income", "pv_claims_death", "pv_claims_lapse", "pv_claims_maturity",
                     "pv_expenses", "pv_commissions", "pv_av_change"]
            checks = []
            for k in gross:
                w = worst_rel(res.policy_sums[k], ref[k])
                checks.append({"name": k.replace("pv_", "PV of ").replace("_", " "),
                               "detail": "every policy × scenario, worst relative difference",
                               "metric": f"{w:.1e}", "passed": w < 1e-12})
            g = sum(np.abs(ref[k]) for k in gross)
            w = float((np.abs(res.policy_sums["pv_net_cf"] - ref["pv_net_cf"]) / np.maximum(g, 1)).max())
            checks.append({"name": "PV of net cash flow", "detail": "relative to gross flows", "metric": f"{w:.1e}",
                           "passed": w < 1e-13})
            ours = res.policy_sums["pv_net_cf"].sum(axis=1)
            sample = [{"policy": f"scenario {s + 1}", "meridian": float(ours[s]),
                       "reference": float(meta["pv_net_cf_by_scenario"][s])} for s in range(len(ours))]
            out.append({"title": f"lifelib CashValue_ME, {title}", "reference": "lifelib (open-source, MIT), run unchanged",
                        "checks": checks, "sample": sample, "sample_label": "Portfolio PV of net cash flow"})
        return clean(out)


# ---- 3. SA family funeral --------------------------------------------------------------------

class FuneralEntry(ModelEntry):
    N_POLICIES = 20_000

    def build(self):
        return fu.build()

    def load_rows(self):
        return fu.synthetic_lives(self.N_POLICIES)

    def base_tables(self):
        return fu.tables()

    @property
    def lanes(self):
        if getattr(self, "_lanes", None) is None:
            self._lanes = fu.model_points(self.rows)
            self._pids = list(dict.fromkeys(self.rows["policy_id"]))
        return self._lanes

    def n_policies(self):
        return int(len(self.rows["policy_id"]))  # rows = lives

    def summary(self):
        s = super().summary()
        s["policies"] = len(set(self.rows["policy_id"]))
        s["rows"] = int(len(self.rows["policy_id"]))
        return s

    def policy_label(self, rows, i):
        return (f"{rows['policy_id'][i]} · {rows['role'][i]} · {rows['sex'][i]}, age {int(rows['age'][i])} · "
                f"cover R{int(rows['cover'][i]):,}")

    def run(self, options, progress):
        overrides = {k: v for k, v in self.overrides.items() if k != "basis"}

        def step(done, total, name):
            progress(0.05 + 0.9 * done / total, f"Basis {done} of {total}: {name.replace('_', ' ')}")

        r = fu.value(self.lanes, overrides=overrides, progress=step)
        b = r.base
        prem = float(b.policy_sums["pv_premiums"].sum())
        series = {k: b.totals[k][0] for k in ["premiums", "claims", "expenses", "commission", "net_outgo", "policies_if", "deaths"]}
        return {
            "kpis": [kpi("Best-estimate liability", r.bel["base"], self.currency, "negative = future profit"),
                     kpi("SCR life", r.scr["life"], self.currency, "after diversification"),
                     kpi("Risk margin", r.risk_margin, self.currency, "6% cost of capital"),
                     kpi("Technical provisions", r.technical_provisions, self.currency, "BEL + risk margin")],
            "pv_table": [{"label": "Premiums", "value": prem, "share": 1.0},
                         {"label": "Claims", "value": float(b.policy_sums["pv_claims"].sum()),
                          "share": float(b.policy_sums["pv_claims"].sum()) / prem},
                         {"label": "BEL (outgo less premiums)", "value": r.bel["base"], "share": r.bel["base"] / prem}],
            "sam": {"bel": r.bel, "scr": r.scr, "risk_margin": r.risk_margin, "tp": r.technical_provisions,
                    "labels": fu.STRESS_LABELS, "projected_scr": r.projected_scr[:40]},
            "series": {k: {"values": v, "label": k.replace("_", " ")} for k, v in series.items()},
            "series_unit": "month",
            "seconds": r.seconds,
            "policies": len(self._pids),
        }

    def explain(self, policy, life, options):
        # `policy` is a row (life) index in the admin data; find its policy and slot.
        rows = self.rows
        pid = rows["policy_id"][policy]
        p = self._pids.index(pid) if getattr(self, "_pids", None) else list(dict.fromkeys(rows["policy_id"])).index(pid)
        members = np.where(rows["policy_id"] == pid)[0]
        slot = int(np.where(members == policy)[0][0])
        _ = self.lanes
        tr = mr_runner.trace(self.model, self.lanes, {k: v for k, v in self.tables().items()}, policy=p, life=slot)
        family = [{"row": int(i), "label": f"{rows['role'][i]} · {rows['sex'][i]}, {int(rows['age'][i])}"} for i in members]
        return _trace_payload(tr, 360, self.policy_label(rows, policy), {"family": family})

    def validate(self):
        import sys
        tests_dir = Path(__file__).resolve().parents[3] / "tests"
        rows = fu.synthetic_lives(40, seed=5)
        mp = fu.model_points(rows)
        pids = list(dict.fromkeys(rows["policy_id"]))
        checks, sample = [], []
        try:
            sys.path.insert(0, str(tests_dir))
            import independent_funeral as ind  # available in the source checkout
        except ImportError:
            ind = None
        for basis in fu.BASES:
            res = mr_runner.run(fu.build(), mp, fu.tables(basis))
            ours = res.policy_sums["bel"][0].reshape(-1, fu.LIVES).sum(axis=1)
            if ind is not None:
                ref = np.array([ind.check_policy(rows, pid, basis) for pid in pids])
                w = worst_rel(ours, ref)
                checks.append({"name": f"BEL per policy, {basis.replace('_', ' ')} basis",
                               "detail": f"{len(pids)} policies vs independent loop implementation",
                               "metric": f"{w:.1e}", "passed": w < 1e-11})
                if basis == "base":
                    sample = [{"policy": pids[i], "meridian": float(ours[i]), "reference": float(ref[i])} for i in range(8)]
        ref_np = mr_runner.run(fu.build(10), mp, fu.tables(), engine="numpy")
        ours_np = mr_runner.run(fu.build(10), mp, fu.tables())
        w = max(worst_rel(ours_np.policy_sums[k], ref_np.policy_sums[k]) for k in ours_np.policy_sums)
        checks.append({"name": "Rust engine vs NumPy reference engine", "detail": "per life, all present values",
                       "metric": f"{w:.1e}", "passed": w < 1e-11})
        return clean([{"title": "Independent implementation and reference engine",
                       "reference": "plain-Python loops written from the product description; NumPy reference engine",
                       "checks": checks, "sample": sample, "sample_label": "BEL per policy (base)"}])


def make_catalog() -> dict[str, ModelEntry]:
    entries = [
        TermEntry(
            id="term", name="Term assurance", tagline="lifelib BasicTerm · 10,000 policies · monthly over 20 years",
            description=("Level term assurance with select-and-ultimate mortality, duration-based lapses, inflating "
                         "expenses and first-year commission. The premium is 150% of the net premium, so each run "
                         "prices first and then projects. Rebuilt from the open-source lifelib BasicTerm model and "
                         "reconciled to it policy by policy."),
            source="lifelib BasicTerm (MIT)", currency="",
            table_info={"mort_table": {"description": "Annual mortality rate by attained age and duration (select 5 years)", "editable": True},
                        "disc_rate_ann": {"description": "Annual discount (zero-spot) rate by projection year", "editable": True}},
            data_columns=[{"key": "point_id", "label": "Policy", "kind": "id"}, {"key": "sex", "label": "Sex"},
                          {"key": "age_at_entry", "label": "Age at entry"}, {"key": "policy_term", "label": "Term (years)"},
                          {"key": "sum_assured", "label": "Sum assured", "kind": "money"}],
            run_options=[],
        ),
        SavingsEntry(
            id="savings", name="Savings with account value",
            tagline="lifelib CashValue_ME · stochastic · 10,000 policies · up to 1,141 months",
            description=("A universal-life style savings product: account value with fees and cost of insurance, "
                         "single or level premiums, surrender charges by product, whole life to age 115, and "
                         "stochastic fund returns. All scenarios run in one pass. Rebuilt from lifelib CashValue_ME "
                         "and reconciled per policy and per scenario."),
            source="lifelib CashValue_ME (MIT)", currency="",
            table_info={"mort_table": {"description": "Annual mortality rate by attained age and duration (0 outside the table)", "editable": True},
                        "surr_charge": {"description": "Surrender charge rate by product and duration", "editable": True},
                        "load_prem_rate": {"description": "Premium loading by product", "editable": True},
                        "disc_rate_ann": {"description": "Annual discount (zero-spot) rate by projection year", "editable": True},
                        "is_wl": {"description": "Whole life (1) or term (0), by product"},
                        "single_premium": {"description": "Single premium (1) or level premium (0), by product"},
                        "has_surr_charge": {"description": "Surrender charge applies (1) or not (0), by product"}},
            data_columns=[{"key": "policy_id", "label": "Policy", "kind": "id"}, {"key": "spec_id", "label": "Product"},
                          {"key": "sex", "label": "Sex"}, {"key": "age_at_entry", "label": "Age at entry"},
                          {"key": "policy_count", "label": "Policies"}, {"key": "sum_assured", "label": "Sum assured", "kind": "money"},
                          {"key": "premium_pp", "label": "Premium", "kind": "money"}],
            run_options=[{"key": "scenarios", "label": "Scenarios", "kind": "choice",
                          "choices": [[0, "lifelib’s 10 scenarios"], [100, "100 generated"], [500, "500 generated"]], "default": 0}],
        ),
        FuneralEntry(
            id="funeral", name="Family funeral (SAM)",
            tagline="South Africa · up to 8 lives per policy · BEL, SCR and risk margin",
            description=("Family funeral cover: main member, spouse, children to age 21 and extended family, each "
                         "with their own cover and premium. The policy ends on lapse or the main member's death. "
                         "Valued on a SAM-style basis: best-estimate liability, six stresses, the life SCR after "
                         "correlation and a 6% cost-of-capital risk margin. Assumptions are illustrative."),
            source="Illustrative assumptions", currency="R",
            table_info={"mortality": {"description": "Annual mortality by sex and age (illustrative, not an ASSA table)", "editable": True},
                        "role_loading": {"description": "Mortality loading by role", "editable": True},
                        "lapse": {"description": "Annual lapse rate by policy year (last value thereafter)", "editable": True},
                        "spot": {"description": "Nominal risk-free spot rate by year", "editable": True},
                        "basis": {"description": "Base assumption set; each SAM stress is its own set"}},
            data_columns=[{"key": "policy_id", "label": "Policy", "kind": "id"}, {"key": "role", "label": "Role"},
                          {"key": "sex", "label": "Sex"}, {"key": "age", "label": "Age"},
                          {"key": "cover", "label": "Cover", "kind": "money"}, {"key": "premium", "label": "Premium", "kind": "money"},
                          {"key": "duration_mth", "label": "Duration (months)"}],
            run_options=[],
        ),
    ]
    return {e.id: e for e in entries}


__all__ = ["make_catalog", "ModelEntry", "clean"]
_ = time  # keep import for callers that time runs
