"""Meridian prototype: a Python modelling language over a Rust vectorised actuarial engine.

See ``meridian/README.md`` and the product spec (``Prophet_Analysis_and_Competitor_Spec.md``).
"""

from .dsl import (
    Model,
    clip,
    exp,
    floor,
    log,
    maximum,
    minimum,
    sqrt,
    sum_policies,
    t,
    where,
)
from .runner import Results, Trace, inspect, run, trace
from .tables import Table, category_code

__all__ = [
    "Model", "Results", "Trace",
    "t", "where", "minimum", "maximum", "clip", "floor", "exp", "log", "sqrt", "sum_policies",
    "run", "inspect", "trace", "Table", "category_code",
]
__version__ = "0.1.0"
