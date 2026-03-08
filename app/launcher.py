from __future__ import annotations

import argparse
import atexit
import os
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

import httpx
import uvicorn

from app.config.settings import clear_settings_cache, get_settings


class SingleInstanceError(RuntimeError):
    pass


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class SingleInstanceLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                existing_pid = int(self.path.read_text(encoding="utf-8").strip())
            except ValueError:
                existing_pid = 0
            if _pid_is_running(existing_pid):
                raise SingleInstanceError(f"Another instance is already running with pid {existing_pid}.")
            self.path.unlink(missing_ok=True)

        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise SingleInstanceError("Another instance is already running.") from exc

        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        self._acquired = True
        atexit.register(self.release)

    def release(self) -> None:
        if not self._acquired:
            return
        try:
            current_pid = int(self.path.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, ValueError):
            current_pid = os.getpid()
        if current_pid == os.getpid():
            self.path.unlink(missing_ok=True)
        self._acquired = False

    def __enter__(self) -> "SingleInstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def choose_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class BackgroundUvicornServer(uvicorn.Server):
    def install_signal_handlers(self) -> None:
        return


class DesktopServer:
    def __init__(self, host: str = "127.0.0.1", port: int | None = None) -> None:
        self.host = host
        self.port = port or choose_free_port()
        self._server: BackgroundUvicornServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        from app.main import create_app

        config = uvicorn.Config(
            create_app(),
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False,
            log_config=None,
        )
        self._server = BackgroundUvicornServer(config=config)
        self._thread = threading.Thread(target=self._server.run, name="desktop-server", daemon=True)
        self._thread.start()

    def wait_until_ready(self, timeout: float = 20.0) -> None:
        if not self._thread:
            raise RuntimeError("Desktop server was not started.")
        deadline = time.time() + timeout
        url = f"{self.base_url}/healthz"
        last_error: Exception | None = None
        while time.time() < deadline:
            if not self._thread.is_alive():
                raise RuntimeError("Desktop server exited before becoming ready.")
            try:
                response = httpx.get(url, timeout=1.0)
                if response.status_code == 200:
                    return
            except Exception as exc:  # pragma: no cover - readiness races are environment-dependent
                last_error = exc
            time.sleep(0.2)
        raise RuntimeError(f"Desktop server did not become ready in time: {last_error}")

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)


def _safe_stderr_print(message: str) -> None:
    if sys.stderr is not None and hasattr(sys.stderr, "write"):
        print(message, file=sys.stderr)


def _show_message(title: str, message: str) -> None:
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
        return
    _safe_stderr_print(f"{title}: {message}")


def run_desktop() -> int:
    os.environ["BOOKCRAWLER_DESKTOP_MODE"] = "true"
    clear_settings_cache()
    settings = get_settings()
    lock = SingleInstanceLock(settings.user_data_dir / ".desktop.lock")
    server = DesktopServer()
    try:
        lock.acquire()
    except SingleInstanceError as exc:
        _show_message(settings.app_name, "이미 실행 중입니다. 기존 창을 확인하세요.")
        _safe_stderr_print(str(exc))
        return 1

    try:
        server.start()
        server.wait_until_ready()
        try:
            import webview
        except ImportError as exc:  # pragma: no cover - depends on optional runtime extra
            raise RuntimeError("pywebview is not installed. Install the windows extra before packaging.") from exc

        webview.create_window(settings.app_name, server.base_url, min_size=(1240, 860))
        webview.start(gui="edgechromium", debug=settings.environment != "production")
        return 0
    except Exception as exc:
        _show_message(settings.app_name, f"앱 실행 중 오류가 발생했습니다.\n{exc}")
        _safe_stderr_print(traceback.format_exc())
        return 1
    finally:
        server.stop()
        lock.release()


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> int:
    os.environ["BOOKCRAWLER_DESKTOP_MODE"] = "false"
    clear_settings_cache()
    if reload:
        uvicorn.run("app.main:app", host=host, port=port, reload=True)
    else:
        uvicorn.run("app.main:app", host=host, port=port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Book Crawling launcher")
    subparsers = parser.add_subparsers(dest="mode")

    desktop_parser = subparsers.add_parser("desktop", help="Run the desktop shell")
    desktop_parser.set_defaults(mode="desktop")

    server_parser = subparsers.add_parser("server", help="Run the local server only")
    server_parser.add_argument("--host", default="127.0.0.1")
    server_parser.add_argument("--port", type=int, default=8000)
    server_parser.add_argument("--reload", action="store_true")
    server_parser.set_defaults(mode="server")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = args.mode or ("desktop" if getattr(sys, "frozen", False) else "server")
    if mode == "desktop":
        return run_desktop()
    return run_server(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    raise SystemExit(main())
