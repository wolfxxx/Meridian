"""Build the Windows installer in one step (run from the meridian/ folder, inside the venv
that has the Rust engine installed):

    python packaging/build_installer.py            # UI -> frozen app -> installer -> checks
    python packaging/build_installer.py --skip-ui  # reuse the last interface build

Needs Node.js (for the interface), PyInstaller, Pillow and Inno Setup 6 (iscc).
Output: dist/Meridian-Setup-<version>.exe
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packaging"


def sh(*cmd, cwd=ROOT):
    print(">", " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True, shell=(os.name == "nt" and cmd[0] == "npm"))


def find_iscc() -> str:
    for c in (shutil.which("iscc"),
              Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Inno Setup 6/ISCC.exe",
              Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6/ISCC.exe",
              Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Inno Setup 6/ISCC.exe"):
        if c and Path(c).exists():
            return str(c)
    raise SystemExit("Inno Setup 6 not found: install it (winget install JRSoftware.InnoSetup) or add iscc to PATH")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-ui", action="store_true")
    ap.add_argument("--skip-checks", action="store_true")
    ap.add_argument("--no-window-test", action="store_true", help="skip the native-window check (CI without a desktop)")
    a = ap.parse_args()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]

    if not a.skip_ui:
        sh("npm", "ci", cwd=ROOT / "ui")
        sh("npm", "run", "build", cwd=ROOT / "ui")
    if not (ROOT / "python/meridian/app/static/index.html").exists():
        raise SystemExit("The interface has not been built (python/meridian/app/static is empty)")

    if not (PKG / "meridian.ico").exists():
        sh(sys.executable, PKG / "make_icon.py")
    sh(sys.executable, "-m", "PyInstaller", "meridian.spec", "--noconfirm",
       "--distpath", ROOT / "dist", "--workpath", ROOT / "build/pyinstaller", cwd=PKG)
    exe = ROOT / "dist/Meridian/Meridian.exe"

    if not a.skip_checks:
        if not a.no_window_test:
            sh(exe, "--smoke-test")
        sh(sys.executable, PKG / "check_frozen.py", exe)

    sh(find_iscc(), "/Q", f"/DAppVersion={version}", PKG / "meridian.iss")
    out = ROOT / f"dist/Meridian-Setup-{version}.exe"
    print(f"\nInstaller ready: {out} ({out.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
