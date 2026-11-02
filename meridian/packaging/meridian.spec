# PyInstaller spec for the Meridian desktop app.
#   pyinstaller packaging/meridian.spec --noconfirm   (run from the meridian/ folder)
# Produces dist/Meridian/Meridian.exe (one folder, no console window). Bundles the *installed*
# meridian package (editable install locally, the built wheel in CI), engine included.

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []
for pkg in ("meridian", "webview", "uvicorn", "fastapi", "starlette"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
hiddenimports += collect_submodules("clr_loader") + ["clr"]

# Keep the bundle lean: test and dev tooling never runs inside the app.
excludes = ["pytest", "tkinter", "matplotlib", "IPython", "pandas", "scipy", "PyInstaller",
            "meridian.tests"]

a = Analysis(
    ["meridian_app.py"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)
# Debug symbols are not needed at run time.
a.datas = [d for d in a.datas if not d[0].lower().endswith(".pdb")]
a.binaries = [b for b in a.binaries if not b[0].lower().endswith(".pdb")]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Meridian",
    icon="meridian.ico",
    console=False,
    version="version_info.txt",
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Meridian", upx=False)
