# LLM Session Summaries for Obsidian Memory

## Overview

Currently, `kimi-mcp-hub` writes raw session observations to the default Obsidian vault as markdown notes. These notes are useful for machine retrieval but hard to read. This feature adds per-session LLM-generated summaries that capture the goal, key decisions, files/tools touched, and open questions/TODOs in a concise, human-readable format.

## Goals

- Replace (or supplement) raw observation dumps with readable session summaries.
- Keep the implementation isolated from Kimi's own LLM provider OAuth flow.
- Gracefully degrade to structured notes when no LLM is configured or the API fails.
- Not break the Kimi CLI session if summary generation fails.

## Non-Goals

- Real-time summarization during a turn (summaries happen on `Stop`/`SessionEnd`).
- Summarization of the full conversation transcript (only observations captured by memory hooks are summarized).
- Support for non-OpenAI-compatible providers in the first version.

## Architecture

```
┌─────────────────┐     Stop/SessionEnd      ┌──────────────────┐
│  Kimi CLI hook  │ ───────────────────────► │   MemoryHooks    │
└─────────────────┘                          └────────┬─────────┘
                                                      │
                                                      ▼
                                            ┌──────────────────┐
                                            │   Summarizer     │
                                            │  (memory/        │
                                            │  summarizer.py)  │
                                            └────────┬─────────┘
                                                     │
                           OpenAI-compatible API call│
                                                     ▼
                                            ┌──────────────────┐
                                            │  LLM provider    │
                                            └──────────────────┘
```

### Components

1. **`memory/summarizer.py`**
   - `Summarizer` class reads `[memory]` config from `~/.kimi-code/config.toml`.
   - Builds a prompt from session observations.
   - Calls the configured LLM endpoint using `requests`.
   - Returns markdown summary or `None` on failure.

2. **`memory/hooks.py`**
   - `MemoryHooks.stop()` and `session_end()` call `Summarizer`.
   - If a summary is returned, write it to `<vault>/Sessions/<timestamp>-<session>-summary.md`.
   - Always keep raw observations in `<vault>/Sessions/<timestamp>-<session>-raw.md` for reference.
   - If summarization is disabled or fails, fall back to a structured note (no `-summary` suffix).

3. **`cli.py`**
   - New command group `memory` with subcommand `config-summary`:
     ```bash
     kimi-mcp-hub memory config-summary --api-key sk-... --model gpt-4o-mini --base-url https://api.openai.com/v1
     ```
   - Stores values under `[memory]` in `config.toml`.
   - Validates that at least `summary_api_key` and `summary_model` are provided.

## Configuration

Stored in `~/.kimi-code/config.toml`:

```toml
[memory]
default_vault = "/Users/zoran/PhpstormProjects/crmtTracker/crmtTracker-Memory"
summary_enabled = true
summary_api_key = "sk-..."
summary_model = "gpt-4o-mini"
summary_base_url = "https://api.openai.com/v1"
```

- `summary_enabled`: boolean, defaults to `true` if `summary_api_key` is set.
- `summary_api_key`: API key for the provider.
- `summary_model`: Model name, e.g. `gpt-4o-mini`.
- `summary_base_url`: OpenAI-compatible endpoint. Defaults to `https://api.openai.com/v1`.

## Prompt

```
You are summarizing a coding session. Given the following observations,
write a concise markdown summary with these sections:

- Goal: what the user was trying to accomplish
- Key decisions: important choices made during the session
- Files and tools touched: relevant files, commands, MCP tools
- Open questions / TODOs: anything unresolved or left to do

Keep it under 300 words. Use bullet points. Do not include raw output dumps.

Observations:
{observations}
```

## Output Format

Example summary note:

```markdown
# Session Summary — 2026-06-30 10:15

## Goal
Debug why the local Obsidian vault was created but nothing was written to it.

## Key decisions
- Root cause: no hook was configured to write memory notes to the vault.
- Implemented `memory_hook.py` CLI entry point for Kimi hooks.
- `obsidian auto` now calls `enable_memory()` to install hooks.

## Files and tools touched
- `src/kimi_mcp_hub/memory/hooks.py`
- `src/kimi_mcp_hub/memory_hook.py`
- `src/kimi_mcp_hub/cli.py`
- `tests/test_obsidian.py`
- `tests/test_cli.py`

## Open questions / TODOs
- None.
```

## Error Handling

- Missing or invalid config: skip LLM, write structured note.
- API timeout or non-2xx response: log to stderr, write structured note.
- Malformed JSON response: write structured note.
- Vault path invalid: already handled by existing `_write_session_note` fallback.

## Testing

1. Unit test `Summarizer.build_prompt()` with sample observations.
2. Mock `requests.post` to test successful summary generation.
3. Mock `requests.post` raising `RequestException` to test fallback.
4. CLI test for `kimi-mcp-hub memory config-summary` updating `config.toml`.
5. Integration test that `MemoryHooks.stop()` writes both `-summary.md` and `-raw.md` when LLM succeeds.

## Future Work

- Allow per-project summary provider configuration.
- Add `--no-raw` flag to skip raw observation notes.
- Support local models via Ollama without an API key.
- Summarize multiple sessions into a daily note.
