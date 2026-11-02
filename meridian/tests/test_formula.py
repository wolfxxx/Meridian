"""Formula text -> expression: round trip over every model, and clear errors."""

import json

import pytest

from meridian.dsl import ScenarioRef, TableLookup, references
from meridian.formula import FormulaContext, FormulaError, parse_formula, with_formulas
from meridian.models import lifelib_basicterm as bt
from meridian.models import lifelib_cashvalue as cv
from meridian.models import sa_funeral as fu


def walk(e, kind):
    seen, stack, out = set(), [e], set()
    while stack:
        x = stack.pop()
        if id(x) in seen:
            continue
        seen.add(id(x))
        if isinstance(x, kind):
            out.add(x.name)
        stack.extend(x.children())
    return out


def context(model):
    tables, inputs, scen = set(), set(), set()
    for d in model.variables.values():
        tables |= walk(d.expr, TableLookup)
        scen |= walk(d.expr, ScenarioRef)
        inputs |= set(references(d.expr)[1])
    return FormulaContext(model, tables, inputs, scen)


MODELS = {"term": lambda: bt.build(20), "savings": lambda: cv.build(120), "funeral": lambda: fu.build(10)}


@pytest.mark.parametrize("name", MODELS)
def test_every_formula_round_trips_to_the_same_engine_graph(name):
    m = MODELS[name]()
    ctx = context(m)
    parsed = {v: parse_formula(d.expr.formula(), ctx) for v, d in m.variables.items()}
    a = json.dumps(m.to_ir(), sort_keys=True)
    b = json.dumps(with_formulas(m, parsed).to_ir(), sort_keys=True)
    assert a == b


@pytest.fixture
def ctx():
    return context(fu.build(10))


@pytest.mark.parametrize("text,msg,col", [
    ("q_month[t-1] *", "not a valid formula", None),
    ("q_mnth * 2", "There is no name called q_mnth. Did you mean q_month?", 0),
    ("mp.agee + 1", "There is no policy data column called agee. Did you mean age?", 0),
    ("q_month[t+1]", "looked back in time", 8),
    ("where(t == 0, 1)", "where takes 3 values, not 2", 0),
    ("1 if t == 0 else 2", "Use where(", 0),
    ("__import__('os')", "There is no function called __import__", 0),
    ("q_month.real", "Use mp.<column>", 0),
    ("(q_month", "bracket is not closed", None),
    ("0 < t < 5", "Compare two things at a time", 0),
    ("mortality", "is a table", 0),
])
def test_errors_are_clear(ctx, text, msg, col):
    with pytest.raises(FormulaError) as e:
        parse_formula(text, ctx)
    assert msg in e.value.message
    if col is not None:
        assert e.value.col == col


def test_dsl_style_and_conveniences(ctx):
    e = parse_formula("v.policy_if.lag(2) * clip(mp.age, 0, 120) and log(2)", ctx)
    f = e.formula()
    assert "policy_if[t-2]" in f and "max(mp.age, 0)" in f and "ln(2)" in f
