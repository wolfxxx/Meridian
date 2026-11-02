"""Independent pure-NumPy implementation of the IR semantics.

This is the reconciliation baseline for the Rust engine (spec section 31.1, "independent
implementation"): it is written separately, keeps full histories and favours clarity over
speed. Results should agree with the Rust engine to ~1e-12 relative.
"""

from __future__ import annotations

import numpy as np

from .tables import as_table

_UNARY = {
    "neg": np.negative,
    "abs": np.abs,
    "exp": np.exp,
    "ln": np.log,
    "floor": np.floor,
    "sqrt": np.sqrt,
}

_BINARY = {
    "add": np.add,
    "sub": np.subtract,
    "mul": np.multiply,
    "div": np.divide,
    "pow": np.power,
    "min": np.fmin,  # NaN-ignoring, matching Rust f64::min
    "max": np.fmax,
    "lt": lambda a, b: (a < b).astype(float),
    "le": lambda a, b: (a <= b).astype(float),
    "gt": lambda a, b: (a > b).astype(float),
    "ge": lambda a, b: (a >= b).astype(float),
    "eq": lambda a, b: (a == b).astype(float),
    "ne": lambda a, b: (a != b).astype(float),
    "and": lambda a, b: ((a != 0) & (b != 0)).astype(float),
    "or": lambda a, b: ((a != 0) | (b != 0)).astype(float),
}


def _order(ir: dict) -> list[int]:
    """Evaluation order from same-time (lag 0) references, declaration order first."""
    nodes, variables = ir["nodes"], ir["variables"]
    index = {v["name"]: i for i, v in enumerate(variables)}

    def deps(root: int) -> set[int]:
        out, stack, seen = set(), [root], set()
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            n = nodes[i]
            if n["op"] == "var":
                if n["name"] not in index:
                    raise ValueError(f"unknown variable `{n['name']}`")
                if n.get("lag", 0) == 0:
                    out.add(index[n["name"]])
            for key in ("a", "b", "cond"):
                if key in n:
                    stack.append(n[key])
            stack.extend(n.get("indices", []))
        return out

    dep = [deps(v["expr"]) for v in variables]
    order, state = [], [0] * len(variables)  # 0 new, 1 active, 2 done

    def visit(v: int, path: list[int]):
        if state[v] == 2:
            return
        if state[v] == 1:
            names = [variables[i]["name"] for i in path[path.index(v):]] + [variables[v]["name"]]
            raise ValueError("circular dependency: " + " -> ".join(names))
        state[v] = 1
        for d in sorted(dep[v]):
            visit(d, path + [v])
        state[v] = 2
        order.append(v)

    for v in range(len(variables)):
        visit(v, [])
    return order


def run_reference(ir: dict, model_points: dict, tables: dict, scenarios: dict,
                  n_policies: int, n_scenarios: int = 1, keep_history: bool = False) -> dict:
    nodes, variables, n_steps = ir["nodes"], ir["variables"], ir["n_steps"]
    lanes = n_policies * n_scenarios
    pol = np.arange(lanes) % n_policies
    scen = np.arange(lanes) // n_policies
    init = {v["name"]: float(v.get("init", 0.0)) for v in variables}
    k_lives = int(ir.get("lives", 1))
    if n_policies % k_lives:
        raise ValueError(f"lanes ({n_policies}) must be a multiple of lives per policy ({k_lives})")
    hist = {v["name"]: np.empty((n_steps, lanes)) for v in variables}
    order = _order(ir)

    def evaluate(i: int, t: int, cache: dict) -> np.ndarray:
        if i in cache:
            return cache[i]
        n = nodes[i]
        op = n["op"]
        if op == "const":
            r = np.full(lanes, float(n["value"]))
        elif op == "time":
            r = np.full(lanes, float(t))
        elif op == "input":
            r = np.asarray(model_points[n["name"]], dtype=float)[pol]
        elif op == "var":
            lag = n.get("lag", 0)
            r = np.full(lanes, init[n["name"]]) if t < lag else hist[n["name"]][t - lag]
        elif op == "table":
            tb = as_table(tables[n["name"]])
            r = tb.lookup([evaluate(k, t, cache) for k in n["indices"]])
        elif op == "scenario":
            r = np.asarray(scenarios[n["name"]], dtype=float)[scen, t]
        elif op == "unary":
            r = _UNARY[n["func"]](evaluate(n["a"], t, cache))
        elif op == "binary":
            r = _BINARY[n["func"]](evaluate(n["a"], t, cache), evaluate(n["b"], t, cache))
        elif op == "select":
            r = np.where(evaluate(n["cond"], t, cache) != 0,
                         evaluate(n["a"], t, cache), evaluate(n["b"], t, cache))
        elif op == "life":
            r = (np.arange(lanes) % k_lives).astype(float)
        elif op == "sum_lives":
            inner = evaluate(n["a"], t, cache).reshape(-1, k_lives)
            r = np.repeat(inner.sum(axis=1), k_lives)
        elif op == "sum_policies":
            inner = evaluate(n["a"], t, cache).reshape(n_scenarios, n_policies)
            r = inner.sum(axis=1)[scen]
        else:  # pragma: no cover
            raise ValueError(f"unknown op {op}")
        cache[i] = r
        return r

    for t in range(n_steps):
        cache: dict = {}  # node values are fixed within a time step once their deps exist
        for v in order:
            hist[variables[v]["name"]][t] = evaluate(variables[v]["expr"], t, cache)

    outs = ir.get("outputs", {})
    return {
        "totals": {name: hist[name].reshape(n_steps, n_scenarios, n_policies).sum(axis=2).T.copy()
                   for name in outs.get("totals", [])},
        "policy_sums": {name: hist[name].sum(axis=0).reshape(n_scenarios, n_policies)
                        for name in outs.get("policy_sums", [])},
        "history": ({name: h.reshape(n_steps, n_scenarios, n_policies) for name, h in hist.items()}
                    if keep_history else {}),
        "order": [variables[v]["name"] for v in order],
    }
