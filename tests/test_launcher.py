import socket
from pathlib import Path

import httpx
import pytest

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
