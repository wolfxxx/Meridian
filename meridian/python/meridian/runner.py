"""Running models and tracing single policies."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .dsl import Model, references
from .reference import run_reference
from .tables import Table, as_table, encode_column

try:
    from . import _engine  # the compiled Rust extension
except ImportError:  # pragma: no cover - only when the extension has not been built
    _engine = None


@dataclass
class Results:
    """Projection results.

    * ``totals[var]``: shape ``(n_scenarios, n_steps)``, summed over policies.
    * ``policy_sums[var]``: shape ``(n_scenarios, n_policies)``, summed over time.
    * ``history[var]``: shape ``(n_steps, n_scenarios, n_policies)`` (only with keep_history).
    """

    model: str
    engine: str
    strategy: str
    n_steps: int
    n_policies: int
    n_scenarios: int
    seconds: float
    order: list[str]
    totals: dict[str, np.ndarray] = field(default_factory=dict)
    policy_sums: dict[str, np.ndarray] = field(default_factory=dict)
    history: dict[str, np.ndarray] = field(default_factory=dict)


def _prepare(model: Model, model_points: dict, tables: dict | None, scenarios: dict | None):
    if not model_points:
        raise ValueError("model_points must contain at least one column")
    mp = {k: encode_column(v) for k, v in model_points.items()}
    lengths = {k: a.shape for k, a in mp.items()}
    n_pol = next(iter(mp.values())).shape[0]
    if any(a.ndim != 1 or a.shape[0] != n_pol for a in mp.values()):
        raise ValueError(f"model-point columns must be 1-D and equal length, got {lengths}")
    tb = {k: as_table(v) for k, v in (tables or {}).items()}
    sc = {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in (scenarios or {}).items()}
    n_scen = 1
    if sc:
        shapes = {k: a.shape for k, a in sc.items()}
        n_scen = next(iter(sc.values())).shape[0]
        if any(a.ndim != 2 or a.shape != (n_scen, model.n_steps) for a in sc.values()):
            raise ValueError(
                f"scenario paths must have shape (n_scenarios, n_steps={model.n_steps}), got {shapes}"
            )
    return mp, tb, sc, n_pol, n_scen


def run(model: Model, model_points: dict, tables: dict | None = None,
        scenarios: dict | None = None, *, engine: str = "rust",
        keep_history: bool = False, chunk_size: int = 2048, strategy: str = "auto") -> Results:
    """Run ``model`` on the given data with the Rust engine (default) or the NumPy reference.

    ``strategy`` (Rust only): ``"auto"`` runs C1 models per chunk (each chunk of policies goes
    through all time steps independently) and C2 models in lockstep; ``"lockstep"`` forces
    lockstep. Results are bit-identical either way.
    """
    mp, tb, sc, n_pol, n_scen = _prepare(model, model_points, tables, scenarios)
    ir_json = model.to_json()
    start = time.perf_counter()
    if engine == "rust":
        if _engine is None:
            raise RuntimeError("Rust extension not built: run `maturin develop --release` in meridian/")
        raw = _engine.run(ir_json, mp, {k: v.flat_values() for k, v in tb.items()}, sc, n_pol,
                          n_scen, keep_history, chunk_size, strategy,
                          table_dims={k: v.engine_dims() for k, v in tb.items()})
        seconds = time.perf_counter() - start
        steps = model.n_steps
        totals = {k: v.reshape(n_scen, steps) for k, v in raw["totals"].items()}
        psums = {k: v.reshape(n_scen, n_pol) for k, v in raw["policy_sums"].items()}
        history = {k: v.reshape(steps, n_scen, n_pol) for k, v in raw["history"].items()}
        order = list(raw["order"])
        used = str(raw["strategy"])
    elif engine == "numpy":
        raw = run_reference(model.to_ir(), mp, tb, sc, n_pol, n_scen, keep_history)
        seconds = time.perf_counter() - start
        totals, psums, history, order = raw["totals"], raw["policy_sums"], raw["history"], raw["order"]
        used = "reference"
    else:
        raise ValueError("engine must be 'rust' or 'numpy'")
    return Results(model.name, engine, used, model.n_steps, n_pol, n_scen, seconds, order,
                   totals, psums, history)


def inspect(model: Model) -> dict:
    """Evaluation order, dependency classes (C1/C2) and required inputs, from the Rust compiler."""
    if _engine is None:
        raise RuntimeError("Rust extension not built: run `maturin develop --release` in meridian/")
    return dict(_engine.inspect(model.to_json()))


@dataclass
class Trace:
    """Every variable's value over time for one policy in one scenario (spec DX-3)."""

    model: Model
    policy: int
    scenario: int
    values: dict[str, np.ndarray]  # var -> (n_steps,)
    inputs: dict[str, float]

    def table(self, variables: list[str] | None = None, steps=range(0, 13)) -> str:
        names = variables or list(self.model.variables)
        steps = list(steps)
        width = max(len(n) for n in names) + 2
        head = "t".rjust(width) + "".join(f"{s:>14d}" for s in steps)
        rows = [head]
        for n in names:
            rows.append(n.rjust(width) + "".join(f"{self.values[n][s]:>14.6g}" for s in steps))
        return "\n".join(rows)

    def explain(self, name: str, step: int) -> str:
        """Formula of ``name`` with the values of everything it references at ``step``."""
        d = self.model.variables[name]
        refs, inputs = references(d.expr)
        lines = [f"{name}[t={step}] = {self.values[name][step]:.10g}",
                 f"  formula: {d.expr.formula()}"]
        if d.doc:
            lines.append(f"  doc: {d.doc}")
        for ref, lag in sorted(refs):
            s = step - lag
            val = self.values[ref][s] if s >= 0 else self.model.variables[ref].init
            label = f"{ref}[t-{lag}]" if lag else ref
            lines.append(f"  {label:<24} = {val:.10g}" + ("   (init)" if s < 0 else ""))
        for inp in sorted(inputs):
            val = self.inputs[inp]
            shown = repr(val) if isinstance(val, str) else f"{val:.10g}"
            lines.append(f"  mp.{inp:<21} = {shown}")
        return "\n".join(lines)


def trace(model: Model, model_points: dict, tables: dict | None = None,
          scenarios: dict | None = None, *, policy: int = 0, scenario: int = 0) -> Trace:
    """Re-run a single policy/scenario with full history kept, for explanation.

    Valid for C1 models. For C2 models a single policy cannot reproduce the portfolio
    aggregates, so the full portfolio is run with history and the requested lane extracted.
    """
    info = inspect(model)
    is_c2 = any(c == "C2" for c in info["classes"].values())
    mp_all = {k: encode_column(v) for k, v in model_points.items()}
    text_inputs = {k: v for k, v in model_points.items() if np.asarray(v).dtype.kind in ("U", "S", "O")}
    if is_c2:
        res = run(model, mp_all, tables, scenarios, keep_history=True)
        values = {k: v[:, scenario, policy].copy() for k, v in res.history.items()}
    else:
        mp_one = {k: v[policy:policy + 1] for k, v in mp_all.items()}
        sc_one = {k: np.asarray(v)[scenario:scenario + 1] for k, v in (scenarios or {}).items()}
        res = run(model, mp_one, tables, sc_one, keep_history=True)
        values = {k: v[:, 0, 0].copy() for k, v in res.history.items()}
    inputs = {k: (str(np.asarray(text_inputs[k])[policy]) if k in text_inputs else float(v[policy]))
              for k, v in mp_all.items()}
    return Trace(model, policy, scenario, values, inputs)
