"""Integration tests for CLI commands and server configuration."""

import os

import platformdirs
import pytest
from click.testing import CliRunner

from kimi_mcp_hub.cli import main
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


@pytest.fixture
def runner():
    return CliRunner()


class TestInitAndServerConfig:
    def test_init_yes_creates_valid_config(self, home, runner, monkeypatch):
        # Allow npx auto-install to run but skip the actual npm install prompts.
        monkeypatch.setattr(
            "kimi_mcp_hub.cli.shutil.which",
            lambda cmd: "/usr/bin/npx" if cmd == "npx" else None,
        )
        monkeypatch.setattr(
            "kimi_mcp_hub.cli.maybe_install_npx_deps",
            lambda cfg, console: True,
        )

        result = runner.invoke(main, ["init", "--yes"])
        assert result.exit_code == 0, result.output

        config = KimiConfig()
        assert config.mcp_json.exists()
        data = config.load_mcp()
        assert "mcpServers" in data
        assert "chrome-devtools" in data["mcpServers"]
        assert "context7" in data["mcpServers"]
        assert "playwright" in data["mcpServers"]

    def test_add_server_writes_config(self, home, runner, monkeypatch):
        monkeypatch.setattr(
            "kimi_mcp_hub.cli.maybe_install_npx_deps",
            lambda cfg, console: True,
        )

        result = runner.invoke(main, ["add", "playwright"])
        assert result.exit_code == 0, result.output

        config = KimiConfig()
        servers = config.list_servers()
        assert "playwright" in servers
        assert servers["playwright"]["command"] == "npx"

    def test_remove_server_removes_from_config(self, home, runner, monkeypatch):
        monkeypatch.setattr(
            "kimi_mcp_hub.cli.maybe_install_npx_deps",
            lambda cfg, console: True,
        )
        result = runner.invoke(main, ["add", "playwright"])
        assert result.exit_code == 0, result.output

        result = runner.invoke(main, ["remove", "playwright"])
        assert result.exit_code == 0, result.output

        config = KimiConfig()
        assert "playwright" not in config.list_servers()

    def test_test_server_found_and_missing(self, home, runner, monkeypatch, tmp_path):
        # Put a fake `npx` binary on PATH so `which npx` succeeds.
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_npx = bin_dir / "npx"
        fake_npx.write_text("#!/bin/sh\necho fake npx")
        fake_npx.chmod(0o755)
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

        monkeypatch.setattr(
            "kimi_mcp_hub.cli.maybe_install_npx_deps",
            lambda cfg, console: True,
        )
        result = runner.invoke(main, ["add", "playwright"])
        assert result.exit_code == 0, result.output

        result = runner.invoke(main, ["test", "playwright"])
        assert result.exit_code == 0, result.output
        assert "found" in result.output

        config = KimiConfig()
        config.add_server(
            "missing-server", {"command": "definitely-not-real-binary-12345"}
        )
        result = runner.invoke(main, ["test", "missing-server"])
        assert result.exit_code == 1, result.output
        assert "not found" in result.output
