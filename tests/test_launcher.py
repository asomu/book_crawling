import logging
import socket
import sys
import types
from pathlib import Path

import httpx
import pytest

from app import launcher as app_launcher
from app import main as app_main
from app.launcher import DesktopServer, SingleInstanceError, SingleInstanceLock, choose_free_port


def test_single_instance_lock_prevents_second_acquire(tmp_path: Path):
    lock_path = tmp_path / "desktop.lock"
    first = SingleInstanceLock(lock_path)
    second = SingleInstanceLock(lock_path)

    first.acquire()
    try:
        with pytest.raises(SingleInstanceError):
            second.acquire()
    finally:
        first.release()

    second.acquire()
    second.release()


def test_windows_pid_probe_reports_dead_process():
    class FakeKernel32:
        def OpenProcess(self, access: int, inherit_handle: bool, pid: int) -> int:
            return 0

        def GetExitCodeProcess(self, handle: int, exit_code_pointer) -> int:
            raise AssertionError("GetExitCodeProcess should not be called when the process handle is missing.")

        def CloseHandle(self, handle: int) -> int:
            return 1

    assert app_launcher._windows_pid_is_running(999999, kernel32=FakeKernel32()) is False


def test_windows_pid_probe_reports_live_process():
    class FakeKernel32:
        def OpenProcess(self, access: int, inherit_handle: bool, pid: int) -> int:
            return 1

        def GetExitCodeProcess(self, handle: int, exit_code_pointer) -> int:
            exit_code_pointer._obj.value = 259
            return 1

        def CloseHandle(self, handle: int) -> int:
            return 1

    assert app_launcher._windows_pid_is_running(1234, kernel32=FakeKernel32()) is True


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only launcher regression")
def test_pid_is_running_handles_stale_windows_pid():
    assert app_launcher._pid_is_running(999999) is False


def test_choose_free_port_returns_bindable_port():
    port = choose_free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_desktop_server_reports_health():
    server = DesktopServer(port=choose_free_port())
    server.start()
    try:
        server.wait_until_ready(timeout=10)
        response = httpx.get(f"{server.base_url}/healthz", timeout=1.0)
        assert response.status_code == 200
        assert response.json()["ok"] is True
    finally:
        server.stop()


def test_build_log_handlers_skips_missing_stderr(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(app_main.sys, "stderr", None)

    handlers = app_main.build_log_handlers(tmp_path / "app.log")

    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.FileHandler)


def test_run_desktop_enables_pywebview_downloads(monkeypatch, tmp_path: Path):
    calls: list[tuple[str, object]] = []

    class FakeSettings:
        app_name = "Book Crawling Test"
        user_data_dir = tmp_path / "user-data"
        environment = "production"

    class FakeLock:
        def __init__(self, path: Path) -> None:
            self.path = path

        def acquire(self) -> None:
            calls.append(("lock.acquire", self.path))

        def release(self) -> None:
            calls.append(("lock.release", self.path))

    class FakeServer:
        base_url = "http://127.0.0.1:54321"

        def start(self) -> None:
            calls.append(("server.start", self.base_url))

        def wait_until_ready(self) -> None:
            calls.append(("server.wait_until_ready", self.base_url))

        def stop(self) -> None:
            calls.append(("server.stop", self.base_url))

    fake_webview = types.SimpleNamespace(
        settings={"ALLOW_DOWNLOADS": False},
        create_window=lambda *args, **kwargs: calls.append(("webview.create_window", (args, kwargs))),
        start=lambda **kwargs: calls.append(("webview.start", kwargs)),
    )

    monkeypatch.setattr(app_launcher, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(app_launcher, "clear_settings_cache", lambda: calls.append(("clear_settings_cache", None)))
    monkeypatch.setattr(app_launcher, "SingleInstanceLock", FakeLock)
    monkeypatch.setattr(app_launcher, "DesktopServer", FakeServer)
    monkeypatch.setitem(app_launcher.sys.modules, "webview", fake_webview)

    assert app_launcher.run_desktop() == 0
    assert fake_webview.settings["ALLOW_DOWNLOADS"] is True
    assert ("server.start", "http://127.0.0.1:54321") in calls
    assert ("webview.start", {"gui": "edgechromium", "debug": False}) in calls


def test_run_desktop_disables_debug_when_frozen(monkeypatch, tmp_path: Path):
    calls: list[tuple[str, object]] = []

    class FakeSettings:
        app_name = "Book Crawling Test"
        user_data_dir = tmp_path / "user-data"
        environment = "development"

    class FakeLock:
        def __init__(self, path: Path) -> None:
            self.path = path

        def acquire(self) -> None:
            return None

        def release(self) -> None:
            return None

    class FakeServer:
        base_url = "http://127.0.0.1:54321"

        def start(self) -> None:
            return None

        def wait_until_ready(self) -> None:
            return None

        def stop(self) -> None:
            return None

    fake_webview = types.SimpleNamespace(
        settings={"ALLOW_DOWNLOADS": False},
        create_window=lambda *args, **kwargs: None,
        start=lambda **kwargs: calls.append(("webview.start", kwargs)),
    )

    monkeypatch.setattr(app_launcher, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(app_launcher, "clear_settings_cache", lambda: None)
    monkeypatch.setattr(app_launcher, "SingleInstanceLock", FakeLock)
    monkeypatch.setattr(app_launcher, "DesktopServer", FakeServer)
    monkeypatch.setitem(app_launcher.sys.modules, "webview", fake_webview)
    monkeypatch.setattr(app_launcher.sys, "frozen", True, raising=False)

    assert app_launcher.run_desktop() == 0
    assert ("webview.start", {"gui": "edgechromium", "debug": False}) in calls
