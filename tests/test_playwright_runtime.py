from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest

from app.config.playwright import (
    PlaywrightRuntimeError,
    ensure_playwright_chromium,
    missing_browser_paths,
    parse_playwright_install_locations,
)


def _sample_dry_run_output(chromium_dir: Path, headless_dir: Path) -> str:
    return f"""Chrome for Testing 145.0.7632.6 (playwright chromium v1208)
  Install location:    {chromium_dir}
  Download url:        https://cdn.playwright.dev/chrome-for-testing-public/145.0.7632.6/win64/chrome-win64.zip

Chrome Headless Shell 145.0.7632.6 (playwright chromium-headless-shell v1208)
  Install location:    {headless_dir}
  Download url:        https://cdn.playwright.dev/chrome-for-testing-public/145.0.7632.6/win64/chrome-headless-shell-win64.zip
"""


def test_parse_playwright_install_locations_reads_required_browsers(tmp_path: Path):
    chromium_dir = tmp_path / "chromium-1208"
    headless_dir = tmp_path / "chromium_headless_shell-1208"
    output = _sample_dry_run_output(chromium_dir, headless_dir)

    install_locations = parse_playwright_install_locations(output)

    assert install_locations["chromium"] == chromium_dir
    assert install_locations["chromium-headless-shell"] == headless_dir


def test_parse_playwright_install_locations_requires_headless_shell(tmp_path: Path):
    chromium_dir = tmp_path / "chromium-1208"
    output = f"""Chrome for Testing 145.0.7632.6 (playwright chromium v1208)
  Install location:    {chromium_dir}
"""

    with pytest.raises(PlaywrightRuntimeError, match="chromium-headless-shell"):
        parse_playwright_install_locations(output)


def test_missing_browser_paths_checks_windows_executables(tmp_path: Path):
    chromium_dir = tmp_path / "chromium-1208"
    headless_dir = tmp_path / "chromium_headless_shell-1208"
    chromium_exe = chromium_dir / "chrome-win64" / "chrome.exe"
    chromium_exe.parent.mkdir(parents=True, exist_ok=True)
    chromium_exe.write_text("", encoding="utf-8")

    missing = missing_browser_paths(
        {
            "chromium": chromium_dir,
            "chromium-headless-shell": headless_dir,
        },
        platform="win32",
    )

    assert missing == [headless_dir / "chrome-headless-shell-win64" / "chrome-headless-shell.exe"]


def test_ensure_playwright_chromium_installs_missing_browsers(monkeypatch, tmp_path: Path):
    chromium_dir = tmp_path / "chromium-1208"
    headless_dir = tmp_path / "chromium_headless_shell-1208"
    chromium_exe = chromium_dir / "chrome-win64" / "chrome.exe"
    headless_exe = headless_dir / "chrome-headless-shell-win64" / "chrome-headless-shell.exe"
    chromium_exe.parent.mkdir(parents=True, exist_ok=True)
    chromium_exe.write_text("", encoding="utf-8")

    output = _sample_dry_run_output(chromium_dir, headless_dir)
    calls: list[list[str]] = []

    def fake_run(command, capture_output=False, text=False, check=False):
        command = list(command)
        calls.append(command)
        if "--dry-run" in command:
            return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")
        if command[-2:] == ["install", "chromium"]:
            headless_exe.parent.mkdir(parents=True, exist_ok=True)
            headless_exe.write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("app.config.playwright.subprocess.run", fake_run)

    stdout = io.StringIO()
    changed = ensure_playwright_chromium(platform="win32", stdout=stdout)

    assert changed is True
    assert headless_exe.exists()
    assert calls[0][-3:] == ["install", "--dry-run", "chromium"]
    assert calls[1][-2:] == ["install", "chromium"]
    assert calls[2][-3:] == ["install", "--dry-run", "chromium"]
    assert "missing" in stdout.getvalue().lower()
