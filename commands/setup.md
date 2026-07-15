---
description: Guided in-session setup — what the plugin provides and what to do next
---

Give the user a concise overview of their Kimi MCP Hub setup and the next steps.
Do not change any files in this command.

1. Explain what the plugin already provides (active after `/reload` or a new session):
   - **Zero-config servers** (work immediately): chrome-devtools, context7, playwright,
     desktop-commander, mobile.
   - **Official remote OAuth servers** (need one login each): linear, jira, confluence,
     supabase, figma, stripe, gitlab, github — authorize with `/mcp-config login <name>`.
   - **57 AI skills**, loaded from the plugin automatically.

2. Check the current state:
   - Run `cat ~/.kimi-code/mcp.json` (via Bash) to see user-level servers that may
     duplicate plugin-provided ones. If duplicates exist (e.g. `linear` in mcp.json AND
     from the plugin), advise removing the old entry with `kimi-mcp-hub remove <name>`
     in a terminal, or by editing `~/.kimi-code/mcp.json`, to avoid duplicate tools.

3. Offer the remaining options:
   - Servers needing credentials (perplexity, slack, datadog, sentry, hubspot,
     postgres, dbhub, gmail, figma-context, grain, obsidian): addable in-session with
     `/kimi-mcp-hub:add <name>`.
   - Persistent memory + Obsidian vaults and lifecycle hooks: require the Python
     package — point the user to `kimi-mcp-hub init` in a terminal (see the repo README).

4. End with a short summary table: server | status (ready / needs login / needs
   credentials) | next action.
