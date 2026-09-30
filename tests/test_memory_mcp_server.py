"""Tests for the stdio MCP server that exposes persistent memory."""

import io
import json
from pathlib import Path

import pytest

from kimi_mcp_hub.memory.db import MemoryDB
from kimi_mcp_hub.memory.mcp_server import (
    DEFAULT_PROTOCOL_VERSION,
    MemoryMCPServer,
    serve,
)

PROJECT = "/tmp/kimi-mcp-project"
OTHER_PROJECT = "/tmp/other-project"


@pytest.fixture
def db(tmp_path):
    database = MemoryDB(db_path=tmp_path / "memory.db")
    database.add_observation(
        session_id="s1",
        obs_type="session",
        content="Rewrote the parser so quoted input stops breaking search",
        summary="Fixed parser quoting",
        tags=["session"],
        project_path=PROJECT,
    )
    database.add_observation(
        session_id="s1",
        obs_type="tool",
        content="pytest output, 314 passed",
        summary="Used Bash",
        tags=["Bash"],
        project_path=PROJECT,
    )
    database.add_observation(
        session_id="s2",
        obs_type="session",
        content="Unrelated work on the parser in another repository",
        summary="Other project parser work",
        tags=["session"],
        project_path=OTHER_PROJECT,
    )
    return database


@pytest.fixture
def server(db):
    return MemoryMCPServer(db=db)


def call(server, name, arguments, msg_id=1):
    """Invoke a tool and return (text, is_error)."""
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    result = response["result"]
    return result["content"][0]["text"], result.get("isError", False)


class TestProtocol:
    def test_initialize_echoes_supported_protocol_version(self, server):
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            }
        )
        assert response["result"]["protocolVersion"] == "2025-06-18"
        assert response["result"]["serverInfo"]["name"] == "kimi-memory"

    def test_initialize_falls_back_for_unknown_protocol_version(self, server):
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "1999-01-01"},
            }
        )
        assert response["result"]["protocolVersion"] == DEFAULT_PROTOCOL_VERSION

    def test_notifications_get_no_response(self, server):
        assert (
            server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
            is None
        )

    def test_tools_list_exposes_the_workflow(self, server):
        response = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [tool["name"] for tool in response["result"]["tools"]]
        assert names == [
            "memory_search",
            "memory_timeline",
            "memory_get",
            "memory_summarize",
            "memory_save",
        ]

    def test_unknown_method_is_an_error(self, server):
        response = server.handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})
        assert response["error"]["code"] == -32601

    def test_unknown_tool_is_an_error(self, server):
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "memory_delete_everything", "arguments": {}},
            }
        )
        assert response["error"]["code"] == -32601


class TestSearch:
    def test_returns_compact_index_without_bodies(self, server):
        text, is_error = call(
            server, "memory_search", {"query": "parser", "project": PROJECT}
        )
        assert not is_error
        assert "#1" in text
        assert "Fixed parser quoting" in text
        # The whole point of the index layer is that it omits content.
        assert "Rewrote the parser" not in text

    def test_scopes_to_the_requested_project(self, server):
        text, _ = call(server, "memory_search", {"query": "parser", "project": PROJECT})
        assert "Other project parser work" not in text

    def test_all_projects_widens_the_scope(self, server):
        text, _ = call(
            server,
            "memory_search",
            {"query": "parser", "project": PROJECT, "all_projects": True},
        )
        assert "Other project parser work" in text

    def test_type_filter(self, server):
        text, _ = call(
            server,
            "memory_search",
            {"query": "parser OR pytest", "project": PROJECT, "type": "tool"},
        )
        assert "Fixed parser quoting" not in text

    def test_punctuation_does_not_break_the_query(self, server):
        """Unescaped input used to raise an FTS5 syntax error, returning nothing."""
        text, is_error = call(
            server,
            "memory_search",
            {"query": 'C++ AND "unbalanced) quoting?', "project": PROJECT},
        )
        assert not is_error
        assert "No memory matches" in text

    def test_empty_query_is_a_tool_error(self, server):
        text, is_error = call(server, "memory_search", {"query": "   "})
        assert is_error
        assert "query" in text

    def test_no_results_suggests_widening(self, server):
        text, _ = call(
            server, "memory_search", {"query": "kubernetes", "project": PROJECT}
        )
        assert "all_projects=true" in text


class TestTimeline:
    def test_surrounds_the_anchor(self, server):
        text, _ = call(server, "memory_timeline", {"anchor_id": 1, "project": PROJECT})
        assert "> #1" in text
        assert "#2" in text

    def test_missing_anchor_reports_clearly(self, server):
        text, _ = call(server, "memory_timeline", {"anchor_id": 999})
        assert "No observation with id 999" in text


class TestGet:
    def test_returns_full_content(self, server):
        text, _ = call(server, "memory_get", {"ids": [1]})
        assert "Rewrote the parser" in text

    def test_rejects_non_list_ids(self, server):
        text, is_error = call(server, "memory_get", {"ids": "1"})
        assert is_error

    def test_caps_the_number_of_ids(self, server):
        text, _ = call(server, "memory_get", {"ids": list(range(1, 40))})
        assert "omitted" in text


class TestSave:
    def test_saves_a_project_note(self, server, db):
        text, is_error = call(
            server,
            "memory_save",
            {"content": "Prefer FTS phrases over raw MATCH", "project": PROJECT},
        )
        assert not is_error
        notes = db.get_memories(project_path=PROJECT, category="project")
        assert notes[0]["content"] == "Prefer FTS phrases over raw MATCH"

    def test_empty_content_is_rejected(self, server):
        _, is_error = call(server, "memory_save", {"content": "  "})
        assert is_error


class TestSummarize:
    def test_model_summary_becomes_the_session_row(self, server, db):
        db.add_observation("s1", "user", "Write the press release", None, [], PROJECT)
        db.add_observation(
            "s1", "session", "Title: auto", "auto", ["session", "auto"], PROJECT
        )
        text, is_error = call(
            server,
            "memory_summarize",
            {
                "session_id": "s1",
                "title": "Drafted the instacom press release",
                "summary": "- Headline: Instacom launches\n- Saved to docs/press.md",
            },
        )
        assert not is_error

        rows = db.get_recent(session_id="s1", obs_type="session")
        assert len(rows) == 1
        assert rows[0]["summary"] == "Drafted the instacom press release"
        assert "Headline: Instacom launches" in rows[0]["content"]
        assert "auto" not in rows[0]["tags"]
        assert rows[0]["project_path"] == str(Path(PROJECT).resolve())
        assert db.search("Instacom launches", obs_type="session", project_path=PROJECT)

    def test_title_defaults_to_the_first_summary_line(self, server, db):
        call(
            server, "memory_summarize", {"session_id": "s1", "summary": "- Did X\n- Y"}
        )
        assert db.get_recent(obs_type="session")[0]["summary"] == "Did X"

    def test_private_spans_are_not_stored(self, server, db):
        call(
            server,
            "memory_summarize",
            {"session_id": "s1", "summary": "Deployed. <private>pw=hunter2</private>"},
        )
        assert "hunter2" not in db.get_recent(obs_type="session")[0]["content"]

    def test_requires_session_id_and_summary(self, server):
        _, is_error = call(server, "memory_summarize", {"session_id": "s1"})
        assert is_error


class TestServeLoop:
    def test_reads_ndjson_and_writes_responses(self, db):
        stdin = io.StringIO(
            '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
            "\n"
            '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
            '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
        )
        stdout = io.StringIO()
        assert serve(stdin=stdin, stdout=stdout, db=db) == 0

        lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
        # Blank lines and notifications produce no frames.
        assert [msg["id"] for msg in lines] == [1, 2]

    def test_malformed_json_gets_a_parse_error(self, db):
        stdout = io.StringIO()
        serve(stdin=io.StringIO("{not json\n"), stdout=stdout, db=db)
        assert json.loads(stdout.getvalue())["error"]["code"] == -32700
