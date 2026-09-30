"""Tests for the viewer's live SSE stream of new observations."""

import socket
import threading
from pathlib import Path

import pytest

from kimi_mcp_hub.memory import viewer as viewer_module
from kimi_mcp_hub.memory.db import MemoryDB
from kimi_mcp_hub.memory.viewer import (
    build_server,
    max_observation_id,
    observations_since,
)

PROJECT = "/tmp/kimi-viewer-stream-project"


@pytest.fixture
def db(tmp_path):
    return MemoryDB(db_path=tmp_path / "memory.db")


def add(db, content, summary=None):
    return db.add_observation(
        session_id="s1",
        obs_type="tool",
        content=content,
        summary=summary,
        project_path=PROJECT,
    )


class TestObservationsSince:
    def test_empty_database_has_no_new_rows(self, db):
        assert observations_since(db, 0) == []
        assert max_observation_id(db) == 0

    def test_returns_only_rows_newer_than_since(self, db):
        first = add(db, "one")
        add(db, "two")
        third = add(db, "three")
        rows = observations_since(db, first)
        assert [row["id"] for row in rows] == [first + 1, third]

    def test_rows_are_ascending_and_compact(self, db):
        add(db, "one", summary="First")
        add(db, "two")
        rows = observations_since(db, 0)
        assert [row["id"] for row in rows] == sorted(row["id"] for row in rows)
        assert set(rows[0]) == {"id", "timestamp", "type", "summary", "project_path"}
        assert rows[0]["summary"] == "First"
        assert rows[0]["project_path"] == str(Path(PROJECT).resolve())

    def test_since_beyond_max_returns_nothing(self, db):
        add(db, "one")
        assert observations_since(db, max_observation_id(db)) == []

    def test_limit_caps_the_batch(self, db):
        for i in range(5):
            add(db, f"row {i}")
        assert len(observations_since(db, 0, limit=3)) == 3


@pytest.fixture
def viewer(tmp_path):
    db_path = tmp_path / "memory.db"
    add(MemoryDB(db_path=db_path), "existing row", summary="Before stream")
    server, token = build_server(db_path=db_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base, token, db_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def open_stream(base, query=""):
    host, port = base.removeprefix("http://").split(":")
    sock = socket.create_connection((host, int(port)), timeout=5)
    sock.sendall(f"GET /api/stream{query} HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n".encode())
    return sock


def read_until(sock, marker):
    wanted = marker.encode()
    data = b""
    while wanted not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", "replace")


class TestStreamEndpoint:
    def test_requires_a_token(self, viewer):
        base, _, _ = viewer
        sock = open_stream(base)
        try:
            assert "401" in read_until(sock, "\r\n")
        finally:
            sock.close()

    def test_streams_only_new_observations_by_default(self, viewer):
        base, token, db_path = viewer
        sock = open_stream(base, f"?token={token}")
        try:
            head = read_until(sock, "retry:")
            assert "text/event-stream" in head
            assert "no-cache" in head
            # The pre-existing row must not replay on a fresh connection.
            assert "Before stream" not in head

            db = MemoryDB(db_path=db_path)
            new_id = add(db, "just landed", summary="Live row")
            body = read_until(sock, "Live row")
            assert "event: observation" in body
            assert f'"id": {new_id}' in body
        finally:
            sock.close()

    def test_since_replays_newer_rows(self, viewer):
        base, token, _ = viewer
        sock = open_stream(base, f"?token={token}&since=0")
        try:
            body = read_until(sock, "Before stream")
            assert "event: observation" in body
        finally:
            sock.close()

    def test_keepalive_ping(self, viewer, monkeypatch):
        monkeypatch.setattr(viewer_module, "STREAM_PING_INTERVAL", 0.1)
        base, token, _ = viewer
        sock = open_stream(base, f"?token={token}")
        try:
            assert ": ping" in read_until(sock, ": ping")
        finally:
            sock.close()

    def test_closing_the_client_stops_the_handler_cleanly(self, viewer):
        base, token, _ = viewer
        sock = open_stream(base, f"?token={token}")
        read_until(sock, "retry:")
        sock.close()
        # A second connection still works: the dead one did not wedge the server.
        sock = open_stream(base, f"?token={token}")
        try:
            assert "retry:" in read_until(sock, "retry:")
        finally:
            sock.close()
