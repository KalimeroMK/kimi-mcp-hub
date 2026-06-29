"""Tests for plugin installer."""

import json
import shutil
from pathlib import Path

import pytest

from kimi_mcp_hub.config import KimiConfig
from kimi_mcp_hub.plugin_installer import (
    _copy_skills,
    _map_matcher,
    convert_hooks,
    discover_plugin_layout,
    install_plugin,
    resolve_repo,
)


class TestResolveRepo:
    def test_owner_repo(self):
        url, name = resolve_repo("DietrichGebert/ponytail")
        assert url == "https://github.com/DietrichGebert/ponytail.git"
        assert name == "ponytail"

    def test_https_url(self):
        url, name = resolve_repo("https://github.com/DietrichGebert/ponytail")
        assert url == "https://github.com/DietrichGebert/ponytail.git"
        assert name == "ponytail"

    def test_local_path(self, tmp_path):
        local = tmp_path / "my-plugin"
        local.mkdir()
        url, name = resolve_repo(str(local))
        assert Path(url).resolve() == local.resolve()
        assert name == "my-plugin"

    def test_invalid_repo(self):
        with pytest.raises(ValueError):
            resolve_repo("not-a-repo")


class TestMapMatcher:
    def test_simple_tool_names(self):
        assert _map_matcher("Write") == "WriteFile|StrReplaceFile"
        assert _map_matcher("Edit") == "Edit|StrReplaceFile"
        assert _map_matcher("Read") == "ReadFile"
        assert _map_matcher("Bash") == "Shell|Bash"

    def test_pipe_separated(self):
        assert _map_matcher("Write|Edit|Read") == "WriteFile|StrReplaceFile|Edit|StrReplaceFile|ReadFile"

    def test_wildcard(self):
        assert _map_matcher("") == ""
        assert _map_matcher("*") == ""

    def test_regex_passthrough_with_mapping(self):
        assert _map_matcher("^(Write|Edit)$") == "^(WriteFile|StrReplaceFile|Edit|StrReplaceFile)$"


class TestConvertHooks:
    def test_command_hook_conversion(self, tmp_path):
        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {"type": "command", "command": "node scripts/guard.js", "timeout": 10},
                    ],
                }
            ]
        }
        result = convert_hooks(hooks_data, tmp_path, "ponytail")
        assert len(result) == 1
        assert result[0]["event"] == "PreToolUse"
        assert result[0]["matcher"] == "WriteFile|StrReplaceFile|Edit|StrReplaceFile"
        assert result[0]["command"].startswith(f'cd "{tmp_path}" &&')
        assert "node scripts/guard.js" in result[0]["command"]
        assert result[0]["timeout"] == 10

    def test_skip_non_command_hooks(self, tmp_path):
        hooks_data = {
            "PostToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [
                        {"type": "prompt", "prompt": "Be concise"},
                    ],
                }
            ]
        }
        result = convert_hooks(hooks_data, tmp_path, "ponytail")
        assert len(result) == 0


class TestDiscoverPluginLayout:
    def test_full_layout(self, tmp_path):
        plugin_dir = tmp_path / "ponytail"
        plugin_dir.mkdir()
        (plugin_dir / "AGENTS.md").write_text("# Rules")
        (plugin_dir / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": []}}))
        skills_dir = plugin_dir / "skills"
        skills_dir.mkdir()
        (skills_dir / "review" / "SKILL.md").parent.mkdir(parents=True)
        (skills_dir / "review" / "SKILL.md").write_text("# Review")

        layout = discover_plugin_layout(plugin_dir)
        assert layout["agents_md"] == plugin_dir / "AGENTS.md"
        assert layout["hooks_config"] == plugin_dir / "hooks.json"
        assert layout["skills_dirs"] == [skills_dir]

    def test_no_layout(self, tmp_path):
        plugin_dir = tmp_path / "empty"
        plugin_dir.mkdir()
        layout = discover_plugin_layout(plugin_dir)
        assert layout["agents_md"] is None
        assert layout["hooks_config"] is None
        assert layout["skills_dirs"] == []


class TestCopySkills:
    def test_copy_with_prefix(self, tmp_path):
        source = tmp_path / "skills"
        (source / "review" / "SKILL.md").parent.mkdir(parents=True)
        (source / "review" / "SKILL.md").write_text("# Review")

        target = tmp_path / "target"
        installed = _copy_skills([source], target, "ponytail")
        assert installed == ["ponytail-review"]
        assert (target / "ponytail-review" / "SKILL.md").exists()

    def test_no_double_prefix(self, tmp_path):
        source = tmp_path / "skills"
        (source / "ponytail-review" / "SKILL.md").parent.mkdir(parents=True)
        (source / "ponytail-review" / "SKILL.md").write_text("# Review")

        target = tmp_path / "target"
        installed = _copy_skills([source], target, "ponytail")
        assert installed == ["ponytail-review"]


class TestKimiConfigPluginHelpers:
    def test_merge_agents_md_idempotent(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()
        content = "## Ponytail rules\nBe lazy."
        assert config.merge_agents_md(content, "ponytail") is True
        assert config.merge_agents_md(content, "ponytail") is False
        text = config.agents_md.read_text(encoding="utf-8")
        assert "<!-- plugin: ponytail -->" in text
        assert "Be lazy." in text

    def test_toml_roundtrip(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()
        data = {"hooks": [{"event": "PreToolUse", "command": "echo hi"}]}
        config.save_toml_config(data)
        loaded = config.load_toml_config()
        assert loaded["hooks"][0]["event"] == "PreToolUse"


class TestInstallPlugin:
    def test_local_plugin_install(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()

        plugin_dir = tmp_path / "ponytail"
        plugin_dir.mkdir()
        (plugin_dir / "AGENTS.md").write_text("## Ponytail\nUse stdlib.")
        (plugin_dir / "hooks.json").write_text(json.dumps({
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Write|Edit",
                        "hooks": [{"type": "command", "command": "node guard.js"}],
                    }
                ]
            }
        }))
        skills = plugin_dir / "skills" / "review"
        skills.mkdir(parents=True)
        (skills / "SKILL.md").write_text("# Review")

        result = install_plugin(str(plugin_dir), config, yes=True)
        assert result["plugin_name"] == "ponytail"
        assert result["agents_md_installed"] is True
        assert result["hooks_installed"] == 1
        assert "ponytail-review" in result["skills_installed"]

        # Verify config.toml
        toml_data = config.load_toml_config()
        assert len(toml_data["hooks"]) == 1
        assert toml_data["hooks"][0]["event"] == "PreToolUse"

        # Verify AGENTS.md
        assert config.agents_md.exists()
        assert "Use stdlib." in config.agents_md.read_text(encoding="utf-8")

        # Verify skills
        assert (config.skills_dir / "ponytail-review" / "SKILL.md").exists()

    def test_reinstall_idempotent(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()

        plugin_dir = tmp_path / "ponytail"
        plugin_dir.mkdir()
        (plugin_dir / "AGENTS.md").write_text("## Ponytail\nUse stdlib.")
        (plugin_dir / "hooks.json").write_text(json.dumps({
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Write",
                        "hooks": [{"type": "command", "command": "node guard.js"}],
                    }
                ]
            }
        }))

        install_plugin(str(plugin_dir), config, yes=True)
        install_plugin(str(plugin_dir), config, yes=True)

        toml_data = config.load_toml_config()
        assert len(toml_data["hooks"]) == 1
