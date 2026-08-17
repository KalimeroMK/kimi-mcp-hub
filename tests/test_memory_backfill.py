"""Tests for recovering project attribution from Obsidian session notes."""

from pathlib import Path

import pytest

from kimi_mcp_hub.memory.backfill import apply_plan, build_plan, parse_session_notes
from kimi_mcp_hub.memory.db import MemoryDB

PROJECT = str(Path("/tmp/kimi-backfill-project").resolve())
OTHER = str(Path("/tmp/kimi-backfill-other").resolve())


def write_note(vault: Path, name: str, session_id: str, project: str) -> None:
    sessions = vault / "Sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / name).write_text(
        f"# Session {name}\n\n"
        f"- **Session ID:** `{session_id}`\n"
        f"- **Project:** `{project}`\n\n"
        "## Observations\n\n- [tool] Used Bash\n",
        encoding="utf-8",
    )


@pytest.fixture
def db(tmp_path):
    return MemoryDB(db_path=tmp_path / "memory.db")


@pytest.fixture
def vault(tmp_path):
    return tmp_path / "vault"


class TestParsing:
    def test_maps_session_to_project(self, vault):
        write_note(vault, "a.md", "sess-1", PROJECT)
        mapping, plan = parse_session_notes(vault)
        assert mapping == {"sess-1": PROJECT}
        assert plan.notes_scanned == 1
        assert plan.sessions_mapped == 1

    def test_paths_are_resolved(self, vault):
        write_note(vault, "a.md", "sess-1", "/tmp/../tmp/kimi-backfill-project")
        mapping, _ = parse_session_notes(vault)
        assert mapping["sess-1"] == PROJECT

    def test_empty_project_is_counted_not_mapped(self, vault):
        """Older notes recorded an empty project; they carry no information."""
        write_note(vault, "a.md", "sess-1", "")
        mapping, plan = parse_session_notes(vault)
        assert mapping == {}
        assert plan.notes_without_project == 1

    def test_repeated_notes_for_one_session_agree(self, vault):
        """A session writes a note per stop, so the same id recurs."""
        write_note(vault, "a.md", "sess-1", PROJECT)
        write_note(vault, "b.md", "sess-1", PROJECT)
        mapping, plan = parse_session_notes(vault)
        assert mapping == {"sess-1": PROJECT}
        assert plan.notes_scanned == 2

    def test_conflicting_notes_are_skipped(self, vault):
        """Guessing between two projects would silently mis-attribute history."""
        write_note(vault, "a.md", "sess-1", PROJECT)
        write_note(vault, "b.md", "sess-1", OTHER)
        mapping, plan = parse_session_notes(vault)
        assert mapping == {}
        assert set(plan.conflicts["sess-1"]) == {PROJECT, OTHER}

    def test_missing_vault_yields_nothing(self, tmp_path):
        mapping, plan = parse_session_notes(tmp_path / "nope")
        assert mapping == {}
        assert plan.notes_scanned == 0

    def test_unparsable_note_is_ignored(self, vault):
        sessions = vault / "Sessions"
        sessions.mkdir(parents=True)
        (sessions / "junk.md").write_text("no fields here", encoding="utf-8")
        mapping, plan = parse_session_notes(vault)
        assert mapping == {}
        assert plan.notes_scanned == 1


class TestPlanning:
    def test_counts_only_unattributed_rows(self, db, vault):
        db.add_observation("sess-1", "tool", "a", "Used Bash")
        db.add_observation("sess-1", "tool", "b", "Used Bash")
        db.add_observation("sess-1", "tool", "c", "Used Bash", project_path=OTHER)
        write_note(vault, "a.md", "sess-1", PROJECT)

        mapping, plan = parse_session_notes(vault)
        plan = build_plan(db, mapping, plan)
        assert plan.observations_to_update == 2
        assert plan.per_project == {PROJECT: 2}

    def test_sessions_with_no_note_are_not_counted(self, db, vault):
        db.add_observation("sess-unknown", "tool", "a", "Used Bash")
        write_note(vault, "a.md", "sess-1", PROJECT)
        mapping, plan = parse_session_notes(vault)
        plan = build_plan(db, mapping, plan)
        assert plan.is_empty


class TestApplying:
    def test_fills_missing_projects(self, db, vault):
        db.add_observation("sess-1", "tool", "a", "Used Bash")
        db.add_observation("sess-2", "tool", "b", "Used Bash")
        write_note(vault, "a.md", "sess-1", PROJECT)
        write_note(vault, "b.md", "sess-2", OTHER)

        mapping, _ = parse_session_notes(vault)
        assert apply_plan(db, mapping) == 2

        assert db.get_recent(session_id="sess-1")[0]["project_path"] == PROJECT
        assert db.get_recent(session_id="sess-2")[0]["project_path"] == OTHER

    def test_never_overwrites_an_existing_project(self, db, vault):
        """Newer rows recorded the project directly; that wins."""
        db.add_observation("sess-1", "tool", "a", "Used Bash", project_path=OTHER)
        write_note(vault, "a.md", "sess-1", PROJECT)

        mapping, _ = parse_session_notes(vault)
        assert apply_plan(db, mapping) == 0
        assert db.get_recent(session_id="sess-1")[0]["project_path"] == OTHER

    def test_is_idempotent(self, db, vault):
        db.add_observation("sess-1", "tool", "a", "Used Bash")
        write_note(vault, "a.md", "sess-1", PROJECT)
        mapping, _ = parse_session_notes(vault)

        assert apply_plan(db, mapping) == 1
        assert apply_plan(db, mapping) == 0

    def test_makes_project_scoped_recall_work(self, db, vault):
        """The whole point: recovered rows become visible to scoped search."""
        db.add_observation(
            "sess-1", "session", "migrated the billing tables", "Billing"
        )
        write_note(vault, "a.md", "sess-1", PROJECT)

        assert db.search("billing", project_path=PROJECT) == []
        apply_plan(db, parse_session_notes(vault)[0])
        assert len(db.search("billing", project_path=PROJECT)) == 1

    def test_handles_more_sessions_than_the_sqlite_variable_limit(self, db, vault):
        """Chunking matters: a year of sessions blows past 999 bound variables."""
        for index in range(1200):
            db.add_observation(f"s{index}", "tool", "x", "Used Bash")
            write_note(vault, f"n{index}.md", f"s{index}", PROJECT)

        mapping, _ = parse_session_notes(vault)
        assert apply_plan(db, mapping) == 1200
        assert db.count_unattributed() == 0


class TestCounting:
    def test_count_unattributed(self, db):
        db.add_observation("s1", "tool", "a", "x")
        db.add_observation("s2", "tool", "b", "x", project_path=PROJECT)
        assert db.count_unattributed() == 1

    def test_empty_string_counts_as_unattributed(self, db):
        db.add_observation("s1", "tool", "a", "x", project_path="")
        assert db.count_unattributed() == 1

    def test_count_by_session_ignores_unknown_ids(self, db):
        db.add_observation("s1", "tool", "a", "x")
        assert db.count_unattributed_by_session(["s1", "nope"]) == {"s1": 1}

    def test_count_by_session_with_no_ids(self, db):
        assert db.count_unattributed_by_session([]) == {}
