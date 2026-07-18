"""Tests for named MCP-server profiles (profiles.py + profile commands)."""

import json

import platformdirs
import pytest
from click.testing import CliRunner

from kimi_mcp_hub.cli import main
from kimi_mcp_hub.config import KimiConfig
from kimi_mcp_hub.profiles import ProfileStore


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
def store(home):
    return ProfileStore()


class TestProfileStore:
    def test_save_load_roundtrip(self, store):
        data = {"mcpServers": {"github": {"url": "https://api.githubcopilot.com/mcp/"}}}
        store.save("work", data)
        assert store.load("work") == data

    def test_list_sorted(self, store):
        store.save("b", {"mcpServers": {}})
        store.save("a", {"mcpServers": {}})
        assert store.list() == ["a", "b"]

    def test_load_missing_returns_none(self, store):
        assert store.load("nope") is None

    def test_load_corrupt_returns_none(self, store):
        store.dir.mkdir(parents=True)
        (store.dir / "broken.json").write_text("not json")
        assert store.load("broken") is None

    def test_remove(self, store):
        store.save("x", {"mcpServers": {}})
        assert store.remove("x") is True
        assert store.remove("x") is False

    def test_rejects_path_traversal_names(self, store):
        with pytest.raises(ValueError):
            store.save("../evil", {"mcpServers": {}})
        with pytest.raises(ValueError):
            store.load("a/b")
        with pytest.raises(ValueError):
            store.remove(".hidden")


class TestProfileCommands:
    def _add_global_server(self):
        KimiConfig().add_server("github", {"url": "https://api.githubcopilot.com/mcp/"})

    def test_save_and_load_roundtrip(self, home):
        runner = CliRunner()
        self._add_global_server()

        result = runner.invoke(main, ["profile", "save", "work"])
        assert result.exit_code == 0, result.output
        assert "Saved profile" in result.output

        # Wipe global, then restore from the profile
        KimiConfig().remove_server("github")
        assert "github" not in KimiConfig().list_servers()

        result = runner.invoke(main, ["profile", "load", "work", "--yes"])
        assert result.exit_code == 0, result.output
        assert "github" in KimiConfig().list_servers()

    def test_load_replaces_global_config(self, home):
        runner = CliRunner()
        self._add_global_server()
        runner.invoke(main, ["profile", "save", "work"])

        config = KimiConfig()
        config.add_server("slack", {"command": "npx"})
        result = runner.invoke(main, ["profile", "load", "work", "--yes"])
        assert result.exit_code == 0, result.output

        servers = KimiConfig().list_servers()
        assert "github" in servers
        assert "slack" not in servers  # replaced, not merged

    def test_load_unknown_profile_fails(self, home):
        result = CliRunner().invoke(main, ["profile", "load", "ghost", "--yes"])
        assert result.exit_code == 1
        assert "Profile not found" in result.output

    def test_list_profiles(self, home):
        runner = CliRunner()
        self._add_global_server()
        runner.invoke(main, ["profile", "save", "work"])

        result = runner.invoke(main, ["profile", "list"])
        assert result.exit_code == 0, result.output
        assert "work" in result.output
        assert "github" in result.output

    def test_list_empty(self, home):
        result = CliRunner().invoke(main, ["profile", "list"])
        assert result.exit_code == 0, result.output
        assert "No profiles saved" in result.output

    def test_remove_profile(self, home):
        runner = CliRunner()
        self._add_global_server()
        runner.invoke(main, ["profile", "save", "work"])

        result = runner.invoke(main, ["profile", "remove", "work"])
        assert result.exit_code == 0, result.output
        assert "Removed profile" in result.output

        result = runner.invoke(main, ["profile", "remove", "work"])
        assert result.exit_code == 1

    def test_save_invalid_name_fails(self, home):
        result = CliRunner().invoke(main, ["profile", "save", "../evil"])
        assert result.exit_code == 1

    def test_saved_profile_is_valid_json(self, home):
        self._add_global_server()
        CliRunner().invoke(main, ["profile", "save", "work"])
        data = json.loads((home / "hub" / "profiles" / "work.json").read_text())
        assert "github" in data["mcpServers"]
