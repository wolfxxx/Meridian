"""End-to-end check of the packaged app: start Meridian.exe as a headless service, run every
model and every validation through the same API the window uses, and fail on any error.

    python packaging/check_frozen.py dist/Meridian/Meridian.exe
"""

import json
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
    proc = subprocess.Popen([exe, "--headless", "--port", str(port)])
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
    finally:
        proc.terminate()
    print("FROZEN CHECK", "PASSED" if not failures else f"FAILED ({failures})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    import os
    main(os.path.abspath(sys.argv[1]))
