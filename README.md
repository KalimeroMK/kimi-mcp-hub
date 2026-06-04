# 🎯 Kimi MCP Hub

One-click MCP server and skills manager for **Kimi CLI** — like `claude-mem` but for connecting Jira, Linear, Confluence, GitHub, Slack, Datadog, Figma, Gmail, HubSpot, Grain, Chrome DevTools, plus 27 AI skills.

## What it does

- **Adds MCP servers** to `~/.kimi/mcp.json` with interactive prompts
- **Installs 27 skills** to `~/.kimi/skills/` — AI behavior patterns
- **OAuth helper** — opens browser, captures callback, stores tokens
- **Persistent memory** — SQLite-based cross-session memory (optional)
- **Import from Claude** — `kimi-mcp-hub import-claude` (API tokens only, OAuth needs re-auth)
- **Lists all tools** — run `kimi-mcp-hub list` to see everything
- **Health check** — `kimi-mcp-hub doctor` verifies node, npx, docker, uv, kimi CLI

## Install

```bash
# With uv (recommended)
uv tool install git+https://github.com/yourname/kimi-mcp-hub.git

# Or pipx
pipx install git+https://github.com/yourname/kimi-mcp-hub.git

# Or pip
pip install git+https://github.com/yourname/kimi-mcp-hub.git
```

## Quick start

```bash
# 🧙 Interactive wizard — servers + skills + memory
kimi-mcp-hub init

# Or add individually
kimi-mcp-hub add jira
kimi-mcp-hub add linear
kimi-mcp-hub add github

# Import from Claude Desktop (API tokens only, OAuth needs re-auth)
kimi-mcp-hub import-claude

# Install skills
kimi-mcp-hub install-skill superpowers
kimi-mcp-hub install-skill caveman
kimi-mcp-hub install-skill karpathy

# See all available skills
kimi-mcp-hub list-skills

# See everything configured
kimi-mcp-hub list

# Check system health
kimi-mcp-hub doctor
```

## Usage in Kimi CLI

After setup, open Kimi CLI and type:

```
/mcp
```

You will see all tools from Jira, Linear, Confluence, Slack, Datadog, Figma, Gmail, HubSpot, Grain, Chrome DevTools. Kimi automatically uses them when you ask:

- "What's in the current sprint?" → Jira
- "Create a Linear ticket for this bug" → Linear
- "Find the onboarding doc" → Confluence
- "Check my unread Slack messages" → Slack
- "Any Datadog alerts?" → Datadog
- "Get design tokens from Figma" → Figma
- "Send email to the team" → Gmail
- "Find contact in HubSpot" → HubSpot
- "Get transcript from yesterday's meeting" → Grain
- "Screenshot this page and check console errors" → Chrome DevTools

## 27 Built-in Skills

| Skill | Description | Trigger |
|-------|-------------|---------|
| **superpowers** | 14 agentic dev skills (plan, debug, test, deploy, audit...) | "plan", "debug", "architect" |
| **ecc** | Engineering Competence (perf, security, research) | "optimize", "secure", "research" |
| **karpathy** | Code discipline (simple, readable, correct) | Any code generation |
| **caveman** | Terse mode (75% token reduction) | "caveman", "terse", "brief" |
| **ui-ux-pro-max** | Design intelligence (Tailwind, accessibility) | "design", "UI", "CSS" |
| **headroom** | Compress tool outputs (save tokens) | Large outputs, "compress" |
| **context-mode** | Context window optimization | "context limit", "token budget" |
| **hindsight** | Memory that learns from mistakes | "remember", "last time" |
| **visual-explainer** | HTML diagrams and slides | "visualize", "diagram" |
| **task-master** | Task management system | "task", "todo", "backlog" |
| **gitnexus** | Code knowledge graph (git blame, blast radius) | "who wrote this", "impact" |
| **ralph** | Autonomous loop with stop-hooks | "keep going", "continue" |
| **security-audit** | Security review checklist | "security", "audit", "vulnerability" |
| **security-guidance** | 3-layer security scanning (Anthropic-style) | File edits, "security scan" |
| **research-mode** | Research-driven development | "research", "compare", "benchmark" |
| **perf-optimization** | Performance profiling and fixes | "slow", "profile", "benchmark" |
| **memory-palace** | Advanced context management | "remember", "previous session" |
| **code-reviewer** | Code review assistant | "review", "CR", "feedback" |
| **code-review-anthropic** | Multi-agent PR review (sub-agents) | "PR review", "deep review" |
| **api-designer** | REST/GraphQL API design | "API", "endpoint", "REST" |
| **docker-pro** | Docker and Kubernetes best practices | "docker", "container", "k8s" |
| **database-expert** | Database design and optimization | "database", "SQL", "schema" |
| **backend-architect** | **Backend architecture (API, DB, scale)** | "design API", "system design" |
| **python-engineer** | **Python specialist (FastAPI, Django, async)** | "Python", "FastAPI", "Django" |
| **react-coder** | **React 19 specialist (RSC, hooks)** | "React", "component", "Next.js" |
| **ts-coder** | **TypeScript specialist (strict, generics)** | "TypeScript", "TS", "generic" |
| **ui-engineer** | **UI/UX engineer (Tailwind, a11y)** | "UI", "Tailwind", "responsive" |
| **backend-typescript-architect** | TypeScript/Bun backend architecture | "design API", "backend architecture" |
| **python-backend-engineer** | Python/FastAPI backend engineer | "Python", "FastAPI", "Django" |
| **react-coder** | React 19 specialist | "React", "component", "hook" |
| **ts-coder** | TypeScript type specialist | "TypeScript", "types", "generic" |
| **ui-engineer** | UI/UX engineer (responsive, a11y, animation) | "responsive", "component", "a11y" |

## Supported MCP Servers (16)

| Server | Auth | Tools | Best for |
|--------|------|-------|----------|
| **Jira** | OAuth (Cloud) or API token | 8 tools | Tickets, sprints, worklogs |
| **Linear** | API key | 6 tools | Issues, projects, teams |
| **Confluence** | OAuth or API token | 5 tools | Docs, wiki, pages |
| **GitHub** | PAT | 6 tools | Repos, PRs, issues, code |
| **Slack** | OAuth or token | 7 tools | Channels, DMs, search |
| **Datadog** | API + App keys | 12 tools | Metrics, logs, monitors, APM |
| **Figma** | OAuth (Official) or PAT (Console) | 9 tools | Designs, tokens, components |
| **Gmail** | OAuth (npx), Chrome bridge, or Python SDK | 8 tools | Read, search, send emails |
| **HubSpot** | Private App token | 9 tools | CRM contacts, deals, companies |
| **Grain** | Browser automation | 2 tools | Meeting transcripts |
| **Chrome DevTools** | STDIO (Node 22+ required) | 10 tools | Performance, network, screenshots, console |

## OAuth with 2 clicks

For **Jira, Confluence, Slack, Figma** — official HTTP endpoints:

```bash
# Jira
kimi mcp add --transport http --auth oauth jira https://mcp.atlassian.com/v1/mcp/authv2
kimi mcp auth jira

# Slack
kimi mcp add --transport http --auth oauth slack https://mcp.slack.com/mcp
kimi mcp auth slack
```

Opens browser → click "Authorize" → done.

## Import from Claude Desktop

```bash
kimi-mcp-hub import-claude
```

- 🔑 **API token servers** → fully imported with credentials
- 🔐 **OAuth servers** → config only, run `kimi mcp auth` after import
- ❓ **Unknown** → skipped unless confirmed

## Architecture

```
┌─────────────────────────────────────────┐
│         kimi-mcp-hub CLI                │
│  ┌─────────────────────────────────┐  │
│  │  init → interactive wizard      │  │
│  │  add  → writes ~/.kimi/mcp.json │  │
│  │  auth → OAuth / API key flow    │  │
│  │  import-claude → migrate config │  │
│  │  list → pretty table of tools   │  │
│  └─────────────────────────────────┘  │
│              ↓                          │
│  ┌─────────────────────────────────┐  │
│  │  ~/.kimi/mcp.json               │  │
│  │  ~/.kimi/skills/ (27 skills)    │  │
│  │  ~/.kimi/mcp-hub/memory.db      │  │
│  └─────────────────────────────────┘  │
│              ↓                          │
│         Kimi CLI reads config           │
│              ↓                          │
│         /mcp shows tools                │
│         Skills auto-activate            │
│         Memory persists context         │
│         Sub-agents parallel review      │
└─────────────────────────────────────────┘
```

## License

MIT
