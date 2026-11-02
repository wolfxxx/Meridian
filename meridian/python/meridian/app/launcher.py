"""Start the Meridian app: a local service plus a native window.

    meridian            # or: python -m meridian.app
    meridian --browser  # open in the default browser instead of an app window
"""

from __future__ import annotations

import argparse
import socket
import threading
import time
import urllib.request
import webbrowser


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(port: int):
    import uvicorn

    from .server import create_app
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")


def _wait(url: str, timeout: float = 30.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except OSError:
            time.sleep(0.15)
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(prog="meridian", description="Meridian actuarial modelling")
    ap.add_argument("--browser", action="store_true", help="open in the default browser")
    ap.add_argument("--port", type=int, default=0, help="port for the local service (default: any free port)")
    ap.add_argument("--headless", action="store_true", help="only run the service (for testing)")
    a = ap.parse_args(argv)

    port = a.port or _free_port()
    url = f"http://127.0.0.1:{port}"
    if a.headless:
        _serve(port)
        return
    threading.Thread(target=_serve, args=(port,), daemon=True).start()
    if not _wait(url):
        raise SystemExit("The Meridian service did not start.")
    if not a.browser:
        try:
            import webview
            webview.create_window("Meridian", url, width=1440, height=920, min_size=(1100, 720),
                                  background_color="#F4F6F8")
            webview.start()
            return
        except Exception as exc:  # no native web view available: fall back to the browser
            print(f"Opening in your browser ({exc})")
    webbrowser.open(url)
    print(f"Meridian is running at {url} — press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
