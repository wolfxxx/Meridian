"""Reference models used by the examples, tests and benchmarks.

They are deliberately simple illustrations of the modelling style and of the two engine
dependency classes, not certified actuarial libraries:

* :mod:`term_life` — a C1 (policy-independent) monthly term assurance projection.
* :mod:`with_profits` — a C2 model where a company-level bonus rate, set from the
  aggregate asset/guarantee position, feeds back into every policy each month.
"""
