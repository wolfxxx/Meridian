"""The modelling language: Python expressions traced into the Meridian IR.

A model is written as decorated Python functions. Each function is called once, at
definition time, and the expression it returns is recorded (traced); Python ``if`` /
loops are therefore not allowed on model values — use :func:`where` instead.

    m = Model("term", n_steps=240)
    v, mp, tb = m.v, m.mp, m.tables

    @m.var(init=0.0)
    def pols_if():
        return where(t == 0, mp.policy_count, v.pols_if.lag(1) - v.deaths.lag(1))

    @m.var(total=True)
    def deaths():
        return v.pols_if * tb.mort_qx[mp.age]

References to variables always go through ``m.v.<name>`` (so definition order does not
matter); ``.lag(k)`` refers to the value ``k`` steps earlier.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Union

from .tables import category_code

Number = Union[int, float]


class Expr:
    """A traced expression node. Combine with arithmetic / comparison operators."""

    __hash__ = object.__hash__  # identity hash; structural equality is via _key()

    # --- arithmetic -----------------------------------------------------------------
    def __add__(self, o): return Binary("add", self, as_expr(o))
    def __radd__(self, o): return Binary("add", as_expr(o), self)
    def __sub__(self, o): return Binary("sub", self, as_expr(o))
    def __rsub__(self, o): return Binary("sub", as_expr(o), self)
    def __mul__(self, o): return Binary("mul", self, as_expr(o))
    def __rmul__(self, o): return Binary("mul", as_expr(o), self)
    def __truediv__(self, o): return Binary("div", self, as_expr(o))
    def __rtruediv__(self, o): return Binary("div", as_expr(o), self)
    def __pow__(self, o): return Binary("pow", self, as_expr(o))
    def __rpow__(self, o): return Binary("pow", as_expr(o), self)
    def __neg__(self): return Unary("neg", self)
    def __abs__(self): return Unary("abs", self)

    # --- comparisons (return 1.0 / 0.0) -----------------------------------------------
    def __lt__(self, o): return Binary("lt", self, as_expr(o))
    def __le__(self, o): return Binary("le", self, as_expr(o))
    def __gt__(self, o): return Binary("gt", self, as_expr(o))
    def __ge__(self, o): return Binary("ge", self, as_expr(o))
    def __eq__(self, o): return Binary("eq", self, as_expr(o))  # type: ignore[override]
    def __ne__(self, o): return Binary("ne", self, as_expr(o))  # type: ignore[override]
    def __and__(self, o): return Binary("and", self, as_expr(o))
    def __rand__(self, o): return Binary("and", as_expr(o), self)
    def __or__(self, o): return Binary("or", self, as_expr(o))
    def __ror__(self, o): return Binary("or", as_expr(o), self)

    def __bool__(self):
        raise TypeError(
            "Model expressions have no Python truth value (they are traced, not computed). "
            "Use where(cond, a, b) instead of `if`, and & / | instead of `and` / `or`."
        )

    # --- serialisation hooks ---------------------------------------------------------
    def _emit(self, emit: Callable[["Expr"], int]) -> dict:  # pragma: no cover
        raise NotImplementedError

    def children(self) -> tuple["Expr", ...]:
        return ()

    def formula(self) -> str:  # pragma: no cover
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Expr {self.formula()}>"


def as_expr(x) -> Expr:
    if isinstance(x, Expr):
        return x
    if isinstance(x, bool):
        return Const(1.0 if x else 0.0)
    if isinstance(x, (int, float)):
        return Const(float(x))
    if isinstance(x, str):
        return Category(x)
    raise TypeError(f"cannot use {type(x).__name__} in a model expression")


def _fmt_num(x: float) -> str:
    return repr(int(x)) if float(x).is_integer() and abs(x) < 1e15 else repr(x)


class Const(Expr):
    def __init__(self, value: float):
        self.value = float(value)

    def _emit(self, emit):
        return {"op": "const", "value": self.value}

    def formula(self):
        return _fmt_num(self.value)


class Category(Const):
    """A text label in a formula (e.g. ``mp.sex == "F"``); compiled to its category code."""

    def __init__(self, label: str):
        super().__init__(category_code(label))
        self.label = label

    def formula(self):
        return repr(self.label)


class _Time(Expr):
    def _emit(self, emit):
        return {"op": "time"}

    def formula(self):
        return "t"


#: The projection time index (0-based; months for a monthly model).
t = _Time()


class Input(Expr):
    def __init__(self, name: str):
        self.name = name

    def _emit(self, emit):
        return {"op": "input", "name": self.name}

    def formula(self):
        return f"mp.{self.name}"


class VarRef(Expr):
    def __init__(self, name: str, lag: int = 0):
        if lag < 0:
            raise ValueError("lag must be >= 0 (references to the future are not supported)")
        self.name = name
        self.lag_ = int(lag)

    def lag(self, k: int = 1) -> "VarRef":
        """Value ``k`` time steps earlier (the variable's ``init`` before the projection)."""
        return VarRef(self.name, self.lag_ + int(k))

    def _emit(self, emit):
        return {"op": "var", "name": self.name, "lag": self.lag_}

    def formula(self):
        return f"{self.name}[t-{self.lag_}]" if self.lag_ else self.name


class TableLookup(Expr):
    def __init__(self, name: str, keys: tuple[Expr, ...]):
        self.name = name
        self.keys = keys

    def children(self):
        return self.keys

    def _emit(self, emit):
        return {"op": "table", "name": self.name, "indices": [emit(k) for k in self.keys]}

    def formula(self):
        return f"{self.name}[{', '.join(k.formula() for k in self.keys)}]"


class ScenarioRef(Expr):
    def __init__(self, name: str):
        self.name = name

    def _emit(self, emit):
        return {"op": "scenario", "name": self.name}

    def formula(self):
        return f"scen.{self.name}"


class Unary(Expr):
    def __init__(self, func: str, a: Expr):
        self.func, self.a = func, a

    def children(self):
        return (self.a,)

    def _emit(self, emit):
        return {"op": "unary", "func": self.func, "a": emit(self.a)}

    def formula(self):
        if self.func == "neg":
            return f"-({self.a.formula()})"
        return f"{self.func}({self.a.formula()})"


_BIN_SYMBOL = {
    "add": "+", "sub": "-", "mul": "*", "div": "/", "pow": "**",
    "lt": "<", "le": "<=", "gt": ">", "ge": ">=", "eq": "==", "ne": "!=",
    "and": "&", "or": "|",
}


class Binary(Expr):
    def __init__(self, func: str, a: Expr, b: Expr):
        self.func, self.a, self.b = func, a, b

    def children(self):
        return (self.a, self.b)

    def _emit(self, emit):
        return {"op": "binary", "func": self.func, "a": emit(self.a), "b": emit(self.b)}

    def formula(self):
        if self.func in ("min", "max"):
            return f"{self.func}({self.a.formula()}, {self.b.formula()})"
        return f"({self.a.formula()} {_BIN_SYMBOL[self.func]} {self.b.formula()})"


class Select(Expr):
    def __init__(self, cond: Expr, a: Expr, b: Expr):
        self.cond, self.a, self.b = cond, a, b

    def children(self):
        return (self.cond, self.a, self.b)

    def _emit(self, emit):
        return {"op": "select", "cond": emit(self.cond), "a": emit(self.a), "b": emit(self.b)}

    def formula(self):
        return f"where({self.cond.formula()}, {self.a.formula()}, {self.b.formula()})"


class SumPolicies(Expr):
    def __init__(self, a: Expr):
        self.a = a

    def children(self):
        return (self.a,)

    def _emit(self, emit):
        return {"op": "sum_policies", "a": emit(self.a)}

    def formula(self):
        return f"sum_policies({self.a.formula()})"


# --- public helper functions ----------------------------------------------------------

def where(cond, a, b) -> Expr:
    """Element-wise ``a if cond else b`` (both branches are evaluated)."""
    return Select(as_expr(cond), as_expr(a), as_expr(b))


def minimum(a, b) -> Expr:
    return Binary("min", as_expr(a), as_expr(b))


def maximum(a, b) -> Expr:
    return Binary("max", as_expr(a), as_expr(b))


def clip(x, lo, hi) -> Expr:
    return minimum(maximum(x, lo), hi)


def floor(x) -> Expr:
    return Unary("floor", as_expr(x))


def exp(x) -> Expr:
    return Unary("exp", as_expr(x))


def log(x) -> Expr:
    return Unary("ln", as_expr(x))


def sqrt(x) -> Expr:
    return Unary("sqrt", as_expr(x))


def sum_policies(x) -> Expr:
    """Sum of ``x`` over all policies of the same scenario, at the current time step.

    Using this makes a model *C2* (aggregate feedback, spec section 19.4): the engine
    computes the total for every policy before evaluating anything that depends on it.
    """
    return SumPolicies(as_expr(x))


# --- namespaces ---------------------------------------------------------------------------

class _VarNamespace:
    def __init__(self, model: "Model"):
        object.__setattr__(self, "_model", model)

    def __getattr__(self, name: str) -> VarRef:
        if name.startswith("_"):
            raise AttributeError(name)
        return VarRef(name)


class _InputNamespace:
    def __getattr__(self, name: str) -> Input:
        if name.startswith("_"):
            raise AttributeError(name)
        return Input(name)


class _Table:
    def __init__(self, name: str):
        self.name = name

    def __getitem__(self, key) -> TableLookup:
        keys = key if isinstance(key, tuple) else (key,)
        return TableLookup(self.name, tuple(as_expr(k) for k in keys))


class _TableNamespace:
    def __getattr__(self, name: str) -> _Table:
        if name.startswith("_"):
            raise AttributeError(name)
        return _Table(name)


class _ScenarioNamespace:
    def __getattr__(self, name: str) -> ScenarioRef:
        if name.startswith("_"):
            raise AttributeError(name)
        return ScenarioRef(name)


@dataclass
class VarDef:
    name: str
    expr: Expr
    init: float = 0.0
    doc: str = ""
    total: bool = False
    policy_sum: bool = False


@dataclass
class Model:
    """A projection model: named variables traced from decorated Python functions."""

    name: str
    n_steps: int
    variables: dict[str, VarDef] = field(default_factory=dict)

    def __post_init__(self):
        if self.n_steps < 1:
            raise ValueError("n_steps must be at least 1")
        self.v = _VarNamespace(self)
        self.mp = _InputNamespace()
        self.tables = _TableNamespace()
        self.scen = _ScenarioNamespace()

    def var(self, fn: Callable[[], object] | None = None, *, init: Number = 0.0,
            total: bool = False, policy_sum: bool = False):
        """Define a variable from a zero-argument function returning an expression.

        ``init``: value seen by lagged references before the projection start.
        ``total``: report the sum over policies for every time step.
        ``policy_sum``: report the sum over time for every policy (e.g. a present value).
        """
        def deco(f):
            name = f.__name__
            if name in self.variables:
                raise ValueError(f"variable `{name}` is already defined")
            expr = as_expr(f())
            self.variables[name] = VarDef(
                name, expr, float(init), (f.__doc__ or "").strip(), total, policy_sum
            )
            return VarRef(name)
        return deco(fn) if fn is not None else deco

    # --- IR -------------------------------------------------------------------------------
    def to_ir(self) -> dict:
        nodes: list[dict] = []
        memo: dict[str, int] = {}

        def emit(e: Expr) -> int:
            node = e._emit(emit)
            key = json.dumps(node, sort_keys=True)
            idx = memo.get(key)
            if idx is None:
                idx = len(nodes)
                nodes.append(node)
                memo[key] = idx
            return idx

        variables = [
            {"name": d.name, "expr": emit(d.expr), "init": d.init}
            for d in self.variables.values()
        ]
        return {
            "name": self.name,
            "n_steps": self.n_steps,
            "nodes": nodes,
            "variables": variables,
            "outputs": {
                "totals": [d.name for d in self.variables.values() if d.total],
                "policy_sums": [d.name for d in self.variables.values() if d.policy_sum],
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_ir())

    def formula(self, name: str) -> str:
        return self.variables[name].expr.formula()

    def describe(self) -> str:
        """Human-readable listing of every variable and its formula."""
        lines = [f"Model {self.name!r}: {len(self.variables)} variables, {self.n_steps} steps"]
        for d in self.variables.values():
            flags = ",".join(f for f, on in (("total", d.total), ("policy_sum", d.policy_sum)) if on)
            lines.append(f"  {d.name}{f' [{flags}]' if flags else ''} = {d.expr.formula()}")
        return "\n".join(lines)


def references(expr: Expr) -> tuple[list[tuple[str, int]], list[str]]:
    """Variables (name, lag) and model-point inputs referenced directly by an expression."""
    vars_, inputs, seen = [], [], set()
    stack = [expr]
    while stack:
        e = stack.pop()
        if id(e) in seen:
            continue
        seen.add(id(e))
        if isinstance(e, VarRef):
            if (e.name, e.lag_) not in vars_:
                vars_.append((e.name, e.lag_))
        elif isinstance(e, Input):
            if e.name not in inputs:
                inputs.append(e.name)
        stack.extend(e.children())
    return vars_, inputs
