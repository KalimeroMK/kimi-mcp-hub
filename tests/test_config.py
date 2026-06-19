"""Tests for KimiConfig and MemoryDB."""

import json
import tempfile
from pathlib import Path

import pytest

from kimi_mcp_hub.config import KimiConfig
from kimi_mcp_hub.memory.db import MemoryDB


@pytest.fixture
def temp_config(tmp_path):
    """Return a KimiConfig pointing at temporary directories."""
    config = KimiConfig()
    # Override paths for isolation
    config.kimi_dir = tmp_path / ".kimi"
    config.mcp_json = config.kimi_dir / "mcp.json"
    config.skills_dir = tmp_path / ".kimi-code" / "skills"
    config.hub_dir = tmp_path / ".config" / "kimi-mcp-hub"
    config.tokens_file = config.hub_dir / "tokens.json"
    config.hub_dir.mkdir(parents=True, exist_ok=True)
    config.kimi_dir.mkdir(parents=True, exist_ok=True)
    return config


class TestKimiConfig:
    def test_add_remove_server(self, temp_config):
        temp_config.add_server("github", {"command": "npx", "args": ["server-github"]})
        servers = temp_config.list_servers()
        assert "github" in servers
        assert servers["github"]["command"] == "npx"

        temp_config.remove_server("github")
        assert "github" not in temp_config.list_servers()

    def test_mcp_json_is_valid_json(self, temp_config):
        temp_config.add_server("test", {"transport": "stdio"})
        data = json.loads(temp_config.mcp_json.read_text())
        assert "mcpServers" in data
        assert data["mcpServers"]["test"]["transport"] == "stdio"

    def test_save_load_token(self, temp_config):
        temp_config.save_token("github", {"access_token": "secret123"})
        loaded = temp_config.load_token("github")
        assert loaded["access_token"] == "secret123"


class TestMemoryDB:
    def test_init_creates_tables(self, tmp_path):
        db_path = tmp_path / "memory.db"
        db = MemoryDB(db_path=db_path)
        assert db_path.exists()
        stats = db.get_stats()
        assert stats["total_observations"] == 0
        assert stats["total_sessions"] == 0

    def test_add_and_search_observation(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_observation(
            session_id="sess-1",
            obs_type="tool",
            content="Ran pytest on the CLI module",
            summary="pytest run",
            tags=["test", "cli"],
        )
        results = db.search("pytest")
        assert len(results) == 1
        assert results[0]["content"] == "Ran pytest on the CLI module"

    def test_recent_observations(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_observation("sess-1", "note", "first")
        db.add_observation("sess-1", "note", "second")
        recent = db.get_recent(limit=2)
        assert len(recent) == 2
        assert recent[0]["content"] == "second"
