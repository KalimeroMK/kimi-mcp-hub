"""Tests for plugin installer."""

import json
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from kimi_mcp_hub.config import KimiConfig
from kimi_mcp_hub.plugin_installer import (
    _copy_skills,
    _load_hooks_json,
    _map_matcher,
    _normalize_claude_plugin_manifest,
    _relativize_plugin_paths,
    clone_or_update_repo,
    convert_hooks,
    discover_plugin_layout,
    install_plugin,
    resolve_repo,
    uninstall_plugin,
    update_plugin,
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
        assert (
            _map_matcher("Write|Edit|Read")
            == "WriteFile|StrReplaceFile|Edit|StrReplaceFile|ReadFile"
        )

    def test_wildcard(self):
        assert _map_matcher("") == ""
        assert _map_matcher("*") == ""

    def test_regex_passthrough_with_mapping(self):
        assert (
            _map_matcher("^(Write|Edit)$")
            == "^(WriteFile|StrReplaceFile|Edit|StrReplaceFile)$"
        )


class TestConvertHooks:
    def test_command_hook_conversion(self, tmp_path):
        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "node scripts/guard.js",
                            "timeout": 10,
                        },
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
        (plugin_dir / "hooks.json").write_text(
            json.dumps({"hooks": {"PreToolUse": []}})
        )
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


class TestCodexHooks:
    def test_discover_codex_hooks(self, tmp_path):
        plugin_dir = tmp_path / "codex-plugin"
        plugin_dir.mkdir()
        codex_hooks = plugin_dir / ".codex" / "hooks.json"
        codex_hooks.parent.mkdir(parents=True)
        codex_hooks.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [
                                    {"type": "command", "command": "python guard.py"}
                                ],
                            }
                        ]
                    }
                }
            )
        )

        layout = discover_plugin_layout(plugin_dir)
        assert layout["hooks_config"] == codex_hooks
        assert layout["hooks_format"] == ".codex/hooks.json"

    def test_convert_codex_hooks(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        plugin_dir = tmp_path / "plugins" / "codex-plugin"
        plugin_dir.mkdir(parents=True)
        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [{"type": "command", "command": "python guard.py"}],
                }
            ]
        }
        result = convert_hooks(hooks_data, plugin_dir, "codex-plugin")
        assert len(result) == 1
        assert result[0]["event"] == "PreToolUse"
        assert result[0]["matcher"] == "WriteFile|StrReplaceFile"
        assert f'cd "{plugin_dir}" && python guard.py' == result[0]["command"]


class TestClaudePluginManifest:
    def test_discover_claude_plugin_json(self, tmp_path):
        plugin_dir = tmp_path / "marketplace-plugin"
        plugin_dir.mkdir()
        manifest = plugin_dir / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "name": "marketplace-plugin",
                    "description": "A test plugin",
                    "version": "1.0.0",
                    "hooks": [
                        {
                            "name": "guard",
                            "description": "Guard writes",
                            "command": "node guard.js",
                        }
                    ],
                }
            )
        )

        layout = discover_plugin_layout(plugin_dir)
        assert layout["hooks_config"] == manifest
        assert layout["hooks_format"] == "claude-plugin"

    def test_normalize_claude_plugin_manifest(self):
        manifest = {
            "name": "marketplace-plugin",
            "hooks": [
                {
                    "name": "guard",
                    "command": ["node", "guard.js"],
                    "args": ["--strict"],
                    "timeout": 15,
                },
                {
                    "name": "simple",
                    "command": "echo hi",
                },
            ],
        }
        internal = _normalize_claude_plugin_manifest(manifest)
        assert "PreToolUse" in internal
        assert len(internal["PreToolUse"]) == 2

        guard = internal["PreToolUse"][0]
        assert guard["matcher"] == ""
        assert guard["hooks"][0]["type"] == "command"
        assert guard["hooks"][0]["command"] == "node guard.js --strict"
        assert guard["hooks"][0]["timeout"] == 15

        simple = internal["PreToolUse"][1]
        assert simple["hooks"][0]["command"] == "echo hi"
        assert simple["hooks"][0]["timeout"] == 30

    def test_install_claude_plugin_manifest(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()

        plugin_dir = tmp_path / "marketplace-plugin"
        plugin_dir.mkdir()
        manifest = plugin_dir / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "name": "marketplace-plugin",
                    "hooks": [
                        {"name": "guard", "command": "node guard.js"},
                    ],
                }
            )
        )

        result = install_plugin(str(plugin_dir), config)
        assert result["plugin_name"] == "marketplace-plugin"
        assert result["hooks_installed"] == 1

        toml_data = config.load_toml_config()
        assert len(toml_data["hooks"]) == 1
        assert toml_data["hooks"][0]["event"] == "PreToolUse"


class TestRelativizePluginPaths:
    def test_relativizes_absolute_command(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        script = plugin_dir / "bin" / "script.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/sh")

        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [{"type": "command", "command": str(script)}],
                }
            ]
        }
        result = convert_hooks(hooks_data, plugin_dir, "my-plugin")
        assert len(result) == 1
        assert result[0]["command"] == f'cd "{plugin_dir}" && bin/script.sh'

    def test_relativizes_argument_paths(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        data_file = plugin_dir / "data" / "rules.json"
        data_file.parent.mkdir(parents=True)
        data_file.write_text("{}")

        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"node guard.js --rules {data_file}",
                        }
                    ],
                }
            ]
        }
        result = convert_hooks(hooks_data, plugin_dir, "my-plugin")
        assert result[0]["command"] == (
            f'cd "{plugin_dir}" && node guard.js --rules data/rules.json'
        )

    def test_preserves_quotes(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        script = plugin_dir / "bin" / "script.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/sh")

        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f'"{script}"',
                        }
                    ],
                }
            ]
        }
        result = convert_hooks(hooks_data, plugin_dir, "my-plugin")
        assert result[0]["command"] == f'cd "{plugin_dir}" && "bin/script.sh"'

    def test_leaves_external_paths_unchanged(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        external = "/usr/bin/node"

        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [{"type": "command", "command": f"{external} script.js"}],
                }
            ]
        }
        result = convert_hooks(hooks_data, plugin_dir, "my-plugin")
        assert result[0]["command"] == (f'cd "{plugin_dir}" && {external} script.js')


class TestPluginRootVariable:
    def test_plugin_root_expansion(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()

        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [
                        {"type": "command", "command": "${PLUGIN_ROOT}/bin/script.sh"}
                    ],
                }
            ]
        }
        result = convert_hooks(hooks_data, plugin_dir, "my-plugin")
        assert len(result) == 1
        assert result[0]["command"] == f'cd "{plugin_dir}" && bin/script.sh'

    def test_existing_claude_variables_still_expand(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()

        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "${CLAUDE_PLUGIN_ROOT}/a && ${CLAUDE_CODE_PLUGIN_ROOT}/b",
                        }
                    ],
                }
            ]
        }
        result = convert_hooks(hooks_data, plugin_dir, "my-plugin")
        assert result[0]["command"] == (f'cd "{plugin_dir}" && a && b')


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
        (plugin_dir / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write|Edit",
                                "hooks": [
                                    {"type": "command", "command": "node guard.js"}
                                ],
                            }
                        ]
                    }
                }
            )
        )
        skills = plugin_dir / "skills" / "review"
        skills.mkdir(parents=True)
        (skills / "SKILL.md").write_text("# Review")

        result = install_plugin(str(plugin_dir), config)
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
        (plugin_dir / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [
                                    {"type": "command", "command": "node guard.js"}
                                ],
                            }
                        ]
                    }
                }
            )
        )

        install_plugin(str(plugin_dir), config)
        install_plugin(str(plugin_dir), config)

        toml_data = config.load_toml_config()
        assert len(toml_data["hooks"]) == 1

    def test_local_plugin_path_rewrite(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        # Use a hub directory without spaces so unquoted path replacements stay
        # valid shell tokens and downstream relativization works predictably.
        hub_dir = tmp_path / "hub"
        monkeypatch.setattr(
            "kimi_mcp_hub.config.platformdirs.user_config_dir",
            lambda *args, **kwargs: str(hub_dir),
        )
        config = KimiConfig()

        plugin_dir = tmp_path / "test-codex-plugin"
        plugin_dir.mkdir()
        script = plugin_dir / "scripts" / "guard.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/sh")

        codex_hooks = plugin_dir / ".codex" / "hooks.json"
        codex_hooks.parent.mkdir(parents=True)
        codex_hooks.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": f"{plugin_dir}/scripts/guard.sh",
                                    }
                                ],
                            }
                        ]
                    }
                }
            )
        )

        result = install_plugin(str(plugin_dir), config)
        assert result["plugin_name"] == "test-codex-plugin"
        assert result["hooks_installed"] == 1

        toml_data = config.load_toml_config()
        command = toml_data["hooks"][0]["command"]
        assert str(plugin_dir) not in command
        assert "scripts/guard.sh" in command
        assert str(config.plugins_dir) not in command.split("&&", 1)[1]

    def test_local_plugin_path_rewrite_symlink_source(self, monkeypatch, tmp_path):
        """Regression test for macOS /tmp -> /private/tmp symlink bug.

        The hook file references the unresolved source path (/tmp/...), but the
        installer is given the resolved path (/private/tmp/...). The installer
        must rewrite the unresolved path too so the command is relativized.
        """
        import shutil
        import uuid

        monkeypatch.setenv("HOME", str(tmp_path))
        # Use a hub directory with spaces to verify spaced install paths are
        # quoted during rewrite and then correctly relativized.
        hub_dir = tmp_path / "hub with spaces"
        monkeypatch.setattr(
            "kimi_mcp_hub.config.platformdirs.user_config_dir",
            lambda *args, **kwargs: str(hub_dir),
        )
        config = KimiConfig()

        # Use the real /private/tmp directory so the source path begins with
        # /private/tmp, matching the macOS symlink scenario.
        resolved_source = Path(f"/private/tmp/kimi-mcp-hub-test-{uuid.uuid4().hex}")
        resolved_source.mkdir(parents=True)
        try:
            unresolved_source = Path("/tmp") / resolved_source.name

            script = resolved_source / "scripts" / "guard.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/bin/sh")

            codex_hooks = resolved_source / ".codex" / "hooks.json"
            codex_hooks.parent.mkdir(parents=True)
            codex_hooks.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Write",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": f"{unresolved_source}/scripts/guard.sh",
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                )
            )

            result = install_plugin(
                str(resolved_source), config, name="test-codex-plugin"
            )
            assert result["plugin_name"] == "test-codex-plugin"
            assert result["hooks_installed"] == 1

            toml_data = config.load_toml_config()
            command = toml_data["hooks"][0]["command"]
            command_body = command.split("&&", 1)[1]
            assert str(resolved_source) not in command
            assert str(unresolved_source) not in command
            assert str(config.plugins_dir) not in command_body
            assert "scripts/guard.sh" in command
            assert not command_body.startswith("/")
        finally:
            shutil.rmtree(resolved_source, ignore_errors=True)


class TestMalformedJson:
    def test_malformed_hooks_json_graceful(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()

        plugin_dir = tmp_path / "bad-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "hooks.json").write_text("{not valid json")
        (plugin_dir / "AGENTS.md").write_text("## Bad\n")

        result = install_plugin(str(plugin_dir), config)
        assert result["plugin_name"] == "bad-plugin"
        assert result["hooks_installed"] == 0
        assert "malformed" in capsys.readouterr().out.lower()

    def test_malformed_plugin_json_graceful(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()

        plugin_dir = tmp_path / "bad-marketplace"
        plugin_dir.mkdir()
        manifest = plugin_dir / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("{not valid json")

        result = install_plugin(str(plugin_dir), config)
        assert result["plugin_name"] == "bad-marketplace"
        assert result["hooks_installed"] == 0
        assert "malformed" in capsys.readouterr().out.lower()

    def test_load_hooks_json_returns_none_on_decode_error(self, tmp_path):
        config_path = tmp_path / "hooks.json"
        config_path.write_text("{not valid")
        assert _load_hooks_json(config_path, "hooks.json") is None


class TestRelativizeEdgeCases:
    def test_quoted_path_with_spaces(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        script = plugin_dir / "my scripts" / "guard.js"
        script.parent.mkdir(parents=True)
        script.write_text("// guard")

        command = _relativize_plugin_paths(f'"{script}"', plugin_dir)
        assert command == '"my scripts/guard.js"'

    def test_flag_equals_absolute_path(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        rules = plugin_dir / "data" / "rules.json"
        rules.parent.mkdir(parents=True)
        rules.write_text("{}")

        command = _relativize_plugin_paths(f"node guard.js --rules={rules}", plugin_dir)
        assert command == "node guard.js --rules=data/rules.json"

    def test_multiple_flag_paths(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        a = plugin_dir / "a.json"
        a.write_text("{}")
        b = plugin_dir / "b.json"
        b.write_text("{}")

        command = _relativize_plugin_paths(f"node guard.js --a={a} --b={b}", plugin_dir)
        assert command == "node guard.js --a=a.json --b=b.json"


class TestConvertHooksEdgeCases:
    def test_non_dict_hooks_data_returns_empty(self, tmp_path):
        assert convert_hooks([], tmp_path, "plugin") == []
        assert convert_hooks("not-a-dict", tmp_path, "plugin") == []
        assert convert_hooks(None, tmp_path, "plugin") == []

    def test_non_list_hook_entry_skipped(self, tmp_path):
        hooks_data = {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": "not-a-list",
                }
            ]
        }
        result = convert_hooks(hooks_data, tmp_path, "plugin")
        assert result == []


class TestCloneOrUpdateRepo:
    def test_removes_corrupted_plugin_dir_before_clone(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / ".git").mkdir()
        (source / "hooks.json").write_text(json.dumps({"hooks": {}}))

        plugin_dir = tmp_path / "target" / "plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "stale-file.txt").write_text("leftover")
        assert not (plugin_dir / ".git").exists()

        clone_or_update_repo(str(source), plugin_dir)

        assert (plugin_dir / "hooks.json").exists()
        assert not (plugin_dir / "stale-file.txt").exists()

    def test_reinstall_local_plugin_leaves_dir_in_place(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "hooks.json").write_text(json.dumps({"hooks": {}}))

        clone_or_update_repo(str(plugin_dir), plugin_dir)

        assert (plugin_dir / "hooks.json").exists()


class TestUninstallPlugin:
    def _make_plugin(self, config, name, tmp_path):
        plugin_dir = config.plugin_dir(name)
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "AGENTS.md").write_text(f"## {name}\nUse stdlib.")
        (plugin_dir / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [
                                    {"type": "command", "command": "node guard.js"}
                                ],
                            }
                        ]
                    }
                }
            )
        )
        skills = plugin_dir / "skills" / "review"
        skills.mkdir(parents=True)
        (skills / "SKILL.md").write_text("# Review")
        return plugin_dir

    def test_uninstall_removes_everything(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()
        config.agents_md.parent.mkdir(parents=True, exist_ok=True)
        config.agents_md.write_text("# Original AGENTS.md\n")

        plugin_dir = self._make_plugin(config, "ponytail", tmp_path)
        install_plugin(str(plugin_dir), config)

        result = uninstall_plugin("ponytail", config)

        assert result["plugin_dir_removed"] is True
        assert not plugin_dir.exists()
        assert result["hooks_removed"] == 1
        assert config.load_toml_config().get("hooks", []) == []
        assert result["skills_removed"] == ["ponytail-review"]
        assert not (config.skills_dir / "ponytail-review").exists()
        assert result["agents_md_removed"] is True
        assert config.agents_md.read_text(encoding="utf-8") == "# Original AGENTS.md\n"

    def test_uninstall_unknown_plugin(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()
        with pytest.raises(ValueError, match="Plugin 'missing' is not installed"):
            uninstall_plugin("missing", config)

    def test_uninstall_multi_plugin_agents_md(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()

        plugin_a = tmp_path / "plugin-a"
        plugin_a.mkdir()
        (plugin_a / "AGENTS.md").write_text("## Plugin A\nA rules.")
        (plugin_a / "hooks.json").write_text(json.dumps({"hooks": {}}))

        plugin_b = tmp_path / "plugin-b"
        plugin_b.mkdir()
        (plugin_b / "AGENTS.md").write_text("## Plugin B\nB rules.")
        (plugin_b / "hooks.json").write_text(json.dumps({"hooks": {}}))

        install_plugin(str(plugin_a), config)
        install_plugin(str(plugin_b), config)

        text_before = config.agents_md.read_text(encoding="utf-8")
        assert "<!-- plugin: plugin-a -->" in text_before
        assert "<!-- plugin: plugin-b -->" in text_before

        uninstall_plugin("plugin-a", config)

        text_after = config.agents_md.read_text(encoding="utf-8")
        assert "<!-- plugin: plugin-a -->" not in text_after
        assert "<!-- plugin: plugin-b -->" in text_after
        assert "B rules." in text_after
        assert "A rules." not in text_after

    def test_uninstall_skill_prefix_collision_uses_metadata(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()

        plugin_a = tmp_path / "plugin-a"
        plugin_a.mkdir()
        (plugin_a / "hooks.json").write_text(json.dumps({"hooks": {}}))
        skills_a = plugin_a / "skills" / "review"
        skills_a.mkdir(parents=True)
        (skills_a / "SKILL.md").write_text("# A review")

        plugin_ab = tmp_path / "plugin-ab"
        plugin_ab.mkdir()
        (plugin_ab / "hooks.json").write_text(json.dumps({"hooks": {}}))
        skills_ab = plugin_ab / "skills" / "review"
        skills_ab.mkdir(parents=True)
        (skills_ab / "SKILL.md").write_text("# AB review")

        install_plugin(str(plugin_a), config)
        install_plugin(str(plugin_ab), config)

        assert (config.skills_dir / "plugin-a-review").exists()
        assert (config.skills_dir / "plugin-ab-review").exists()

        uninstall_plugin("plugin-a", config)

        assert not (config.skills_dir / "plugin-a-review").exists()
        assert (config.skills_dir / "plugin-ab-review").exists()

    def test_uninstall_fallback_without_metadata(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()

        plugin_dir = self._make_plugin(config, "legacy", tmp_path)
        install_plugin(str(plugin_dir), config)

        # Simulate a plugin installed before metadata tracking.
        meta_path = plugin_dir / ".kimi-mcp-hub-meta.json"
        meta_path.unlink()

        result = uninstall_plugin("legacy", config)

        assert result["plugin_dir_removed"] is True
        assert "legacy-review" in result["skills_removed"]
        assert not (config.skills_dir / "legacy-review").exists()


class TestUpdatePlugin:
    def _make_plugin(self, config, name):
        plugin_dir = config.plugin_dir(name)
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "AGENTS.md").write_text(f"## {name}\nUse stdlib.")
        (plugin_dir / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [
                                    {"type": "command", "command": "node guard.js"}
                                ],
                            }
                        ]
                    }
                }
            )
        )
        skills = plugin_dir / "skills" / "review"
        skills.mkdir(parents=True)
        (skills / "SKILL.md").write_text("# Review")
        return plugin_dir

    def test_update_git_plugin_pulls(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()
        plugin_dir = self._make_plugin(config, "ponytail")
        (plugin_dir / ".git").mkdir()

        run_calls = []

        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            if cmd[0] == "git":
                return mock.Mock(returncode=0, stdout="", stderr="")
            return subprocess.run(cmd, **kwargs)

        with mock.patch(
            "kimi_mcp_hub.plugin_installer.subprocess.run", side_effect=fake_run
        ):
            result = update_plugin("ponytail", config)

        assert any("pull" in c and "--ff-only" in c for c in run_calls)
        assert result["plugin_name"] == "ponytail"
        assert result["hooks_installed"] == 1

    def test_update_local_plugin_reinstalls(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()
        self._make_plugin(config, "ponytail")

        with mock.patch("kimi_mcp_hub.plugin_installer.subprocess.run") as run_mock:
            result = update_plugin("ponytail", config)

        run_mock.assert_not_called()
        assert result["plugin_name"] == "ponytail"
        assert result["hooks_installed"] == 1

    def test_update_unknown_plugin(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()
        with pytest.raises(ValueError, match="Plugin 'missing' is not installed"):
            update_plugin("missing", config)

    def test_update_git_pull_failure(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        config = KimiConfig()
        plugin_dir = self._make_plugin(config, "ponytail")
        (plugin_dir / ".git").mkdir()

        with mock.patch(
            "kimi_mcp_hub.plugin_installer.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["git"], stderr="fail"),
        ):
            with pytest.raises(subprocess.CalledProcessError):
                update_plugin("ponytail", config)
