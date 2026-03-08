#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGING_DIR = PROJECT_ROOT / "build" / "windows" / "staging"
DIST_DIR = PROJECT_ROOT / "dist"
SPEC_PATH = PROJECT_ROOT / "packaging" / "windows" / "book_crawling.spec"
ISS_PATH = PROJECT_ROOT / "packaging" / "windows" / "book_crawling.iss"
WEBVIEW2_BOOTSTRAPPER_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
ICON_SOURCE_PATH = PROJECT_ROOT / "legacy" / "build" / "book_icon.png"


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True, env=env)


def read_version() -> str:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not determine project version from pyproject.toml.")
    return match.group(1)


def ensure_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Windows packaging must be run on Windows.")


def prepare_staging() -> None:
    shutil.rmtree(STAGING_DIR, ignore_errors=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)


def install_bundled_chromium() -> Path:
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    run([sys.executable, "-m", "playwright", "install", "chromium"], env=env)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        executable_path = Path(playwright.chromium.executable_path)

    for candidate in executable_path.parents:
        if candidate.name in {"ms-playwright", ".local-browsers"}:
            return candidate
    raise RuntimeError(f"Could not locate bundled Playwright browsers from {executable_path}")


def stage_playwright_browsers() -> None:
    source = install_bundled_chromium()
    destination = STAGING_DIR / "ms-playwright"
    shutil.copytree(source, destination, dirs_exist_ok=True)


def stage_webview2_bootstrapper() -> Path:
    destination = STAGING_DIR / "MicrosoftEdgeWebView2Setup.exe"
    urllib.request.urlretrieve(WEBVIEW2_BOOTSTRAPPER_URL, str(destination))
    return destination


def stage_app_icon() -> Path:
    if not ICON_SOURCE_PATH.exists():
        raise RuntimeError(f"App icon source is missing: {ICON_SOURCE_PATH}")

    destination = STAGING_DIR / "book.ico"
    with Image.open(ICON_SOURCE_PATH) as source:
        icon = source.convert("RGBA")
        icon.save(
            destination,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
    return destination


def build_pyinstaller(icon_path: Path) -> None:
    env = os.environ.copy()
    env["BOOKCRAWLER_WINDOWS_ICON"] = str(icon_path)
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC_PATH)], env=env)


def build_inno_setup(version: str, bootstrapper_path: Path, icon_path: Path) -> None:
    iscc = os.environ.get("ISCC_PATH") or shutil.which("ISCC.exe") or shutil.which("iscc")
    if not iscc:
        raise RuntimeError("Inno Setup compiler was not found. Set ISCC_PATH or add ISCC.exe to PATH.")

    run(
        [
            iscc,
            f"/DAppVersion={version}",
            f"/DStageDir={DIST_DIR / 'BookCrawling'}",
            f"/DBootstrapperPath={bootstrapper_path}",
            f"/DSetupIconPath={icon_path}",
            str(ISS_PATH),
        ]
    )


def main() -> int:
    ensure_windows()
    version = read_version()
    prepare_staging()
    stage_playwright_browsers()
    icon_path = stage_app_icon()
    bootstrapper_path = stage_webview2_bootstrapper()
    build_pyinstaller(icon_path)
    build_inno_setup(version, bootstrapper_path, icon_path)
    print(f"Windows installer build completed: {DIST_DIR / 'installer'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
