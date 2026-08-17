"""Tests for observation capture: project scoping, dedup, and noise filtering.

These cover behaviour that regressed silently before: observations were stored
without a project, every repeated tool call created a new row, and read-only
tools filled the database with file dumps.
"""

from pathlib import Path

import pytest

from kimi_mcp_hub.memory.db import MemoryDB
from kimi_mcp_hub.memory.hooks import MemoryHooks

# Resolved so assertions match what the code stores (on macOS /tmp is a
# symlink to /private/tmp).
PROJECT = str(Path("/tmp/kimi-capture-project").resolve())
OTHER = str(Path("/tmp/kimi-other-project").resolve())


@pytest.fixture
def db(tmp_path):
    return MemoryDB(db_path=tmp_path / "memory.db")


@pytest.fixture
def hooks(db):
    return MemoryHooks(db=db)


class TestProjectAttribution:
    def test_tool_observations_record_the_project(self, hooks, db):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "done",
                "cwd": PROJECT,
            }
        )
        stored = db.get_recent()[0]
        assert stored["project_path"] == PROJECT

    def test_project_path_is_resolved(self, hooks, db):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "done",
                "cwd": "/tmp/../tmp/kimi-capture-project",
            }
        )
        assert db.get_recent()[0]["project_path"] == PROJECT

    def test_missing_cwd_falls_back_to_the_working_directory(self, hooks, db):
        hooks.post_tool_use(
            {"session_id": "s1", "tool_name": "Bash", "tool_response": "done"}
        )
        assert db.get_recent()[0]["project_path"]

    def test_session_start_ignores_other_projects(self, hooks, db):
        db.add_observation("s0", "tool", "noise", "Used Other", ["x"], OTHER)
        db.add_observation("s0", "tool", "signal", "Used Mine", ["x"], PROJECT)

        context = hooks.session_start({"cwd": PROJECT})
        assert "Used Mine" in context
        assert "Used Other" not in context

    def test_session_start_without_a_project_shows_everything(self, hooks, db):
        db.add_observation("s0", "tool", "noise", "Used Other", ["x"], OTHER)
        assert "Used Other" in hooks.session_start({})


class TestDeduplication:
    def test_identical_tool_results_are_stored_once(self, hooks, db):
        payload = {
            "session_id": "s1",
            "tool_name": "Bash",
            "tool_response": "same output",
            "cwd": PROJECT,
        }
        hooks.post_tool_use(payload)
        hooks.post_tool_use(payload)
        hooks.post_tool_use(payload)
        assert db.get_stats()["total_observations"] == 1

    def test_different_results_are_kept(self, hooks, db):
        for output in ("first", "second"):
            hooks.post_tool_use(
                {
                    "session_id": "s1",
                    "tool_name": "Bash",
                    "tool_response": output,
                    "cwd": PROJECT,
                }
            )
        assert db.get_stats()["total_observations"] == 2

    def test_dedup_is_scoped_to_one_session(self, hooks, db):
        for session in ("s1", "s2"):
            hooks.post_tool_use(
                {
                    "session_id": session,
                    "tool_name": "Bash",
                    "tool_response": "same output",
                    "cwd": PROJECT,
                }
            )
        assert db.get_stats()["total_observations"] == 2


class TestNoiseFiltering:
    def test_read_only_tool_bodies_are_dropped(self, hooks, db):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Read",
                "tool_response": "a very long file body " * 50,
                "cwd": PROJECT,
            }
        )
        stored = db.get_recent()[0]
        # The call is still on the timeline, the payload is not.
        assert stored["summary"] == "Used Read"
        assert stored["content"] == "[Read output omitted]"

    def test_working_tool_bodies_are_kept(self, hooks, db):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "test suite passed",
                "cwd": PROJECT,
            }
        )
        assert db.get_recent()[0]["content"] == "test suite passed"

    def test_capture_all_env_var_disables_filtering(self, hooks, db, monkeypatch):
        monkeypatch.setenv("KIMI_MEMORY_CAPTURE_ALL", "1")
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Read",
                "tool_response": "file body",
                "cwd": PROJECT,
            }
        )
        assert db.get_recent()[0]["content"] == "file body"

    def test_skip_list_env_var_extends_filtering(self, hooks, db, monkeypatch):
        monkeypatch.setenv("KIMI_MEMORY_SKIP_TOOLS", "Bash")
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "noisy build log",
                "cwd": PROJECT,
            }
        )
        assert db.get_recent()[0]["content"] == "[Bash output omitted]"


class TestSessionSummaryIsSearchable:
    def test_stop_stores_the_summary_as_an_observation(self, hooks, db, monkeypatch):
        monkeypatch.setattr(
            MemoryHooks,
            "_summarize",
            lambda self, observations: "Migrated the billing tables to UUID keys",
        )
        hooks.stop({"session_id": "s1", "cwd": PROJECT})

        hits = db.search("billing UUID", project_path=PROJECT, obs_type="session")
        assert len(hits) == 1
        assert hits[0]["summary"] == "Migrated the billing tables to UUID keys"

    def test_stop_without_a_summary_still_records_the_session(
        self, hooks, db, monkeypatch
    ):
        monkeypatch.setattr(MemoryHooks, "_summarize", lambda self, obs: None)
        hooks.stop({"session_id": "s1", "cwd": PROJECT})
        assert db.get_recent(obs_type="session")[0]["content"] == "Session ended"


class TestUserPromptSubmit:
    def test_injects_matching_project_notes(self, hooks, db):
        db.add_memory("Billing uses UUID primary keys", "project", [], PROJECT)
        context = hooks.user_prompt_submit(
            {"cwd": PROJECT, "prompt": "how are billing keys generated?"}
        )
        assert "UUID primary keys" in context

    def test_injects_matching_past_sessions(self, hooks, db):
        db.add_observation(
            "s0",
            "session",
            "Rewrote the billing importer to stream rows",
            "Billing importer rewrite",
            ["session"],
            PROJECT,
        )
        context = hooks.user_prompt_submit(
            {"cwd": PROJECT, "prompt": "what changed in the billing importer?"}
        )
        assert "Billing importer rewrite" in context
        assert "memory_get" in context

    def test_ignores_other_projects(self, hooks, db):
        db.add_memory("Secret from another repo", "project", [], OTHER)
        context = hooks.user_prompt_submit(
            {"cwd": PROJECT, "prompt": "tell me the secret from another repo"}
        )
        assert context == ""

    def test_short_prompts_are_skipped(self, hooks, db):
        db.add_memory("Billing uses UUID primary keys", "project", [], PROJECT)
        assert hooks.user_prompt_submit({"cwd": PROJECT, "prompt": "hi"}) == ""

    def test_no_matches_injects_nothing(self, hooks):
        assert (
            hooks.user_prompt_submit({"cwd": PROJECT, "prompt": "unrelated question"})
            == ""
        )


class TestBrowseAndTimeline:
    def _seed(self, db, count=5):
        for index in range(count):
            db.add_observation(
                "s1", "tool", f"content {index}", f"summary {index}", [], PROJECT
            )

    def test_browse_paginates_newest_first(self, db):
        self._seed(db)
        page, total = db.browse_observations(limit=2, offset=0, project_path=PROJECT)
        assert total == 5
        assert [row["summary"] for row in page] == ["summary 4", "summary 3"]

        page, _ = db.browse_observations(limit=2, offset=2, project_path=PROJECT)
        assert [row["summary"] for row in page] == ["summary 2", "summary 1"]

    def test_timeline_returns_neighbours_in_order(self, db):
        self._seed(db)
        rows = db.timeline(3, before=1, after=1, project_path=PROJECT)
        assert [row["id"] for row in rows] == [2, 3, 4]

    def test_timeline_clamps_at_the_edges(self, db):
        self._seed(db)
        assert [row["id"] for row in db.timeline(1, before=5, after=1)] == [1, 2]

    def test_timeline_for_unknown_anchor_is_empty(self, db):
        assert db.timeline(42) == []

    def test_list_projects_and_types(self, db):
        self._seed(db, count=2)
        db.add_observation("s1", "session", "done", "Session", [], OTHER)
        assert db.list_projects()[0] == {"project_path": PROJECT, "count": 2}
        assert db.list_types() == ["session", "tool"]

    def test_search_index_omits_content(self, db):
        self._seed(db, count=1)
        row = db.search_index("summary", project_path=PROJECT)[0]
        assert "content" not in row
        assert row["summary"] == "summary 0"
