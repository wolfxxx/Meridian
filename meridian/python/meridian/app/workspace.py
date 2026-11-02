"""Keeps the user's work between sessions: edited tables, edited formulas, imported policy data
and run history, under ``<settings home>/workspace``.

    workspace/<model>/tables.json      {"table": values, ...}
    workspace/<model>/formulas.json    {"variable": "formula text", ...}
    workspace/<model>/data.csv         imported policy data (as checked), + data.json {name, at}
    workspace/runs/<run id>.json       one finished run, results included

Everything is restored on start-up through the same checks the app uses, so a file that no
longer fits (for example after an update changes a model) is skipped and reported, never
trusted blindly. Writes go through a temporary file so a crash cannot leave half a file.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import settings

KEEP_RUNS_PER_MODEL = 40


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


class Workspace:
    def __init__(self, root: Path | None = None):
        self.root = root or settings.home() / "workspace"
        self.notes: list[str] = []      # what could not be restored, shown once in the app

    def _dir(self, model_id: str) -> Path:
        return self.root / model_id

    # ---- saving --------------------------------------------------------------------------
    def save_tables(self, e):
        p = self._dir(e.id) / "tables.json"
        if e.overrides:
            _write(p, json.dumps({n: t.values.tolist() for n, t in e.overrides.items()}))
        else:
            p.unlink(missing_ok=True)

    def save_formulas(self, e):
        p = self._dir(e.id) / "formulas.json"
        if e.formula_overrides:
            _write(p, json.dumps(e.formula_overrides, indent=2))
        else:
            p.unlink(missing_ok=True)

    def save_data(self, e):
        d = self._dir(e.id)
        if e.data_source:
            _write(d / "data.csv", e.export_csv())
            _write(d / "data.json", json.dumps(e.data_source))
        else:
            (d / "data.csv").unlink(missing_ok=True)
            (d / "data.json").unlink(missing_ok=True)

    def save_run(self, rec: dict):
        _write(self.root / "runs" / f"{rec['id']}.json", json.dumps(rec))

    def delete_run(self, run_id: str):
        (self.root / "runs" / f"{run_id}.json").unlink(missing_ok=True)

    def prune_runs(self, runs: dict[str, dict]) -> list[str]:
        """Keep the newest runs of each model; returns the ids removed."""
        gone = []
        by_model: dict[str, list[dict]] = {}
        for r in runs.values():
            by_model.setdefault(r["model"], []).append(r)
        for items in by_model.values():
            items.sort(key=lambda r: -r["started"])
            for r in items[KEEP_RUNS_PER_MODEL:]:
                gone.append(r["id"])
        for rid in gone:
            runs.pop(rid, None)
            self.delete_run(rid)
        return gone

    # ---- restoring -----------------------------------------------------------------------
    def restore(self, catalog: dict) -> dict[str, dict]:
        """Restore every model's saved state; returns the saved runs by id."""
        for e in catalog.values():
            d = self._dir(e.id)
            self._restore_data(e, d)
            self._restore_tables(e, d)
            self._restore_formulas(e, d)
        return self._restore_runs(catalog)

    def _restore_data(self, e, d: Path):
        if not (d / "data.csv").exists():
            return
        try:
            meta = json.loads((d / "data.json").read_text(encoding="utf-8"))
            report = e.check_import((d / "data.csv").read_text(encoding="utf-8"))
            if not report.get("ok"):
                raise ValueError(report.get("fatal") or f"{report.get('error_count')} problems")
            e.set_rows(report["columns"], meta.get("name", "imported.csv"))
            e.data_source["at"] = meta.get("at", e.data_source["at"])
        except Exception as exc:
            self.notes.append(f"{e.name}: your imported policy data could not be reloaded ({exc}); "
                              "the model's own data is used.")

    def _restore_tables(self, e, d: Path):
        if not (d / "tables.json").exists():
            return
        try:
            saved = json.loads((d / "tables.json").read_text(encoding="utf-8"))
        except ValueError:
            saved = {}
        for name, values in saved.items():
            try:
                e.set_table(name, values)
            except Exception as exc:
                self.notes.append(f"{e.name}: your edits to {name} could not be reloaded ({exc}).")

    def _restore_formulas(self, e, d: Path):
        if not (d / "formulas.json").exists():
            return
        try:
            saved = json.loads((d / "formulas.json").read_text(encoding="utf-8"))
        except ValueError:
            saved = {}
        for name, text in saved.items():
            try:
                e.set_formula(name, text)
            except Exception as exc:
                msg = getattr(exc, "message", None) or str(exc)
                self.notes.append(f"{e.name}: your formula for {name} could not be reloaded ({msg}).")

    def _restore_runs(self, catalog: dict) -> dict[str, dict]:
        runs = {}
        for p in sorted((self.root / "runs").glob("*.json")) if (self.root / "runs").exists() else []:
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if rec.get("model") not in catalog:
                continue
            if rec.get("status") in ("queued", "running"):
                rec.update(status="failed", error="Meridian was closed before this run finished.",
                           message="Run interrupted", finished=rec.get("finished") or time.time())
            rec["restored"] = True
            runs[rec["id"]] = rec
        self.prune_runs(runs)
        return runs
