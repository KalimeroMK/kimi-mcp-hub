# Kimi MCP Hub

One-click MCP server and skills manager for **Kimi CLI** -- like `claude-mem` but for connecting 23 MCP servers (Jira, GitHub, Slack, Datadog, Perplexity, Stripe, GitLab, DBHub, etc.), 56 AI skills (6 core + 50 optional), persistent memory, and Claude Desktop import.

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
- [MCP Servers](#23-mcp-servers)
- [Skills](#56-skills)
- [Architecture](#architecture)

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
Kimi MCP Hub v0.1.0 installed successfully!

23 MCP servers available
56 AI skills for better coding
1  Persistent memory system

To get started:
  kimi-mcp-hub init    -- interactive wizard
  kimi-mcp-hub welcome -- detailed overview
  kimi-mcp-hub status  -- status check
  kimi-mcp-hub doctor  -- system health check
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
rm -f ~/.kimi-code/mcp.json
rm -rf ~/.kimi-code/skills/
rm -rf ~/.kimi-mcp-hub/
rm -rf ~/.config/kimi-mcp-hub/

# Or use the CLI
kimi-mcp-hub remove jira      # remove one server
kimi-mcp-hub remove github    # remove another
```

**Complete reinstall:**

```bash
pip uninstall kimi-mcp-hub
rm -rf ~/.kimi-code/mcp.json ~/.kimi-code/skills/ ~/.kimi-mcp-hub/
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
kimi-mcp-hub add slack
kimi-mcp-hub add supabase
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
kimi-mcp-hub auth figma
kimi-mcp-hub auth gitlab
kimi-mcp-hub auth stripe

# For official remote MCP servers, Kimi CLI handles the popup:
# /mcp-config login jira
# /mcp-config login linear
# /mcp-config login confluence
# /mcp-config login supabase

# See everything configured
kimi-mcp-hub list
kimi-mcp-hub status
kimi-mcp-hub welcome
kimi-mcp-hub notify

# Fix broken configs after package updates
kimi-mcp-hub repair

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
|--------|------|:-----:|
| **GitHub** | Device Flow (or PAT fallback) | Yes |
| **Jira** | Official MCP OAuth or API token | Yes* |
| **Confluence** | Official MCP OAuth or API token | Yes* |
| **Slack** | Bot/User token (`slack-mcp-server`) | No (manual token) |
| **Figma** | Official OAuth 2.1, PAT or custom OAuth 2.0 | Yes* |
| **Gmail** | Google OAuth 2.0 or npx | Yes |
| **Linear** | Official OAuth 2.1 or API key | Yes* |
| **Stripe** | Official OAuth 2.1 or restricted API key | Yes* |
| **GitLab** | Official OAuth 2.1 or PAT | Yes* |
| **Supabase** | Official remote OAuth or access-token stdio | Yes* |
| **Datadog** | API + App keys | No (manual) |

\* Official remote OAuth 2.1 is initiated by Kimi CLI (`kimi mcp auth <server>` or `/mcp-config login <server>`) after you add the official remote MCP server.

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
| `kimi-mcp-hub notify` | Short startup notification for shell wrappers |
| `kimi-mcp-hub add <server>` | Add an MCP server |
| `kimi-mcp-hub remove <server>` | Remove an MCP server |
| `kimi-mcp-hub auth <server>` | OAuth with auto-browser |
| `kimi-mcp-hub repair` | Fix broken/outdated server configs |
| `kimi-mcp-hub import-claude` | Import from Claude Desktop |
| `kimi-mcp-hub list` | All servers + skills + memory |
| `kimi-mcp-hub list-skills` | All 56 available skills |
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
| **Slack** | Bot/User token (`slack-mcp-server`) | 7 | Channels, DMs, search |
| **Datadog** | Official remote MCP (API + App keys) | 12 | Metrics, logs, monitors, APM |
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
| **Supabase** | Official remote OAuth or access-token stdio | 6 | Database, auth, storage, realtime, edge functions |
| **Perplexity** | **API key (free tier)** | **3** | **Real-time web search with AI summaries + citations** |

---

## 56 Skills

### Core Skills (installed by default)

| Skill | Description |
|-------|-------------|
| **karpathy** | Clean, simple, readable code discipline |
| **superpowers** | 14 agentic workflows (plan, debug, test, deploy...) |
| **headroom** | Compress large tool outputs to save tokens |
| **context-mode** | Context window optimization and token budget |
| **cybersecurity** | Cybersecurity expert (OWASP, cloud, IR, pentest) |
| **caveman** | Ultra-compressed caveman communication mode |

### Frontend Skills (installed as a stack by default)

| Skill | Description |
|-------|-------------|
| **react-coder** | React 19 specialist (RSC, hooks) |
| **ts-coder** | TypeScript specialist (strict, generics) |
| **ui-engineer** | UI component implementation (Tailwind, a11y) |
| **ui-ux-pro-max** | UI/UX design intelligence and design systems |
| **vercel-react-best-practices** | React/Next.js performance optimization |
| **web-design-guidelines** | Audit UI code against Vercel guidelines |
| **agent-browser** | Browser automation for web tasks and testing |
| **design-system** | Design tokens, component specs, and systematic design systems |

### Code Quality & Review Skills

| Skill | Description |
|-------|-------------|
| **code-reviewer** | Quick single-agent code review |
| **code-review** | Multi-agent code review (explore/coder/plan) |
| **surgical-refactoring** | Surgical code refactoring without behavior change |
| **tdd** | Test-driven development with red-green-refactor |
| **perf-optimization** | Performance profiling and optimization |
| **security-audit** | Security review checklist |
| **security-guidance** | 3-layer security scanning guidance |

### Architecture & Design Skills

| Skill | Description |
|-------|-------------|
| **api-designer** | REST/GraphQL API design |
| **backend-architect** | Backend architecture and system design |
| **backend-typescript-architect** | TypeScript/Bun backend architecture |
| **codebase-design** | Design deep modules and testable interfaces |
| **domain-modeling** | Build domain models and ubiquitous language |
| **database-expert** | Database design and optimization |
| **api-design** | REST API design patterns |

### DevOps & Deployment Skills

| Skill | Description |
|-------|-------------|
| **docker-pro** | Docker and Kubernetes best practices |
| **gitnexus** | Code knowledge graph and blast radius |
| **resolving-merge-conflicts** | Resolve git merge/rebase conflicts |
| **deployment-patterns** | CI/CD and deployment best practices |

### Language / Framework Skills

| Skill | Description |
|-------|-------------|
| **python-engineer** | Python specialist (FastAPI, Django, async) |
| **laravel-engineer** | Laravel specialist (Eloquent, Blade, Livewire) |
| **php-pro** | Senior PHP development (strict typing, Laravel/Symfony, PSR) |
| **wp-plugin-development** | WordPress plugin development with hooks and Settings API |
| **react-coder** | React 19 specialist (RSC, hooks) |
| **ts-coder** | TypeScript specialist (strict, generics) |
| **ui-engineer** | UI component implementation (Tailwind, a11y) |
| **ui-ux-pro-max** | UI/UX design intelligence and design systems |

### Data & Migrations Skills

| Skill | Description |
|-------|-------------|
| **database-migrations** | Safe database migration patterns |

### Testing & Browser Skills

| Skill | Description |
|-------|-------------|
| **playwright-best-practices** | Playwright testing best practices |
| **chrome-devtools-skill** | Chrome DevTools MCP debugging and automation |

### Research & Automation Skills

| Skill | Description |
|-------|-------------|
| **search-first** | Research-before-coding workflow |
| **regex-vs-llm-structured-text** | Regex vs LLM parsing decision framework |

### Productivity & Meta Skills

| Skill | Description |
|-------|-------------|
| **caveman-review** | Ultra-compressed code review comments |
| **caveman-commit** | Ultra-compressed Conventional Commits messages |
| **memory-palace** | Advanced memory and context retrieval |
| **hindsight** | Memory that learns from past decisions |
| **task-master** | Task management system |
| **ralph** | Autonomous loop with stop-hooks |
| **grill-me** | Stress-test a plan or design |
| **visual-explainer** | HTML diagrams and slides |
| **research-mode** | Research-driven development |
| **ecc** | Engineering competence (perf, security, research) |
| **skill-creator** | Create and optimize agent skills |
| **agent-automation-recommender** | Recommend agent automations for codebases |
| **find-skills** | Discover and install agent skills |

### Integration Skills

| Skill | Description |
|-------|-------------|
| **stripe-best-practices** | Stripe integration best practices |

---

## Architecture

```
+-----------------------------------------+
|         kimi-mcp-hub CLI                |
|  +---------------------------------+    |
|  |  (no args) -> welcome banner    |    |
|  |  install -> PyPI/GitHub update  |    |
|  |  init -> interactive wizard     |    |
|  |  add  -> writes ~/.kimi-code/...|    |
|  |  auth -> OAuth + auto browser   |    |
|  |  repair -> fix broken configs   |    |
|  |  import-claude -> migrate config|    |
|  |  list -> pretty table of tools  |    |
|  |  status -> version + health     |    |
|  |  welcome -> full info display   |    |
|  |  notify -> startup notification |    |
|  +---------------------------------+    |
|              |                          |
|  +---------------------------------+    |
|  |  ~/.kimi-code/mcp.json          |    |
|  |  ~/.kimi-code/skills/ (56 skills)|    |
|  |  ~/.config/kimi-mcp-hub/        |    |
|  |    tokens.json + memory.db      |    |
|  +---------------------------------+    |
|              |                          |
|  Optional shell wrapper prints notify   |
|  on every `kimi` start                  |
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
- API keys and PATs are written to `~/.kimi-code/mcp.json`. Protect that file accordingly.

---

## License

MIT
