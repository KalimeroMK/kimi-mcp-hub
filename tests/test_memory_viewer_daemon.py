"""Tests for the always-on viewer: persistent token, pidfile, and autostart."""

import json
import os
import stat
import sys
import time

import pytest

from kimi_mcp_hub.memory import viewer as viewer_module
from kimi_mcp_hub.memory.db import MemoryDB
from kimi_mcp_hub.memory.hooks import MemoryHooks


@pytest.fixture
def state(tmp_path, monkeypatch):
    """Point every viewer state file at an isolated directory."""
    monkeypatch.setattr(viewer_module, "state_dir", lambda: tmp_path)
    return tmp_path


class TestPersistentToken:
    def test_token_is_stable_across_calls(self, state):
        first = viewer_module.load_or_create_token()
        assert viewer_module.load_or_create_token() == first

    def test_token_survives_a_restart(self, state):
        """A stable token is what makes the URL bookmarkable."""
        token = viewer_module.load_or_create_token()
        _, served = viewer_module.build_server(db_path=state / "memory.db", port=0)
        try:
            assert served == token
        finally:
            pass

    def test_token_file_is_not_world_readable(self, state):
        viewer_module.load_or_create_token()
        mode = viewer_module.token_path().stat().st_mode
        assert not mode & stat.S_IRWXG
        assert not mode & stat.S_IRWXO

    def test_rotate_invalidates_the_old_token(self, state):
        old = viewer_module.load_or_create_token()
        new = viewer_module.rotate_token()
        assert new != old
        assert viewer_module.load_or_create_token() == new

    def test_empty_token_file_is_replaced(self, state):
        viewer_module.token_path().write_text("   ", encoding="utf-8")
        assert viewer_module.load_or_create_token().strip()

    def test_url_carries_the_token(self, state):
        token = viewer_module.load_or_create_token()
        assert viewer_module.viewer_url(8765) == f"http://127.0.0.1:8765/?token={token}"


class TestStatus:
    def test_no_pidfile_means_stopped(self, state):
        assert viewer_module.viewer_status() == {"state": "stopped"}

    def test_dead_pid_is_reported_as_stale(self, state):
        viewer_module.pid_path().write_text(
            json.dumps({"pid": 999_999, "port": 8765}), encoding="utf-8"
        )
        status = viewer_module.viewer_status()
        assert status["state"] == "stale"

    def test_live_pid_is_reported_as_running(self, state):
        viewer_module.pid_path().write_text(
            json.dumps({"pid": os.getpid(), "port": 8765}), encoding="utf-8"
        )
        status = viewer_module.viewer_status()
        assert status["state"] == "running"
        assert status["url"].endswith(viewer_module.load_or_create_token())

    def test_corrupt_pidfile_is_ignored(self, state):
        viewer_module.pid_path().write_text("{ not json", encoding="utf-8")
        assert viewer_module.viewer_status() == {"state": "stopped"}

    def test_pidfile_without_a_pid_is_ignored(self, state):
        viewer_module.pid_path().write_text('{"port": 8765}', encoding="utf-8")
        assert viewer_module.viewer_status() == {"state": "stopped"}


class TestStartStop:
    def test_start_is_idempotent(self, state, monkeypatch):
        viewer_module.pid_path().write_text(
            json.dumps({"pid": os.getpid(), "port": 8765}), encoding="utf-8"
        )
        spawned = []
        monkeypatch.setattr(
            viewer_module.subprocess, "Popen", lambda *a, **k: spawned.append(a)
        )
        result = viewer_module.start_daemon(port=8765)
        assert result["started"] is False
        assert spawned == []

    def test_stale_pidfile_does_not_block_a_start(self, state, monkeypatch):
        viewer_module.pid_path().write_text(
            json.dumps({"pid": 999_999, "port": 8765}), encoding="utf-8"
        )
        monkeypatch.setattr(viewer_module, "_port_accepts", lambda port, **kw: False)

        class FakeProcess:
            pid = 4242

        monkeypatch.setattr(
            viewer_module.subprocess, "Popen", lambda *a, **k: FakeProcess()
        )
        result = viewer_module.start_daemon(port=8765)
        assert result["started"] is True
        assert viewer_module.read_pidfile()["pid"] == 4242

    def test_busy_port_is_not_claimed(self, state, monkeypatch):
        """Another process owning the port must not be recorded as ours."""
        monkeypatch.setattr(viewer_module, "_port_accepts", lambda port, **kw: True)
        result = viewer_module.start_daemon(port=8765)
        assert result["state"] == "port_busy"
        assert viewer_module.read_pidfile() is None

    def test_spawn_failure_is_reported(self, state, monkeypatch):
        monkeypatch.setattr(viewer_module, "_port_accepts", lambda port, **kw: False)

        def boom(*a, **k):
            raise OSError("no exec")

        monkeypatch.setattr(viewer_module.subprocess, "Popen", boom)
        result = viewer_module.start_daemon(port=8765)
        assert result["state"] == "failed"
        assert "no exec" in result["reason"]

    def test_stop_when_not_running(self, state):
        assert viewer_module.stop_daemon()["stopped"] is False

    def test_stop_cleans_a_stale_pidfile(self, state):
        viewer_module.pid_path().write_text(
            json.dumps({"pid": 999_999, "port": 8765}), encoding="utf-8"
        )
        result = viewer_module.stop_daemon()
        assert result["cleaned_stale"] is True
        assert viewer_module.read_pidfile() is None


@pytest.mark.skipif(os.name == "nt", reason="POSIX process handling")
class TestRealDaemon:
    """Actually spawn and kill the background viewer."""

    def test_start_serve_and_stop(self, state, monkeypatch):
        db_path = state / "memory.db"
        db = MemoryDB(db_path=db_path)
        db.add_observation("s1", "session", "daemon smoke test", "Daemon smoke test")

        # The child is a separate process, so it needs the same state and db
        # directory through the environment rather than the monkeypatch.
        monkeypatch.setenv("XDG_CONFIG_HOME", str(state / "xdg"))
        token = viewer_module.load_or_create_token()

        port = _free_port()
        result = viewer_module.start_daemon(port=port)
        assert result["started"] is True, result

        try:
            deadline = time.time() + 15
            while time.time() < deadline and not viewer_module._port_accepts(port):
                time.sleep(0.2)
            assert viewer_module._port_accepts(port), "daemon never bound the port"

            status = viewer_module.viewer_status()
            assert status["state"] == "running"
            assert status["responding"] is True
            assert token in status["url"]
        finally:
            stopped = viewer_module.stop_daemon()

        assert stopped["stopped"] is True
        assert viewer_module.read_pidfile() is None
        assert not viewer_module._pid_alive(result["pid"])


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestAutostartHook:
    def test_disabled_by_default(self, tmp_path, monkeypatch):
        """Installing must never leave a server running behind the user's back."""
        monkeypatch.setenv("HOME", str(tmp_path))
        called = []
        monkeypatch.setattr(
            viewer_module, "start_daemon", lambda **kw: called.append(kw)
        )
        hooks = MemoryHooks(db=MemoryDB(db_path=tmp_path / "memory.db"))
        hooks.session_start({"cwd": str(tmp_path)})
        assert called == []

    def test_starts_when_enabled(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from kimi_mcp_hub.config import KimiConfig

        KimiConfig().set_viewer_autostart(True, port=8790)

        called = []
        monkeypatch.setattr(
            viewer_module, "start_daemon", lambda **kw: called.append(kw)
        )
        hooks = MemoryHooks(db=MemoryDB(db_path=tmp_path / "memory.db"))
        hooks.session_start({"cwd": str(tmp_path)})
        assert called == [{"port": 8790}]

    def test_a_broken_viewer_never_breaks_the_session(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from kimi_mcp_hub.config import KimiConfig

        KimiConfig().set_viewer_autostart(True)

        def boom(**kw):
            raise RuntimeError("viewer exploded")

        monkeypatch.setattr(viewer_module, "start_daemon", boom)
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_observation("s1", "tool", "x", "Used Bash", [], str(tmp_path))
        hooks = MemoryHooks(db=db)

        # The session context is still produced despite the failure.
        assert "Used Bash" in hooks.session_start({"cwd": str(tmp_path)})


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX config paths")
class TestAutostartConfig:
    def test_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from kimi_mcp_hub.config import KimiConfig

        config = KimiConfig()
        assert config.is_viewer_autostart_enabled() is False
        assert config.get_viewer_port() == 8765

        config.set_viewer_autostart(True, port=9100)
        assert KimiConfig().is_viewer_autostart_enabled() is True
        assert KimiConfig().get_viewer_port() == 9100

        config.set_viewer_autostart(False)
        assert KimiConfig().is_viewer_autostart_enabled() is False
        # Turning autostart off keeps the chosen port.
        assert KimiConfig().get_viewer_port() == 9100

    def test_invalid_port_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from kimi_mcp_hub.config import KimiConfig

        config = KimiConfig()
        data = config.load_toml_config()
        data.setdefault("memory", {})["viewer_port"] = "not-a-port"
        config.save_toml_config(data)
        assert KimiConfig().get_viewer_port() == 8765
