"""Tests for the local web viewer over the memory database."""

import json
import threading
import urllib.error
import urllib.request
import webbrowser

import pytest

from kimi_mcp_hub.memory import viewer as viewer_module
from kimi_mcp_hub.memory.db import MemoryDB
from kimi_mcp_hub.memory.viewer import build_server, has_display, open_in_browser

PROJECT = "/tmp/kimi-viewer-project"


@pytest.fixture
def viewer(tmp_path):
    db_path = tmp_path / "memory.db"
    db = MemoryDB(db_path=db_path)
    db.add_observation(
        session_id="s1",
        obs_type="session",
        content="Wired the viewer to loopback only",
        summary="Viewer bound to loopback",
        tags=["session"],
        project_path=PROJECT,
    )
    db.add_observation(
        session_id="s1",
        obs_type="tool",
        content="curl output",
        summary="Used Bash",
        tags=["Bash"],
        project_path=PROJECT,
    )
    db.add_memory("Never bind the viewer to 0.0.0.0", "project", ["security"], PROJECT)

    server, token = build_server(db_path=db_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base, token
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def fetch(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


class TestBrowserOpening:
    """Auto-open must fail loudly, not silently, on headless machines."""

    def test_headless_linux_has_no_display(self, monkeypatch):
        monkeypatch.setattr(viewer_module.sys, "platform", "linux")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.delenv("BROWSER", raising=False)
        assert has_display() is False

    def test_linux_with_x11_has_a_display(self, monkeypatch):
        monkeypatch.setattr(viewer_module.sys, "platform", "linux")
        monkeypatch.delenv("BROWSER", raising=False)
        monkeypatch.setenv("DISPLAY", ":0")
        assert has_display() is True

    def test_linux_with_wayland_has_a_display(self, monkeypatch):
        monkeypatch.setattr(viewer_module.sys, "platform", "linux")
        monkeypatch.delenv("BROWSER", raising=False)
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        assert has_display() is True

    def test_explicit_browser_env_var_wins(self, monkeypatch):
        """WSL sets BROWSER=wslview with no DISPLAY, and that works."""
        monkeypatch.setattr(viewer_module.sys, "platform", "linux")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setenv("BROWSER", "wslview")
        assert has_display() is True

    def test_macos_always_has_a_display(self, monkeypatch):
        monkeypatch.setattr(viewer_module.sys, "platform", "darwin")
        monkeypatch.delenv("DISPLAY", raising=False)
        assert has_display() is True

    def test_headless_reports_a_reason(self, monkeypatch):
        monkeypatch.setattr(viewer_module, "has_display", lambda: False)
        opened, reason = open_in_browser("http://127.0.0.1:8765/")
        assert opened is False
        assert "display" in reason

    def test_launcher_refusal_reports_a_reason(self, monkeypatch):
        monkeypatch.setattr(viewer_module, "has_display", lambda: True)
        monkeypatch.setattr(viewer_module.webbrowser, "open", lambda url: False)
        opened, reason = open_in_browser("http://127.0.0.1:8765/")
        assert opened is False
        assert "browser" in reason

    def test_launcher_error_is_caught(self, monkeypatch):
        def boom(url):
            raise webbrowser.Error("no runnable browser")

        monkeypatch.setattr(viewer_module, "has_display", lambda: True)
        monkeypatch.setattr(viewer_module.webbrowser, "open", boom)
        opened, reason = open_in_browser("http://127.0.0.1:8765/")
        assert opened is False
        assert "no runnable browser" in reason

    def test_success_reports_no_reason(self, monkeypatch):
        monkeypatch.setattr(viewer_module, "has_display", lambda: True)
        monkeypatch.setattr(viewer_module.webbrowser, "open", lambda url: True)
        assert open_in_browser("http://127.0.0.1:8765/") == (True, "")


class TestViewerSecurity:
    def test_binds_loopback_only(self, tmp_path):
        server, _ = build_server(db_path=tmp_path / "memory.db", port=0)
        try:
            assert server.server_address[0] == "127.0.0.1"
        finally:
            server.server_close()

    def test_api_requires_a_token(self, viewer):
        base, _ = viewer
        status, _ = fetch(f"{base}/api/stats")
        assert status == 401

    def test_api_rejects_a_wrong_token(self, viewer):
        base, _ = viewer
        status, _ = fetch(f"{base}/api/stats?token=guess")
        assert status == 401

    def test_non_local_host_header_is_rejected(self, viewer):
        """Defends against DNS rebinding, where a remote name resolves to 127.0.0.1."""
        base, token = viewer
        status, _ = fetch(f"{base}/api/stats?token={token}", {"Host": "evil.example"})
        assert status == 403

    def test_no_cors_header_is_sent(self, viewer):
        base, token = viewer
        request = urllib.request.Request(f"{base}/api/stats?token={token}")
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.headers.get("Access-Control-Allow-Origin") is None

    def test_index_page_needs_no_token(self, viewer):
        """The shell is inert; the token gates the data it fetches."""
        base, _ = viewer
        status, body = fetch(f"{base}/")
        assert status == 200
        assert "Kimi Memory" in body

    def test_index_page_explains_an_unauthorized_browser(self, viewer):
        """An unauthorized browser should be guided, not just refused."""
        base, _ = viewer
        _, body = fetch(f"{base}/")
        assert "not authorized yet" in body
        assert "kimi-mcp-hub memory viewer" in body

    def test_index_page_carries_no_token(self, viewer):
        """The token must never be embedded in the page the server hands out."""
        base, token = viewer
        _, body = fetch(f"{base}/")
        assert token not in body


class TestSessionCookie:
    """The first visit through the printed link authorizes the browser."""

    def test_index_sets_a_cookie_when_the_token_is_valid(self, viewer):
        base, token = viewer
        request = urllib.request.Request(f"{base}/?token={token}")
        with urllib.request.urlopen(request, timeout=5) as response:
            cookie = response.headers.get("Set-Cookie")
        assert cookie is not None
        assert f"kimi_viewer={token}" in cookie
        # Another site's requests must never carry it, and page scripts must
        # not be able to read it.
        assert "HttpOnly" in cookie
        assert "SameSite=Strict" in cookie

    def test_index_sets_no_cookie_without_a_valid_token(self, viewer):
        base, _ = viewer
        request = urllib.request.Request(f"{base}/?token=wrong")
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.headers.get("Set-Cookie") is None

    def test_cookie_authorizes_api_calls(self, viewer):
        """This is what lets the bare address work on later visits."""
        base, token = viewer
        status, body = fetch(f"{base}/api/stats", {"Cookie": f"kimi_viewer={token}"})
        assert status == 200
        assert json.loads(body)["observations"]["total_observations"] == 2

    def test_wrong_cookie_is_rejected(self, viewer):
        base, _ = viewer
        status, _ = fetch(f"{base}/api/stats", {"Cookie": "kimi_viewer=guess"})
        assert status == 401

    def test_malformed_cookie_header_is_rejected(self, viewer):
        base, _ = viewer
        status, _ = fetch(f"{base}/api/stats", {"Cookie": "=====;;;"})
        assert status == 401

    def test_unrelated_cookies_do_not_authorize(self, viewer):
        base, token = viewer
        status, _ = fetch(f"{base}/api/stats", {"Cookie": f"other={token}"})
        assert status == 401


class TestTokenDisabled:
    """`--no-token` trades the local-account protection for convenience."""

    @pytest.fixture
    def open_viewer(self, tmp_path):
        db_path = tmp_path / "memory.db"
        MemoryDB(db_path=db_path).add_observation("s1", "tool", "x", "Used Bash")
        server, _ = build_server(db_path=db_path, port=0, require_token=False)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_address[1]}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_api_needs_no_token(self, open_viewer):
        status, body = fetch(f"{open_viewer}/api/stats")
        assert status == 200
        assert json.loads(body)["observations"]["total_observations"] == 1

    def test_host_header_check_still_applies(self, open_viewer):
        """Dropping the token must not drop the DNS-rebinding defence."""
        status, _ = fetch(f"{open_viewer}/api/stats", {"Host": "evil.example"})
        assert status == 403

    def test_no_cors_header_is_still_sent(self, open_viewer):
        request = urllib.request.Request(f"{open_viewer}/api/stats")
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.headers.get("Access-Control-Allow-Origin") is None

    def test_no_cookie_is_set(self, open_viewer):
        request = urllib.request.Request(f"{open_viewer}/")
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.headers.get("Set-Cookie") is None


class TestViewerApi:
    def test_stats(self, viewer):
        base, token = viewer
        status, body = fetch(f"{base}/api/stats?token={token}")
        data = json.loads(body)
        assert status == 200
        assert data["observations"]["total_observations"] == 2
        assert data["memories"]["total_memories"] == 1
        assert sorted(data["types"]) == ["session", "tool"]
        assert data["projects"][0]["count"] == 2

    def test_browse_is_paginated(self, viewer):
        base, token = viewer
        status, body = fetch(f"{base}/api/observations?token={token}&limit=1")
        data = json.loads(body)
        assert status == 200
        assert data["paginated"] is True
        assert data["total"] == 2
        assert len(data["rows"]) == 1

    def test_offset_moves_through_results(self, viewer):
        base, token = viewer
        _, first = fetch(f"{base}/api/observations?token={token}&limit=1&offset=0")
        _, second = fetch(f"{base}/api/observations?token={token}&limit=1&offset=1")
        assert json.loads(first)["rows"][0]["id"] != json.loads(second)["rows"][0]["id"]

    def test_search_is_not_paginated(self, viewer):
        base, token = viewer
        _, body = fetch(f"{base}/api/observations?token={token}&q=loopback")
        data = json.loads(body)
        assert data["paginated"] is False
        assert len(data["rows"]) == 1

    def test_type_filter(self, viewer):
        base, token = viewer
        _, body = fetch(f"{base}/api/observations?token={token}&type=tool")
        rows = json.loads(body)["rows"]
        assert [row["type"] for row in rows] == ["tool"]

    def test_single_observation(self, viewer):
        base, token = viewer
        _, body = fetch(f"{base}/api/observations/1?token={token}")
        assert "loopback" in json.loads(body)["content"]

    def test_missing_observation(self, viewer):
        base, token = viewer
        status, _ = fetch(f"{base}/api/observations/999?token={token}")
        assert status == 404

    def test_non_numeric_id_is_a_bad_request(self, viewer):
        base, token = viewer
        status, _ = fetch(f"{base}/api/observations/abc?token={token}")
        assert status == 400

    def test_memories(self, viewer):
        base, token = viewer
        _, body = fetch(f"{base}/api/memories?token={token}")
        rows = json.loads(body)["rows"]
        assert rows[0]["content"] == "Never bind the viewer to 0.0.0.0"

    def test_bad_limit_is_rejected(self, viewer):
        base, token = viewer
        status, body = fetch(f"{base}/api/observations?token={token}&limit=abc")
        assert status == 400
        assert "integer" in json.loads(body)["error"]

    def test_unknown_endpoint(self, viewer):
        base, token = viewer
        status, _ = fetch(f"{base}/api/nope?token={token}")
        assert status == 404
