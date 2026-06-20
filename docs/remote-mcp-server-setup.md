# Remote MCP Server Setup

This guide covers official **remote MCP servers** that use OAuth 2.1 and are authorized through a browser popup inside Kimi CLI.

## Which servers use this flow

- **Linear**
- **Jira**
- **Confluence**
- **Supabase**
- **Figma**
- **Stripe**
- **GitLab**

These servers are hosted by the service provider and require OAuth authorization from within Kimi CLI.

---

## Quick steps

### 1. Add the server outside Kimi CLI

Open your normal terminal (not the Kimi CLI session) and run:

```bash
kimi-mcp-hub add <server>
```

For example:

```bash
kimi-mcp-hub add linear
```

When prompted, choose `official-oauth` (or `official`).

This writes the server entry to `~/.kimi-code/mcp.json`.

### 2. Restart Kimi CLI

The new config is only read when Kimi starts:

```bash
exit
kimi
```

### 3. Authorize from inside Kimi CLI

Once Kimi is running, run:

```text
/mcp-config login <server>
```

For example:

```text
/mcp-config login linear
```

Kimi will open a browser OAuth popup. Complete the authorization there.

### 4. Verify the server is connected

Run:

```text
/mcp
```

You should see the tools from the server listed.

---

## Common issues

### `unknown command 'mcp'`

You probably ran `kimi mcp auth <server>` outside of Kimi CLI. This command must be executed **inside** the Kimi session as `/mcp-config login <server>`.

Fix:

```bash
kimi
```

Then inside Kimi:

```text
/mcp-config login linear
```

### Server does not appear in `/mcp`

Check that the server was actually saved:

```bash
kimi-mcp-hub list
```

If it is missing, repeat step 1.

### OAuth popup does not open

Make sure Kimi CLI has permission to open your browser. If not, use the URL shown in the popup prompt or try:

```text
/mcp-config login linear
```

again after granting permissions.

---

## API-key alternative

Some servers also support an API key instead of OAuth. To use that:

```bash
kimi-mcp-hub add linear
```

Choose `api-key` and enter your token. No browser authorization is needed.

For Linear, you can create an API key at:

```text
https://linear.app/settings/api
```

---

## Summary

| Step | Where | Command |
|------|-------|---------|
| Add server | Normal terminal | `kimi-mcp-hub add linear` |
| Restart | Normal terminal | `kimi` |
| Authorize | Inside Kimi CLI | `/mcp-config login linear` |
| Verify | Inside Kimi CLI | `/mcp` |
