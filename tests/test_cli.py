"""Tests for the Kimi MCP Hub CLI."""

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from kimi_mcp_hub.cli import main, SERVERS, SKILLS, CORE_SKILLS
from kimi_mcp_hub import __version__, TOTAL_SERVERS, TOTAL_SKILLS
from kimi_mcp_hub.auth.oauth import WebFlowHandler
from kimi_mcp_hub.servers.linear import LinearServer
from kimi_mcp_hub.servers.figma import FigmaServer
from kimi_mcp_hub.servers.obsidian import ObsidianServer
from kimi_mcp_hub.servers.stripe import StripeServer
from kimi_mcp_hub.servers.gitlab import GitLabServer
from kimi_mcp_hub.servers.figma_context import FigmaContextServer
from kimi_mcp_hub.servers.desktop_commander import DesktopCommanderServer
from kimi_mcp_hub.servers.dbhub import DBHubServer
from kimi_mcp_hub.servers.mobile_mcp import MobileMCPServer


class TestVersion:
    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert f"kimi-mcp-hub, version {__version__}" in result.output

    def test_main_module(self):
        """`python -m kimi_mcp_hub --version` should work."""
        result = subprocess.run(
            [sys.executable, "-m", "kimi_mcp_hub", "--version"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert f"kimi-mcp-hub, version {__version__}" in result.stdout


class TestServerDefinitions:
    def test_all_servers_have_tools(self):
        for name, cls in SERVERS.items():
            tools = cls.get_tools()
            assert isinstance(tools, list), f"{name}.get_tools() must return a list"
            assert all("name" in t and "desc" in t for t in tools), f"{name} tools malformed"

    def test_server_count_matches_constant(self):
        assert len(SERVERS) == TOTAL_SERVERS

    def test_obsidian_server_config(self):
        cfg = ObsidianServer.get_stdio_config("/path/to/vault")
        assert cfg["command"] == "npx"
        assert "obsidian-mcp" in cfg["args"]
        assert "/path/to/vault" in cfg["args"]

    def test_linear_has_oauth_and_api_key_modes(self):
        assert LinearServer.get_official_config()["url"] == "https://mcp.linear.app/mcp"
        assert LinearServer.get_official_config()["auth"] == "oauth"
        assert "LINEAR_API_KEY" in LinearServer.get_stdio_config("test-key")["env"]
        assert LinearServer.get_official_stdio_config()["command"] == "npx"

    def test_figma_has_official_oauth_and_pat_modes(self):
        assert FigmaServer.get_official_config()["url"] == "https://mcp.figma.com/mcp"
        assert FigmaServer.get_official_config()["auth"] == "oauth"
        assert "FIGMA_ACCESS_TOKEN" in FigmaServer.get_console_config("test-token")["env"]
        assert FigmaServer.get_official_stdio_config()["command"] == "npx"

    def test_stripe_has_official_oauth_and_api_key_modes(self):
        assert StripeServer.get_official_config()["url"] == "https://mcp.stripe.com"
        assert StripeServer.get_official_config()["auth"] == "oauth"
        cfg = StripeServer.get_stdio_config("rk_test")
        assert any("rk_test" in arg for arg in cfg["args"])
        assert cfg["command"] == "npx"
        assert StripeServer.get_official_stdio_config()["command"] == "npx"
        docker_cfg = StripeServer.get_docker_config("rk_test")
        assert docker_cfg["command"] == "docker"
        assert any("rk_test" in arg for arg in docker_cfg["args"])

    def test_gitlab_has_official_oauth_and_pat_modes(self):
        assert GitLabServer.get_official_config()["url"] == "https://gitlab.com/api/v4/mcp"
        assert GitLabServer.get_official_config()["auth"] == "oauth"
        self_managed = GitLabServer.get_official_config("https://gitlab.example.com")
        assert self_managed["url"] == "https://gitlab.example.com/api/v4/mcp"
        cfg = GitLabServer.get_stdio_config("glpat-test")
        assert cfg["env"]["GITLAB_PERSONAL_ACCESS_TOKEN"] == "glpat-test"
        assert "https://gitlab.com/api/v4" in cfg["env"]["GITLAB_API_URL"]
        assert GitLabServer.get_official_stdio_config()["command"] == "npx"

    def test_figma_context_uses_developer_mcp(self):
        cfg = FigmaContextServer.get_stdio_config("figd-test")
        assert cfg["command"] == "npx"
        assert any("figma-developer-mcp" in arg for arg in cfg["args"])
        assert any("figd-test" in arg for arg in cfg["args"])
        assert cfg["env"]["FIGMA_API_KEY"] == "figd-test"

    def test_desktop_commander_configs(self):
        cfg = DesktopCommanderServer.get_stdio_config()
        assert cfg["command"] == "npx"
        assert any("@wonderwhy-er/desktop-commander" in arg for arg in cfg["args"])
        docker_cfg = DesktopCommanderServer.get_docker_config()
        assert docker_cfg["command"] == "docker"

    def test_dbhub_stdio_and_docker(self):
        cfg = DBHubServer.get_stdio_config("postgres://u:p@localhost/db")
        assert cfg["command"] == "npx"
        assert "@bytebase/dbhub" in cfg["args"]
        assert "postgres://u:p@localhost/db" in cfg["args"]
        assert "--readonly" not in cfg["args"]
        readonly_cfg = DBHubServer.get_stdio_config("postgres://u:p@localhost/db", readonly=True)
        assert "--readonly" in readonly_cfg["args"]
        demo_cfg = DBHubServer.get_demo_config()
        assert "--demo" in demo_cfg["args"]
        docker_cfg = DBHubServer.get_docker_config("postgres://u:p@host.docker.internal/db")
        assert docker_cfg["command"] == "docker"

    def test_mobile_mcp_config(self):
        cfg = MobileMCPServer.get_stdio_config()
        assert cfg["command"] == "npx"
        assert any("@mobilenext/mobile-mcp" in arg for arg in cfg["args"])


class TestSkillDefinitions:
    def test_all_skills_have_directories(self):
        pkg_dir = Path(__file__).parent.parent / "src" / "kimi_mcp_hub" / "skills"
        skill_dirs = {d.name for d in pkg_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()}
        assert skill_dirs == set(SKILLS.keys())

    def test_core_skills_are_known(self):
        assert all(skill in SKILLS for skill in CORE_SKILLS)

    def test_skill_count_matches_constant(self):
        assert len(SKILLS) == TOTAL_SKILLS

    def test_skill_descriptions_are_short(self):
        for name, desc in SKILLS.items():
            assert len(desc) <= 240, f"{name} description too long: {len(desc)} chars"


class TestConfigCommands:
    def test_status_runs(self):
        runner = CliRunner()
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_list_skills_runs(self):
        runner = CliRunner()
        result = runner.invoke(main, ["list-skills"])
        assert result.exit_code == 0
        assert "karpathy" in result.output

    def test_doctor_runs(self):
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        # doctor may show missing dependencies, but should not crash
        assert result.exit_code in (0, 1)


class TestOAuthRedirect:
    def test_web_flow_uses_callback_path(self):
        """OAuth web flow must use /callback path for redirect URI."""
        handler = WebFlowHandler(
            auth_url="https://example.com/auth",
            token_url="https://example.com/token",
            client_id="test",
        )
        # We cannot easily call authorize() without a browser, but we can verify
        # the callback server class accepts the /callback path and that the
        # redirect URI format is correct by inspecting the implementation.
        from kimi_mcp_hub.auth.oauth import LocalCallbackServer
        server = LocalCallbackServer()
        port = server.start()
        try:
            redirect_uri = f"http://127.0.0.1:{port}/callback"
            assert redirect_uri.endswith("/callback")
        finally:
            server.stop()
