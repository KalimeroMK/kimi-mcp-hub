# LLM Session Summaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate per-session LLM summaries from memory observations and save them as readable markdown notes in the default Obsidian vault.

**Architecture:** Add a `Summarizer` class under `memory/summarizer.py` that reads `[memory]` config, calls an OpenAI-compatible chat completions endpoint, and returns markdown. `MemoryHooks.stop()` / `session_end()` will call the summarizer and write the result to `<vault>/Sessions/<timestamp>-<session>-summary.md`. A new CLI command `kimi-mcp-hub memory config-summary` lets users set the API key, model, and base URL.

**Tech Stack:** Python 3.11+, `requests` (already a dependency), `tomli`/`tomli_w` for config, pytest for tests.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/kimi_mcp_hub/memory/summarizer.py` | New. Builds prompts and calls the LLM API. |
| `src/kimi_mcp_hub/memory/hooks.py` | Modified. Calls summarizer and writes summary + raw notes. |
| `src/kimi_mcp_hub/cli.py` | Modified. Adds `memory` group and `config-summary` command. |
| `src/kimi_mcp_hub/config.py` | Modified. Adds helpers to read/write summary config under `[memory]`. |
| `tests/test_memory_summarizer.py` | New. Unit tests for `Summarizer`. |
| `tests/test_obsidian.py` | Modified. Adds integration test for summary note creation. |
| `tests/test_cli.py` | Modified. Adds test for `memory config-summary` command. |

---

## Task 1: Config helpers for summary settings

**Files:**
- Modify: `src/kimi_mcp_hub/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_config.py`:

```python
def test_summary_config_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = KimiConfig()
    config.set_memory_summary_config(
        api_key="sk-test", model="gpt-4o-mini", base_url="https://api.example.com/v1", enabled=True
    )
    assert config.get_memory_summary_api_key() == "sk-test"
    assert config.get_memory_summary_model() == "gpt-4o-mini"
    assert config.get_memory_summary_base_url() == "https://api.example.com/v1"
    assert config.is_memory_summary_enabled() is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate && python -m pytest tests/test_config.py::test_summary_config_round_trip -v
```

Expected: FAIL with `AttributeError: 'KimiConfig' object has no attribute 'set_memory_summary_config'`

- [ ] **Step 3: Implement config helpers**

Add the following methods to `KimiConfig` in `src/kimi_mcp_hub/config.py` (after `get_default_memory_vault` / `set_default_memory_vault`):

```python
    def get_memory_summary_api_key(self) -> str:
        return self.load_toml_config().get("memory", {}).get("summary_api_key", "")

    def get_memory_summary_model(self) -> str:
        return self.load_toml_config().get("memory", {}).get("summary_model", "gpt-4o-mini")

    def get_memory_summary_base_url(self) -> str:
        return self.load_toml_config().get("memory", {}).get("summary_base_url", "https://api.openai.com/v1")

    def is_memory_summary_enabled(self) -> bool:
        memory = self.load_toml_config().get("memory", {})
        if "summary_enabled" in memory:
            return bool(memory["summary_enabled"])
        return bool(memory.get("summary_api_key", ""))

    def set_memory_summary_config(
        self,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        enabled: bool = True,
    ) -> None:
        data = self.load_toml_config()
        memory = data.setdefault("memory", {})
        memory["summary_api_key"] = api_key
        memory["summary_model"] = model
        memory["summary_base_url"] = base_url
        memory["summary_enabled"] = enabled
        self.save_toml_config(data)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
source .venv/bin/activate && python -m pytest tests/test_config.py::test_summary_config_round_trip -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kimi_mcp_hub/config.py tests/test_config.py
git commit -m "feat(config): add memory summary config helpers"
```

---

## Task 2: Summarizer implementation

**Files:**
- Create: `src/kimi_mcp_hub/memory/summarizer.py`
- Test: `tests/test_memory_summarizer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_memory_summarizer.py`:

```python
"""Tests for memory.summarizer."""

from unittest import mock

import pytest

from kimi_mcp_hub.memory.summarizer import Summarizer


class TestSummarizer:
    def test_build_prompt_includes_observations(self):
        summarizer = Summarizer(api_key="sk-test", model="gpt-4o-mini")
        observations = [
            {"type": "tool", "summary": "Used bash", "content": "ls -la"},
            {"type": "session", "summary": "Session completed", "content": "Session ended"},
        ]
        prompt = summarizer._build_prompt(observations)
        assert "Used bash" in prompt
        assert "ls -la" in prompt
        assert "Session completed" in prompt

    def test_summarize_success_returns_markdown(self):
        summarizer = Summarizer(api_key="sk-test", model="gpt-4o-mini")
        with mock.patch("kimi_mcp_hub.memory.summarizer.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "choices": [{"message": {"content": "## Summary\n\nGreat session."}}]
            }
            mock_post.return_value.status_code = 200
            result = summarizer.summarize_session([{"type": "session", "summary": "done", "content": "done"}])
        assert result == "## Summary\n\nGreat session."

    def test_summarize_missing_api_key_returns_none(self):
        summarizer = Summarizer(api_key="", model="gpt-4o-mini")
        assert summarizer.summarize_session([]) is None

    def test_summarize_api_error_returns_none(self):
        summarizer = Summarizer(api_key="sk-test", model="gpt-4o-mini")
        with mock.patch("kimi_mcp_hub.memory.summarizer.requests.post") as mock_post:
            mock_post.side_effect = Exception("network down")
            assert summarizer.summarize_session([]) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate && python -m pytest tests/test_memory_summarizer.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'kimi_mcp_hub.memory.summarizer'`

- [ ] **Step 3: Implement Summarizer**

Create `src/kimi_mcp_hub/memory/summarizer.py`:

```python
"""LLM-powered session summarization for Obsidian memory."""

from __future__ import annotations

import json
from typing import Any

import requests


PROMPT_TEMPLATE = """You are summarizing a coding session. Given the following observations,
write a concise markdown summary with these sections:

- Goal: what the user was trying to accomplish
- Key decisions: important choices made during the session
- Files and tools touched: relevant files, commands, MCP tools
- Open questions / TODOs: anything unresolved or left to do

Keep it under 300 words. Use bullet points. Do not include raw output dumps.

Observations:
{observations}
"""


class Summarizer:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_config(cls, config: Any | None = None) -> "Summarizer":
        from ..config import KimiConfig

        cfg = config or KimiConfig()
        return cls(
            api_key=cfg.get_memory_summary_api_key(),
            model=cfg.get_memory_summary_model(),
            base_url=cfg.get_memory_summary_base_url(),
        )

    def _build_prompt(self, observations: list[dict[str, Any]]) -> str:
        lines = []
        for obs in observations:
            summary = obs.get("summary") or obs.get("content", "")[:200]
            lines.append(f"- [{obs.get('type', 'unknown')}] {summary}")
        return PROMPT_TEMPLATE.format(observations="\n".join(lines) if lines else "- No observations.")

    def summarize_session(self, observations: list[dict[str, Any]]) -> str | None:
        if not self.api_key:
            return None

        prompt = self._build_prompt(observations)
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful coding session summarizer."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
source .venv/bin/activate && python -m pytest tests/test_memory_summarizer.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kimi_mcp_hub/memory/summarizer.py tests/test_memory_summarizer.py
git commit -m "feat(memory): add LLM session summarizer"
```

---

## Task 3: MemoryHooks writes summary notes

**Files:**
- Modify: `src/kimi_mcp_hub/memory/hooks.py`
- Test: `tests/test_obsidian.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_obsidian.py` in `TestMemoryHooksObsidian`:

```python
    def test_stop_writes_summary_and_raw_notes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        vault = tmp_path / "Memory"
        config = KimiConfig()
        config.set_default_memory_vault(str(vault))
        config.set_memory_summary_config(api_key="sk-test", model="gpt-4o-mini")

        db = MemoryDB()
        db.add_observation(
            session_id="sess-1",
            obs_type="tool",
            content="output",
            summary="Used bash",
            tags=["bash"],
        )

        hooks = MemoryHooks(db=db)
        with mock.patch(
            "kimi_mcp_hub.memory.hooks.Summarizer.summarize_session",
            return_value="## Summary\n\nGreat session.",
        ):
            hooks.stop({"session_id": "sess-1", "project_path": "/tmp/project"})

        summary_notes = list((vault / "Sessions").glob("*summary.md"))
        raw_notes = [p for p in (vault / "Sessions").glob("*.md") if not p.name.endswith("-summary.md")]
        assert len(summary_notes) == 1
        assert len(raw_notes) == 1
        assert "## Summary" in summary_notes[0].read_text(encoding="utf-8")
        assert "Used bash" in raw_notes[0].read_text(encoding="utf-8")
```

Add `from unittest import mock` to the imports at the top of `tests/test_obsidian.py` if not already present.

- [ ] **Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate && python -m pytest tests/test_obsidian.py::TestMemoryHooksObsidian::test_stop_writes_summary_and_raw_notes -v
```

Expected: FAIL because `_write_session_note` does not yet create `-summary.md` or `-raw.md`.

- [ ] **Step 3: Update MemoryHooks to write summary and raw notes**

Modify `src/kimi_mcp_hub/memory/hooks.py`:

1. Add import at the top:

```python
from .summarizer import Summarizer
```

2. Replace `_write_session_note` with `_write_session_notes`:

```python
    def _write_session_notes(self, payload: dict) -> None:
        """Persist raw observations and an LLM summary to the default Obsidian vault."""
        vault_path = self._default_vault_path()
        if not vault_path:
            return

        if not ObsidianServer.validate_vault(vault_path, fix=True):
            return

        session_id = payload.get("session_id", "unknown")
        project_path = payload.get("project_path", "")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")

        recent = self.db.get_recent(session_id=session_id, limit=50)

        try:
            note_dir = vault_path / "Sessions"
            note_dir.mkdir(parents=True, exist_ok=True)

            raw_path = note_dir / f"{timestamp}-{session_id[:8]}.md"
            raw_path.write_text(
                self._format_raw_note(timestamp, session_id, project_path, recent),
                encoding="utf-8",
            )

            summarizer = Summarizer.from_config()
            summary = summarizer.summarize_session(recent)
            if summary:
                summary_path = note_dir / f"{timestamp}-{session_id[:8]}-summary.md"
                summary_path.write_text(
                    self._format_summary_note(timestamp, session_id, project_path, summary),
                    encoding="utf-8",
                )
        except OSError:
            return

    def _format_raw_note(
        self,
        timestamp: str,
        session_id: str,
        project_path: str,
        observations: list[dict],
    ) -> str:
        lines = [
            f"# Session {timestamp} — Raw",
            "",
            f"- **Session ID:** `{session_id}`",
            f"- **Project:** `{project_path}`",
            "",
            "## Observations",
            "",
        ]
        for obs in observations:
            summary = obs["summary"] or obs["content"][:200]
            lines.append(f"- [{obs['type']}] {summary}")
        if not observations:
            lines.append("- No observations captured yet.")
        return "\n".join(lines) + "\n"

    def _format_summary_note(
        self,
        timestamp: str,
        session_id: str,
        project_path: str,
        summary: str,
    ) -> str:
        return (
            f"# Session Summary {timestamp}\n\n"
            f"- **Session ID:** `{session_id}`\n"
            f"- **Project:** `{project_path}`\n\n"
            f"{summary}\n"
        )
```

3. Update `stop()` and `session_end()` to call `_write_session_notes`:

```python
    def stop(self, payload: dict) -> None:
        """Called on Stop. Summarizes session."""
        session_id = payload.get("session_id", "unknown")
        self.db.add_observation(
            session_id=session_id,
            obs_type="session",
            content="Session ended",
            summary="Session completed",
            tags=["session"],
        )
        self._write_session_notes(payload)

    def session_end(self, payload: dict) -> None:
        """Called on SessionEnd. Finalizes."""
        self._write_session_notes(payload)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
source .venv/bin/activate && python -m pytest tests/test_obsidian.py::TestMemoryHooksObsidian -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kimi_mcp_hub/memory/hooks.py tests/test_obsidian.py
git commit -m "feat(memory): write LLM summary and raw notes to Obsidian vault"
```

---

## Task 4: CLI command `memory config-summary`

**Files:**
- Modify: `src/kimi_mcp_hub/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli.py`:

```python

class TestMemoryConfigSummary:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        return tmp_path

    def test_config_summary_stores_values(self, home):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "memory",
                "config-summary",
                "--api-key",
                "sk-test",
                "--model",
                "gpt-4o",
                "--base-url",
                "https://api.example.com/v1",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

        config = KimiConfig()
        assert config.get_memory_summary_api_key() == "sk-test"
        assert config.get_memory_summary_model() == "gpt-4o"
        assert config.get_memory_summary_base_url() == "https://api.example.com/v1"
        assert config.is_memory_summary_enabled() is True

    def test_config_summary_requires_api_key(self, home):
        runner = CliRunner()
        result = runner.invoke(main, ["memory", "config-summary"])
        assert result.exit_code != 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate && python -m pytest tests/test_cli.py::TestMemoryConfigSummary -v
```

Expected: FAIL because `memory` group and `config-summary` command do not exist.

- [ ] **Step 3: Implement CLI command**

Add to `src/kimi_mcp_hub/cli.py` after the `obsidian` group definitions (around line 2250):

```python
@click.group(name="memory")
def memory_group():
    """Manage persistent memory settings."""


@memory_group.command(name="config-summary")
@click.option("--api-key", required=True, help="API key for the summary LLM provider.")
@click.option("--model", default="gpt-4o-mini", show_default=True, help="Model name.")
@click.option(
    "--base-url",
    default="https://api.openai.com/v1",
    show_default=True,
    help="OpenAI-compatible base URL.",
)
@click.option("--enabled/--disabled", default=True, help="Enable or disable summaries.")
def config_summary(api_key: str, model: str, base_url: str, enabled: bool):
    """Configure the LLM used for session summaries."""
    config = KimiConfig()
    config.set_memory_summary_config(
        api_key=api_key,
        model=model,
        base_url=base_url,
        enabled=enabled,
    )
    console.print("[green]Memory summary configuration saved.[/green]")


main.add_command(memory_group)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
source .venv/bin/activate && python -m pytest tests/test_cli.py::TestMemoryConfigSummary -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kimi_mcp_hub/cli.py tests/test_cli.py
git commit -m "feat(cli): add memory config-summary command"
```

---

## Task 5: End-to-end verification

- [ ] **Step 1: Run full test suite**

```bash
source .venv/bin/activate && python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Manual smoke test**

```bash
cd /tmp && rm -rf smoke-test smoke-home && mkdir smoke-test && cd smoke-test && git init -q
HOME=/tmp/smoke-home python -m kimi_mcp_hub obsidian auto
HOME=/tmp/smoke-home python -m kimi_mcp_hub memory config-summary --api-key sk-test --model gpt-4o-mini
echo '{"session_id": "smoke-1", "project_path": "/tmp/smoke-test"}' | HOME=/tmp/smoke-home python -m kimi_mcp_hub.memory_hook stop
ls /tmp/smoke-test/smoke-test-Memory/Sessions/
```

Expected: both `-raw.md` and `-summary.md` files exist.

- [ ] **Step 3: Commit any remaining changes**

```bash
git add -A
git commit -m "test: verify LLM session summaries end-to-end" || true
```

---

## Self-Review

1. **Spec coverage:**
   - Per-session LLM summary on `Stop`/`SessionEnd` → Task 3.
   - Config under `[memory]` → Tasks 1 and 4.
   - OpenAI-compatible API call → Task 2.
   - Fallback to structured notes if LLM fails → Task 2 returns `None`, Task 3 only writes summary if returned.
   - CLI command `memory config-summary` → Task 4.
   - Tests → all tasks include test steps.

2. **Placeholder scan:** no TBD/TODO/fill-in details. All code and commands are concrete.

3. **Type consistency:** `Summarizer` constructor and `from_config` use the same parameter names. `KimiConfig` helpers match the TOML keys. `MemoryHooks` methods renamed consistently (`_write_session_note` → `_write_session_notes`).
