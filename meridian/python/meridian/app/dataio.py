"""Policy data in and out of the app: CSV import with column matching and row-by-row checks,
CSV export, and templates.

Each model describes its input in a *schema*: one :class:`Field` per column the model reads.
Importing is two steps so nothing changes until the user has seen the result:

1. :func:`check_csv` parses the file, matches its headings to the schema (ignoring case,
   spaces and punctuation, and allowing common alternative names), checks every value and
   returns a report: matched and missing columns, errors with their spreadsheet row, a preview
   and the parsed columns.
2. The caller replaces the model's data with the parsed columns only if the report is clean.

Files from Excel in South Africa often use ``;`` between fields and a decimal comma; both
forms are accepted, as are thousands separators written with spaces and an ``R`` prefix.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

import numpy as np

MAX_ERRORS = 200


@dataclass
class Field:
    key: str
    label: str
    kind: str = "number"                 # "number", "integer" or "text"
    description: str = ""
    choices: list[str] | None = None     # allowed text values
    min: float | None = None
    max: float | None = None
    aliases: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "kind": self.kind, "description": self.description,
                "choices": self.choices, "min": self.min, "max": self.max}


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_columns(headers: list[str], schema: list[Field]) -> tuple[dict[str, int], list[str], list[str]]:
    """Map schema keys to header positions. Returns (matched, missing keys, unused headers)."""
    pos = {}
    for i, h in enumerate(headers):
        pos.setdefault(_norm(h), i)
    matched = {}
    for f in schema:
        for cand in [f.key, f.label, *f.aliases]:
            i = pos.get(_norm(cand))
            if i is not None and i not in matched.values():
                matched[f.key] = i
                break
    missing = [f.key for f in schema if f.key not in matched]
    used = set(matched.values())
    unused = [h for i, h in enumerate(headers) if i not in used and h.strip()]
    return matched, missing, unused


def _sniff(text: str) -> str:
    first = text.split("\n", 1)[0]
    counts = {d: first.count(d) for d in [",", ";", "\t", "|"]}
    return max(counts, key=counts.get) if max(counts.values()) else ","


def _number(raw: str, decimal_comma: bool) -> float:
    s = raw.strip().replace(" ", "").replace(" ", "")
    if s[:1] in ("R", "r") and len(s) > 1:
        s = s[1:]
    if decimal_comma:
        s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 else s.replace(",", "")
    else:
        s = s.replace(",", "")
    v = float(s)
    if not np.isfinite(v):
        raise ValueError
    return v


def check_csv(text: str, schema: list[Field], group_check=None) -> dict:
    """Parse and check a CSV against a schema. ``group_check(columns)`` may add whole-file
    errors (e.g. "policy X has no main member"). Returns a JSON-ready report; when it has no
    errors, ``report["columns"]`` holds the parsed numpy columns (removed before sending)."""
    text = text.lstrip("﻿")
    if not text.strip():
        return {"ok": False, "fatal": "The file is empty."}
    delim = _sniff(text)
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(c.strip() for c in r)]
    if len(rows) < 2:
        return {"ok": False, "fatal": "The file has a heading row but no data rows."}
    headers = [h.strip() for h in rows[0]]
    body = rows[1:]
    matched, missing, unused = match_columns(headers, schema)
    report = {"ok": False, "delimiter": delim, "rows": len(body), "headers": headers,
              "matched": [{"key": k, "label": f.label, "column": headers[matched[k]]}
                          for f in schema for k in [f.key] if k in matched],
              "missing": [{"key": f.key, "label": f.label, "description": f.description}
                          for f in schema if f.key in missing],
              "unused": unused, "errors": [], "error_count": 0, "error_summary": {}}
    if missing:
        report["fatal"] = "Some columns the model needs are not in the file."
        return report

    decimal_comma = delim == ";"
    errors = []
    counts: dict[str, int] = {}

    def err(row_no, f: Field | None, value, msg):
        key = f.label if f else "File"
        counts[key] = counts.get(key, 0) + 1
        if len(errors) < MAX_ERRORS:
            errors.append({"row": row_no, "column": f.label if f else "", "value": value, "message": msg})

    cols: dict[str, list] = {f.key: [] for f in schema}
    for n, r in enumerate(body):
        row_no = n + 2  # spreadsheet row: heading is row 1
        for f in schema:
            i = matched[f.key]
            raw = r[i].strip() if i < len(r) else ""
            if raw == "":
                err(row_no, f, raw, "is empty")
                cols[f.key].append(None)
                continue
            if f.kind == "text":
                v = raw
                if f.choices:
                    hit = next((c for c in f.choices if c.lower() == raw.lower()), None)
                    if hit is None:
                        err(row_no, f, raw, f"must be one of {', '.join(f.choices)}")
                    v = hit or raw
                cols[f.key].append(v)
                continue
            try:
                v = _number(raw, decimal_comma)
            except ValueError:
                err(row_no, f, raw, "is not a number")
                cols[f.key].append(None)
                continue
            if f.kind == "integer" and v != int(v):
                err(row_no, f, raw, "must be a whole number")
            if f.min is not None and v < f.min:
                err(row_no, f, raw, f"must be at least {f.min:g}")
            if f.max is not None and v > f.max:
                err(row_no, f, raw, f"must be at most {f.max:g}")
            cols[f.key].append(v)

    cell_errors = bool(counts)
    columns = {f.key: (np.array(["" if v is None else v for v in cols[f.key]]) if f.kind == "text"
                       else np.array([np.nan if v is None else v for v in cols[f.key]], dtype=float))
               for f in schema}
    if group_check:
        # Whole-policy rules run even when some cells are wrong, so every problem shows at once.
        # A rule that cannot be evaluated because of a bad cell is skipped until the cell is fixed.
        try:
            found = group_check(columns)
        except (KeyError, ValueError, TypeError):
            found = []
        for row_no, label, value, msg in found:
            f = next((x for x in schema if x.label == label), None)
            err(row_no, f, value, msg)
    if not counts and not cell_errors:
        report["columns"] = columns
    report["errors"] = errors
    report["error_count"] = sum(counts.values())
    report["error_summary"] = counts
    report["ok"] = not counts
    report["preview"] = [{f.key: (r[matched[f.key]].strip() if matched[f.key] < len(r) else "") for f in schema}
                         for r in body[:8]]
    return report


def to_csv(columns: dict[str, np.ndarray], schema: list[Field], limit: int | None = None) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow([f.key for f in schema])
    n = len(next(iter(columns.values())))
    for i in range(n if limit is None else min(n, limit)):
        row = []
        for f in schema:
            v = columns[f.key][i]
            if f.kind == "text":
                row.append(str(v))
            elif f.kind == "integer" or float(v) == int(v):
                row.append(str(int(v)))
            else:
                row.append(repr(float(v)))
        w.writerow(row)
    return out.getvalue()


def funeral_group_check(columns: dict) -> list[tuple]:
    """Whole-policy rules for family funeral data: at most 8 lives and exactly one main member."""
    out = []
    pid, role = columns["policy_id"], columns["role"]
    first_row: dict[str, int] = {}
    lives: dict[str, int] = {}
    mains: dict[str, int] = {}
    for i, (p, r) in enumerate(zip(pid, role)):
        first_row.setdefault(p, i + 2)
        lives[p] = lives.get(p, 0) + 1
        mains[p] = mains.get(p, 0) + (r == "main")
    for p in first_row:
        if lives[p] > 8:
            out.append((first_row[p], "Policy", p, f"has {lives[p]} lives; a policy covers at most 8"))
        if mains[p] != 1:
            out.append((first_row[p], "Policy", p,
                        "has no main member" if mains[p] == 0 else f"has {mains[p]} main members; it needs exactly one"))
    return out
