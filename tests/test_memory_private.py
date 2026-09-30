"""Tests for the <private> tag filter: marked text must never be persisted."""

from pathlib import Path

import pytest

from kimi_mcp_hub.memory.db import MemoryDB
from kimi_mcp_hub.memory.hooks import MemoryHooks, strip_private

# Resolved so assertions match what the code stores (on macOS /tmp is a
# symlink to /private/tmp).
PROJECT = str(Path("/tmp/kimi-private-project").resolve())


@pytest.fixture
def db(tmp_path):
    return MemoryDB(db_path=tmp_path / "memory.db")


@pytest.fixture
def hooks(db):
    return MemoryHooks(db=db)


class TestStripPrivate:
    def test_plain_text_is_untouched(self):
        assert strip_private("hello world") == "hello world"

    def test_removes_a_single_span(self):
        assert strip_private("a <private>secret</private> b") == "a  b"

    def test_removes_multiple_spans(self):
        text = "<private>one</private> keep <private>two</private> keep2"
        assert strip_private(text) == " keep  keep2"

    def test_span_may_cross_lines(self):
        text = "before <private>line1\nline2\nline3</private> after"
        assert strip_private(text) == "before  after"

    def test_tag_name_is_case_insensitive(self):
        text = "a <PRIVATE>secret</PRIVATE> b <Private>x</Private> c"
        assert strip_private(text) == "a  b  c"

    def test_unclosed_tag_drops_to_end_of_text(self):
        assert strip_private("keep <private>never closed") == "keep "

    def test_empty_and_none_are_safe(self):
        assert strip_private("") == ""


class TestToolOutputCapture:
    def test_private_spans_are_not_stored(self, hooks, db):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "ok <private>hunter2</private> done",
                "cwd": PROJECT,
            }
        )
        stored = db.get_recent()[0]
        assert "hunter2" not in stored["content"]
        assert "ok" in stored["content"] and "done" in stored["content"]

    def test_multiline_and_mixed_case_spans_are_not_stored(self, hooks, db):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "start <PRIVATE>line1\nline2</PRIVATE> end",
                "cwd": PROJECT,
            }
        )
        content = db.get_recent()[0]["content"]
        assert "line1" not in content and "line2" not in content

    def test_nothing_storable_skips_the_insert(self, hooks, db):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "<private>only secrets here</private>",
                "cwd": PROJECT,
            }
        )
        assert db.get_stats()["total_observations"] == 0

    def test_unclosed_tag_skips_the_insert(self, hooks, db):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "   <private>never closed",
                "cwd": PROJECT,
            }
        )
        assert db.get_stats()["total_observations"] == 0

    def test_hash_is_computed_after_stripping(self, hooks, db):
        # The private wrapper must not change the dedup hash: a result that
        # differs only inside <private> tags is the same observation.
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "same output <private>secret</private>",
                "cwd": PROJECT,
            }
        )
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_response": "same output ",
                "cwd": PROJECT,
            }
        )
        assert db.get_stats()["total_observations"] == 1

    def test_noisy_tool_placeholder_still_recorded(self, hooks, db):
        hooks.post_tool_use(
            {
                "session_id": "s1",
                "tool_name": "Read",
                "tool_response": "<private>file body</private>",
                "cwd": PROJECT,
            }
        )
        assert db.get_recent()[0]["content"] == "[Read output omitted]"


class TestUserPromptSubmit:
    def test_private_prompt_text_still_retrieves_public_matches(self, hooks, db):
        db.add_memory("Billing uses UUID primary keys", "project", [], PROJECT)
        context = hooks.user_prompt_submit(
            {
                "cwd": PROJECT,
                "prompt": "how are billing keys generated? <private>my password</private>",
            }
        )
        assert "UUID primary keys" in context

    def test_fully_private_prompt_is_skipped(self, hooks, db):
        db.add_memory("Billing uses UUID primary keys", "project", [], PROJECT)
        context = hooks.user_prompt_submit(
            {"cwd": PROJECT, "prompt": "<private>what are the billing keys</private>"}
        )
        assert context == ""
