"""Tests for the Kimi Code plugin manifest (kimi.plugin.json)."""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "kimi.plugin.json"
COMMANDS_DIR = REPO_ROOT / "commands"


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestManifestShape:
    def test_name_matches_plugin_id_rules(self, manifest):
        assert re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", manifest["name"])

    def test_version_matches_package(self, manifest):
        from kimi_mcp_hub import __version__

        assert manifest["version"] == __version__

    def test_skills_path_exists(self, manifest):
        skills = manifest["skills"]
        assert skills.startswith("./")
        skills_dir = REPO_ROOT / skills
        assert skills_dir.is_dir()
        # Every skill directory must contain a SKILL.md
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        assert len(skill_dirs) >= 50
        for d in skill_dirs:
            assert (d / "SKILL.md").is_file(), f"missing SKILL.md in {d.name}"

    def test_commands_path_exists(self, manifest):
        commands = manifest["commands"]
        assert commands.startswith("./")
        assert (REPO_ROOT / commands).is_dir()


class TestManifestMcpServers:
    def test_entries_have_valid_shape(self, manifest):
        for name, cfg in manifest["mcpServers"].items():
            assert isinstance(cfg, dict), name
            if "command" in cfg:
                assert cfg.get("args"), f"{name}: stdio entry needs args"
            else:
                assert cfg.get("url"), f"{name}: entry needs command or url"

    def test_stdio_entries_match_server_modules(self, manifest):
        from kimi_mcp_hub.servers.chrome_devtools import ChromeDevToolsServer
        from kimi_mcp_hub.servers.context7 import Context7Server
        from kimi_mcp_hub.servers.desktop_commander import DesktopCommanderServer
        from kimi_mcp_hub.servers.mobile_mcp import MobileMCPServer
        from kimi_mcp_hub.servers.playwright import PlaywrightServer

        expected = {
            "chrome-devtools": ChromeDevToolsServer.get_stdio_config(),
            "context7": Context7Server.get_stdio_config(),
            "desktop-commander": DesktopCommanderServer.get_stdio_config(),
            "mobile": MobileMCPServer.get_stdio_config(),
            "playwright": PlaywrightServer.get_stdio_config(),
        }
        servers = manifest["mcpServers"]
        for name, cfg in expected.items():
            entry = servers[name]
            assert entry["command"] == cfg["command"], name
            assert entry["args"] == cfg["args"], name

    def test_oauth_entries_match_server_modules(self, manifest):
        from kimi_mcp_hub.servers.confluence import ConfluenceServer
        from kimi_mcp_hub.servers.figma import FigmaServer
        from kimi_mcp_hub.servers.github import GitHubServer
        from kimi_mcp_hub.servers.gitlab import GitLabServer
        from kimi_mcp_hub.servers.jira import JiraServer
        from kimi_mcp_hub.servers.linear import LinearServer
        from kimi_mcp_hub.servers.stripe import StripeServer
        from kimi_mcp_hub.servers.supabase import SupabaseServer

        expected = {
            "linear": LinearServer.get_official_config(),
            "jira": JiraServer.get_oauth_config(),
            "confluence": ConfluenceServer.get_oauth_config(),
            "supabase": SupabaseServer.get_official_config(),
            "figma": FigmaServer.get_official_config(),
            "stripe": StripeServer.get_official_config(),
            "gitlab": GitLabServer.get_official_config(),
            "github": GitHubServer.get_official_config(),
        }
        servers = manifest["mcpServers"]
        for name, cfg in expected.items():
            entry = servers[name]
            assert entry["url"] == cfg["url"], name
            assert entry.get("transport") == cfg.get("transport"), name
            assert entry.get("auth") == cfg.get("auth"), name


class TestCommandFiles:
    def test_commands_have_frontmatter_description(self):
        command_files = list(COMMANDS_DIR.glob("*.md"))
        assert command_files, "no command files found"
        for path in command_files:
            text = path.read_text(encoding="utf-8")
            assert text.startswith("---\n"), f"{path.name}: missing frontmatter"
            end = text.find("\n---\n", 4)
            assert end != -1, f"{path.name}: unterminated frontmatter"
            frontmatter = text[4:end]
            assert "description:" in frontmatter, (
                f"{path.name}: frontmatter needs a description"
            )
            assert text[end + 5 :].strip(), f"{path.name}: empty command body"
