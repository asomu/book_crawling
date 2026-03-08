import os
from pathlib import Path

from app.config.settings import AppSettings, clear_settings_cache, get_settings


def test_settings_support_user_data_dir_override(monkeypatch, tmp_path: Path):
    user_data_dir = tmp_path / "desktop-data"
    monkeypatch.setenv("BOOKCRAWLER_USER_DATA_DIR", str(user_data_dir))
    monkeypatch.setenv("BOOKCRAWLER_DESKTOP_MODE", "true")
    clear_settings_cache()

    settings = get_settings()

    assert settings.user_data_dir == user_data_dir
    assert settings.data_dir == user_data_dir / "data"
    assert settings.logs_dir == user_data_dir / "logs"
    assert settings.desktop_mode is True
    assert settings.template_dir.exists()
    assert settings.static_dir.exists()

    clear_settings_cache()


def test_configure_process_environment_prefers_packaged_playwright_browser(monkeypatch, tmp_path: Path):
    bundle_dir = tmp_path / "bundle"
    packaged_browser_dir = bundle_dir / "playwright" / "driver" / "package" / ".local-browsers"
    bundled_browser_dir = bundle_dir / "ms-playwright"
    packaged_browser_dir.mkdir(parents=True, exist_ok=True)
    bundled_browser_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    settings = AppSettings(
        bundle_dir=bundle_dir,
        user_data_dir=tmp_path / "user-data",
    )
    settings.ensure_runtime_dirs()
    settings.configure_process_environment()
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", os.environ["PLAYWRIGHT_BROWSERS_PATH"])

    assert settings.user_data_dir == tmp_path / "user-data"
    assert packaged_browser_dir.as_posix() == os.environ["PLAYWRIGHT_BROWSERS_PATH"]


def test_configure_process_environment_falls_back_to_staged_browser(monkeypatch, tmp_path: Path):
    bundle_dir = tmp_path / "bundle"
    bundled_browser_dir = bundle_dir / "ms-playwright"
    bundled_browser_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    settings = AppSettings(
        bundle_dir=bundle_dir,
        user_data_dir=tmp_path / "user-data",
    )
    settings.ensure_runtime_dirs()
    settings.configure_process_environment()
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", os.environ["PLAYWRIGHT_BROWSERS_PATH"])

    assert settings.user_data_dir == tmp_path / "user-data"
    assert bundled_browser_dir.as_posix() == os.environ["PLAYWRIGHT_BROWSERS_PATH"]
