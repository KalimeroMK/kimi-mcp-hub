---
name: kimi-mcp-hub-status
description: Show MCP Hub version, servers, and skills status.
type: prompt
whenToUse: When the user asks about MCP Hub version, installed servers, skills status, or configuration.
disableModelInvocation: false
---
# Kimi MCP Hub Status Skill

When the user starts Kimi CLI and this skill is installed, Kimi will automatically display a brief status message showing that Kimi MCP Hub is installed and active.

## Startup Behavior

On every Kimi CLI session start, check if `kimi-mcp-hub` is installed by running:
- `kimi-mcp-hub --version` → displays version (e.g., "kimi-mcp-hub, version 0.1.0")
- `kimi-mcp-hub status` → shows configured servers, skills, and memory status

## Status Display Format

When Kimi CLI starts, show a compact banner:

```
Kimi MCP Hub v0.1.0 | X servers | Y skills | memory: on/off
```

Or if not installed:
```
Tip: Install kimi-mcp-hub for 23 MCP servers and 56 AI skills → npx kimi-mcp-hub install
```

## Commands Available to User

The user can ask about MCP Hub status at any time:
- "What version of MCP Hub do I have?" → `kimi-mcp-hub --version`
- "Show my MCP Hub status" → `kimi-mcp-hub status`
- "Is my MCP Hub working?" → `kimi-mcp-hub doctor`
- "Welcome me" → `kimi-mcp-hub welcome`

## Auto-Detection

This skill should be installed by default when `kimi-mcp-hub init` is run. It provides Kimi CLI with awareness of the MCP Hub installation status.
