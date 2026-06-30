"""Tests for KimiConfig."""

import json

import pytest

from kimi_mcp_hub.config import KimiConfig


@pytest.fixture
def temp_config(tmp_path):
    """Return a KimiConfig pointing at temporary directories."""
    config = KimiConfig()
    # Override paths for isolation
    config.kimi_dir = tmp_path / ".kimi"
    config.mcp_json = config.kimi_dir / "mcp.json"
    config.config_toml = config.kimi_dir / "config.toml"
    config.agents_md = config.kimi_dir / "AGENTS.md"
    config.skills_dir = tmp_path / ".kimi-code" / "skills"
    config.hub_dir = tmp_path / ".config" / "kimi-mcp-hub"
    config.tokens_file = config.hub_dir / "tokens.json"
    config.hub_dir.mkdir(parents=True, exist_ok=True)
    config.kimi_dir.mkdir(parents=True, exist_ok=True)
    return config


class TestKimiConfig:
    def test_add_remove_server(self, temp_config):
        temp_config.add_server("github", {"command": "npx", "args": ["server-github"]})
        servers = temp_config.list_servers()
        assert "github" in servers
        assert servers["github"]["command"] == "npx"

        temp_config.remove_server("github")
        assert "github" not in temp_config.list_servers()

    def test_mcp_json_is_valid_json(self, temp_config):
        temp_config.add_server("test", {"transport": "stdio"})
        data = json.loads(temp_config.mcp_json.read_text())
        assert "mcpServers" in data
        assert data["mcpServers"]["test"]["transport"] == "stdio"

    def test_save_load_token(self, temp_config):
        temp_config.save_token("github", {"access_token": "secret123"})
        loaded = temp_config.load_token("github")
        assert loaded["access_token"] == "secret123"

    def test_memory_summary_config_defaults(self, temp_config):
        assert temp_config.get_memory_summary_api_key() == ""
        assert temp_config.get_memory_summary_model() == "gpt-4o-mini"
        assert temp_config.get_memory_summary_base_url() == "https://api.openai.com/v1"
        assert temp_config.is_memory_summary_enabled() is False

    def test_memory_summary_config_round_trip(self, temp_config):
        temp_config.set_memory_summary_config(
            api_key="sk-test",
            model="gpt-4o-mini",
            base_url="https://api.example.com/v1",
            enabled=True,
        )
        assert temp_config.get_memory_summary_api_key() == "sk-test"
        assert temp_config.get_memory_summary_model() == "gpt-4o-mini"
        assert temp_config.get_memory_summary_base_url() == "https://api.example.com/v1"
        assert temp_config.is_memory_summary_enabled() is True

    def test_memory_summary_config_disabled_round_trip(self, temp_config):
        temp_config.set_memory_summary_config(
            api_key="sk-test",
            model="gpt-4o-mini",
            base_url="https://api.example.com/v1",
            enabled=False,
        )
        assert temp_config.is_memory_summary_enabled() is False

    def test_memory_summary_enabled_fallback_to_api_key(self, temp_config):
        data = temp_config.load_toml_config()
        data.setdefault("memory", {})["summary_api_key"] = "sk-test"
        temp_config.save_toml_config(data)
        assert temp_config.is_memory_summary_enabled() is True

    def test_memory_summary_config_overwrite(self, temp_config):
        temp_config.set_memory_summary_config(
            api_key="sk-first",
            model="gpt-4o-mini",
            base_url="https://api.first.com/v1",
            enabled=True,
        )
        temp_config.set_memory_summary_config(
            api_key="sk-second",
            model="gpt-4o",
        )
        assert temp_config.get_memory_summary_api_key() == "sk-second"
        assert temp_config.get_memory_summary_model() == "gpt-4o"
        assert temp_config.get_memory_summary_base_url() == "https://api.openai.com/v1"
        assert temp_config.is_memory_summary_enabled() is True
