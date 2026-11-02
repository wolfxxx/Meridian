# Data from lifelib (MIT License)

`model_point_10000.csv`, `product_spec_table.csv`, `surr_charge_table.csv`, `mort_table.csv`,
`disc_rate_ann.csv` and `std_norm_rand.csv` are copied unchanged, apart from conversion from `.xlsx` to
`.csv`, from the **CashValue_ME** model of the open-source [lifelib](https://lifelib.io) project
(library `savings`, version 0.17.2), by the lifelib Developers. `model_point_inforce_1000.csv` is
derived from the first 1,000 rows of `model_point_10000.csv` with random in-force durations and
account values (see `meridian/tools/make_lifelib_cashvalue_reference.py`).

lifelib's results for the same inputs are in `meridian/tests/data/lifelib_cashvalue/`. Meridian
is reconciled against them in `meridian/tests/test_lifelib_cashvalue.py`.

lifelib's licence, copied from the installed package's `LICENSE.txt`:

```
MIT License

Copyright (c) 2022 lifelib Developers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
