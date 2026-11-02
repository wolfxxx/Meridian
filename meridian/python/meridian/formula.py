"""Read formulas typed by a user back into model expressions.

This is the inverse of :meth:`Expr.formula`: it accepts the notation the app displays,

    pols_if[t-1] * (1 - q_month[t-1])        a variable, one step earlier
    mort_table[mp.age_at_entry + duration, min(duration, 5)]    a table lookup
    where(t == 0, mp.policy_count, 0)        functions: where, min, max, clip, abs,
                                             floor, exp, ln (or log), sqrt,
                                             sum_lives, sum_policies
    mp.sum_assured, scen.std_norm_rand, t, life, 'F'

Text is parsed with Python's ``ast`` module (``mode="eval"``) and only the constructs above
are accepted; nothing in a formula is ever executed. Errors carry the column where they were
found so the editor can point at them.
"""

from __future__ import annotations

import ast
import difflib

from .dsl import (Binary, Category, Const, Expr, Model, ScenarioRef, Select, SumLives, SumPolicies,
                  TableLookup, Unary, VarRef, Input, life, t)


class FormulaError(ValueError):
    def __init__(self, message: str, col: int | None = None):
        super().__init__(message)
        self.message = message
        self.col = col


_BIN = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div", ast.Pow: "pow",
        ast.BitAnd: "and", ast.BitOr: "or"}
_CMP = {ast.Lt: "lt", ast.LtE: "le", ast.Gt: "gt", ast.GtE: "ge", ast.Eq: "eq", ast.NotEq: "ne"}
_UNARY_FUNCS = {"abs": "abs", "floor": "floor", "exp": "exp", "ln": "ln", "log": "ln", "sqrt": "sqrt"}
FUNCTIONS = ["where", "min", "max", "clip", "abs", "floor", "exp", "ln", "sqrt", "sum_lives", "sum_policies"]


class FormulaContext:
    """What a formula may refer to in one model."""

    def __init__(self, model: Model, tables, inputs, scenarios=()):
        self.variables = set(model.variables)
        self.tables = set(tables)
        self.inputs = set(inputs)
        self.scenarios = set(scenarios)
        self.lives = model.lives

    def names(self) -> list[str]:
        return sorted(self.variables | self.tables | set(FUNCTIONS) | {"t", "life", "mp", "scen"})


def parse_formula(text: str, ctx: FormulaContext) -> Expr:
    text = text.strip()
    if not text:
        raise FormulaError("The formula is empty.", 0)
    if len(text) > 5000:
        raise FormulaError("The formula is too long.")
    try:
        tree = ast.parse(text.replace("\n", " "), mode="eval")
    except SyntaxError as exc:
        col = (exc.offset or 1) - 1
        msg = exc.msg.replace("invalid syntax", "This is not a valid formula")
        if "was never closed" in msg or "unexpected EOF" in msg:
            msg = "A bracket is not closed."
        raise FormulaError(f"{msg[0].upper()}{msg[1:]}.".replace("..", "."), col) from None
    return _Reader(ctx).read(tree.body)


class _Reader:
    def __init__(self, ctx: FormulaContext):
        self.ctx = ctx

    def fail(self, node, msg):
        raise FormulaError(msg, getattr(node, "col_offset", None))

    def unknown(self, node, name, pool, what="name"):
        close = difflib.get_close_matches(name, sorted(pool), n=1, cutoff=0.7)
        hint = f" Did you mean {close[0]}?" if close else ""
        self.fail(node, f"There is no {what} called {name}.{hint}")

    def read(self, n) -> Expr:
        if isinstance(n, ast.BinOp):
            op = _BIN.get(type(n.op))
            if op is None:
                self.fail(n, f"The operator {type(n.op).__name__} is not available in formulas.")
            return Binary(op, self.read(n.left), self.read(n.right))
        if isinstance(n, ast.UnaryOp):
            if isinstance(n.op, ast.USub):
                if isinstance(n.operand, ast.Constant) and isinstance(n.operand.value, (int, float)) \
                        and not isinstance(n.operand.value, bool):
                    return Const(-float(n.operand.value))
                return Unary("neg", self.read(n.operand))
            if isinstance(n.op, ast.UAdd):
                return self.read(n.operand)
            self.fail(n, "Use 1 - x instead of 'not x'.")
        if isinstance(n, ast.Compare):
            if len(n.ops) != 1:
                self.fail(n, "Compare two things at a time, e.g. (a < b) & (b < c).")
            op = _CMP.get(type(n.ops[0]))
            if op is None:
                self.fail(n, "Only <, <=, >, >=, == and != comparisons are available.")
            return Binary(op, self.read(n.left), self.read(n.comparators[0]))
        if isinstance(n, ast.BoolOp):
            op = "and" if isinstance(n.op, ast.And) else "or"
            out = self.read(n.values[0])
            for v in n.values[1:]:
                out = Binary(op, out, self.read(v))
            return out
        if isinstance(n, ast.IfExp):
            self.fail(n, "Use where(condition, value if true, value if false).")
        if isinstance(n, ast.Constant):
            v = n.value
            if isinstance(v, bool):
                return Const(1.0 if v else 0.0)
            if isinstance(v, (int, float)):
                return Const(float(v))
            if isinstance(v, str):
                return Category(v)
            self.fail(n, "Only numbers and quoted text labels can be written directly.")
        if isinstance(n, ast.Name):
            return self.name(n)
        if isinstance(n, ast.Subscript):
            return self.subscript(n)
        if isinstance(n, ast.Attribute):
            return self.attribute(n)
        if isinstance(n, ast.Call):
            return self.call(n)
        self.fail(n, "This part of the formula is not understood.")

    def name(self, n: ast.Name) -> Expr:
        name = n.id
        if name == "t":
            return t
        if name == "life":
            if self.ctx.lives == 1:
                self.fail(n, "life is only available in models with several lives per policy.")
            return life
        if name in self.ctx.variables:
            return VarRef(name)
        if name in self.ctx.tables:
            self.fail(n, f"{name} is a table: look it up with {name}[key, ...].")  # pragma: no cover
        if name in FUNCTIONS:
            self.fail(n, f"{name} is a function: write {name}(...).")
        self.unknown(n, name, self.ctx.names())

    def lag_of(self, s) -> int | None:
        if isinstance(s, ast.Name) and s.id == "t":
            return 0
        if (isinstance(s, ast.BinOp) and isinstance(s.op, ast.Sub) and isinstance(s.left, ast.Name)
                and s.left.id == "t" and isinstance(s.right, ast.Constant) and isinstance(s.right.value, int)
                and s.right.value >= 1):
            return s.right.value
        return None

    def subscript(self, n: ast.Subscript) -> Expr:
        if not isinstance(n.value, ast.Name):
            self.fail(n, "Square brackets go after a variable or table name.")
        name, s = n.value.id, n.slice
        # A variable and a table may share a name: name[t-k] is the variable k steps earlier,
        # any other key is a table lookup.
        lag = self.lag_of(s) if name in self.ctx.variables else None
        if lag is not None:
            return VarRef(name, lag)
        if name in self.ctx.variables and name not in self.ctx.tables:
            self.fail(s, f"A variable can only be looked back in time: {name}[t-1] is the value one step earlier.")
        if name in self.ctx.tables:
            keys = s.elts if isinstance(s, ast.Tuple) else [s]
            if any(isinstance(k, ast.Slice) for k in keys):
                self.fail(s, "Table keys are values, not ranges.")
            return TableLookup(name, tuple(self.read(k) for k in keys))
        self.unknown(n.value, name, self.ctx.variables | self.ctx.tables, "variable or table")

    def attribute(self, n: ast.Attribute) -> Expr:
        if isinstance(n.value, ast.Name):
            ns, attr = n.value.id, n.attr
            if ns == "mp":
                if attr not in self.ctx.inputs:
                    self.unknown(n, attr, self.ctx.inputs, "policy data column")
                return Input(attr)
            if ns == "scen":
                if attr not in self.ctx.scenarios:
                    self.unknown(n, attr, self.ctx.scenarios, "scenario input")
                return ScenarioRef(attr)
            if ns == "v":
                if attr not in self.ctx.variables:
                    self.unknown(n, attr, self.ctx.variables, "variable")
                return VarRef(attr)
        self.fail(n, "Use mp.<column> for policy data and scen.<name> for scenario inputs.")

    def call(self, n: ast.Call) -> Expr:
        if n.keywords:
            self.fail(n, "Functions take plain arguments, without names.")
        f = n.func
        if isinstance(f, ast.Attribute) and f.attr == "lag":       # v.x.lag(k) style
            base = self.read(f.value)
            if not isinstance(base, VarRef) or base.lag_ or len(n.args) > 1:
                self.fail(n, "Use name[t-k] to look back k steps.")
            k = 1
            if n.args:
                a = n.args[0]
                if not (isinstance(a, ast.Constant) and isinstance(a.value, int) and a.value >= 1):
                    self.fail(a, "The lag must be a whole number of steps, at least 1.")
                k = a.value
            return VarRef(base.name, k)
        if not isinstance(f, ast.Name):
            self.fail(n, "Only the built-in functions can be called.")
        name, args = f.id, n.args

        def need(k):
            if len(args) != k:
                self.fail(n, f"{name} takes {k} value{'s' if k > 1 else ''}, not {len(args)}.")

        if name == "where":
            need(3)
            return Select(*(self.read(a) for a in args))
        if name in ("min", "max", "minimum", "maximum"):
            need(2)
            return Binary("min" if name.startswith("min") else "max", self.read(args[0]), self.read(args[1]))
        if name == "clip":
            need(3)
            x, lo, hi = (self.read(a) for a in args)
            return Binary("min", Binary("max", x, lo), hi)
        if name in _UNARY_FUNCS:
            need(1)
            return Unary(_UNARY_FUNCS[name], self.read(args[0]))
        if name == "sum_lives":
            need(1)
            if self.ctx.lives == 1:
                self.fail(n, "sum_lives is only available in models with several lives per policy.")
            return SumLives(self.read(args[0]))
        if name == "sum_policies":
            need(1)
            return SumPolicies(self.read(args[0]))
        if name in self.ctx.variables or name in self.ctx.tables:
            self.fail(n, f"{name} is not a function: use {name}[...] .")
        self.unknown(f, name, FUNCTIONS, "function")


def with_formulas(model: Model, edits: dict[str, Expr]) -> Model:
    """A copy of ``model`` with some variables' expressions replaced (the original is untouched)."""
    import copy
    from dataclasses import replace

    out = copy.copy(model)
    out.variables = {name: (replace(d, expr=edits[name]) if name in edits else d) for name, d in model.variables.items()}
    return out


__all__ = ["FormulaContext", "FormulaError", "parse_formula", "with_formulas", "FUNCTIONS"]
