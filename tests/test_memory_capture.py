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

    def test_stop_falls_back_to_the_user_prompt_when_summary_is_missing(
        self, hooks, db, monkeypatch
    ):
        monkeypatch.setattr(MemoryHooks, "_summarize", lambda self, obs: None)
        hooks.user_prompt_submit(
            {
                "session_id": "s1",
                "cwd": PROJECT,
                "prompt": "Migrate the billing tables to UUID keys",
            }
        )
        hooks.stop({"session_id": "s1", "cwd": PROJECT})

        session = db.get_recent(session_id="s1", obs_type="session", limit=1)[0]
        assert session["summary"] == "Migrate the billing tables to UUID keys"
        assert session["content"].startswith("Title: Migrate the billing tables")


class TestToolDescriptions:
    def _call(self, hooks, name, tool_input, output="ok"):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": name,
                "tool_input": tool_input,
                "tool_output": output,
                "cwd": PROJECT,
            }
        )

    def test_label_names_the_command_or_file(self, hooks, db):
        self._call(hooks, "Bash", {"command": "pytest -q tests/"})
        self._call(hooks, "Edit", {"path": "src/app.py"})
        labels = {row["summary"] for row in db.get_recent()}
        assert labels == {"Bash: pytest -q tests/", "Edit: src/app.py"}

    def test_label_falls_back_when_there_is_no_input(self, hooks, db):
        self._call(hooks, "Bash", None)
        assert db.get_recent()[0]["summary"] == "Used Bash"

    def test_secrets_in_commands_are_redacted(self, hooks, db):
        self._call(
            hooks, "Bash", {"command": "curl -H 'Authorization: Bearer abc123' x.io"}
        )
        self._call(hooks, "Bash", {"command": "deploy --api-key=sk-live-1234567890"})
        for row in db.get_recent():
            assert "abc123" not in row["summary"]
            assert "1234567890" not in row["summary"]

    def test_private_spans_in_commands_are_dropped(self, hooks, db):
        self._call(hooks, "Bash", {"command": "echo <private>hunter2</private> done"})
        assert "hunter2" not in db.get_recent()[0]["summary"]

    def test_each_file_read_is_kept_not_just_the_first(self, hooks, db):
        for name in ("a.py", "b.py", "c.py"):
            self._call(hooks, "Read", {"path": name})
        assert db.get_stats()["total_observations"] == 3


class TestOfflineSessionSummary:
    """With no LLM at all, a session must still be recallable."""

    def _session(self, hooks):
        hooks.user_prompt_submit(
            {
                "session_id": "s1",
                "cwd": PROJECT,
                "prompt": "Write the press release for instacom",
            }
        )
        for name, tool_input in (
            ("Write", {"path": "docs/press.md"}),
            ("Edit", {"path": "docs/press.md"}),
            ("Bash", {"command": "git add docs"}),
        ):
            hooks.post_tool_use(
                {
                    "session_id": "s1",
                    "tool_name": name,
                    "tool_input": tool_input,
                    "tool_output": "done",
                    "cwd": PROJECT,
                }
            )

    def test_summary_lists_requests_files_and_commands(self, hooks, db, monkeypatch):
        monkeypatch.setattr(MemoryHooks, "_summarize", lambda self, obs: None)
        self._session(hooks)
        hooks.stop({"session_id": "s1", "cwd": PROJECT})

        row = db.get_recent(session_id="s1", obs_type="session")[0]
        assert row["summary"] == "Write the press release for instacom"
        assert "Files changed: docs/press.md" in row["content"]
        assert "Commands: git add docs" in row["content"]

    def test_session_keeps_one_row_across_turns_and_stays_searchable(
        self, hooks, db, monkeypatch
    ):
        monkeypatch.setattr(MemoryHooks, "_summarize", lambda self, obs: None)
        self._session(hooks)
        for _ in range(3):
            hooks.stop({"session_id": "s1", "cwd": PROJECT})

        assert len(db.get_recent(session_id="s1", obs_type="session")) == 1
        assert db.search("press release", obs_type="session", project_path=PROJECT)
        with db._connect() as conn:
            conn.execute(
                "INSERT INTO observations_fts(observations_fts) VALUES('integrity-check')"
            )

    def test_generated_summary_is_not_downgraded(self, hooks, db, monkeypatch):
        self._session(hooks)
        monkeypatch.setattr(MemoryHooks, "_summarize", lambda self, obs: "Title: LLM")
        hooks.stop({"session_id": "s1", "cwd": PROJECT})
        monkeypatch.setattr(MemoryHooks, "_summarize", lambda self, obs: None)
        hooks.stop({"session_id": "s1", "cwd": PROJECT})

        row = db.get_recent(session_id="s1", obs_type="session")[0]
        assert row["content"] == "Title: LLM"

    def test_empty_session_gets_no_fake_summary(self, hooks, db, monkeypatch):
        monkeypatch.setattr(MemoryHooks, "_summarize", lambda self, obs: None)
        hooks.stop({"session_id": "s1", "cwd": PROJECT})
        assert db.get_recent(obs_type="session")[0]["summary"] == "Session completed"


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


class TestUserPromptCapture:
    def test_prompt_is_stored_and_searchable(self, hooks, db):
        hooks.user_prompt_submit(
            {
                "session_id": "s1",
                "cwd": PROJECT,
                "prompt": "Write the press release for instacom",
            }
        )
        stored = db.get_recent(session_id="s1", obs_type="user")[0]
        assert stored["type"] == "user"
        assert stored["content"] == "Write the press release for instacom"
        assert stored["project_path"] == PROJECT

        hits = db.search("press release", project_path=PROJECT, obs_type="user")
        assert len(hits) == 1

    def test_identical_prompt_is_stored_once(self, hooks, db):
        payload = {
            "session_id": "s1",
            "cwd": PROJECT,
            "prompt": "deploy to production now",
        }
        hooks.user_prompt_submit(payload)
        hooks.user_prompt_submit(payload)
        assert db.get_stats()["total_observations"] == 1

    def test_short_prompts_are_not_stored(self, hooks, db):
        hooks.user_prompt_submit({"session_id": "s1", "cwd": PROJECT, "prompt": "hi"})
        assert db.get_recent(obs_type="user") == []

    def test_prompts_are_project_scoped(self, hooks, db):
        hooks.user_prompt_submit(
            {"session_id": "s1", "cwd": OTHER, "prompt": "secret launch plan"}
        )
        assert db.search("secret", project_path=PROJECT, obs_type="user") == []


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


class TestSessionTitles:
    """The session list is only useful if titles say what happened."""

    def test_explicit_title_line_wins(self):
        from kimi_mcp_hub.memory.hooks import _first_line

        assert (
            _first_line("Title: Added the memory MCP server\n\n## Goal\n- x")
            == "Added the memory MCP server"
        )

    def test_bold_title_line(self):
        from kimi_mcp_hub.memory.hooks import _first_line

        assert (
            _first_line("**Title:** Fixed FTS5 escaping\n\nbody")
            == "Fixed FTS5 escaping"
        )

    def test_generic_headings_are_skipped(self):
        from kimi_mcp_hub.memory.hooks import _first_line

        text = "## Coding Session Summary\n\n### Goal\n\nMigrated billing to UUID keys"
        assert _first_line(text) == "Migrated billing to UUID keys"

    def test_section_names_are_not_titles(self):
        from kimi_mcp_hub.memory.hooks import _first_line

        assert _first_line("# Summary\n\n## Goal:\n\nReworked the importer") == (
            "Reworked the importer"
        )

    def test_empty_summary_yields_no_title(self):
        from kimi_mcp_hub.memory.hooks import _first_line

        assert _first_line("") == ""
        assert _first_line(None) == ""

    def test_title_is_trimmed(self):
        from kimi_mcp_hub.memory.hooks import _first_line

        assert len(_first_line("Title: " + "x" * 500)) == 160

    def test_stop_stores_the_generated_title(self, hooks, db, monkeypatch):
        monkeypatch.setattr(
            MemoryHooks,
            "_summarize",
            lambda self, obs: (
                "Title: Recovered project paths from vault notes\n\n## Goal\n- x"
            ),
        )
        hooks.stop({"session_id": "s1", "cwd": PROJECT})
        row = db.get_recent(session_id="s1", obs_type="session", limit=1)[0]
        assert row["summary"] == "Recovered project paths from vault notes"


class TestModelWrittenSummary:
    """With no summary provider, the active model is asked to write it."""

    def _work(self, hooks, count=6, session="s1", offset=0):
        hooks.user_prompt_submit(
            {"session_id": session, "cwd": PROJECT, "prompt": "Write the press release"}
        )
        for index in range(count - 1):
            hooks.post_tool_use(
                {
                    "session_id": session,
                    "tool_name": "Bash",
                    "tool_input": {"command": f"step {offset + index}"},
                    "tool_output": f"out {offset + index}",
                    "cwd": PROJECT,
                }
            )

    @pytest.fixture(autouse=True)
    def no_provider(self, monkeypatch):
        monkeypatch.setattr(MemoryHooks, "_summarize", lambda self, obs: None)

    def test_asks_the_model_once_enough_has_happened(self, hooks):
        self._work(hooks)
        request = hooks.stop({"session_id": "s1", "cwd": PROJECT})
        assert "memory_summarize" in request
        assert 'session_id: "s1"' in request

    def test_does_not_ask_for_a_small_session(self, hooks):
        self._work(hooks, count=3)
        assert hooks.stop({"session_id": "s1", "cwd": PROJECT}) is None

    def test_does_not_loop_on_its_own_block(self, hooks):
        self._work(hooks)
        payload = {"session_id": "s1", "cwd": PROJECT, "stop_hook_active": True}
        assert hooks.stop(payload) is None

    def test_asks_only_once_per_batch_of_work(self, hooks):
        self._work(hooks)
        assert hooks.stop({"session_id": "s1", "cwd": PROJECT})
        assert hooks.stop({"session_id": "s1", "cwd": PROJECT}) is None
        self._work(hooks, count=7, offset=100)
        assert hooks.stop({"session_id": "s1", "cwd": PROJECT})

    def test_a_model_summary_resets_the_counter(self, hooks, db):
        self._work(hooks)
        db.add_observation(
            "s1", "session", "Title: X", "X", ["session", "model"], PROJECT
        )
        assert hooks.stop({"session_id": "s1", "cwd": PROJECT}) is None

    def test_provider_summary_means_no_request(self, hooks, monkeypatch):
        monkeypatch.setattr(MemoryHooks, "_summarize", lambda self, obs: "Title: LLM")
        self._work(hooks)
        assert hooks.stop({"session_id": "s1", "cwd": PROJECT}) is None

    def test_can_be_turned_off(self, hooks):
        from kimi_mcp_hub.config import KimiConfig

        config = KimiConfig()
        data = config.load_toml_config()
        data.setdefault("memory", {})["summary_by_model"] = False
        config.save_toml_config(data)

        self._work(hooks)
        assert hooks.stop({"session_id": "s1", "cwd": PROJECT}) is None

    def test_marker_rows_stay_out_of_the_session_context(self, hooks, db):
        self._work(hooks)
        hooks.stop({"session_id": "s1", "cwd": PROJECT})
        assert "summary requested" not in hooks.session_start({"cwd": PROJECT})

    def test_cli_blocks_the_stop_with_exit_code_2(self, db):
        import json
        import subprocess
        import sys

        hooks = MemoryHooks(db=MemoryDB())
        self._work(hooks)
        result = subprocess.run(
            [sys.executable, "-m", "kimi_mcp_hub.memory_hook", "stop"],
            input=json.dumps({"session_id": "s1", "cwd": PROJECT}),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert "memory_summarize" in result.stderr
