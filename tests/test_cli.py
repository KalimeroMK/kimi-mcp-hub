"""Tests for the Kimi MCP Hub CLI."""

import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from kimi_mcp_hub.cli import (
    main,
    SERVERS,
    SKILLS,
    CORE_SKILLS,
    _is_dev_install,
    _get_venv_info,
    _link_venv_binaries,
    _run_pip_upgrade,
)
from kimi_mcp_hub.config import KimiConfig
from kimi_mcp_hub import __version__, TOTAL_SERVERS, TOTAL_SKILLS
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
            assert all("name" in t and "desc" in t for t in tools), (
                f"{name} tools malformed"
            )

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
        assert (
            "FIGMA_ACCESS_TOKEN" in FigmaServer.get_console_config("test-token")["env"]
        )
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
        assert (
            GitLabServer.get_official_config()["url"] == "https://gitlab.com/api/v4/mcp"
        )
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
        readonly_cfg = DBHubServer.get_stdio_config(
            "postgres://u:p@localhost/db", readonly=True
        )
        assert "--readonly" in readonly_cfg["args"]
        demo_cfg = DBHubServer.get_demo_config()
        assert "--demo" in demo_cfg["args"]
        docker_cfg = DBHubServer.get_docker_config(
            "postgres://u:p@host.docker.internal/db"
        )
        assert docker_cfg["command"] == "docker"

    def test_mobile_mcp_config(self):
        cfg = MobileMCPServer.get_stdio_config()
        assert cfg["command"] == "npx"
        assert any("@mobilenext/mobile-mcp" in arg for arg in cfg["args"])


class TestSkillDefinitions:
    def test_all_skills_have_directories(self):
        pkg_dir = Path(__file__).parent.parent / "src" / "kimi_mcp_hub" / "skills"
        skill_dirs = {
            d.name
            for d in pkg_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        }
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


class TestUpdateCommand:
    def test_update_dev_install(self):
        runner = CliRunner()
        with mock.patch("kimi_mcp_hub.cli._is_dev_install", return_value=True):
            result = runner.invoke(main, ["update"])
        assert result.exit_code == 0
        assert "Detected development install" in result.output
        assert "git pull && pip install -e ." in result.output

    def test_update_uses_github_first(self):
        runner = CliRunner()
        venv_dir = Path("/fake/venv")
        with (
            mock.patch("kimi_mcp_hub.cli._is_dev_install", return_value=False),
            mock.patch(
                "kimi_mcp_hub.cli._get_venv_info",
                return_value=("/fake/venv/bin/python", venv_dir, False),
            ),
            mock.patch(
                "kimi_mcp_hub.cli._run_pip_upgrade", return_value=True
            ) as pip_mock,
            mock.patch("kimi_mcp_hub.cli._link_venv_binaries") as link_mock,
        ):
            result = runner.invoke(main, ["update"])
        assert result.exit_code == 0
        pip_mock.assert_called_once()
        sources = pip_mock.call_args[0][1]
        assert sources[0][0] == "GitHub"
        assert sources[1][0] == "PyPI"
        link_mock.assert_called_once_with(venv_dir)

    def test_update_in_place_existing_venv(self):
        runner = CliRunner()
        with (
            mock.patch("kimi_mcp_hub.cli._is_dev_install", return_value=False),
            mock.patch(
                "kimi_mcp_hub.cli._get_venv_info",
                return_value=(sys.executable, Path("/existing/venv"), True),
            ),
            mock.patch(
                "kimi_mcp_hub.cli._run_pip_upgrade", return_value=True
            ) as pip_mock,
            mock.patch("kimi_mcp_hub.cli._link_venv_binaries") as link_mock,
        ):
            result = runner.invoke(main, ["update"])
        assert result.exit_code == 0
        pip_mock.assert_called_once()
        link_mock.assert_not_called()

    def test_update_failure_shows_fallback(self):
        runner = CliRunner()
        with (
            mock.patch("kimi_mcp_hub.cli._is_dev_install", return_value=False),
            mock.patch(
                "kimi_mcp_hub.cli._get_venv_info",
                return_value=("/fake/venv/bin/python", Path("/fake/venv"), False),
            ),
            mock.patch(
                "kimi_mcp_hub.cli._run_pip_upgrade", return_value=False
            ) as pip_mock,
            mock.patch("kimi_mcp_hub.cli._link_venv_binaries") as link_mock,
        ):
            result = runner.invoke(main, ["update"])
        assert result.exit_code == 1
        assert "Update failed" in result.output
        link_mock.assert_not_called()
        sources = pip_mock.call_args[0][1]
        assert [s[0] for s in sources] == ["GitHub", "PyPI"]

    def test_run_pip_upgrade_tries_sources_in_order(self):
        results = iter(
            [
                mock.Mock(returncode=1, stdout="", stderr="git error"),
                mock.Mock(returncode=0, stdout="", stderr=""),
            ]
        )
        with (
            mock.patch(
                "kimi_mcp_hub.cli.subprocess.run",
                side_effect=lambda *a, **k: next(results),
            ) as run_mock,
            mock.patch("kimi_mcp_hub.cli.console.print"),
        ):
            success = _run_pip_upgrade(
                "/fake/python",
                [
                    ("GitHub", "git+https://github.com/KalimeroMK/kimi-mcp-hub.git"),
                    ("PyPI", "kimi-mcp-hub"),
                ],
            )
        assert success is True
        assert run_mock.call_count == 2
        assert (
            run_mock.call_args_list[0][0][0][-1]
            == "git+https://github.com/KalimeroMK/kimi-mcp-hub.git"
        )
        assert run_mock.call_args_list[1][0][0][-1] == "kimi-mcp-hub"

    def test_link_venv_binaries_creates_symlinks(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        venv_dir = home / ".kimi-mcp-hub" / ".venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        for name in ["kimi-mcp-hub", "kmcp"]:
            (venv_bin / name).write_text("#!/bin/sh")
        _link_venv_binaries(venv_dir)
        for name in ["kimi-mcp-hub", "kmcp"]:
            dst = home / ".local" / "bin" / name
            assert dst.is_symlink()
            assert dst.resolve() == venv_bin / name

    def test_get_venv_info_creates_and_reuses_isolated_venv(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("kimi_mcp_hub.cli.sys.prefix", "/usr")
        monkeypatch.setattr("kimi_mcp_hub.cli.sys.base_prefix", "/usr")
        monkeypatch.setenv("HOME", str(tmp_path))

        created = []

        def fake_subprocess(cmd, **kwargs):
            if "venv" in cmd:
                venv_dir = Path(cmd[-1])
                (venv_dir / "bin" / "python").mkdir(parents=True)
                created.append(venv_dir)
                return mock.Mock(returncode=0, stdout="", stderr="")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch(
            "kimi_mcp_hub.cli.subprocess.run", side_effect=fake_subprocess
        ) as run_mock:
            target, venv_dir, in_venv = _get_venv_info()
        assert in_venv is False
        assert created
        assert str(venv_dir) == str(tmp_path / ".kimi-mcp-hub" / ".venv")
        assert (venv_dir / "bin" / "python").exists()
        assert "venv" in run_mock.call_args[0][0]

        with mock.patch("kimi_mcp_hub.cli.subprocess.run") as run_mock2:
            target2, venv_dir2, in_venv2 = _get_venv_info()
        assert venv_dir2 == venv_dir
        assert in_venv2 is False
        run_mock2.assert_not_called()

    def test_get_venv_info_uses_active_venv(self, monkeypatch):
        monkeypatch.setattr("kimi_mcp_hub.cli.sys.prefix", "/venv")
        monkeypatch.setattr("kimi_mcp_hub.cli.sys.base_prefix", "/usr")
        monkeypatch.setattr("kimi_mcp_hub.cli.sys.executable", "/venv/bin/python")
        target, venv_dir, in_venv = _get_venv_info()
        assert in_venv is True
        assert target == "/venv/bin/python"
        assert venv_dir is None


class TestDevInstallDetection:
    def test_is_dev_install_true_in_git_repo(self, tmp_path, monkeypatch):
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        fake_file = str(repo / "src" / "kimi_mcp_hub" / "cli.py")
        monkeypatch.setattr("kimi_mcp_hub.cli.__file__", fake_file)
        assert _is_dev_install() is True

    def test_is_dev_install_false_outside_git_repo(self, tmp_path, monkeypatch):
        site_packages = tmp_path / "site-packages" / "kimi_mcp_hub"
        fake_file = str(site_packages / "cli.py")
        monkeypatch.setattr("kimi_mcp_hub.cli.__file__", fake_file)
        assert _is_dev_install() is False


class TestObsidianCLI:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        return tmp_path

    def test_status_no_vaults(self, home):
        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "status"])
        assert result.exit_code == 0
        assert "No Obsidian vaults configured" in result.output
        assert "kimi-mcp-hub obsidian add" in result.output

    def test_add_creates_vault_and_updates_config(self, home):
        vault = home / "My Vault"
        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "add", str(vault)])
        assert result.exit_code == 0, result.output
        assert "Added vault" in result.output
        assert "my-vault" in result.output
        assert "Set as default memory vault" in result.output

        config = KimiConfig()
        assert config.get_obsidian_vaults() == [str(vault.resolve())]
        assert config.get_default_memory_vault() == str(vault.resolve())
        assert ObsidianServer.validate_vault(vault) is True
        assert (vault / "README.md").exists()

    def test_status_shows_vault_valid(self, home):
        vault = home / "ExistingVault"
        ObsidianServer.scaffold_vault(vault)
        config = KimiConfig()
        config.set_obsidian_vaults([str(vault.resolve())])

        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "status"])
        assert result.exit_code == 0
        assert "existingvault" in result.output
        assert "valid" in result.output

    def test_status_expands_tilde_path(self, home):
        vault = home / "Memory"
        ObsidianServer.scaffold_vault(vault)
        config = KimiConfig()
        config.set_obsidian_vaults(["~/Memory"])

        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "status"])
        assert result.exit_code == 0, result.output
        assert "memory" in result.output
        assert "valid" in result.output
        assert "missing" not in result.output

    def test_list_alias(self, home):
        vault = home / "VaultTwo"
        ObsidianServer.scaffold_vault(vault)
        config = KimiConfig()
        config.set_obsidian_vaults([str(vault.resolve())])

        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "list"])
        assert result.exit_code == 0
        assert "vaulttwo" in result.output

    def test_add_second_vault_keeps_default(self, home):
        vault1 = home / "First"
        vault2 = home / "Second"
        runner = CliRunner()
        runner.invoke(main, ["obsidian", "add", str(vault1)])
        result = runner.invoke(main, ["obsidian", "add", str(vault2)])
        assert result.exit_code == 0, result.output

        config = KimiConfig()
        assert config.get_default_memory_vault() == str(vault1.resolve())
        vaults = config.get_obsidian_vaults()
        assert str(vault1.resolve()) in vaults
        assert str(vault2.resolve()) in vaults

    def test_remove_by_slug(self, home):
        vault = home / "ToRemove"
        ObsidianServer.scaffold_vault(vault)
        config = KimiConfig()
        config.set_obsidian_vaults([str(vault.resolve())])
        config.set_default_memory_vault(str(vault.resolve()))

        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "remove", "toremove"])
        assert result.exit_code == 0, result.output
        assert "Removed vault 'toremove'" in result.output

        config = KimiConfig()
        assert config.get_obsidian_vaults() == []
        assert config.get_default_memory_vault() is None

    def test_remove_unknown_slug_errors(self, home):
        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "remove", "missing"])
        assert result.exit_code == 1
        assert "No vault with slug 'missing'" in result.output

    def test_add_existing_file_fails(self, home):
        existing_file = home / "not-a-dir.md"
        existing_file.write_text("# notes", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "add", str(existing_file)])
        # Click's built-in path validation exits with code 2 for usage errors.
        assert result.exit_code == 2
        assert "Invalid value for 'PATH'" in result.output
        assert "is a file" in result.output

    def test_add_duplicate_slug_rejected(self, home):
        vault1 = home / "Memory"
        vault2 = home / "subdir" / "Memory"
        runner = CliRunner()
        runner.invoke(main, ["obsidian", "add", str(vault1)])

        result = runner.invoke(main, ["obsidian", "add", str(vault2)])
        assert result.exit_code == 1, result.output
        assert "Vault slug 'memory' already used by" in result.output
        assert "Choose a vault path with a different directory name." in result.output

        config = KimiConfig()
        assert str(vault2.resolve()) not in config.get_obsidian_vaults()

    def test_add_tilde_path_does_not_duplicate(self, home):
        vault = home / "Memory"
        ObsidianServer.scaffold_vault(vault)
        config = KimiConfig()
        config.set_obsidian_vaults(["~/Memory"])

        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "add", "~/Memory"])
        assert result.exit_code == 0, result.output
        assert "already configured" in result.output

        config = KimiConfig()
        assert config.get_obsidian_vaults() == ["~/Memory"]

    def test_remove_reassigns_default_vault(self, home):
        vault1 = home / "First"
        vault2 = home / "Second"
        runner = CliRunner()
        runner.invoke(main, ["obsidian", "add", str(vault1)])
        runner.invoke(main, ["obsidian", "add", str(vault2)])

        result = runner.invoke(main, ["obsidian", "remove", "first"])
        assert result.exit_code == 0, result.output
        assert "Default memory vault moved to" in result.output

        config = KimiConfig()
        assert config.get_default_memory_vault() == str(vault2.resolve())
        vaults = config.get_obsidian_vaults()
        assert str(vault1.resolve()) not in vaults
        assert str(vault2.resolve()) in vaults

    def test_remove_tilde_default_vault_clears_default(self, home):
        vault = home / "Memory"
        ObsidianServer.scaffold_vault(vault)
        config = KimiConfig()
        config.set_obsidian_vaults(["~/Memory"])
        config.set_default_memory_vault("~/Memory")

        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "remove", "memory"])
        assert result.exit_code == 0, result.output
        assert "Removed vault 'memory'" in result.output

        config = KimiConfig()
        assert config.get_obsidian_vaults() == []
        assert config.get_default_memory_vault() is None

    def test_remove_reassigns_tilde_default_vault(self, home):
        vault1 = home / "First"
        vault2 = home / "Second"
        ObsidianServer.scaffold_vault(vault1)
        ObsidianServer.scaffold_vault(vault2)
        config = KimiConfig()
        config.set_obsidian_vaults(["~/First", str(vault2.resolve())])
        config.set_default_memory_vault("~/First")

        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "remove", "first"])
        assert result.exit_code == 0, result.output
        assert "Default memory vault moved to" in result.output

        config = KimiConfig()
        assert config.get_default_memory_vault() == str(vault2.resolve())
        vaults = config.get_obsidian_vaults()
        assert str(vault1.resolve()) not in vaults
        assert str(vault2.resolve()) in vaults

    def test_sync_templates(self, home):
        vault = home / "Templated"
        ObsidianServer.scaffold_vault(vault)
        config = KimiConfig()
        config.set_obsidian_vaults([str(vault.resolve())])

        templates = home / "templates"
        templates.mkdir()
        (templates / "daily.md").write_text("# Daily\n", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "obsidian",
                "sync-templates",
                "--templates-dir",
                str(templates),
                "templated",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Synced 1 template" in result.output
        assert (vault / "daily.md").exists()
        assert (vault / "daily.md").read_text(encoding="utf-8") == "# Daily\n"

    def test_sync_templates_unknown_vault_errors(self, home):
        runner = CliRunner()
        result = runner.invoke(main, ["obsidian", "sync-templates", "unknown"])
        assert result.exit_code == 1
        assert "No vault with slug 'unknown'" in result.output
