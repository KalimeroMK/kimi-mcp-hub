# Remote MCP Server Setup

This guide covers official **remote MCP servers** that use OAuth 2.1 and are
authorized through a browser popup inside Kimi CLI.

## Which servers use this flow

- **Linear**
- **Jira**
- **Confluence**
- **Supabase**
- **Figma**
- **Stripe**
- **GitLab**
- **GitHub**

These servers are hosted by the service provider and require OAuth authorization
from within Kimi CLI.

---

## Quick steps (Kimi plugin — recommended)

Everything happens inside the Kimi session:

### 1. Install the plugin

```text
/plugins install https://github.com/KalimeroMK/kimi-mcp-hub
/reload
```

All eight OAuth servers above are declared by the plugin, plus five zero-config
stdio servers and 57 skills.

### 2. Authorize each server you want

```text
/mcp-config login linear
```

Kimi opens a browser OAuth popup. Complete the authorization there. Repeat per
server (`/mcp-config login jira`, `/mcp-config login github`, ...).

### 3. Verify

```text
/mcp
```

You should see the server's tools listed (namespaced as
`mcp__plugin-kimi-mcp-hub_<server>__*`).

---

## Classic flow (terminal CLI)

If you installed the Python package instead of the plugin, add servers from a
normal terminal:

```bash
kimi-mcp-hub add linear   # choose official-oauth
```

This writes the server entry to `~/.kimi-code/mcp.json`. Then **restart Kimi
CLI** and authorize with `/mcp-config login linear` as above.

> Note: servers added this way are not namespaced; don't keep both the plugin
> and the manual entry for the same server, or tools appear twice. Remove the
> manual one with `kimi-mcp-hub remove <server>`.

---

## Common issues

### `unknown command 'mcp'`

You probably ran `kimi mcp auth <server>` outside of Kimi CLI. Authorization
must be executed **inside** the Kimi session as `/mcp-config login <server>`.

### Server does not appear in `/mcp`

- Plugin install: make sure you ran `/reload` (or started a new session) after
  installing. Check `/plugins info kimi-mcp-hub` — the server should be listed
  and enabled (`/plugins mcp enable kimi-mcp-hub <server>` if disabled).
- Classic install: check `kimi-mcp-hub list` and repeat the add step if missing.

### OAuth popup does not open

Make sure Kimi CLI has permission to open your browser. If not, use the URL
shown in the popup prompt, or run `/mcp-config login <server>` again after
granting permissions.

---

## API-key alternative

Some servers also support an API key instead of OAuth:

- **In-session:** `/kimi-mcp-hub:add linear` — the agent asks for the key and
  writes the config (credentials typed in chat land in session history).
- **Terminal:** `kimi-mcp-hub add linear`, choose `api-key`. No browser
  authorization needed; restart Kimi CLI afterwards.

For Linear, create an API key at `https://linear.app/settings/api`.

---

## Summary

| Step | Where | Command |
|------|-------|---------|
| Install plugin | Inside Kimi CLI | `/plugins install https://github.com/KalimeroMK/kimi-mcp-hub` |
| Activate | Inside Kimi CLI | `/reload` |
| Authorize | Inside Kimi CLI | `/mcp-config login linear` |
| Verify | Inside Kimi CLI | `/mcp` |
