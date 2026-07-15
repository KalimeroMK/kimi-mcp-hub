---
description: Add an MCP server without leaving Kimi (OAuth, API-key, or token)
---

Add the MCP server `$ARGUMENTS` to this Kimi installation. Follow these steps exactly:

1. If `$ARGUMENTS` is empty, ask the user which server they want and list the options from step 2.

2. Locate the server definition: read the file
   `~/.kimi-code/plugins/managed/kimi-mcp-hub/src/kimi_mcp_hub/servers/<name>.py`
   (replace `<name>` with the server key, e.g. `perplexity.py`). If the file does not
   exist, list the available keys by reading the `SERVERS` registry in
   `~/.kimi-code/plugins/managed/kimi-mcp-hub/src/kimi_mcp_hub/cli.py` and stop.

3. Choose the branch by server type:

   - **Official remote OAuth servers** (linear, jira, confluence, supabase, figma,
     stripe, gitlab, github): these are already declared by the plugin. Nothing to
     write. Tell the user to run `/mcp-config login <name>` and then check `/mcp`.
     Stop here.

   - **Zero-config stdio servers** (chrome-devtools, context7, playwright,
     desktop-commander, mobile): already declared by the plugin. Tell the user to run
     `/reload` if tools are not visible yet. Stop here.

   - **API-key / token / DSN servers** (everything else: perplexity, slack, datadog,
     sentry, hubspot, postgres, dbhub, gmail, figma-context, grain, obsidian):
     continue with step 4.

4. Ask the user for the required credentials. Derive what is needed from the server
   module's `get_stdio_config` / `get_*_config` signatures (e.g. API key, bot token,
   DSN). Warn the user once: credentials typed in chat are stored in session history;
   if they prefer, they can instead run `kimi-mcp-hub add <name>` in a terminal.

5. Write the config into `~/.kimi-code/mcp.json`:
   - Read the current file (create `{"mcpServers": {}}` if missing).
   - Build the server entry exactly as the server module's config classmethod returns
     it for the given credentials, and merge it under `mcpServers.<name>`.
   - Preserve all existing entries. Keep file permissions restrictive.

6. If the entry uses `command: "npx"`, offer to pre-install the package with
   `npm install -g <package>` to avoid a first-run timeout.

7. Tell the user to run `/reload` (or start a new session), then verify with `/mcp`.
