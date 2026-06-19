# Kimi MCP Hub

One-click MCP server and skills manager for **Kimi CLI** -- like `claude-mem` but for connecting 23 MCP servers (Jira, GitHub, Slack, Datadog, Perplexity, Stripe, GitLab, DBHub, etc.), 34 AI skills (6 core + 28 optional), persistent memory, and Claude Desktop import.

---

## Table of Contents

- [Install](#install)
  - [One-liner (no clone)](#one-liner-no-clone)
  - [From GitHub (pip)](#from-github-pip)
  - [Clone + Install](#clone--install)
  - [Verify](#verify)
- [Uninstall](#uninstall)
- [Quick Start](#quick-start)
- [OAuth Auto-Browser](#oauth-auto-browser)
- [All Commands](#all-commands)
- [MCP Servers](#17-mcp-servers)
- [Skills](#34-skills)
- [Architecture](#architecture)
- [Ideas from Claude-Mem](#-ideas-from-claude-mem)

---

## Install

### One-liner with npx (recommended)

```bash
# macOS / Linux / Windows
npx kimi-mcp-hub install
```

This creates an isolated Python virtual environment in `~/.kimi-mcp-hub/venv`, installs the package, and runs the interactive setup wizard.

### One-liner (curl / PowerShell)

```bash
# macOS / Linux (curl + pip from GitHub)
curl -fsSL https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.sh | bash

# Windows (PowerShell)
iwr -useb https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.ps1 | iex
```

### From GitHub (pip)

```bash
# Direct from GitHub -- no clone needed
pip install --user git+https://github.com/KalimeroMK/kimi-mcp-hub.git

# Upgrade
pip install --user --upgrade git+https://github.com/KalimeroMK/kimi-mcp-hub.git
```

### From PyPI (when published)

```bash
pip install --user kimi-mcp-hub
```

### Clone + Install (development)

```bash
git clone https://github.com/KalimeroMK/kimi-mcp-hub.git
cd kimi-mcp-hub
pip install -e .
```

### Requirements

- **Python** 3.10+
- **Node.js** + **npm/npx** (for MCP servers that need it)
- **Kimi CLI** installed
- Optional: **Docker** (for some servers)

### Verify

```bash
kimi-mcp-hub --version
# -> kimi-mcp-hub, version 0.1.0
```

On first run you'll see:

```
Kimi MCP Hub v0.1.0 e uspeshno instaliran!

23 MCP serveri dostapni
34 AI skills za podobro kodiranje
1  Persistent memory sistem

Za da zapochnesh:
  kimi-mcp-hub init    -- interaktiven wizard
  kimi-mcp-hub welcome -- detalen pregled
  kimi-mcp-hub status  -- status proverka
  kimi-mcp-hub doctor  -- zdravje na sistemot
```

### Run the wizard

```bash
kimi-mcp-hub init
```

This walks you through:
1. **MCP Servers** -- pick which services to connect
2. **Skills** -- install AI behavior patterns
3. **Memory** -- enable persistent cross-session memory

---

## Uninstall

```bash
# Full reset
pip uninstall kimi-mcp-hub
rm -f ~/.kimi/mcp.json
rm -rf ~/.kimi/skills/
rm -rf ~/.kimi/mcp-hub/
rm -rf ~/.config/kimi-mcp-hub/

# Or use the CLI
kimi-mcp-hub remove jira      # remove one server
kimi-mcp-hub remove github    # remove another
```

**Complete reinstall:**

```bash
pip uninstall kimi-mcp-hub
rm -rf ~/.kimi/mcp.json ~/.kimi/skills/ ~/.kimi/mcp-hub/
pip install --user git+https://github.com/KalimeroMK/kimi-mcp-hub.git
kimi-mcp-hub init
```

---

## Quick Start

```bash
# Show welcome banner + status
kimi-mcp-hub

# Check system health
kimi-mcp-hub doctor

# Full interactive setup
kimi-mcp-hub init

# Add servers individually
kimi-mcp-hub add jira
kimi-mcp-hub add github
kimi-mcp-hub add perplexity
kimi-mcp-hub add gitlab
kimi-mcp-hub add stripe
kimi-mcp-hub add figma-context
kimi-mcp-hub add desktop-commander
kimi-mcp-hub add dbhub
kimi-mcp-hub add mobile

# Or use npx without installing Node package globally:
# npx kimi-mcp-hub status

# Auth with auto-browser (OAuth) -- like Claude Code CLI
kimi-mcp-hub auth github
kimi-mcp-hub auth slack
kimi-mcp-hub auth figma
kimi-mcp-hub auth gitlab
kimi-mcp-hub auth stripe

# See everything configured
kimi-mcp-hub list
kimi-mcp-hub status
kimi-mcp-hub welcome

# Import from Claude Desktop
kimi-mcp-hub import-claude

# Manage skills
kimi-mcp-hub list-skills
kimi-mcp-hub install-skill docker-pro

# Test a server
kimi-mcp-hub test github
```

---

## OAuth Auto-Browser

Like Claude Code CLI, `kimi-mcp-hub` automatically opens your browser for OAuth:

```bash
$ kimi-mcp-hub auth github

> Github Authorization
  Auto-browser mode (like Claude Code CLI)

  Method: Device Flow -- auto browser + code

Your verification code: ABCD-1234
Opening browser...

If browser didn't open:
1. Go to: https://github.com/login/device
2. Enter code: ABCD-1234
3. Click 'Authorize'

Waiting for you to authorize in browser...

GitHub authorized successfully!
```

| Server | Method | Auto-browser |
|--------|--------|:------------:|
| **GitHub** | Device Flow (or PAT fallback) | Yes |
| **Jira** | API Token or Official MCP OAuth | Yes |
| **Confluence** | API Token or Official MCP OAuth | Yes |
| **Slack** | Bot Token or OAuth 2.0 | Yes |
| **Figma** | Official OAuth 2.1, PAT or custom OAuth 2.0 | Yes* |
| **Gmail** | Google OAuth 2.0 or npx | Yes |
| **Linear** | Official OAuth 2.1 or API key | Yes* |
| **Stripe** | Official OAuth 2.1 or restricted API key | Yes* |
| **GitLab** | Official OAuth 2.1 or PAT | Yes* |
| **Datadog** | API + App keys | No (manual) |

\* Linear/Figma/Stripe/GitLab OAuth 2.1 се иницира од Kimi CLI (`kimi mcp auth <server>`) откако ќе го додадете официјалниот remote MCP сервер.

---

## All Commands

| Command | Description |
|---------|-------------|
| `kimi-mcp-hub` | Show welcome banner and status |
| `kimi-mcp-hub --version` | Show version |
| `kimi-mcp-hub install` | Install/update from PyPI/GitHub |
| `kimi-mcp-hub init` | Full interactive wizard |
| `kimi-mcp-hub status` | Version, servers, skills, memory |
| `kimi-mcp-hub welcome` | Detailed welcome banner |
| `kimi-mcp-hub add <server>` | Add an MCP server |
| `kimi-mcp-hub remove <server>` | Remove an MCP server |
| `kimi-mcp-hub auth <server>` | OAuth with auto-browser |
| `kimi-mcp-hub import-claude` | Import from Claude Desktop |
| `kimi-mcp-hub list` | All servers + skills + memory |
| `kimi-mcp-hub list-skills` | All 34 available skills |
| `kimi-mcp-hub install-skill <name>` | Install a skill |
| `kimi-mcp-hub test <server>` | Test if server responds |
| `kimi-mcp-hub doctor` | System health check |

---

## 23 MCP Servers

| Server | Auth | Tools | Best for |
|--------|------|:-----:|----------|
| **Jira** | OAuth (Cloud) or API token | 8 | Tickets, sprints, worklogs |
| **Linear** | Official OAuth 2.1 or API key | 6 | Issues, projects, teams |
| **Confluence** | OAuth or API token | 5 | Docs, wiki, pages |
| **GitHub** | Device Flow / PAT | 6 | Repos, PRs, issues, code |
| **Slack** | OAuth or token | 7 | Channels, DMs, search |
| **Datadog** | API + App keys | 12 | Metrics, logs, monitors, APM |
| **Figma** | Official OAuth 2.1, PAT or custom OAuth | 9 | Designs, tokens, components |
| **Figma Context** | Figma API access token | 3 | Design-to-code implementation |
| **GitLab** | Official OAuth 2.1 or PAT | 8 | Repos, MRs, issues, CI/CD pipelines |
| **Gmail** | OAuth (npx), Chrome bridge, or Python SDK | 8 | Read, search, send emails |
| **HubSpot** | Private App token | 9 | CRM contacts, deals, companies |
| **Stripe** | Official OAuth 2.1 or restricted API key | 8 | Payments, customers, subscriptions, invoices |
| **Desktop Commander** | STDIO (npx/Docker) | 8 | Terminal commands, file ops, process management |
| **DBHub** | DSN string (read-only optional) | 2 | Multi-database gateway (PG, MySQL, SQLite, etc.) |
| **Mobile MCP** | STDIO (npx) | 9 | iOS/Android automation on simulators and real devices |
| **Grain** | Browser automation | 2 | Meeting transcripts |
| **Chrome DevTools** | STDIO (Node 22+ required) | 10 | Performance, network, screenshots, console |
| **PostgreSQL** | DSN string | 6 | SQL queries, schema, slow query analysis |
| **Playwright** | STDIO (Node.js) | 8 | Browser automation, E2E testing, screenshots |
| **Sentry** | Auth token + org | 6 | Error tracking, issue triage, stack traces |
| **Context7** | STDIO (npx) | 4 | Live library docs, version-aware API lookup |
| **Supabase** | URL + API key | 6 | Database, auth, storage, realtime, edge functions |
| **Perplexity** | **API key (free tier)** | **3** | **Real-time web search with AI summaries + citations** |

---

## 34 Skills

### Core Skills (installed by default)

| Skill | Description | Trigger |
|-------|-------------|---------|
| **karpathy** | Clean, simple, readable code | Any code generation |
| **superpowers** | 14 agentic dev skills (plan, debug, test, deploy...) | "plan", "debug", "architect" |
| **headroom** | Compress tool outputs (save tokens) | Large outputs, "compress" |
| **context-mode** | Context window optimization | "context limit", "token budget" |
| **cybersecurity** | Security expert (OWASP, cloud, IR, pentest) | "security", "hack", "OWASP" |
| **kimi-mcp-hub-status** | Shows MCP Hub version/status in Kimi CLI | Session start |

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
| **laravel-engineer** | Laravel specialist (Eloquent, Blade, Livewire, Queues) | "Laravel", "Eloquent", "PHP" |
| **find-skills** | Discover and install agent skills from the open ecosystem | "find skill", "install skill" |

---

## Ideas from Claude-Mem

Features we adopted from the 81k-star `claude-mem` project:

| Feature | Claude-Mem | Kimi MCP Hub |
|---------|-----------|-------------|
| **One-line install** | `npx claude-mem install` | `curl .../install.sh \| bash` |
| **Auto-detect CLI** | `--ide gemini-cli`, `--ide opencode` | Auto-detect `kimi` CLI |
| **Persistent memory** | AI-compressed observations | SQLite + FTS5 |
| **Web viewer UI** | `http://localhost:37777` | Coming soon |
| **Skills / memory search** | `mem-search` skill | Built-in `memory_palace` skill |
| **Privacy tags** | `<private>` content exclusion | Planned |
| **Plugin hooks** | `.claude/`, `.codex/` hooks | `~/.kimi/skills/` directory |
| **Import from other tools** | - | Claude Desktop import |

---

## Architecture

```
+-----------------------------------------+
|         kimi-mcp-hub CLI                |
|  +---------------------------------+    |
|  |  (no args) -> welcome banner    |    |
|  |  install -> PyPI/GitHub update  |    |
|  |  init -> interactive wizard     |    |
|  |  add  -> writes ~/.kimi/mcp.json|    |
|  |  auth -> OAuth + auto browser   |    |
|  |  import-claude -> migrate config|    |
|  |  list -> pretty table of tools  |    |
|  |  status -> version + health     |    |
|  |  welcome -> full info display   |    |
|  +---------------------------------+    |
|              |                          |
|  +---------------------------------+    |
|  |  ~/.kimi/mcp.json               |    |
|  |  ~/.kimi-code/skills/ (34 skills) |    |
|  |  ~/.kimi/mcp-hub/memory.db      |    |
|  +---------------------------------+    |
|              |                          |
|  First-run welcome message (auto)       |
|              |                          |
|         Kimi CLI reads config           |
|              |                          |
|         /mcp shows tools                |
|         Skills auto-activate            |
|         Memory persists context         |
+-----------------------------------------+
```

---

## Security Notes

- OAuth tokens are stored as plain JSON in `~/.config/kimi-mcp-hub/tokens.json`. This keeps the tool dependency-free, but means anyone with access to your user account can read them.
- By default GitHub authentication uses a public OAuth app (`kimi-mcp-hub`). You can supply your own GitHub/Atlassian OAuth Client ID when running `kimi-mcp-hub auth <server>`.
- API keys and PATs are written to `~/.kimi/mcp.json`. Protect that file accordingly.

---

## License

MIT
