"""End-to-end check of the packaged app: start Meridian.exe as a headless service, run every
model and every validation through the same API the window uses, and fail on any error.

    python packaging/check_frozen.py dist/Meridian/Meridian.exe
"""

import json
import os
import tempfile
import socket
import subprocess
import sys
import time
import urllib.request


def call(url, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def wait_for(fn, timeout=600):
    end = time.time() + timeout
    while time.time() < end:
        r = fn()
        if r["status"] in ("done", "failed"):
            return r
        time.sleep(0.5)
    raise TimeoutError


def main(exe):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    home = tempfile.mkdtemp(prefix="meridian-check-")
    proc = subprocess.Popen([exe, "--headless", "--port", str(port)], env={**os.environ, "MERIDIAN_HOME": home})
    failures = 0
    try:
        for _ in range(240):
            try:
                call(base + "/api/health")
                break
            except OSError:
                time.sleep(0.25)
        else:
            raise SystemExit("service did not start")
        html = urllib.request.urlopen(base + "/", timeout=10).read().decode()
        assert "<div id=\"root\">" in html or "id=\"root\"" in html, "interface files missing"
        models = [m["id"] for m in call(base + "/api/workspace")]
        print("models:", ", ".join(models))
        for mid in models:
            run = call(f"{base}/api/models/{mid}/runs", "POST", {"options": {}})
            r = wait_for(lambda: call(f"{base}/api/runs/{run['id']}"))
            ok = r["status"] == "done"
            failures += not ok
            print(f"  run        {mid:<10} {r['status']:<7} {r.get('error') or ''}")
            call(f"{base}/api/models/{mid}/validation", "POST")
            v = wait_for(lambda: call(f"{base}/api/models/{mid}/validation"))
            checks = [c for g in (v["result"] or []) for c in g["checks"]] if v["status"] == "done" else []
            passed = bool(checks) and all(c["passed"] for c in checks)
            failures += not passed
            print(f"  validation {mid:<10} {'passed' if passed else 'FAILED'} ({len(checks)} checks) {v.get('error') or ''}")
            lever = call(f"{base}/api/models/{mid}")["levers"][0]
            run = call(f"{base}/api/models/{mid}/runs", "POST", {"options": {"levers": {lever["key"]: lever["step"]}}})
            w = wait_for(lambda: call(f"{base}/api/runs/{run['id']}"))
            ok = w["status"] == "done" and w["kpis"] != r["kpis"]
            failures += not ok
            print(f"  what-if    {mid:<10} {'done' if ok else 'FAILED'}  {w['label']}")

        # policy data: export, import a slice back, run on it, restore
        text = urllib.request.urlopen(base + "/api/models/funeral/data/export.csv", timeout=60).read().decode()
        lines = text.splitlines()
        cut = next(i for i in range(400, len(lines)) if lines[i].split(",")[0] != lines[i - 1].split(",")[0])
        rep = call(base + "/api/models/funeral/data/import", "POST",
                   {"csv": "\n".join(lines[:cut]), "name": "check.csv", "apply": True})
        run = call(f"{base}/api/models/funeral/runs", "POST", {"options": {}})
        r = wait_for(lambda: call(f"{base}/api/runs/{run['id']}"))
        call(base + "/api/models/funeral/data/reset", "POST")
        ok = rep.get("applied") and r["status"] == "done" and r["data"] == "check.csv"
        failures += not ok
        print(f"  import     funeral    {'done' if ok else 'FAILED'}  {cut - 1} lives imported and run")

        s1 = call(base + "/api/settings", "PUT", {"tour_done": True})
        ok = s1["tour_done"] is True and os.path.exists(os.path.join(home, "settings.json"))
        failures += not ok
        print(f"  settings   {'saved' if ok else 'FAILED'}")
    finally:
        proc.terminate()
    print("FROZEN CHECK", "PASSED" if not failures else f"FAILED ({failures})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    import os
    main(os.path.abspath(sys.argv[1]))
