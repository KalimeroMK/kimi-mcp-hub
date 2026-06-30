"""Tests for MemoryDB."""

import json

import pytest

from kimi_mcp_hub.memory.db import MemoryDB


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

    def test_add_and_search_memory(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_memory("Use pytest for tests", category="user", tags=["testing"])
        results = db.search_memories("pytest")
        assert len(results) == 1
        assert results[0]["content"] == "Use pytest for tests"

    def test_get_memories_by_category(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_memory("project fact", category="project", project_path="/foo")
        db.add_memory("user fact", category="user")
        assert len(db.get_memories(category="project")) == 1

    def test_delete_memory(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        mem_id = db.add_memory("to delete")
        assert db.delete_memory(mem_id) is True
        assert db.delete_memory(mem_id) is False

    def test_delete_nonexistent_memory_returns_false(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        assert db.delete_memory(999) is False

    def test_search_empty_query_returns_empty(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_memory("Use pytest for tests", category="user", tags=["testing"])
        assert db.search_memories("") == []
        assert db.search_memories("   ") == []

    def test_add_memory_with_tags_round_trip(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        tags = ["testing", "cli"]
        mem_id = db.add_memory("Use pytest for tests", category="user", tags=tags)

        by_search = db.search_memories("cli")
        assert len(by_search) == 1
        assert json.loads(by_search[0]["tags"]) == tags

        by_id = db.get_memories(limit=1)
        assert by_id[0]["id"] == mem_id
        assert json.loads(by_id[0]["tags"]) == tags

    def test_get_memory_stats(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_memory("project fact", category="project", project_path="/foo")
        db.add_memory("user fact", category="user")
        db.add_memory("another project fact", category="project")

        stats = db.get_memory_stats()
        assert stats["total_memories"] == 3
        assert stats["categories"] == {"project": 2, "user": 1}

    def test_search_memories_with_category_and_project_path(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_memory("project alpha fact", category="project", project_path="/alpha")
        db.add_memory("project beta fact", category="project", project_path="/beta")
        db.add_memory("user alpha fact", category="user", project_path="/alpha")

        results = db.search_memories("fact", category="project", project_path="/alpha")
        assert len(results) == 1
        assert results[0]["content"] == "project alpha fact"

    def test_get_memories_by_project_path(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_memory("project alpha fact", category="project", project_path="/alpha")
        db.add_memory("project beta fact", category="project", project_path="/beta")
        db.add_memory("user alpha fact", category="user", project_path="/alpha")

        alpha = db.get_memories(project_path="/alpha")
        assert len(alpha) == 2
        assert all(m["project_path"] == "/alpha" for m in alpha)

    def test_get_memory_stats_empty_db(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        stats = db.get_memory_stats()
        assert stats["total_memories"] == 0
        assert stats["categories"] == {}

    def test_search_observations_empty_query_returns_empty(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_observation("sess-1", "note", "observable content")
        assert db.search("") == []
        assert db.search("   ") == []

    def test_search_with_malformed_fts_query_returns_empty(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_observation("sess-1", "note", "observable content")
        assert db.search('"unmatched quote') == []

    def test_search_memories_with_malformed_fts_query_returns_empty(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_memory("observable content", category="general")
        assert db.search_memories('"unmatched quote') == []

    def test_negative_limit_raises_value_error(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        with pytest.raises(ValueError, match="limit must be non-negative"):
            db.search("content", limit=-1)
        with pytest.raises(ValueError, match="limit must be non-negative"):
            db.search_memories("content", limit=-1)
        with pytest.raises(ValueError, match="limit must be non-negative"):
            db.get_recent(limit=-1)
        with pytest.raises(ValueError, match="limit must be non-negative"):
            db.get_memories(limit=-1)
