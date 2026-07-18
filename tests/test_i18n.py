"""Tests for localization (src/kimi_mcp_hub/i18n.py)."""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from kimi_mcp_hub import i18n


@pytest.fixture
def reload_i18n(monkeypatch):
    """Reload the i18n module with given env vars, restoring it afterwards."""
    original_env = os.environ.get("KIMI_MCP_HUB_LANG")

    def _reload(lang: str | None):
        if lang is None:
            monkeypatch.delenv("KIMI_MCP_HUB_LANG", raising=False)
        else:
            monkeypatch.setenv("KIMI_MCP_HUB_LANG", lang)
        return importlib.reload(i18n)

    yield _reload

    # Restore module state for other tests
    if original_env is None:
        monkeypatch.delenv("KIMI_MCP_HUB_LANG", raising=False)
    else:
        monkeypatch.setenv("KIMI_MCP_HUB_LANG", original_env)
    importlib.reload(i18n)


class TestI18nModule:
    def test_fallback_returns_english_msgid(self, reload_i18n):
        module = reload_i18n("en")
        assert module._("Memory") == "Memory"

    def test_no_env_returns_english(self, reload_i18n):
        module = reload_i18n(None)
        assert module._("Memory") == "Memory"

    def test_macedonian_translation(self, reload_i18n):
        module = reload_i18n("mk")
        assert module._("Memory") == "Меморија"
        assert module._("Skills") == "Вештини"

    def test_untranslated_string_falls_back(self, reload_i18n):
        module = reload_i18n("mk")
        assert module._("a string with no translation") == (
            "a string with no translation"
        )

    def test_unknown_language_falls_back(self, reload_i18n):
        module = reload_i18n("xx-nonexistent")
        assert module._("Memory") == "Memory"

    def test_format_placeholders_survive_translation(self, reload_i18n):
        module = reload_i18n("mk")
        out = module._("[green]{n} installed[/green]").format(n=5)
        assert out == "[green]5 инсталирани[/green]"

    def test_mo_file_is_packaged(self):
        mo = (
            Path(i18n.LOCALEDIR) / "mk" / "LC_MESSAGES" / "kimi-mcp-hub.mo"
        )
        assert mo.exists()

    def test_po_and_mo_cover_same_strings(self):
        """Every msgid in the .po must have a non-empty msgstr."""
        po = Path(i18n.LOCALEDIR) / "mk" / "LC_MESSAGES" / "kimi-mcp-hub.po"
        entries = po.read_text(encoding="utf-8").split("\n\n")
        untranslated = []
        for entry in entries:
            lines = entry.splitlines()
            if not lines or not lines[0].startswith("msgid"):
                continue
            if lines[0] == 'msgid ""':  # header
                continue
            msgstr_idx = next(
                (i for i, ln in enumerate(lines) if ln.startswith("msgstr")), None
            )
            if msgstr_idx is None:
                untranslated.append(lines[0])
                continue
            has_value = lines[msgstr_idx] != 'msgstr ""' or (
                msgstr_idx + 1 < len(lines)
                and lines[msgstr_idx + 1].startswith('"')
            )
            if not has_value:
                untranslated.append(lines[0])
        assert not untranslated, f"Untranslated msgids: {untranslated}"


class TestCliLocalized:
    def test_status_command_renders_macedonian(self, tmp_path):
        env = {
            **os.environ,
            "KIMI_MCP_HUB_LANG": "mk",
            "HOME": str(tmp_path),
        }
        result = subprocess.run(
            [sys.executable, "-m", "kimi_mcp_hub", "status"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "Верзија" in result.stdout
        assert "Меморија" in result.stdout

    def test_status_command_defaults_to_english(self, tmp_path):
        env = {
            k: v for k, v in os.environ.items() if k != "KIMI_MCP_HUB_LANG"
        }
        env["HOME"] = str(tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "kimi_mcp_hub", "status"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "Version" in result.stdout
        assert "Memory" in result.stdout
