"""Start the Meridian app: a local service plus a native window.

    meridian            # or: python -m meridian.app, or the installed Meridian.exe
    meridian --browser  # open in the default browser instead of an app window

The window opens straight away on a short "starting" screen and switches to the app as soon
as the local service answers, so a double-click never looks unresponsive.
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

SPLASH = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{height:100%;margin:0;background:#f3f5f7;font-family:"Segoe UI",system-ui,sans-serif;color:#0f1a24}
@media (prefers-color-scheme: dark){html,body{background:#0c1217;color:#e3eaf0}}
.c{height:100%;display:grid;place-items:center}.b{display:grid;justify-items:center;gap:14px}
.t{font-size:22px;font-weight:600;letter-spacing:.01em}.s{font-size:13px;opacity:.65}
.bar{width:180px;height:4px;border-radius:4px;background:rgba(14,106,140,.18);overflow:hidden}
.bar i{display:block;width:40%;height:100%;background:#0e6a8c;border-radius:4px;animation:m 1.1s ease-in-out infinite}
@keyframes m{0%{transform:translateX(-100%)}100%{transform:translateX(260%)}}
</style></head><body><div class="c"><div class="b">
<svg width="56" height="56" viewBox="0 0 32 32"><circle cx="16" cy="16" r="12.5" fill="none" stroke="#0e6a8c" stroke-width="2.4"/>
<path d="M16 3.5c5.2 4 5.2 21 0 25" fill="none" stroke="#0e6a8c" stroke-width="2.4"/></svg>
<div class="t">Meridian</div><div class="bar"><i></i></div><div class="s">Starting the calculation engine…</div>
</div></div></body></html>"""


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(port: int):
    import uvicorn

    from .server import create_app
    # log_config=None: no console logging setup (the installed app has no console).
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning", log_config=None)


def _wait(url: str, timeout: float = 60.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except OSError:
            time.sleep(0.15)
    return False


def _native_window_ok() -> bool:
    """True when a modern native web view is available. On Windows that means the Edge WebView2
    runtime; without it pywebview would fall back to the retired IE engine, which cannot show
    the interface, so the browser is the better choice."""
    if sys.platform != "win32":
        return True
    try:
        from webview.platforms import winforms
    except Exception:
        return False
    return getattr(winforms, "renderer", "") == "edgechromium"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="meridian", description="Meridian actuarial modelling")
    ap.add_argument("--browser", action="store_true", help="open in the default browser")
    ap.add_argument("--port", type=int, default=0, help="port for the local service (default: any free port)")
    ap.add_argument("--headless", action="store_true", help="only run the service (for testing)")
    ap.add_argument("--smoke-test", action="store_true", help="open the window, check the app loads, then close")
    a = ap.parse_args(argv)

    port = a.port or _free_port()
    url = f"http://127.0.0.1:{port}"
    if a.headless:
        _serve(port)
        return
    threading.Thread(target=_serve, args=(port,), daemon=True).start()

    if not a.browser:
        try:
            import webview
            native = _native_window_ok()
        except Exception as exc:  # no native web view: fall back to the browser
            print(f"Opening in your browser ({exc})")
            native = False
        if native:
            window = webview.create_window("Meridian", html=SPLASH, width=1440, height=920,
                                           min_size=(1100, 720), background_color="#F3F5F7")
            result = {"ok": None}

            def boot():
                if not _wait(url):
                    window.load_html(SPLASH.replace("Starting the calculation engine…",
                                                    "The calculation engine did not start. Please restart Meridian."))
                    result["ok"] = False
                    return
                window.load_url(url)
                if a.smoke_test:
                    # Wait for the interface to render its workspace, then close.
                    for _ in range(100):
                        time.sleep(0.2)
                        try:
                            n = window.evaluate_js("document.querySelectorAll('.model-card').length")
                        except Exception:
                            n = 0
                        if n:
                            result["ok"] = int(n) == 3
                            break
                    else:
                        result["ok"] = False
                    window.destroy()

            webview.start(boot)
            if a.smoke_test:
                print("SMOKE TEST", "PASSED" if result["ok"] else "FAILED")
                sys.exit(0 if result["ok"] else 1)
            return

    if not _wait(url):
        raise SystemExit("The Meridian service did not start.")
    webbrowser.open(url)
    print(f"Meridian is running at {url} — press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
