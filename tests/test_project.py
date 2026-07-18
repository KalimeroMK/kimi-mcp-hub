"""Tests for project-level MCP configuration (src/kimi_mcp_hub/project.py)."""

import json

import pytest
from click.testing import CliRunner

from kimi_mcp_hub.cli import main
from kimi_mcp_hub.project import (
    ProjectConfig,
    find_project_root,
    merge_mcp_configs,
    resolve_placeholders,
)


@pytest.fixture
def project(tmp_path):
    """A ProjectConfig rooted at a temporary directory."""
    return ProjectConfig(tmp_path)


class TestFindProjectRoot:
    def test_finds_kimi_dir(self, tmp_path):
        (tmp_path / ".kimi").mkdir()
        assert find_project_root(tmp_path) == tmp_path

    def test_falls_back_to_git_root(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert find_project_root(tmp_path) == tmp_path

    def test_walks_up_from_subdirectory(self, tmp_path):
        (tmp_path / ".git").mkdir()
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        assert find_project_root(sub) == tmp_path

    def test_prefers_nearest_kimi_over_git(self, tmp_path):
        (tmp_path / ".git").mkdir()
        sub = tmp_path / "sub"
        (sub / ".kimi").mkdir(parents=True)
        assert find_project_root(sub) == sub

    def test_returns_none_outside_project(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert find_project_root() is None

    def test_defaults_to_cwd(self, tmp_path, monkeypatch):
        (tmp_path / ".kimi").mkdir()
        monkeypatch.chdir(tmp_path)
        assert find_project_root() == tmp_path


class TestResolvePlaceholders:
    def test_replaces_known_vars(self):
        assert resolve_placeholders("token=${API_KEY}", {"API_KEY": "secret"}) == (
            "token=secret"
        )

    def test_leaves_unknown_vars_untouched(self):
        assert resolve_placeholders("${MISSING}", {}) == "${MISSING}"

    def test_recurses_dicts_and_lists(self):
        obj = {
            "env": {"KEY": "${KEY}"},
            "args": ["-k", "${KEY}"],
            "port": 8080,
        }
        resolved = resolve_placeholders(obj, {"KEY": "v1"})
        assert resolved == {
            "env": {"KEY": "v1"},
            "args": ["-k", "v1"],
            "port": 8080,
        }

    def test_resolves_multiple_vars_in_one_string(self):
        out = resolve_placeholders(
            "https://${HOST}:${PORT}/api", {"HOST": "example.com", "PORT": "443"}
        )
        assert out == "https://example.com:443/api"


class TestMergeMcpConfigs:
    def test_overlay_wins_on_name_conflict(self):
        base = {"mcpServers": {"a": {"url": "old"}, "b": {"url": "keep"}}}
        overlay = {"mcpServers": {"a": {"url": "new"}}}
        merged = merge_mcp_configs(base, overlay)
        assert merged["mcpServers"]["a"] == {"url": "new"}
        assert merged["mcpServers"]["b"] == {"url": "keep"}

    def test_handles_missing_sections(self):
        assert merge_mcp_configs({}, {}) == {"mcpServers": {}}
        merged = merge_mcp_configs({"mcpServers": {"x": {}}}, {})
        assert merged["mcpServers"] == {"x": {}}


class TestProjectConfig:
    def test_exists_false_then_true_after_save(self, project):
        assert not project.exists()
        project.save_mcp({"mcpServers": {}})
        assert project.exists()

    def test_save_and_load_roundtrip(self, project):
        data = {"mcpServers": {"linear": {"url": "https://mcp.linear.app/mcp"}}}
        project.save_mcp(data)
        assert project.load_mcp() == data

    def test_load_mcp_returns_empty_on_corrupt_json(self, project):
        project.ensure_dir()
        project.mcp_json.write_text("not json")
        assert project.load_mcp() == {"mcpServers": {}}

    def test_add_server_extracts_env_to_env_file(self, project):
        cfg = {
            "command": "npx",
            "args": ["server"],
            "env": {"API_KEY": "supersecret", "PLAIN": "${PLAIN}"},
        }
        result = project.add_server("svc", cfg)

        # Secret extracted and replaced with a placeholder
        assert result["env"]["API_KEY"] == "${API_KEY}"
        # Already-a-placeholder value is left alone and not written to env file
        assert result["env"]["PLAIN"] == "${PLAIN}"

        on_disk = project.load_mcp()["mcpServers"]["svc"]
        assert on_disk["env"]["API_KEY"] == "${API_KEY}"
        assert "supersecret" not in project.mcp_json.read_text()

        env = project.env_file.read_text()
        assert "API_KEY=supersecret" in env
        assert "PLAIN=" not in env

    def test_add_server_without_env_writes_no_env_file(self, project):
        project.add_server("svc", {"url": "https://example.com"})
        assert not project.env_file.exists()

    def test_remove_server(self, project):
        project.add_server("svc", {"url": "https://example.com"})
        project.remove_server("svc")
        assert project.load_mcp()["mcpServers"] == {}

    def test_env_file_updates_merge_and_sort(self, project):
        project.add_server("a", {"env": {"ZETA": "1", "ALPHA": "1"}})
        project.add_server("b", {"env": {"ALPHA": "2"}})
        lines = [
            ln
            for ln in project.env_file.read_text().splitlines()
            if ln and not ln.startswith("#")
        ]
        assert lines == ["ALPHA=2", "ZETA=1"]

    def test_load_env_merges_shell_and_file(self, project, monkeypatch):
        monkeypatch.setenv("FROM_SHELL", "shell")
        project.add_server("svc", {"env": {"FROM_FILE": "file"}})

        env = project.load_env()
        assert env["FROM_SHELL"] == "shell"
        assert env["FROM_FILE"] == "file"

    def test_load_env_file_overrides_shell(self, project, monkeypatch):
        monkeypatch.setenv("KEY", "shell")
        project.add_server("svc", {"env": {"KEY": "file"}})
        assert project.load_env()["KEY"] == "file"

    def test_load_env_skips_comments_and_bad_lines(self, project):
        project.ensure_dir()
        project.env_file.write_text("# comment\n\nNO_EQUALS\nGOOD=1\n")
        env = project.load_env()
        assert env["GOOD"] == "1"
        assert "NO_EQUALS" not in env

    def test_env_value_with_equals_sign_kept_intact(self, project):
        project.add_server("svc", {"env": {"DSN": "postgres://u:p@h/db?x=1"}})
        assert project.load_env()["DSN"] == "postgres://u:p@h/db?x=1"


class TestSyncCommand:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        """Redirect HOME and hub config to a temporary directory."""
        monkeypatch.setenv("HOME", str(tmp_path))
        return tmp_path

    def test_sync_merges_project_into_global(self, home, tmp_path, monkeypatch):
        project_dir = tmp_path / "proj"
        (project_dir / ".git").mkdir(parents=True)
        pc = ProjectConfig(project_dir)
        pc.add_server(
            "linear",
            {
                "url": "https://mcp.linear.app/mcp",
                "env": {"LINEAR_API_KEY": "lin_key_123"},
            },
        )
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        assert "Synced 1 project MCP server" in result.output

        global_cfg = json.loads((home / ".kimi-code" / "mcp.json").read_text())
        linear = global_cfg["mcpServers"]["linear"]
        assert linear["env"]["LINEAR_API_KEY"] == "lin_key_123"
        # Placeholder resolved, secret not left as ${...}
        assert "${LINEAR_API_KEY}" not in json.dumps(global_cfg)

    def test_sync_project_overrides_global_server(self, home, tmp_path, monkeypatch):
        from kimi_mcp_hub.config import KimiConfig

        KimiConfig().add_server("svc", {"url": "https://global.example.com"})

        project_dir = tmp_path / "proj"
        (project_dir / ".kimi").mkdir(parents=True)
        ProjectConfig(project_dir).add_server(
            "svc", {"url": "https://project.example.com"}
        )
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["sync"])
        assert result.exit_code == 0, result.output

        servers = KimiConfig().list_servers()
        assert servers["svc"]["url"] == "https://project.example.com"

    def test_sync_fails_outside_project(self, home, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(main, ["sync"])
        assert result.exit_code == 1
        assert "No project root found" in result.output

    def test_sync_fails_without_project_mcp_json(self, home, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(main, ["sync"])
        assert result.exit_code == 1
        assert "No " in result.output and "mcp.json" in result.output

    def test_sync_accepts_explicit_project_path(self, home, tmp_path):
        project_dir = tmp_path / "proj"
        (project_dir / ".kimi").mkdir(parents=True)
        ProjectConfig(project_dir).add_server("svc", {"url": "https://example.com"})

        result = CliRunner().invoke(main, ["sync", str(project_dir)])
        assert result.exit_code == 0, result.output

        from kimi_mcp_hub.config import KimiConfig

        assert "svc" in KimiConfig().list_servers()


class TestAddRemoveProjectCommands:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        return tmp_path

    def test_add_with_project_flag_writes_project_config(
        self, home, tmp_path, monkeypatch
    ):
        project_dir = tmp_path / "proj"
        (project_dir / ".git").mkdir(parents=True)
        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(
            "kimi_mcp_hub.cli.helpers.maybe_install_npx_deps",
            lambda cfg, console, **kw: True,
        )

        result = CliRunner().invoke(main, ["add", "--project", "playwright"])
        assert result.exit_code == 0, result.output

        assert ProjectConfig(project_dir).load_mcp()["mcpServers"]["playwright"]
        from kimi_mcp_hub.config import KimiConfig

        assert "playwright" not in KimiConfig().list_servers()

    def test_remove_with_project_flag(self, home, tmp_path, monkeypatch):
        project_dir = tmp_path / "proj"
        (project_dir / ".git").mkdir(parents=True)
        pc = ProjectConfig(project_dir)
        pc.add_server("svc", {"url": "https://example.com"})
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["remove", "--project", "svc"])
        assert result.exit_code == 0, result.output
        assert pc.load_mcp()["mcpServers"] == {}

    def test_legacy_migration_does_not_steal_home_project_config(
        self, home, tmp_path, monkeypatch
    ):
        """KimiConfig must not treat ~/​.kimi/mcp.json as legacy global config
        when it is actually a project config (HOME is the project root)."""
        (tmp_path / ".git").mkdir()  # HOME is itself a project root
        monkeypatch.chdir(tmp_path)
        ProjectConfig(tmp_path).add_server("svc", {"url": "https://example.com"})

        from kimi_mcp_hub.config import KimiConfig

        KimiConfig()  # triggers _migrate_legacy_config
        assert "svc" not in KimiConfig().list_servers()


class TestAutoProjectMode:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        return tmp_path

    @pytest.fixture
    def project_dir(self, tmp_path):
        d = tmp_path / "proj"
        (d / ".kimi").mkdir(parents=True)
        return d

    def _mock_npx_install(self, monkeypatch):
        monkeypatch.setattr(
            "kimi_mcp_hub.cli.helpers.maybe_install_npx_deps",
            lambda cfg, console, **kw: True,
        )

    def test_add_auto_adopts_project_when_kimi_dir_exists(
        self, home, project_dir, monkeypatch
    ):
        self._mock_npx_install(monkeypatch)
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["add", "playwright"])
        assert result.exit_code == 0, result.output
        assert "Project config detected" in result.output

        assert "playwright" in ProjectConfig(project_dir).load_mcp()["mcpServers"]
        from kimi_mcp_hub.config import KimiConfig

        assert "playwright" not in KimiConfig().list_servers()

    def test_add_stays_global_in_plain_git_repo(self, home, tmp_path, monkeypatch):
        self._mock_npx_install(monkeypatch)
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        monkeypatch.chdir(repo)

        result = CliRunner().invoke(main, ["add", "playwright"])
        assert result.exit_code == 0, result.output

        from kimi_mcp_hub.config import KimiConfig

        assert "playwright" in KimiConfig().list_servers()
        assert not (repo / ".kimi").exists()

    def test_add_global_flag_forces_global_in_project(
        self, home, project_dir, monkeypatch
    ):
        self._mock_npx_install(monkeypatch)
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["add", "--global", "playwright"])
        assert result.exit_code == 0, result.output

        from kimi_mcp_hub.config import KimiConfig

        assert "playwright" in KimiConfig().list_servers()
        assert "playwright" not in ProjectConfig(project_dir).load_mcp()["mcpServers"]

    def test_project_and_global_flags_conflict(self, home, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        result = CliRunner().invoke(main, ["add", "--project", "--global", "playwright"])
        assert result.exit_code == 1
        assert "mutually exclusive" in result.output

    def test_remove_auto_adopts_project(self, home, project_dir, monkeypatch):
        pc = ProjectConfig(project_dir)
        pc.add_server("svc", {"url": "https://example.com"})
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["remove", "svc"])
        assert result.exit_code == 0, result.output
        assert pc.load_mcp()["mcpServers"] == {}

    def test_remove_global_flag_forces_global(self, home, project_dir, monkeypatch):
        from kimi_mcp_hub.config import KimiConfig

        KimiConfig().add_server("svc", {"url": "https://example.com"})
        pc = ProjectConfig(project_dir)
        pc.add_server("svc", {"url": "https://project.example.com"})
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["remove", "--global", "svc"])
        assert result.exit_code == 0, result.output
        assert "svc" not in KimiConfig().list_servers()
        # Project entry untouched
        assert "svc" in pc.load_mcp()["mcpServers"]


class TestProjectSkills:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        return tmp_path

    def test_load_skills_empty_and_corrupt(self, project):
        assert project.load_skills() == []
        project.ensure_dir()
        project.skills_json.write_text("not json")
        assert project.load_skills() == []

    def test_add_skill_dedupes_and_sorts(self, project):
        project.add_skill("php-pro")
        project.add_skill("karpathy")
        project.add_skill("php-pro")
        assert project.load_skills() == ["karpathy", "php-pro"]

    def test_install_skill_with_project_flag(self, home, tmp_path, monkeypatch):
        project_dir = tmp_path / "proj"
        (project_dir / ".git").mkdir(parents=True)
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(
            main, ["install-skill", "--project", "karpathy"]
        )
        assert result.exit_code == 0, result.output

        pc = ProjectConfig(project_dir)
        assert "karpathy" in pc.load_skills()
        from kimi_mcp_hub.config import KimiConfig

        assert (KimiConfig().skills_dir / "karpathy" / "SKILL.md").exists()

    def test_sync_installs_project_skills(self, home, tmp_path, monkeypatch):
        project_dir = tmp_path / "proj"
        (project_dir / ".git").mkdir(parents=True)
        pc = ProjectConfig(project_dir)
        pc.add_server("svc", {"url": "https://example.com"})
        pc.add_skill("karpathy")
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        assert "skill" in result.output

        from kimi_mcp_hub.config import KimiConfig

        assert (KimiConfig().skills_dir / "karpathy" / "SKILL.md").exists()

    def test_sync_works_with_skills_json_only(self, home, tmp_path, monkeypatch):
        """sync must not fail when the project has skills but no mcp.json."""
        project_dir = tmp_path / "proj"
        (project_dir / ".git").mkdir(parents=True)
        pc = ProjectConfig(project_dir)
        pc.add_skill("karpathy")
        assert not pc.exists()
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["sync"])
        assert result.exit_code == 0, result.output

        from kimi_mcp_hub.config import KimiConfig

        assert (KimiConfig().skills_dir / "karpathy" / "SKILL.md").exists()

    def test_sync_ignores_unknown_skills(self, home, tmp_path, monkeypatch):
        project_dir = tmp_path / "proj"
        (project_dir / ".git").mkdir(parents=True)
        pc = ProjectConfig(project_dir)
        pc.add_skill("not-a-real-skill")
        monkeypatch.chdir(project_dir)

        result = CliRunner().invoke(main, ["sync"])
        assert result.exit_code == 0, result.output

        from kimi_mcp_hub.config import KimiConfig

        assert not (KimiConfig().skills_dir / "not-a-real-skill").exists()
