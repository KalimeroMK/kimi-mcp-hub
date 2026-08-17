"""Tests for the memory block injected at session start.

Every line here is spent from each session's context window, so the tests are
mostly about what gets left out.
"""

import sqlite3
from pathlib import Path

import pytest

from kimi_mcp_hub.memory.context import build_context
from kimi_mcp_hub.memory.db import MemoryDB

PROJECT = str(Path("/tmp/kimi-context-project").resolve())
OTHER = str(Path("/tmp/kimi-context-other").resolve())


@pytest.fixture
def db(tmp_path):
    return MemoryDB(db_path=tmp_path / "memory.db")


def add_session(db, session_id, title, project=PROJECT, timestamp=None):
    row_id = db.add_observation(
        session_id, "session", f"{title}\n\nbody", title, ["session"], project
    )
    if timestamp:
        with sqlite3.connect(db.db_path) as conn:
            conn.execute(
                "UPDATE observations SET timestamp = ? WHERE id = ?",
                (timestamp, row_id),
            )
    return row_id


class TestWhatIsIncluded:
    def test_sessions_are_listed_with_ids(self, db):
        row_id = add_session(db, "s1", "Migrated billing tables to UUID keys")
        block = build_context(db, PROJECT)
        assert f"#{row_id}" in block
        assert "Migrated billing tables to UUID keys" in block

    def test_project_notes_are_listed(self, db):
        db.add_memory("Billing uses UUID primary keys", "project", [], PROJECT)
        assert "Billing uses UUID primary keys" in build_context(db, PROJECT)

    def test_footer_explains_how_to_go_deeper(self, db):
        add_session(db, "s1", "Did a thing")
        block = build_context(db, PROJECT)
        assert "memory_get" in block
        assert "memory_search" in block

    def test_footer_reports_real_counts(self, db):
        add_session(db, "s1", "Did a thing")
        for _ in range(5):
            db.add_observation("s1", "tool", "x", "Used Bash", [], PROJECT)
        block = build_context(db, PROJECT)
        assert "6 observations here" in block

    def test_project_name_is_the_heading(self, db):
        add_session(db, "s1", "Did a thing")
        assert "# Memory — kimi-context-project" in build_context(db, PROJECT)


class TestWhatIsLeftOut:
    def test_tool_noise_is_excluded_when_sessions_exist(self, db):
        """Eight lines of "Used Bash" is the thing this replaces."""
        add_session(db, "s1", "Did a thing")
        for _ in range(20):
            db.add_observation("s1", "tool", "output", "Used Bash", [], PROJECT)
        assert "Used Bash" not in build_context(db, PROJECT)

    def test_placeholder_sessions_are_dropped(self, db):
        """Sessions predating summarization carry no title worth a line."""
        add_session(db, "s1", "Session completed")
        add_session(db, "s2", "Session ended")
        add_session(db, "s3", "Reworked the importer")
        block = build_context(db, PROJECT)
        assert "Session completed" not in block
        assert "Session ended" not in block
        assert "Reworked the importer" in block

    def test_other_projects_are_excluded(self, db):
        add_session(db, "s1", "Something in another repo", project=OTHER)
        add_session(db, "s2", "Something here")
        block = build_context(db, PROJECT)
        assert "another repo" not in block
        assert "Something here" in block

    def test_empty_database_injects_nothing(self, db):
        assert build_context(db, PROJECT) == ""

    def test_a_project_with_only_placeholders_falls_back_to_activity(self, db):
        """A new user must still see that memory is working."""
        add_session(db, "s1", "Session completed")
        db.add_observation("s1", "tool", "output", "Used Bash", [], PROJECT)
        block = build_context(db, PROJECT)
        assert "Recent activity" in block
        assert "Used Bash" in block

    def test_limits_are_respected(self, db):
        for index in range(12):
            add_session(db, f"s{index}", f"Session number {index}")
        block = build_context(db, PROJECT, max_sessions=3)
        assert block.count("Session number") == 3

    def test_notes_limit_is_respected(self, db):
        for index in range(8):
            db.add_memory(f"Note number {index}", "project", [], PROJECT)
        add_session(db, "s1", "Did a thing")
        block = build_context(db, PROJECT, max_notes=2)
        assert block.count("Note number") == 2

    def test_long_titles_are_truncated(self, db):
        add_session(db, "s1", "x" * 400)
        assert "…" in build_context(db, PROJECT)


class TestDateGrouping:
    def test_sessions_group_under_one_heading_per_day(self, db):
        add_session(db, "s1", "First", timestamp="2026-08-16T09:20:00+00:00")
        add_session(db, "s2", "Second", timestamp="2026-08-16T10:21:00+00:00")
        add_session(db, "s3", "Third", timestamp="2026-08-17T11:22:00+00:00")
        block = build_context(db, PROJECT)
        assert block.count("### Aug 16, 2026") == 1
        assert block.count("### Aug 17, 2026") == 1

    def test_an_unparsable_timestamp_still_groups_with_its_day(self, db):
        """A stray format must not split one day into two headings."""
        add_session(db, "s1", "Normal", timestamp="2026-08-16T10:00:00+00:00")
        add_session(db, "s2", "Odd", timestamp="2026-08-16T9:20:00+00:00")
        block = build_context(db, PROJECT)
        assert block.count("### Aug 16, 2026") == 1
        assert "2026-08-16T" not in block


class TestScoping:
    def test_all_projects_shows_everything(self, db):
        add_session(db, "s1", "In project A", project=PROJECT)
        add_session(db, "s2", "In project B", project=OTHER)
        block = build_context(db, None)
        assert "In project A" in block
        assert "In project B" in block
        assert "all projects" in block

    def test_notes_are_project_scoped_only(self, db):
        db.add_memory("Scoped note", "project", [], PROJECT)
        add_session(db, "s1", "Did a thing", project=PROJECT)
        assert "Scoped note" not in build_context(db, None)
