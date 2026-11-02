"""Small per-user settings (theme, whether the tour has been seen), kept in a JSON file.

The app's address changes on every start (it uses a free port), so the browser's own storage
cannot remember anything between sessions; this file can. Location: ``%APPDATA%\\Meridian`` on
Windows, ``~/.meridian`` elsewhere, or the folder in ``MERIDIAN_HOME``.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

DEFAULTS = {"theme": None, "tour_done": False}
ALLOWED = {"theme": (str, type(None)), "tour_done": (bool,)}
_lock = threading.Lock()


def home() -> Path:
    if os.environ.get("MERIDIAN_HOME"):
        return Path(os.environ["MERIDIAN_HOME"])
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "Meridian"
    return Path.home() / ".meridian"


def _path() -> Path:
    return home() / "settings.json"


def load() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {k: data.get(k, v) for k, v in DEFAULTS.items()}


def update(changes: dict) -> dict:
    """Merge known keys with valid types into the settings file; returns the new settings."""
    with _lock:
        s = load()
        for k, v in changes.items():
            if k in ALLOWED and isinstance(v, ALLOWED[k]):
                s[k] = v
        try:
            _path().parent.mkdir(parents=True, exist_ok=True)
            tmp = _path().with_suffix(".tmp")
            tmp.write_text(json.dumps(s, indent=2), encoding="utf-8")
            tmp.replace(_path())
        except OSError:
            pass  # settings are a convenience; never fail the app over them
        return s
