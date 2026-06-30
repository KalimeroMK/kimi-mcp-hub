"""Tests for ObsidianServer multi-vault helpers and templates."""

from pathlib import Path

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
    def test_stop_writes_session_note_to_default_vault(
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
