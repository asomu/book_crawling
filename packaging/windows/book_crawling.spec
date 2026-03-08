# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


spec_dir = Path(SPECPATH).resolve()
project_root = spec_dir.parent.parent
staging_root = project_root / "build" / "windows" / "staging"
icon_path = Path(os.environ.get("BOOKCRAWLER_WINDOWS_ICON", staging_root / "book.ico"))


def collect_tree(source: Path, destination: str):
    entries = []
    if not source.exists():
        return entries
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative_parent = path.relative_to(source).parent.as_posix()
        dest_dir = destination if relative_parent == "." else f"{destination}/{relative_parent}"
        entries.append((str(path), dest_dir))
    return entries


datas = collect_data_files("playwright", include_py_files=True)
datas += collect_data_files("webview", include_py_files=True)
datas += collect_tree(project_root / "app" / "web" / "templates", "app/web/templates")
datas += collect_tree(project_root / "app" / "web" / "static", "app/web/static")
datas += collect_tree(project_root / "resource", "resource")
datas += collect_tree(project_root / "alembic", "alembic")
datas += collect_tree(staging_root / "ms-playwright", "ms-playwright")
datas.append((str(project_root / "alembic.ini"), "."))

hiddenimports = []
hiddenimports.append("webview")
hiddenimports += collect_submodules("playwright")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("webview")

block_cipher = None

a = Analysis(
    [str(project_root / "launcher.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BookCrawling",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BookCrawling",
)
