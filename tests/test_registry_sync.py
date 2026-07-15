"""Consistency guards: registry, plugin manifest, versions, and skill groups.

These tests exist so the catalogs and manifests cannot silently drift apart
again (e.g. a skill added on disk but missing from SKILLS, or a version
bumped in pyproject.toml but not in kimi.plugin.json).
"""

import json
from pathlib import Path

from kimi_mcp_hub import __version__
from kimi_mcp_hub.registry import (
    AUTO_INSTALL_SERVERS,
    CORE_SKILLS,
    FRONTEND_SKILLS,
    OPTIONAL_SKILL_GROUPS,
    SERVERS,
    SKILLS,
)

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "src" / "kimi_mcp_hub" / "skills"


def _skills_on_disk() -> set[str]:
    return {
        d.name
        for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    }


class TestSkillsRegistrySync:
    def test_skills_dict_matches_disk(self):
        assert set(SKILLS) == _skills_on_disk()

    def test_every_group_entry_exists(self):
        for category, keys in OPTIONAL_SKILL_GROUPS:
            for key in keys:
                assert key in SKILLS, f"{key} (group '{category}') not in SKILLS"

    def test_no_duplicate_group_entries(self):
        seen: set[str] = set()
        for _, keys in OPTIONAL_SKILL_GROUPS:
            for key in keys:
                assert key not in seen, f"{key} appears in two groups"
                seen.add(key)

    def test_every_skill_is_reachable_via_init(self):
        """Every skill must be installable from the init wizard."""
        reachable = set(CORE_SKILLS) | set(FRONTEND_SKILLS)
        for _, keys in OPTIONAL_SKILL_GROUPS:
            reachable.update(keys)
        unreachable = set(SKILLS) - reachable
        assert not unreachable, f"skills not in any init group: {sorted(unreachable)}"

    def test_core_and_frontend_skills_exist(self):
        for key in CORE_SKILLS + FRONTEND_SKILLS:
            assert key in SKILLS, f"{key} missing from SKILLS"


class TestPluginManifestSync:
    def _manifest(self) -> dict:
        return json.loads((ROOT / "kimi.plugin.json").read_text(encoding="utf-8"))

    def test_plugin_servers_are_known(self):
        manifest_servers = set(self._manifest()["mcpServers"])
        unknown = manifest_servers - set(SERVERS)
        assert not unknown, f"plugin manifest has unknown servers: {sorted(unknown)}"

    def test_plugin_servers_require_no_api_key(self):
        """The plugin only ships servers that work without interactive secrets."""
        manifest = self._manifest()["mcpServers"]
        for name, cfg in manifest.items():
            assert not cfg.get("env"), f"{name} has env secrets in plugin manifest"

    def test_auto_install_servers_are_in_manifest(self):
        manifest_servers = set(self._manifest()["mcpServers"])
        for key in AUTO_INSTALL_SERVERS:
            assert key in manifest_servers, f"{key} missing from plugin manifest"

    def test_plugin_skills_dir_has_all_skills(self):
        manifest = self._manifest()
        skills_dir = (ROOT / manifest["skills"]).resolve()
        assert skills_dir == SKILLS_DIR.resolve()
        assert _skills_on_disk() == set(SKILLS)


class TestVersionSync:
    def test_all_manifests_share_the_version(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert f'version = "{__version__}"' in pyproject

        package_json = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        assert package_json["version"] == __version__

        plugin_json = json.loads((ROOT / "kimi.plugin.json").read_text(encoding="utf-8"))
        assert plugin_json["version"] == __version__

        skill_version = (
            SKILLS_DIR / "kimi-mcp-hub-status" / ".kimi-mcp-hub-version"
        ).read_text(encoding="utf-8")
        assert skill_version.strip() == __version__

    def test_counts_match_registry(self):
        from kimi_mcp_hub import TOTAL_SERVERS, TOTAL_SKILLS

        assert TOTAL_SERVERS == len(SERVERS)
        assert TOTAL_SKILLS == len(SKILLS)
