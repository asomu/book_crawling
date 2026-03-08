#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGING_DIR = PROJECT_ROOT / "build" / "windows" / "staging"
DIST_DIR = PROJECT_ROOT / "dist"
SPEC_PATH = PROJECT_ROOT / "packaging" / "windows" / "book_crawling.spec"
ISS_PATH = PROJECT_ROOT / "packaging" / "windows" / "book_crawling.iss"
WEBVIEW2_BOOTSTRAPPER_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
ICON_SOURCE_CANDIDATES = [
    PROJECT_ROOT / "legacy" / "build" / "book_icon.png",
    PROJECT_ROOT / "legacy" / "build" / "book.ico",
]
COMMON_INNO_SETUP_PATHS = [
    Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "Inno Setup 5" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 5" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 5" / "ISCC.exe",
]


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


def ensure_packaging_dependencies() -> None:
    missing: list[str] = []
    for module_name in ("PyInstaller", "webview"):
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)

    if missing:
        missing_display = ", ".join(missing)
        raise RuntimeError(
            "Missing Windows packaging dependencies: "
            + missing_display
            + '. Install the Windows extra first, then rebuild. '
            + 'For uv use `uv sync --extra dev --extra windows` or '
            + '`uv run --extra dev --extra windows scripts/build_windows.py`. '
            + 'For pip use `pip install -e ".[dev,windows]"`.'
        )


def prepare_staging() -> None:
    shutil.rmtree(STAGING_DIR, ignore_errors=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)


def resolve_local_playwright_browser_root(playwright_package_root: Path | None = None) -> Path:
    if playwright_package_root is None:
        import playwright

        playwright_package_root = Path(playwright.__file__).resolve().parent

    browser_root = playwright_package_root / "driver" / "package" / ".local-browsers"
    if not browser_root.exists():
        raise RuntimeError(f"Expected local Playwright browsers at {browser_root}, but the directory is missing.")

    required_prefixes = ("chromium-", "chromium_headless_shell-")
    missing_prefixes = [
        prefix
        for prefix in required_prefixes
        if not any(path.is_dir() and path.name.startswith(prefix) for path in browser_root.iterdir())
    ]
    if missing_prefixes:
        missing_display = ", ".join(missing_prefixes)
        raise RuntimeError(
            "Playwright browser bundle is incomplete at "
            + str(browser_root)
            + f". Missing expected browser directories: {missing_display}."
        )
    return browser_root


def install_bundled_chromium() -> Path:
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    run([sys.executable, "-m", "playwright", "install", "chromium"], env=env)
    return resolve_local_playwright_browser_root()


def stage_playwright_browsers() -> None:
    source = install_bundled_chromium()
    destination = STAGING_DIR / "ms-playwright"
    shutil.copytree(source, destination, dirs_exist_ok=True)


def stage_webview2_bootstrapper() -> Path:
    destination = STAGING_DIR / "MicrosoftEdgeWebView2Setup.exe"
    urllib.request.urlretrieve(WEBVIEW2_BOOTSTRAPPER_URL, str(destination))
    return destination


def stage_app_icon() -> Path:
    destination = STAGING_DIR / "book.ico"
    source_path = next((path for path in ICON_SOURCE_CANDIDATES if path.exists()), None)
    if source_path:
        with Image.open(source_path) as source:
            icon = source.convert("RGBA")
    else:
        icon = generate_fallback_icon()

    icon.save(
        destination,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    return destination


def generate_fallback_icon(size: int = 512) -> Image.Image:
    image = Image.new("RGBA", (size, size), (246, 241, 231, 255))
    draw = ImageDraw.Draw(image)

    margin = int(size * 0.16)
    cover = [margin, margin, size - margin, size - margin]
    draw.rounded_rectangle(cover, radius=int(size * 0.08), fill=(44, 78, 126, 255))

    page_margin = int(size * 0.08)
    pages = [
        cover[0] + page_margin,
        cover[1] + page_margin,
        cover[2] - page_margin,
        cover[3] - page_margin,
    ]
    draw.rounded_rectangle(pages, radius=int(size * 0.05), fill=(252, 250, 245, 255))

    spine_x = int(size * 0.42)
    draw.rectangle(
        [spine_x, pages[1] + int(size * 0.02), spine_x + int(size * 0.035), pages[3] - int(size * 0.02)],
        fill=(210, 182, 110, 255),
    )
    draw.line(
        [pages[0] + int(size * 0.07), int(size * 0.34), pages[2] - int(size * 0.07), int(size * 0.34)],
        fill=(44, 78, 126, 180),
        width=max(4, int(size * 0.012)),
    )
    draw.line(
        [pages[0] + int(size * 0.07), int(size * 0.48), pages[2] - int(size * 0.12), int(size * 0.48)],
        fill=(44, 78, 126, 160),
        width=max(4, int(size * 0.012)),
    )
    draw.line(
        [pages[0] + int(size * 0.07), int(size * 0.62), pages[2] - int(size * 0.18), int(size * 0.62)],
        fill=(44, 78, 126, 140),
        width=max(4, int(size * 0.012)),
    )
    draw.ellipse(
        [
            size - int(size * 0.23),
            size - int(size * 0.23),
            size - int(size * 0.08),
            size - int(size * 0.08),
        ],
        fill=(205, 93, 67, 255),
    )
    return image


def build_pyinstaller(icon_path: Path) -> None:
    env = os.environ.copy()
    env["BOOKCRAWLER_WINDOWS_ICON"] = str(icon_path)
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC_PATH)], env=env)


def should_skip_installer() -> bool:
    return os.environ.get("BOOKCRAWLER_SKIP_INSTALLER", "").lower() in {"1", "true", "yes"}


def find_inno_setup() -> str | None:
    candidates: list[Path | str] = []
    if os.environ.get("ISCC_PATH"):
        candidates.append(os.environ["ISCC_PATH"])
    candidates.extend(
        candidate
        for candidate in (
            shutil.which("ISCC.exe"),
            shutil.which("iscc"),
            *COMMON_INNO_SETUP_PATHS,
        )
        if candidate
    )

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return str(path)
    return None


def build_inno_setup(version: str, bootstrapper_path: Path, icon_path: Path) -> None:
    iscc = find_inno_setup()
    if not iscc:
        raise RuntimeError(
            "Inno Setup compiler was not found. Install Inno Setup, set ISCC_PATH, or rerun with "
            "BOOKCRAWLER_SKIP_INSTALLER=1 to keep the dist/BookCrawling bundle only."
        )

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
    ensure_packaging_dependencies()
    version = read_version()
    prepare_staging()
    stage_playwright_browsers()
    icon_path = stage_app_icon()
    build_pyinstaller(icon_path)

    if should_skip_installer():
        print(f"PyInstaller bundle completed: {DIST_DIR / 'BookCrawling'}")
        print("Installer step skipped because BOOKCRAWLER_SKIP_INSTALLER is enabled.")
        return 0

    bootstrapper_path = stage_webview2_bootstrapper()
    build_inno_setup(version, bootstrapper_path, icon_path)
    print(f"Windows installer build completed: {DIST_DIR / 'installer'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

