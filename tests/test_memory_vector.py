"""Tests for semantic vector search (sqlite-vec + EmbeddingClient)."""

import hashlib
import sys

import pytest

from kimi_mcp_hub.memory.db import MemoryDB
from kimi_mcp_hub.memory.embeddings import EmbeddingClient
from kimi_mcp_hub.memory.mcp_server import MemoryMCPServer

# One axis per document so ranking is obvious and deterministic.
_VECTORS = {
    "apple pie recipe": [1.0, 0.0, 0.0],
    "banana bread guide": [0.0, 1.0, 0.0],
    "cherry tart notes": [0.0, 0.0, 1.0],
    "an apple dessert for dinner": [0.5, 0.4, 0.1],
    "apple dessert": [0.9, 0.1, 0.0],
}


def fake_embed(texts: list[str]) -> list[list[float]]:
    return [_VECTORS[text] for text in texts]


def hash_embed(texts: list[str]) -> list[list[float]]:
    return [
        [b / 255.0 for b in hashlib.sha256(t.encode()).digest()[:8]] for t in texts
    ]


def make_vec_db(tmp_path, embed_on_insert=True) -> MemoryDB:
    db = MemoryDB(
        db_path=tmp_path / "memory.db",
        embedding_client=EmbeddingClient(embed=fake_embed),
        embed_on_insert=embed_on_insert,
    )
    if not db.vec_available:
        pytest.skip("sqlite-vec not installed")
    return db


class TestEmbeddingClient:
    def test_unavailable_without_configuration(self):
        client = EmbeddingClient()
        assert client.available is False
        assert client.embed(["hello"]) is None

    def test_injected_embed_callable_is_used(self):
        client = EmbeddingClient(embed=fake_embed)
        assert client.available is True
        assert client.embed(["apple pie recipe"]) == [[1.0, 0.0, 0.0]]

    def test_failing_callable_reports_unavailable(self):
        def boom(texts):
            raise RuntimeError("nope")

        client = EmbeddingClient(embed=boom)
        assert client.embed(["x"]) is None

    def test_network_error_reports_unavailable(self, monkeypatch):
        def boom(*args, **kwargs):
            raise ConnectionError("offline")

        monkeypatch.setattr("requests.post", boom)
        client = EmbeddingClient(
            api_key="k", model="m", base_url="http://localhost:1"
        )
        assert client.embed(["x"]) is None

    def test_http_error_reports_unavailable(self, monkeypatch):
        class Resp:
            ok = False
            status_code = 500

        monkeypatch.setattr("requests.post", lambda *a, **k: Resp())
        client = EmbeddingClient(
            api_key="k", model="m", base_url="http://localhost:1"
        )
        assert client.embed(["x"]) is None


class TestVectorIndex:
    def test_vec_table_created_on_first_embed(self, tmp_path):
        db = make_vec_db(tmp_path)
        db.add_observation("sess-1", "note", "apple pie recipe")
        with db._connect() as conn:
            rows = conn.execute(
                "SELECT rowid, embedding FROM observation_vec"
            ).fetchall()
        assert len(rows) == 1

    def test_embedding_on_insert_is_opt_in(self, tmp_path):
        db = MemoryDB(
            db_path=tmp_path / "memory.db",
            embedding_client=EmbeddingClient(embed=fake_embed),
        )
        db.add_observation("sess-1", "note", "apple pie recipe")
        if db.vec_available:
            with db._connect() as conn:
                table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE name = 'observation_vec'"
                ).fetchone()
            assert table is None

    def test_vector_search_ranks_by_distance(self, tmp_path):
        db = make_vec_db(tmp_path)
        apple_id = db.add_observation("sess-1", "note", "apple pie recipe")
        db.add_observation("sess-1", "note", "banana bread guide")
        db.add_observation("sess-1", "note", "cherry tart notes")

        results = db.vector_search(_VECTORS["apple dessert"], limit=3)
        assert [r["id"] for r in results] == [apple_id, 2, 3]
        assert results[0]["distance"] <= results[1]["distance"]

    def test_vector_search_filters_by_project(self, tmp_path):
        db = make_vec_db(tmp_path)
        db.add_observation(
            "sess-1", "note", "apple pie recipe", project_path=str(tmp_path / "proj")
        )
        db.add_observation("sess-1", "note", "banana bread guide")
        results = db.vector_search(
            _VECTORS["apple dessert"],
            limit=5,
            project_path=str(tmp_path / "proj"),
        )
        assert len(results) == 1

    def test_vector_search_empty_when_nothing_embedded(self, tmp_path):
        db = make_vec_db(tmp_path)
        db.add_observation("sess-1", "note", "apple pie recipe")
        db2 = MemoryDB(
            db_path=tmp_path / "empty.db",
            embedding_client=EmbeddingClient(embed=fake_embed),
        )
        assert db2.vector_search(_VECTORS["apple dessert"], limit=5) == []


class TestServerModes:
    def make_server(self, tmp_path) -> MemoryMCPServer:
        db = make_vec_db(tmp_path)
        for text in (
            "apple pie recipe",
            "banana bread guide",
            "cherry tart notes",
            "an apple dessert for dinner",
        ):
            db.add_observation("sess-1", "note", text)
        return MemoryMCPServer(
            db=db, embedding_client=EmbeddingClient(embed=fake_embed)
        )

    def call(self, server, args) -> str:
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "memory_search", "arguments": args},
            }
        )
        return response["result"]["content"][0]["text"]

    def test_semantic_mode_finds_by_meaning(self, tmp_path):
        server = self.make_server(tmp_path)
        text = self.call(server, {"query": "apple dessert", "mode": "semantic", "all_projects": True})
        assert "#1" in text.splitlines()[1]
        assert "unavailable" not in text

    def test_hybrid_mode_merges_keyword_and_semantic(self, tmp_path):
        server = self.make_server(tmp_path)
        # FTS matches only #4 ("apple" AND "dessert"); semantic ranks #1 first.
        # RRF promotes the FTS hit to the top while keeping the semantic hit.
        text = self.call(
            server, {"query": "apple dessert", "mode": "hybrid", "all_projects": True}
        )
        assert "unavailable" not in text
        assert "#4" in text.splitlines()[1]
        assert "#1" in text

    def test_semantic_falls_back_to_keyword_when_unavailable(self, tmp_path):
        db = make_vec_db(tmp_path)
        db.add_observation("sess-1", "note", "apple pie recipe")
        server = MemoryMCPServer(db=db, embedding_client=EmbeddingClient())
        text = self.call(server, {"query": "apple pie", "mode": "semantic", "all_projects": True})
        assert "semantic search unavailable" in text
        assert "#1" in text

    def test_hybrid_falls_back_to_keyword_when_unavailable(self, tmp_path):
        db = make_vec_db(tmp_path)
        db.add_observation("sess-1", "note", "apple pie recipe")
        server = MemoryMCPServer(db=db, embedding_client=EmbeddingClient())
        text = self.call(server, {"query": "apple pie", "mode": "hybrid", "all_projects": True})
        assert "semantic search unavailable" in text
        assert "#1" in text

    def test_invalid_mode_is_rejected(self, tmp_path):
        server = self.make_server(tmp_path)
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "memory_search", "arguments": {"query": "x", "mode": "bogus", "all_projects": True}},
            }
        )
        assert response["result"]["isError"] is True

    def test_keyword_mode_is_unchanged(self, tmp_path):
        server = self.make_server(tmp_path)
        text = self.call(server, {"query": "banana bread", "all_projects": True})
        assert "#2" in text
        assert "unavailable" not in text


class TestSqliteVecMissing:
    def test_vector_features_disable_gracefully(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "sqlite_vec", None)
        db = MemoryDB(
            db_path=tmp_path / "memory.db",
            embedding_client=EmbeddingClient(embed=hash_embed),
            embed_on_insert=True,
        )
        assert db.vec_available is False
        row_id = db.add_observation("sess-1", "note", "apple pie recipe")
        assert db.embed_observation(row_id, "apple pie recipe") is False
        assert db.vector_search([1.0, 0.0, 0.0], limit=5) == []
        # Keyword search keeps working.
        assert len(db.search("apple")) == 1
