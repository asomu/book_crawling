import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_windows.py"
SPEC = importlib.util.spec_from_file_location("build_windows", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
build_windows = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_windows)


def test_resolve_local_playwright_browser_root_uses_local_bundle_layout(tmp_path: Path):
    package_root = tmp_path / "playwright"
    browser_root = package_root / "driver" / "package" / ".local-browsers"
    (browser_root / "chromium-1208").mkdir(parents=True, exist_ok=True)
    (browser_root / "chromium_headless_shell-1208").mkdir(parents=True, exist_ok=True)

    assert build_windows.resolve_local_playwright_browser_root(package_root) == browser_root


def test_resolve_local_playwright_browser_root_requires_headless_shell(tmp_path: Path):
    package_root = tmp_path / "playwright"
    browser_root = package_root / "driver" / "package" / ".local-browsers"
    (browser_root / "chromium-1208").mkdir(parents=True, exist_ok=True)

    with pytest.raises(RuntimeError, match="chromium_headless_shell-"):
        build_windows.resolve_local_playwright_browser_root(package_root)


def test_find_inno_setup_checks_localappdata_programs(monkeypatch, tmp_path: Path):
    local_appdata = tmp_path / "localappdata"
    iscc = local_appdata / "Programs" / "Inno Setup 6" / "ISCC.exe"
    iscc.parent.mkdir(parents=True, exist_ok=True)
    iscc.write_text("", encoding="utf-8")

    monkeypatch.delenv("ISCC_PATH", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "programfiles"))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "programfilesx86"))
    monkeypatch.setattr(build_windows.shutil, "which", lambda _: None)

    build_windows.COMMON_INNO_SETUP_PATHS = [
        Path(build_windows.os.environ["LOCALAPPDATA"]) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(build_windows.os.environ["ProgramFiles(x86)"]) / "Inno Setup 6" / "ISCC.exe",
        Path(build_windows.os.environ["ProgramFiles"]) / "Inno Setup 6" / "ISCC.exe",
        Path(build_windows.os.environ["LOCALAPPDATA"]) / "Programs" / "Inno Setup 5" / "ISCC.exe",
        Path(build_windows.os.environ["ProgramFiles(x86)"]) / "Inno Setup 5" / "ISCC.exe",
        Path(build_windows.os.environ["ProgramFiles"]) / "Inno Setup 5" / "ISCC.exe",
    ]

    assert build_windows.find_inno_setup() == str(iscc)
