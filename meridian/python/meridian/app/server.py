"""Local web service behind the Meridian app: a JSON API plus the built interface."""

from __future__ import annotations

import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .catalog import clean, make_catalog

STATIC = Path(__file__).resolve().parent / "static"


class TableEdit(BaseModel):
    values: list


class RunRequest(BaseModel):
    options: dict = {}
    label: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="Meridian", docs_url=None, redoc_url=None)
    catalog = make_catalog()
    runs: dict[str, dict] = {}
    validations: dict[str, dict] = {}
    pool = ThreadPoolExecutor(max_workers=2)
    runs_lock = threading.Lock()

    def entry(model_id: str):
        if model_id not in catalog:
            raise HTTPException(404, f"No model called {model_id}")
        return catalog[model_id]

    @app.get("/api/workspace")
    def workspace():
        out = []
        for e in catalog.values():
            s = e.summary()
            last = [r for r in runs.values() if r["model"] == e.id and r["status"] == "done"]
            s["last_run"] = _brief(max(last, key=lambda r: r["finished"])) if last else None
            out.append(s)
        return clean(out)

    @app.get("/api/models/{model_id}")
    def model_detail(model_id: str):
        return entry(model_id).detail()

    @app.get("/api/models/{model_id}/tables/{name}")
    def get_table(model_id: str, name: str):
        e = entry(model_id)
        if name not in e.tables():
            raise HTTPException(404, f"No table called {name}")
        return e.table(name)

    @app.put("/api/models/{model_id}/tables/{name}")
    def put_table(model_id: str, name: str, body: TableEdit):
        try:
            return entry(model_id).set_table(name, body.values)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/models/{model_id}/tables/reset")
    def reset_tables(model_id: str):
        entry(model_id).reset_tables()
        return {"ok": True}

    @app.get("/api/models/{model_id}/data")
    def data(model_id: str, offset: int = 0, limit: int = 100, search: str = ""):
        return entry(model_id).data_page(max(offset, 0), min(max(limit, 1), 500), search)

    @app.get("/api/models/{model_id}/data/stats")
    def data_stats(model_id: str):
        return entry(model_id).data_stats()

    @app.get("/api/models/{model_id}/explain")
    def explain(model_id: str, policy: int = 0, life: int = 0):
        e = entry(model_id)
        if not 0 <= policy < e.n_policies():
            raise HTTPException(400, "No such policy")
        try:
            return e.explain(policy, life, {})
        except Exception as exc:  # pragma: no cover - surfaced to the user
            traceback.print_exc()
            raise HTTPException(500, f"Could not explain this policy: {exc}") from exc

    # ---- runs ---------------------------------------------------------------------------------
    def _brief(r):
        return {k: r.get(k) for k in ["id", "model", "label", "status", "progress", "message",
                                      "started", "finished", "seconds", "error", "kpis", "modified_tables"]}

    @app.post("/api/models/{model_id}/runs")
    def start_run(model_id: str, body: RunRequest):
        e = entry(model_id)
        rid = uuid.uuid4().hex[:10]
        modified = sorted(e.overrides)
        label = body.label or ("What-if: " + ", ".join(modified) if modified else "Base run")
        rec = {"id": rid, "model": model_id, "label": label, "status": "queued", "progress": 0.0,
               "message": "Waiting to start", "started": time.time(), "finished": None, "seconds": None,
               "error": None, "result": None, "kpis": None, "options": body.options, "modified_tables": modified}
        with runs_lock:
            runs[rid] = rec

        def progress(frac, msg):
            rec["progress"], rec["message"] = float(frac), msg

        def job():
            rec["status"], rec["message"] = "running", "Starting"
            t0 = time.perf_counter()
            try:
                with e.lock:
                    result = e.run(body.options, progress)
                rec["result"] = clean(result)
                rec["kpis"] = rec["result"]["kpis"]
                rec["status"], rec["progress"], rec["message"] = "done", 1.0, "Finished"
            except Exception as exc:  # pragma: no cover - surfaced to the user
                traceback.print_exc()
                rec["status"], rec["error"], rec["message"] = "failed", str(exc), "Run failed"
            rec["finished"] = time.time()
            rec["seconds"] = time.perf_counter() - t0

        pool.submit(job)
        return _brief(rec)

    @app.get("/api/models/{model_id}/runs")
    def list_runs(model_id: str):
        items = [r for r in runs.values() if r["model"] == model_id]
        return clean([_brief(r) for r in sorted(items, key=lambda r: -r["started"])])

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, full: bool = True):
        if run_id not in runs:
            raise HTTPException(404, "No such run")
        r = runs[run_id]
        out = _brief(r)
        if full:
            out["result"] = r["result"]
        return clean(out)

    # ---- validation ---------------------------------------------------------------------------
    @app.post("/api/models/{model_id}/validation")
    def start_validation(model_id: str):
        e = entry(model_id)
        v = validations.get(model_id)
        if v and v["status"] in ("running", "done"):
            return v
        rec = {"status": "running", "result": None, "error": None, "started": time.time(), "seconds": None}
        validations[model_id] = rec

        def job():
            t0 = time.perf_counter()
            try:
                rec["result"] = e.validate()
                rec["status"] = "done"
            except Exception as exc:  # pragma: no cover
                traceback.print_exc()
                rec["status"], rec["error"] = "failed", str(exc)
            rec["seconds"] = time.perf_counter() - t0

        pool.submit(job)
        return rec

    @app.get("/api/models/{model_id}/validation")
    def get_validation(model_id: str):
        entry(model_id)
        return clean(validations.get(model_id) or {"status": "not_started"})

    @app.get("/api/health")
    def health():
        return {"ok": True}

    # ---- interface ------------------------------------------------------------------------------
    if STATIC.exists():
        app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

        @app.get("/{path:path}")
        def index(path: str):
            f = STATIC / path
            if path and f.is_file():
                return FileResponse(f)
            return FileResponse(STATIC / "index.html")
    else:
        @app.get("/")
        def missing():
            return JSONResponse({"error": "Interface not built. Run `npm run build` in meridian/ui."}, 503)

    return app
