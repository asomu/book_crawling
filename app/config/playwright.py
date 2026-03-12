from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


REQUIRED_BROWSERS = ("chromium", "chromium-headless-shell")
WINDOWS_BROWSER_EXECUTABLES = {
    "chromium": Path("chrome-win64") / "chrome.exe",
    "chromium-headless-shell": Path("chrome-headless-shell-win64") / "chrome-headless-shell.exe",
}


class PlaywrightRuntimeError(RuntimeError):
    """Raised when the local Playwright browser installation is unusable."""


def parse_playwright_install_locations(output: str) -> dict[str, Path]:
    locations: dict[str, Path] = {}
    current_browser: str | None = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if "(playwright chromium-headless-shell v" in line:
            current_browser = "chromium-headless-shell"
            continue
        if "(playwright chromium v" in line:
            current_browser = "chromium"
            continue
        if line.startswith("Install location:") and current_browser is not None:
            location = line.split(":", 1)[1].strip()
            if location:
                locations[current_browser] = Path(location)
            current_browser = None

    missing_browsers = [browser for browser in REQUIRED_BROWSERS if browser not in locations]
    if missing_browsers:
        missing_display = ", ".join(missing_browsers)
        raise PlaywrightRuntimeError(
            "Could not determine Playwright install locations for: " + missing_display
        )

    return locations


def inspect_playwright_installation(
    command: Sequence[str] | None = None,
) -> dict[str, Path]:
    playwright_command = list(command or [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"])
    result = subprocess.run(playwright_command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"exit code {result.returncode}"
        raise PlaywrightRuntimeError(f"Failed to inspect Playwright browser installation: {detail}")
    return parse_playwright_install_locations(result.stdout)


def expected_browser_paths(
    install_locations: Mapping[str, Path],
    platform: str | None = None,
) -> list[Path]:
    platform_name = platform or sys.platform
    if platform_name == "win32":
        return [install_locations[browser] / WINDOWS_BROWSER_EXECUTABLES[browser] for browser in REQUIRED_BROWSERS]
    return [install_locations[browser] for browser in REQUIRED_BROWSERS]


def missing_browser_paths(
    install_locations: Mapping[str, Path],
    platform: str | None = None,
) -> list[Path]:
    return [path for path in expected_browser_paths(install_locations, platform) if not path.exists()]


def ensure_playwright_chromium(
    inspect_command: Sequence[str] | None = None,
    install_command: Sequence[str] | None = None,
    platform: str | None = None,
    stdout=None,
) -> bool:
    stdout = stdout or sys.stdout

    install_locations = inspect_playwright_installation(inspect_command)
    missing_paths = missing_browser_paths(install_locations, platform)
    if not missing_paths:
        print("Playwright Chromium browser binaries are ready.", file=stdout)
        return False

    print("Playwright Chromium browser binaries are missing. Installing...", file=stdout)
    playwright_install_command = list(install_command or [sys.executable, "-m", "playwright", "install", "chromium"])
    result = subprocess.run(playwright_install_command, check=False)
    if result.returncode != 0:
        raise PlaywrightRuntimeError(
            f"Playwright browser installation failed with exit code {result.returncode}."
        )

    install_locations = inspect_playwright_installation(inspect_command)
    missing_paths = missing_browser_paths(install_locations, platform)
    if missing_paths:
        missing_display = ", ".join(str(path) for path in missing_paths)
        raise PlaywrightRuntimeError(
            "Playwright browser installation finished, but required executables are still missing: "
            + missing_display
        )

    print("Playwright Chromium browser binaries installed.", file=stdout)
    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or install Playwright Chromium browsers.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("check", "ensure"),
        default="ensure",
        help="Use 'check' to verify browsers or 'ensure' to install missing ones.",
    )
    args = parser.parse_args(argv)

    try:
        install_locations = inspect_playwright_installation()
        missing_paths = missing_browser_paths(install_locations)
        if args.command == "check":
            if missing_paths:
                missing_display = ", ".join(str(path) for path in missing_paths)
                raise PlaywrightRuntimeError(
                    "Playwright Chromium browser binaries are missing: " + missing_display
                )
            print("Playwright Chromium browser binaries are ready.")
            return 0

        if missing_paths:
            ensure_playwright_chromium()
            return 0

        print("Playwright Chromium browser binaries are ready.")
        return 0
    except PlaywrightRuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
