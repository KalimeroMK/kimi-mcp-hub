# Kimi MCP Hub

One-click MCP server and skills manager for **Kimi CLI** -- like `claude-mem` but for connecting Jira, Linear, Confluence, GitHub, Slack, Datadog, Figma, Gmail, HubSpot, Grain, Chrome DevTools, PostgreSQL, Playwright, Sentry, Context7, Supabase, plus 28 AI skills (5 core + 23 optional), persistent memory, and Claude Desktop import.

---

## Install

```bash
# Clone or download this repo
cd kimi-mcp-hub

# Install with pip (recommended)
pip install -e .

# Or with uv
uv pip install -e .

# Verify installation
kimi-mcp-hub --version
# -> 0.1.0
```

**Requirements:** Python 3.10+, Node.js (for MCP servers), `npx` or `npm`

---

## Quick Start

```bash
# Check status (shows version, servers, skills, memory)
kimi-mcp-hub status

# Display welcome banner with full info
kimi-mcp-hub welcome

# Run the interactive wizard
kimi-mcp-hub init

# Or add servers individually
kimi-mcp-hub add jira
kimi-mcp-hub add linear
kimi-mcp-hub add github
kimi-mcp-hub add perplexity

# Import from Claude Desktop (API tokens only, OAuth needs re-auth)
kimi-mcp-hub import-claude

# See everything configured
kimi-mcp-hub list

# Check system health
kimi-mcp-hub doctor
```

---

## `kimi-mcp-hub init` -- What it does

The wizard walks you through 3 steps:

### Step 1: MCP Servers (external tools)
Choose which services to connect:
- Jira, Linear, Confluence, GitHub, Slack
- Datadog, Figma, Gmail, HubSpot, Grain
- Chrome DevTools, PostgreSQL, Playwright, Sentry, Context7, Supabase, Perplexity

### Step 2: Skills (AI behavior patterns)
**Core skills** (installed by default, press Enter to accept):
| Skill | What it does |
|-------|-------------|
| **karpathy** | Clean, simple, readable code |
| **superpowers** | 14 agentic dev skills (plan, debug, test, deploy...) |
| **headroom** | Compress large tool outputs to save tokens |
| **context-mode** | Optimize context window usage |
| **cybersecurity** | Security expert (OWASP, cloud, IR, pentest) |

**Optional skills** (press `y` to install):
- caveman, ecc, ui-ux-pro-max, visual-explainer, task-master
- gitnexus, ralph, security-audit, security-guidance, research-mode
- perf-optimization, memory-palace, code-reviewer, code-review-anthropic
- api-designer, docker-pro, database-expert, backend-architect
- python-engineer, react-coder, ts-coder, ui-engineer, laravel-engineer

### Step 3: Persistent Memory (optional)
Enable SQLite-based memory that persists across sessions.

---

## First-Run Welcome Message

After installation, the first time you run any `kimi-mcp-hub` command, you'll see:

```
Kimi MCP Hub v0.1.0 e uspeshno instaliran!

17 MCP serveri dostapni
28 AI skills za podobro kodiranje
1 Persistent memory sistem

Za da zapochnesh:
  kimi-mcp-hub init    -- interaktiven wizard
  kimi-mcp-hub welcome -- detalen pregled
  kimi-mcp-hub status  -- status proverka
  kimi-mcp-hub doctor  -- zdravje na sistemot
```

---

## Usage in Kimi CLI

After setup, start Kimi CLI:

```bash
kimi
```

Inside Kimi CLI:

```
/mcp              # List all available MCP tools
/skills           # (if supported by Kimi CLI) list installed skills
```

Kimi automatically uses skills when you say trigger words:
- `"Plan this feature"` -> activates **superpowers** `/plan`
- `"Check for SQL injection"` -> activates **cybersecurity**
- `"Make it shorter"` -> activates **caveman** (if installed)
- `"Review this PR"` -> activates **code-review-anthropic**

---

## Uninstall / Remove

If you don't like it, remove everything cleanly:

```bash
# 1. Uninstall the Python package
pip uninstall kimi-mcp-hub
# or: uv pip uninstall kimi-mcp-hub

# 2. Remove MCP servers
kimi-mcp-hub remove jira
kimi-mcp-hub remove linear
# ... or edit ~/.kimi/mcp.json manually

# 3. Remove skills
rm -rf ~/.kimi/skills/*

# 4. Remove memory database
rm -rf ~/.kimi/mcp-hub/

# 5. Remove config and tokens
rm -rf ~/.config/kimi-mcp-hub/
```

**To completely reset:**
```bash
rm -rf ~/.kimi/mcp.json
rm -rf ~/.kimi/skills/
rm -rf ~/.kimi/mcp-hub/
rm -rf ~/.config/kimi-mcp-hub/
pip uninstall kimi-mcp-hub
```

---

## All Commands

| Command | Description |
|---------|-------------|
| `kimi-mcp-hub` (no args) | Show welcome banner and status |
| `kimi-mcp-hub --version` | Show version |
| `kimi-mcp-hub init` | Full interactive wizard |
| `kimi-mcp-hub status` | Show version, servers, skills, memory status |
| `kimi-mcp-hub welcome` | Display welcome banner with installation info |
| `kimi-mcp-hub add <server>` | Add one MCP server |
| `kimi-mcp-hub remove <server>` | Remove one MCP server |
| `kimi-mcp-hub auth <server>` | OAuth / API key flow |
| `kimi-mcp-hub import-claude` | Import from Claude Desktop |
| `kimi-mcp-hub list` | Show all servers + skills + memory |
| `kimi-mcp-hub list-skills` | Show all 28 available skills |
| `kimi-mcp-hub install-skill <name>` | Install one skill |
| `kimi-mcp-hub test <server>` | Test if server is responding |
| `kimi-mcp-hub doctor` | Health check (node, npx, docker, uv, kimi) |

---

## 17 MCP Servers

| Server | Auth | Tools | Best for |
|--------|------|-------|----------|
| **Jira** | OAuth (Cloud) or API token | 8 | Tickets, sprints, worklogs |
| **Linear** | API key | 6 | Issues, projects, teams |
| **Confluence** | OAuth or API token | 5 | Docs, wiki, pages |
| **GitHub** | PAT | 6 | Repos, PRs, issues, code |
| **Slack** | OAuth or token | 7 | Channels, DMs, search |
| **Datadog** | API + App keys | 12 | Metrics, logs, monitors, APM |
| **Figma** | OAuth (Official) or PAT (Console) | 9 | Designs, tokens, components |
| **Gmail** | OAuth (npx), Chrome bridge, or Python SDK | 8 | Read, search, send emails |
| **HubSpot** | Private App token | 9 | CRM contacts, deals, companies |
| **Grain** | Browser automation | 2 | Meeting transcripts |
| **Chrome DevTools** | STDIO (Node 22+ required) | 10 | Performance, network, screenshots, console |
| **PostgreSQL** | DSN string | 6 | SQL queries, schema, slow query analysis |
| **Playwright** | STDIO (Node.js) | 8 | Browser automation, E2E testing, screenshots |
| **Sentry** | Auth token + org | 6 | Error tracking, issue triage, stack traces |
| **Context7** | STDIO (npx) | 4 | Live library docs, version-aware API lookup |
| **Supabase** | URL + API key | 6 | Database, auth, storage, realtime, edge functions |
| **Perplexity** | **API key (free tier)** | **3** | **Real-time web search with AI summaries + citations** |

---

## 28 Skills (5 Core + 23 Optional)

### Core Skills (installed by default)
| Skill | Description | Trigger |
|-------|-------------|---------|
| **karpathy** | Code discipline (simple, readable, correct) | Any code generation |
| **superpowers** | 14 agentic dev skills (plan, debug, test, deploy...) | "plan", "debug", "architect" |
| **headroom** | Compress tool outputs (save tokens) | Large outputs, "compress" |
| **context-mode** | Context window optimization | "context limit", "token budget" |
| **cybersecurity** | Security expert (OWASP, cloud, IR, pentest) | "security", "hack", "OWASP" |

### Optional Skills
| Skill | Description | Trigger |
|-------|-------------|---------|
| **caveman** | Terse mode (75% token reduction) | "caveman", "terse", "brief" |
| **ecc** | Engineering Competence (perf, security, research) | "optimize", "secure", "research" |
| **ui-ux-pro-max** | Design intelligence (Tailwind, accessibility) | "design", "UI", "CSS" |
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
| **backend-architect** | Backend architecture (API, DB, scale) | "design API", "system design" |
| **python-engineer** | Python specialist (FastAPI, Django, async) | "Python", "FastAPI", "Django" |
| **react-coder** | React 19 specialist (RSC, hooks) | "React", "component", "Next.js" |
| **ts-coder** | TypeScript specialist (strict, generics) | "TypeScript", "TS", "generic" |
| **ui-engineer** | UI/UX engineer (Tailwind, a11y, responsive) | "UI", "Tailwind", "responsive" |
| **laravel-engineer** | **Laravel specialist (Eloquent, Blade, Livewire, Queues)** | "Laravel", "Eloquent", "PHP" |

---

## Architecture

```
+-----------------------------------------+
|         kimi-mcp-hub CLI                |
|  +---------------------------------+  |
|  |  (no args) -> welcome banner    |  |
|  |  init -> interactive wizard     |  |
|  |  add  -> writes ~/.kimi/mcp.json |  |
|  |  auth -> OAuth / API key flow   |  |
|  |  import-claude -> migrate config |  |
|  |  list -> pretty table of tools  |  |
|  |  status -> version + health     |  |
|  |  welcome -> full info display   |  |
|  +---------------------------------+  |
|              |                          |
|  +---------------------------------+  |
|  |  ~/.kimi/mcp.json               |  |
|  |  ~/.kimi/skills/ (28 skills)    |  |
|  |  ~/.kimi/mcp-hub/memory.db      |  |
|  +---------------------------------+  |
|              |                          |
|  First-run welcome message (auto)     |
|              |                          |
|         Kimi CLI reads config           |
|              |                          |
|         /mcp shows tools                |
|         Skills auto-activate            |
|         Memory persists context         |
+-----------------------------------------+
```

---

## Requirements

- **Python** 3.10+
- **Node.js** + **npm/npx** (for MCP servers)
- **Kimi CLI** installed and configured
- Optional: **Docker** (for Datadog, HubSpot Docker mode)
- Optional: **uv** (for Grain, faster Python package management)

---

## License

MIT
