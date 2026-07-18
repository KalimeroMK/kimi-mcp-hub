"""Tests for shell-init and doctor duplicate detection."""

import json

import platformdirs
import pytest
from click.testing import CliRunner

from kimi_mcp_hub.cli import main
from kimi_mcp_hub.cli.misc_cmds import SHELL_INIT_MARKER_BEGIN
from kimi_mcp_hub.config import KimiConfig


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Redirect HOME and hub config to a temporary directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    hub_dir = tmp_path / "hub"
    monkeypatch.setattr(
        platformdirs,
        "user_config_dir",
        lambda *args, **kwargs: str(hub_dir),
    )
    return tmp_path


class TestShellInit:
    def test_prints_snippet_without_install(self, home):
        result = CliRunner().invoke(main, ["shell-init"])
        assert result.exit_code == 0, result.output
        assert "kimi-mcp-hub sync" in result.output
        assert "k()" in result.output
        assert SHELL_INIT_MARKER_BEGIN in result.output

    def test_install_appends_to_zshrc(self, home, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        result = CliRunner().invoke(main, ["shell-init", "--install"])
        assert result.exit_code == 0, result.output

        rc = home / ".zshrc"
        assert rc.exists()
        content = rc.read_text()
        assert SHELL_INIT_MARKER_BEGIN in content
        assert "kimi-mcp-hub sync" in content

    def test_install_is_idempotent(self, home, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        runner = CliRunner()
        assert runner.invoke(main, ["shell-init", "--install"]).exit_code == 0
        result = runner.invoke(main, ["shell-init", "--install"])
        assert result.exit_code == 0, result.output
        assert "Already installed" in result.output
        # Snippet appears only once
        assert (home / ".bashrc").read_text().count(SHELL_INIT_MARKER_BEGIN) == 1

    def test_install_unsupported_shell_fails(self, home, monkeypatch):
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        result = CliRunner().invoke(main, ["shell-init", "--install"])
        assert result.exit_code == 1
        assert "Unsupported shell" in result.output


class TestDoctorDuplicates:
    def _install_fake_plugin_manifest(self, home, server_names):
        manifest_dir = home / ".kimi-code" / "plugins" / "managed" / "kimi-mcp-hub"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "kimi.plugin.json").write_text(
            json.dumps({"mcpServers": {name: {} for name in server_names}})
        )

    def test_doctor_warns_on_plugin_duplicate(self, home):
        KimiConfig().add_server("github", {"url": "https://api.githubcopilot.com/mcp/"})
        KimiConfig().add_server("slack", {"command": "npx"})
        self._install_fake_plugin_manifest(home, ["github"])

        result = CliRunner().invoke(main, ["doctor"])
        assert result.exit_code == 0, result.output
        assert "Duplicate" in result.output
        assert "github" in result.output
        # slack is not duplicated, must not be listed as one
        dup_section = result.output.split("Duplicate")[1]
        assert "slack" not in dup_section

    def test_doctor_no_duplicates_no_warning(self, home):
        KimiConfig().add_server("slack", {"command": "npx"})
        self._install_fake_plugin_manifest(home, ["github"])

        result = CliRunner().invoke(main, ["doctor"])
        assert result.exit_code == 0, result.output
        assert "Duplicate" not in result.output
