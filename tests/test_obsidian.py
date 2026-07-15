"""Tests for ObsidianServer multi-vault helpers and templates."""

from pathlib import Path
from unittest import mock

import pytest

from kimi_mcp_hub.config import KimiConfig
from kimi_mcp_hub.memory.db import MemoryDB
from kimi_mcp_hub.memory.hooks import MemoryHooks
from kimi_mcp_hub.servers.obsidian import ObsidianServer


class TestObsidianStdioConfig:
    def test_single_vault_backward_compatible(self):
        cfg = ObsidianServer.get_stdio_config("/path/to/vault")
        assert cfg["command"] == "npx"
        assert cfg["args"] == ["-y", "obsidian-mcp", "/path/to/vault"]
        assert cfg["env"] == {}

    def test_multi_vault_config(self):
        cfg = ObsidianServer.get_stdio_config(["/path/vault1", "/path/vault2"])
        assert cfg["command"] == "npx"
        assert cfg["args"] == ["-y", "obsidian-mcp", "/path/vault1", "/path/vault2"]
        assert cfg["env"] == {}


class TestObsidianSlug:
    def test_slug_from_basename(self):
        assert ObsidianServer.slug_from_vault_path("/home/user/My Vault") == "my-vault"

    def test_slug_strips_special_characters(self):
        assert (
            ObsidianServer.slug_from_vault_path("Vault v1.0 (notes)")
            == "vault-v1-0-notes"
        )

    def test_slug_falls_back_to_vault(self):
        assert ObsidianServer.slug_from_vault_path("...") == "vault"

    def test_slug_accepts_path_input(self, tmp_path):
        assert (
            ObsidianServer.slug_from_vault_path(Path("/home/user/My Vault"))
            == "my-vault"
        )


class TestObsidianVaultValidation:
    def test_validate_vault_false_for_missing_obsidian_dir(self, tmp_path):
        vault = tmp_path / "empty-vault"
        vault.mkdir()
        assert ObsidianServer.validate_vault(vault) is False

    def test_validate_vault_false_for_missing_app_json(self, tmp_path):
        vault = tmp_path / "partial-vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        assert ObsidianServer.validate_vault(vault) is False

    def test_validate_vault_fix_creates_app_json(self, tmp_path):
        vault = tmp_path / "fixable-vault"
        assert ObsidianServer.validate_vault(vault, fix=True) is True
        assert (vault / ".obsidian" / "app.json").exists()

    def test_validate_vault_true_for_existing_vault(self, tmp_path):
        vault = tmp_path / "good-vault"
        ObsidianServer.scaffold_vault(vault)
        assert ObsidianServer.validate_vault(vault) is True

    def test_validate_vault_fix_false_when_path_is_file(self, tmp_path):
        file_path = tmp_path / "not-a-dir"
        file_path.write_text("I am a file", encoding="utf-8")
        assert ObsidianServer.validate_vault(file_path, fix=True) is False


class TestObsidianScaffold:
    def test_scaffold_creates_readme_and_app_json(self, tmp_path):
        vault = tmp_path / "new-vault"
        ObsidianServer.scaffold_vault(vault)

        assert vault.is_dir()
        assert (vault / ".obsidian").is_dir()
        assert (vault / ".obsidian" / "app.json").is_file()

        readme = vault / "README.md"
        assert readme.is_file()
        assert "Kimi Memory Vault" in readme.read_text(encoding="utf-8")

    def test_scaffold_is_idempotent(self, tmp_path):
        vault = tmp_path / "idempotent-vault"
        ObsidianServer.scaffold_vault(vault)
        first_text = (vault / "README.md").read_text(encoding="utf-8")

        ObsidianServer.scaffold_vault(vault)
        assert (vault / "README.md").read_text(encoding="utf-8") == first_text


class TestObsidianTemplateSync:
    def test_sync_templates_copies_markdown_files(self, tmp_path):
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "daily.md").write_text("# Daily note\n", encoding="utf-8")
        (templates / "ignored.txt").write_text("not copied", encoding="utf-8")

        vault = tmp_path / "vault"
        vault.mkdir()

        copied = ObsidianServer.sync_templates(templates, vault)
        assert len(copied) == 1
        assert (vault / "daily.md").exists()
        assert not (vault / "ignored.txt").exists()

    def test_sync_templates_preserves_subdirectory_structure(self, tmp_path):
        templates = tmp_path / "templates"
        nested = templates / "projects"
        nested.mkdir(parents=True)
        (nested / "brief.md").write_text("brief", encoding="utf-8")

        vault = tmp_path / "vault"
        vault.mkdir()

        copied = ObsidianServer.sync_templates(templates, vault)
        assert (vault / "projects" / "brief.md") in copied
        assert (vault / "projects" / "brief.md").read_text(encoding="utf-8") == "brief"

    def test_sync_templates_skips_hidden_files(self, tmp_path):
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "visible.md").write_text("visible", encoding="utf-8")
        hidden_dir = templates / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "secret.md").write_text("secret", encoding="utf-8")

        vault = tmp_path / "vault"
        vault.mkdir()

        copied = ObsidianServer.sync_templates(templates, vault)
        assert (vault / "visible.md") in copied
        assert not (vault / ".hidden" / "secret.md").exists()

    def test_sync_templates_overwrite_false_preserves_existing(self, tmp_path):
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "daily.md").write_text("# Template daily\n", encoding="utf-8")

        vault = tmp_path / "vault"
        vault.mkdir()
        existing = vault / "daily.md"
        existing.write_text("# User daily\n", encoding="utf-8")

        copied = ObsidianServer.sync_templates(templates, vault, overwrite=False)
        assert copied == []
        assert existing.read_text(encoding="utf-8") == "# User daily\n"

    def test_sync_templates_overwrite_true_replaces_existing(self, tmp_path):
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "daily.md").write_text("# Template daily\n", encoding="utf-8")

        vault = tmp_path / "vault"
        vault.mkdir()
        existing = vault / "daily.md"
        existing.write_text("# User daily\n", encoding="utf-8")

        copied = ObsidianServer.sync_templates(templates, vault, overwrite=True)
        assert copied == [existing]
        assert existing.read_text(encoding="utf-8") == "# Template daily\n"

    def test_sync_templates_missing_dir_raises(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()

        with pytest.raises(FileNotFoundError, match="Templates directory not found"):
            ObsidianServer.sync_templates(tmp_path / "does-not-exist", vault)

    def test_sync_templates_missing_ok_returns_empty(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()

        copied = ObsidianServer.sync_templates(
            tmp_path / "does-not-exist", vault, missing_ok=True
        )
        assert copied == []


class TestMemoryHooksObsidian:
    def test_stop_writes_session_note_to_default_vault(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"
        config = KimiConfig()
        config.set_default_memory_vault(str(vault))

        db = MemoryDB()
        db.add_observation(
            session_id="sess-1",
            obs_type="tool",
            content="output",
            summary="Used bash",
            tags=["bash"],
        )

        hooks = MemoryHooks(db=db)
        hooks.stop({"session_id": "sess-1", "project_path": "/tmp/project"})

        notes = list((vault / "Sessions").glob("*.md"))
        assert len(notes) == 1
        text = notes[0].read_text(encoding="utf-8")
        assert "# Session" in text
        assert "sess-1" in text
        assert "Used bash" in text

    def test_stop_does_nothing_without_default_vault(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"

        db = MemoryDB()
        hooks = MemoryHooks(db=db)
        hooks.stop({"session_id": "sess-1", "project_path": "/tmp/project"})

        assert not vault.exists()

    def test_stop_writes_summary_and_raw_notes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"
        config = KimiConfig()
        config.set_default_memory_vault(str(vault))
        config.set_memory_summary_config(api_key="sk-test", model="gpt-4o-mini")

        db = MemoryDB()
        db.add_observation(
            session_id="sess-1",
            obs_type="tool",
            content="output",
            summary="Used bash",
            tags=["bash"],
        )

        hooks = MemoryHooks(db=db)
        with mock.patch(
            "kimi_mcp_hub.memory.hooks.Summarizer.summarize_session",
            return_value="## Summary\n\nGreat session.",
        ):
            hooks.stop({"session_id": "sess-1", "project_path": "/tmp/project"})

        summary_notes = list((vault / "Sessions").glob("*summary.md"))
        raw_notes = [
            p
            for p in (vault / "Sessions").glob("*.md")
            if not p.name.endswith("-summary.md")
        ]
        assert len(summary_notes) == 1
        assert len(raw_notes) == 1
        assert "## Summary" in summary_notes[0].read_text(encoding="utf-8")
        assert "Used bash" in raw_notes[0].read_text(encoding="utf-8")

    def test_stop_writes_session_note_using_cwd(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"
        config = KimiConfig()
        config.set_default_memory_vault(str(vault))

        db = MemoryDB()
        db.add_observation(
            session_id="sess-1",
            obs_type="tool",
            content="output",
            summary="Used bash",
            tags=["bash"],
        )

        hooks = MemoryHooks(db=db)
        hooks.stop({"session_id": "sess-1", "cwd": "/tmp/project"})

        notes = list((vault / "Sessions").glob("*.md"))
        assert len(notes) == 1
        text = notes[0].read_text(encoding="utf-8")
        assert "`/tmp/project`" in text

    def test_stop_note_includes_content_not_only_generic_summary(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"
        config = KimiConfig()
        config.set_default_memory_vault(str(vault))

        db = MemoryDB()
        db.add_observation(
            session_id="sess-1",
            obs_type="tool",
            content="file.txt\n",
            summary="Used bash",
            tags=["bash"],
        )

        hooks = MemoryHooks(db=db)
        hooks.stop({"session_id": "sess-1", "cwd": "/tmp/project"})

        notes = list((vault / "Sessions").glob("*.md"))
        assert len(notes) == 1
        text = notes[0].read_text(encoding="utf-8")
        assert "Used bash" in text
        assert "file.txt" in text
        assert "- [tool] Used\n" not in text

    def test_stop_note_saves_image_attachment_to_vault(self, tmp_path, monkeypatch):
        import base64

        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"
        config = KimiConfig()
        config.set_default_memory_vault(str(vault))

        db = MemoryDB()
        hooks = MemoryHooks(db=db)
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes" * 8
        hooks.post_tool_use(
            {
                "session_id": "sess-img",
                "tool_name": "take_screenshot",
                "tool_output": {
                    "mime_type": "image/png",
                    "data": base64.b64encode(png_bytes).decode(),
                },
            }
        )
        hooks.stop({"session_id": "sess-img", "cwd": "/tmp/project"})

        notes = list((vault / "Sessions").glob("*.md"))
        assert len(notes) == 1
        attachments = list((vault / "Attachments").glob("*.png"))
        assert len(attachments) == 1
        text = notes[0].read_text(encoding="utf-8")
        assert "![take_screenshot]" in text
        assert "Attachments/" in text

    def test_stop_note_falls_back_to_current_working_directory(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"
        config = KimiConfig()
        config.set_default_memory_vault(str(vault))

        db = MemoryDB()
        hooks = MemoryHooks(db=db)
        monkeypatch.chdir(tmp_path)
        hooks.stop({"session_id": "sess-cwd"})

        notes = list((vault / "Sessions").glob("*.md"))
        assert len(notes) == 1
        text = notes[0].read_text(encoding="utf-8")
        assert f"`{tmp_path}`" in text

    def test_session_start_returns_recent_context(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        db.add_observation(
            session_id="sess-start",
            obs_type="tool",
            content="output content",
            summary="Used bash",
            tags=["bash"],
        )

        hooks = MemoryHooks(db=db)
        context = hooks.session_start(
            {"session_id": "sess-start", "project_path": "/tmp/project"}
        )

        assert "[Memory] Recent context:" in context
        assert "Used bash" in context

    def test_post_tool_use_adds_observation(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        hooks.post_tool_use(
            {
                "session_id": "sess-tool",
                "tool": "bash",
                "output": "some output",
            }
        )

        recent = db.get_recent()
        assert len(recent) == 1
        assert recent[0]["type"] == "tool"
        assert recent[0]["summary"] == "Used bash"
        assert recent[0]["content"] == "some output"

    def test_post_tool_use_adds_observation_from_kimi_payload(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        hooks.post_tool_use(
            {
                "session_id": "sess-tool",
                "tool_name": "bash",
                "tool_input": {"command": "ls -la"},
                "tool_output": "file.txt\n",
            }
        )

        recent = db.get_recent()
        assert len(recent) == 1
        assert recent[0]["type"] == "tool"
        assert recent[0]["summary"] == "Used bash"
        assert recent[0]["content"] == "file.txt\n"

    def test_post_tool_use_reads_tool_response(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        hooks.post_tool_use(
            {
                "session_id": "sess-tool",
                "tool_name": "Bash",
                "tool_input": {"command": "echo hi"},
                "tool_response": {"stdout": "hi\n", "stderr": "", "isImage": False},
            }
        )

        recent = db.get_recent()
        assert len(recent) == 1
        assert recent[0]["type"] == "tool"
        assert recent[0]["summary"] == "Used Bash"
        assert "hi" in recent[0]["content"]

    def test_post_tool_use_extracts_text_from_dict_response(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        hooks.post_tool_use(
            {
                "session_id": "sess-tool",
                "name": "Read",
                "tool_input": {"file_path": "foo.txt"},
                "tool_response": "line 1\nline 2\n",
            }
        )

        recent = db.get_recent()
        assert len(recent) == 1
        assert recent[0]["summary"] == "Used Read"
        assert "line 1" in recent[0]["content"]

    def test_session_end_writes_no_notes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"
        config = KimiConfig()
        config.set_default_memory_vault(str(vault))

        db = MemoryDB()
        hooks = MemoryHooks(db=db)
        hooks.session_end({"session_id": "sess-end", "project_path": "/tmp/project"})

        assert not (vault / "Sessions").exists()


class TestMemoryHookCli:
    def test_cli_stop_writes_session_note(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"
        config = KimiConfig()
        config.set_default_memory_vault(str(vault))

        import json
        import subprocess
        import sys

        payload = json.dumps({"session_id": "sess-cli", "project_path": "/tmp/project"})
        result = subprocess.run(
            [sys.executable, "-m", "kimi_mcp_hub.memory_hook", "stop"],
            input=payload,
            text=True,
            capture_output=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, result.stderr

        notes = list((vault / "Sessions").glob("*.md"))
        assert len(notes) == 1
        assert "sess-cli" in notes[0].read_text(encoding="utf-8")


class TestMemoryHooksProjectMemory:
    def test_session_start_includes_project_memories(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        db.add_memory(
            "Always run tests before push",
            category="project",
            project_path=str(tmp_path),
        )
        result = hooks.session_start(
            {"session_id": "s1", "project_path": str(tmp_path)}
        )
        assert "[Memory] Project notes:" in result
        assert "Always run tests before push" in result

    def test_session_start_uses_cwd_as_project_path(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        db.add_memory(
            "Always run tests before push",
            category="project",
            project_path=str(tmp_path),
        )
        result = hooks.session_start({"session_id": "s1", "cwd": str(tmp_path)})
        assert "[Memory] Project notes:" in result
        assert "Always run tests before push" in result

    def test_session_start_excludes_non_matching_project_path(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        db.add_memory(
            "Other project note",
            category="project",
            project_path="/some/other/path",
        )
        result = hooks.session_start(
            {"session_id": "s1", "project_path": str(tmp_path)}
        )
        assert "[Memory] Project notes:" not in result
        assert "Other project note" not in result

    def test_session_start_trailing_slash_matches_same_project(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        db.add_memory(
            "Trailing slash note",
            category="project",
            project_path=str(tmp_path),
        )
        result = hooks.session_start(
            {"session_id": "s1", "project_path": str(tmp_path) + "/"}
        )
        assert "[Memory] Project notes:" in result
        assert "Trailing slash note" in result

    def test_session_start_excludes_non_project_category(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        db.add_memory(
            "General note",
            category="general",
            project_path=str(tmp_path),
        )
        result = hooks.session_start(
            {"session_id": "s1", "project_path": str(tmp_path)}
        )
        assert "[Memory] Project notes:" not in result
        assert "General note" not in result

    def test_session_start_no_project_path_no_project_notes(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        db.add_observation(
            session_id="s1",
            obs_type="tool",
            content="output content",
            summary="Used bash",
            tags=["bash"],
        )
        result = hooks.session_start({"session_id": "s1", "project_path": ""})
        assert "[Memory] Project notes:" not in result

    def test_session_start_truncates_long_memory(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        long_content = "x" * 500
        db.add_memory(
            long_content,
            category="project",
            project_path=str(tmp_path),
        )
        result = hooks.session_start(
            {"session_id": "s1", "project_path": str(tmp_path)}
        )
        assert "[Memory] Project notes:" in result
        assert "x" * 200 in result
        assert "... [truncated]" in result
        assert len(result) < len(long_content)
