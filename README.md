# Kimi MCP Hub

One-click MCP server and skills manager for **Kimi CLI** -- like `claude-mem` but for connecting 24 MCP servers (Jira, GitHub, Slack, Obsidian, Datadog, Perplexity, Stripe, GitLab, DBHub, etc.), 57 AI skills (7 core + 50 optional), persistent memory, and Claude Desktop import.

---

## Table of Contents

- [Install](#install)
  - [One-liner with npx (recommended)](#one-liner-with-npx-recommended)
  - [One-liner (curl / PowerShell)](#one-liner-curl-powershell)
  - [From GitHub (pip) inside a venv](#from-github-pip-inside-a-venv)
  - [Clone + Install (development)](#clone-install-development)
  - [Requirements](#requirements)
  - [Verify](#verify)
  - [Run the wizard](#run-the-wizard)
- [Uninstall](#uninstall)
- [Quick Start](#quick-start)
- [Update](#update)
- [Managing MCP Servers and Skills](#managing-mcp-servers-and-skills)
- [Repository Packing](#repository-packing)
- [Obsidian Local Memory](#obsidian-local-memory)
- [Advanced Memory Layer](#advanced-memory-layer)
- [Install Claude/Codex Plugins](#install-claudecodex-plugins)
- [Project-Level MCP Configuration](#project-level-mcp-configuration)
- [Remote MCP Server Setup](docs/remote-mcp-server-setup.md)
- [OAuth Auto-Browser](#oauth-auto-browser)
- [CLAUDE.md Compatibility](#claudemd-compatibility)
- [All Commands](#all-commands)
- [Testing](#testing)
- [MCP Servers](#24-mcp-servers)
- [Skills](#57-skills)
- [Architecture](#architecture)

---

## Install

### One-liner with npx (recommended)

```bash
npx kimi-mcp-hub install
```

This creates an isolated Python virtual environment at `~/.kimi-mcp-hub/.venv`, installs the package, and runs the interactive setup.

### One-liner (curl / PowerShell)

```bash
# macOS / Linux (curl + pip from GitHub)
curl -fsSL https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.sh | bash

# macOS / Linux with auto CLAUDE.md support
curl -fsSL https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.sh | bash -s -- -y

# macOS / Linux with Obsidian local memory
curl -fsSL https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.sh | bash -s -- --with-obsidian

# Windows (PowerShell)
iwr -useb https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.ps1 | iex

# Windows with auto CLAUDE.md support
iwr -useb https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.ps1 | & ([scriptblock]::create($_)) -Yes

# Windows with Obsidian local memory
iwr -useb https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.ps1 | & ([scriptblock]::create($_)) -Yes -WithObsidian
```

### From GitHub (pip) inside a venv

```bash
# Direct from GitHub -- no clone needed
python3 -m venv ~/.kimi-mcp-hub/.venv
~/.kimi-mcp-hub/.venv/bin/pip install --upgrade git+https://github.com/KalimeroMK/kimi-mcp-hub.git
ln -s ~/.kimi-mcp-hub/.venv/bin/kimi-mcp-hub ~/.local/bin/kimi-mcp-hub
```

### Clone + Install (development)

```bash
git clone https://github.com/KalimeroMK/kimi-mcp-hub.git
cd kimi-mcp-hub
python3 -m venv .venv
source .venv/bin/activate
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
# -> kimi-mcp-hub, version 0.2.0
```

On first run you'll see:

```
Kimi MCP Hub v0.2.0 installed successfully!

24 MCP servers available
57 AI skills for better coding
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
1. **MCP Servers** -- Chrome DevTools, Context7, and Playwright are auto-installed if `npx` is available; pick additional services manually
2. **Skills** -- install AI behavior patterns
3. **Memory** -- enable persistent cross-session memory


---

## Uninstall

```bash
# Full reset
rm -f ~/.kimi-code/mcp.json
rm -rf ~/.kimi-code/skills/
rm -rf ~/.kimi-mcp-hub/
rm -rf ~/.config/kimi-mcp-hub/
rm -f ~/.local/bin/kimi-mcp-hub
rm -f ~/.local/bin/kmcp

# Or use the CLI
kimi-mcp-hub remove jira      # remove one server
kimi-mcp-hub remove github    # remove another
```

**Complete reinstall:**

```bash
rm -rf ~/.kimi-code/mcp.json ~/.kimi-code/skills/ ~/.kimi-mcp-hub/
bash -c "$(curl -fsSL https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.sh)"
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

# Non-interactive setup (auto-installs core + frontend skills, memory, and claude-compat)
kimi-mcp-hub init --yes

# Auto-load CLAUDE.md and CLAUDE.local.md at every session start
kimi-mcp-hub claude-compat
kimi-mcp-hub claude-compat --yes

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

# Update to the latest version
kimi-mcp-hub update

# Add and authorize OAuth servers -- like Claude Code CLI
kimi-mcp-hub add github   # choose oauth-device to configure and authorize
kimi-mcp-hub add figma

# GitLab and Stripe are official remote MCP servers; authorize via Kimi CLI:
# kimi mcp auth gitlab
# kimi mcp auth stripe

# For other official remote MCP servers, Kimi CLI handles the popup:
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

# Per-project MCP configuration
kimi-mcp-hub add --project linear   # save to ./.kimi/mcp.json
kimi-mcp-hub sync                   # merge project config into global config

# Import from Claude Desktop
kimi-mcp-hub import-claude

# Manage skills
kimi-mcp-hub list-skills
kimi-mcp-hub install-skill docker-pro

# Test a server
kimi-mcp-hub test github

# Manage Obsidian vaults for local memory
kimi-mcp-hub obsidian status
kimi-mcp-hub obsidian add ~/Documents/MyVault
kimi-mcp-hub obsidian auto
kimi-mcp-hub obsidian list
kimi-mcp-hub obsidian remove myvault
kimi-mcp-hub obsidian sync-templates myvault
kimi-mcp-hub obsidian sync-templates --templates-dir ./templates myvault
```

---

## Update

Update `kimi-mcp-hub` to the latest version in the isolated venv:

```bash
kimi-mcp-hub update
```

This upgrades the package from GitHub and refreshes the `~/.local/bin` symlinks. Development installs (git checkouts) are detected and skipped.

---

## Managing MCP Servers and Skills

### Skills

Skills are toggled **inside Kimi CLI**:

```text
/skill:caveman
/skill:headroom
/skill:code-review
```

- Core skills (`karpathy`, `superpowers`, `caveman`, `headroom`, `context-mode`, `cybersecurity`, `kimi-mcp-hub-status`) activate automatically on every Kimi start.
- Install more skills from the terminal:
  ```bash
  kimi-mcp-hub install-skill docker-pro
  ```

### MCP Servers

MCP servers are enabled **outside Kimi CLI**, in your regular terminal:

```bash
# Stdio / API-key servers
kimi-mcp-hub add github   # choose PAT or oauth-device
kimi-mcp-hub add slack

# Official remote OAuth servers can also be connected inside Kimi:
# /mcp-config login linear
# /mcp-config login jira
# /mcp-config login supabase
```

`linear` also supports an API-key stdio mode via `kimi-mcp-hub add linear` → choose `api-key`.

When you add an `npx`-based server for the first time, `kimi-mcp-hub` checks if the package is already installed and prompts to install it globally. This prevents the 30-second timeout that can happen when Kimi CLI tries to launch a not-yet-cached npx package.

After adding a server, **restart Kimi CLI** (`exit` → `kimi`) so it picks up the new config.

For a detailed walkthrough of official remote OAuth servers (Linear, Jira, Confluence, Supabase, Figma, Stripe, GitLab), see [Remote MCP Server Setup](docs/remote-mcp-server-setup.md).

---

## Repository Packing

Pack a repository into a single AI-friendly markdown file for context windows.

```bash
# Pack the current directory
kimi-mcp-hub pack

# Pack a specific repository
kimi-mcp-hub pack /path/to/repo

# Exclude patterns
kimi-mcp-hub pack -e '*.test.js' -e 'dist/'

# Increase size budget and write to a file
kimi-mcp-hub pack --max-size 1048576 -o repo.md
```

- `.gitignore` is respected by default; use `--no-gitignore` to disable.
- Binary files appear in the generated file tree but are omitted from code blocks.
- Files that would push the output over the size budget are listed in a warning and skipped.

---

## Obsidian Local Memory

Obsidian vaults can be used as local memory and knowledge bases. The `obsidian` command group manages vault paths without needing the full `init` wizard.

```bash
# Show configured vaults and their status
kimi-mcp-hub obsidian status

# Add a vault path (scaffolds the vault if needed)
kimi-mcp-hub obsidian add ~/Documents/MyVault

# Auto-create a project vault for the current git repo
kimi-mcp-hub obsidian auto

# List configured vaults
kimi-mcp-hub obsidian list

# Remove a vault from the config by slug (files are kept)
kimi-mcp-hub obsidian remove myvault

# Copy built-in templates into a vault
kimi-mcp-hub obsidian sync-templates myvault

# Copy custom templates into a vault
kimi-mcp-hub obsidian sync-templates --templates-dir ./templates myvault
```

The first vault added is set as the default memory vault. After adding a vault, restart Kimi CLI so the Obsidian MCP server picks it up.

### Project-specific memory

When working across multiple repositories, `kimi-mcp-hub obsidian auto` detects the current git repo and creates/switches to a project-specific vault at `<repo-root>/<RepoName>-Memory`. If the vault lives inside the repo, the command also adds it to `.gitignore` so it is never committed. To make this automatic whenever you start Kimi, add a shell wrapper to your `~/.zshrc`:

```bash
k() {
  kimi-mcp-hub obsidian auto >/dev/null 2>&1
  kimi "$@"
}
```

Then use `k` instead of `kimi`. Each project gets its own memory vault automatically.

### LLM-powered session summaries

By default, every session is saved as a raw observation note. You can also enable LLM-generated summaries that extract the goal, key decisions, files/tools touched, and open TODOs.

```bash
# Configure an OpenAI-compatible provider
kimi-mcp-hub memory config-summary --api-key sk-... --model gpt-4o-mini

# Or use an environment variable (safer — avoids shell history)
export KIMI_MEMORY_SUMMARY_API_KEY=sk-...
kimi-mcp-hub memory config-summary --model gpt-4o-mini

# Interactive prompt (key is hidden)
kimi-mcp-hub memory config-summary

# Disable summaries but keep raw notes
kimi-mcp-hub memory config-summary --api-key sk-... --disabled
```

Supported providers include OpenAI, OpenRouter, and local [Ollama](https://ollama.com) endpoints. If no key is configured or the LLM call fails, `kimi-mcp-hub` falls back to the raw observation note.

After a session you will find two notes in `<vault>/Sessions/`:

- `YYYY-MM-DD-HHMMSS-<session>.md` — raw observations
- `YYYY-MM-DD-HHMMSS-<session>-summary.md` — LLM-generated summary

---

## Advanced Memory Layer

In addition to Obsidian notes, `kimi-mcp-hub` keeps a local, long-term memory store for facts, preferences, and project context. Memories are saved to a SQLite database and are searchable from the CLI. Project-scoped memories are automatically injected at session start when the working directory matches.

```bash
# Save a user preference
kimi-mcp-hub memory add "Use ruff for linting" --category user --tags linting

# Save project context for the current directory
kimi-mcp-hub memory add "API base URL is https://api.example.com" --category project

# Search all memories
kimi-mcp-hub memory search "ruff"

# List recent memories
kimi-mcp-hub memory list

# Delete a memory by ID
kimi-mcp-hub memory forget 3
```

Project memories (`--category project`) are injected into the session context whenever you start Kimi in the matching project directory. This is useful for base URLs, coding conventions, or reminders that should apply to a specific codebase.

---

## Install Claude/Codex Plugins

Kimi CLI now supports lifecycle hooks (`PreToolUse`, `PostToolUse`, `Stop`, etc.) via `~/.kimi-code/config.toml`. Because Kimi uses the same JSON wire protocol as Claude Code and Codex, plugins written for those agents can be adapted automatically.

```bash
# Install Ponytail (reduces over-engineering)
kimi-mcp-hub install-plugin DietrichGebert/ponytail

# From a full URL
kimi-mcp-hub install-plugin https://github.com/DietrichGebert/ponytail

# From a local checkout
kimi-mcp-hub install-plugin ./ponytail

# Non-interactive reinstall/update
kimi-mcp-hub install-plugin DietrichGebert/ponytail --yes
```

`install-plugin` does the following:

1. Clones the repo to `~/.config/kimi-mcp-hub/plugins/<name>/` (or copies a local directory)
2. Discovers the plugin manifest among supported formats:
   - `hooks.json` / `hooks/hooks.json` / `hooks/claude-codex-hooks.json`
   - `.claude/settings.json`
   - `.codex/hooks.json`
   - `.claude-plugin/plugin.json` (Claude marketplace format)
   - `gemini-extension.json`
3. Converts discovered hooks to Kimi `[[hooks]]` entries in `~/.kimi-code/config.toml`
4. Expands `${PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_ROOT}`, and `${CLAUDE_CODE_PLUGIN_ROOT}` to the install directory
5. Relativizes hardcoded absolute paths that still point inside the plugin directory so commands stay portable
6. Merges the plugin's `AGENTS.md` into `~/.kimi-code/AGENTS.md` (idempotent by marker)
7. Copies plugin skills into `~/.kimi-code/skills/`

**What this unlocks**

1. **Ponytail** works immediately — reduces over-engineering in every project.
2. **Security hooks** — block edits to `.env` files or dangerous `rm` commands.
3. **Auto-format / auto-lint** hooks after every `WriteFile`.
4. **Stop hooks** — verify tests passed before the session ends.
5. `kimi-mcp-hub` becomes a hub for agent extensions, not just an MCP manager.

**Tool-name mapping**

| Claude/Codex | Kimi matcher |
|--------------|--------------|
| `Write` | `WriteFile\|StrReplaceFile` |
| `Edit` | `Edit\|StrReplaceFile` |
| `Read` | `ReadFile` |
| `Bash` | `Shell\|Bash` |

After installing a plugin, **restart Kimi CLI** for the hooks to take effect.

### Managing installed plugins

Plugins installed from GitHub can be updated and removed through the CLI:

```bash
# Pull latest changes for a git plugin, or re-copy a local plugin
kimi-mcp-hub update-plugin ponytail

# Remove a plugin completely
kimi-mcp-hub uninstall-plugin ponytail
```

`update-plugin` re-runs the install merge, so new hooks, skills, and `AGENTS.md` sections are applied automatically. `uninstall-plugin` removes the plugin directory, deletes its hooks from `~/.kimi-code/config.toml`, removes any skills it installed, and removes its section from `~/.kimi-code/AGENTS.md`.

---

## Project-Level MCP Configuration

If you work on multiple projects that need different MCP accounts, you can store MCP servers inside each project. The example below adds Linear's official remote OAuth server:

```bash
cd my-project
kimi-mcp-hub add --project linear   # choose the default "official-oauth" mode
kimi-mcp-hub sync
```

This creates:

```text
my-project/
└── .kimi/
    ├── mcp.json          # server config
    └── mcp.env           # only needed for API-key / stdio servers (add this to .gitignore)
```

`.kimi/mcp.json` example (Linear official remote OAuth — no `env`):

```json
{
  "mcpServers": {
    "linear": {
      "transport": "http",
      "url": "https://mcp.linear.app/mcp",
      "auth": "oauth"
    }
  }
}
```

`.kimi/mcp.env` is only required for servers that store secrets in environment variables (for example, API-key stdio servers such as Perplexity or a GitHub PAT). OAuth servers like Linear keep tokens inside Kimi CLI's own secure storage and do not need a project `.env` file.

### Switching between projects

When you switch projects, run `sync` to rewrite the global `~/.kimi-code/mcp.json` with that project's servers:

```bash
cd project-a && kimi-mcp-hub sync   # global config now uses project-a's Linear
cd project-b && kimi-mcp-hub sync   # global config now uses project-b's Linear
```

Project servers override global servers with the same name. Global servers that are not overridden remain available.

### Commands with --project

```bash
kimi-mcp-hub init --project          # save wizard servers to current project
kimi-mcp-hub add --project perplexity # add API-key server to current project
kimi-mcp-hub add --project linear    # add official remote OAuth server to current project
kimi-mcp-hub auth --project figma    # authorize and save an OAuth server to current project
kimi-mcp-hub remove --project perplexity # remove server from current project
kimi-mcp-hub sync                    # merge current project into global config
kimi-mcp-hub sync /path/to/project   # merge a specific project
```


If you have **Desktop Commander** installed, you can also ask Kimi to run the command for you:

```text
run kimi-mcp-hub add linear in the terminal
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
| **Slack** | Bot/User token (`slack-mcp-server`) | Yes |
| **Figma** | Official OAuth 2.1, PAT or custom OAuth 2.0 | Yes* |
| **Gmail** | Google OAuth 2.0 or npx | Yes |
| **Linear** | Official OAuth 2.1 or API key | Yes* |
| **Stripe** | Official OAuth 2.1 or restricted API key | Yes* |
| **GitLab** | Official OAuth 2.1 or PAT | Yes* |
| **Supabase** | Official remote OAuth or access-token stdio | Yes* |
| **Datadog** | API + App keys | No (manual) |

\* Official remote OAuth 2.1 is initiated by Kimi CLI (`kimi mcp auth <server>` or `/mcp-config login <server>`) after you add the official remote MCP server. For Slack, run `kimi-mcp-hub auth slack` to start the browser-based OAuth flow.

---

## CLAUDE.md Compatibility

If you are migrating from Claude Code or want Kimi to automatically read project instructions, apply the `claude-compat` patch:

```bash
# Interactive
kimi-mcp-hub claude-compat

# Non-interactive (useful in install scripts)
kimi-mcp-hub claude-compat --yes
```

This appends a block to `~/.kimi-code/AGENTS.md` that tells Kimi to check for two files at the start of every session:

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `CLAUDE.local.md` | Local overrides — machine-specific, gitignored |
| 2 | `CLAUDE.md` | Project-wide instructions — committed to the repo |

`CLAUDE.local.md` takes precedence over `CLAUDE.md` when they conflict.

---

## All Commands

| Command | Description |
|---------|-------------|
| `kimi-mcp-hub` | Show welcome banner and status |
| `kimi-mcp-hub --version` | Show version |
| `kimi-mcp-hub install` | Install or update Kimi MCP Hub |
| `kimi-mcp-hub update` | Update to the latest version |
| `kimi-mcp-hub init` | Full interactive wizard |
| `kimi-mcp-hub init --yes` | Non-interactive setup with defaults |
| `kimi-mcp-hub claude-compat` | Patch AGENTS.md for CLAUDE.md auto-load |
| `kimi-mcp-hub claude-compat --yes` | Apply patch without confirmation |
| `kimi-mcp-hub status` | Version, servers, skills, memory |
| `kimi-mcp-hub welcome` | Detailed welcome banner |
| `kimi-mcp-hub notify` | Short startup notification for shell wrappers |
| `kimi-mcp-hub add <server>` | Add an MCP server |
| `kimi-mcp-hub add obsidian` | Add Obsidian vault as local memory |
| `kimi-mcp-hub add --project <server>` | Add an MCP server to the current project |
| `kimi-mcp-hub remove <server>` | Remove an MCP server |
| `kimi-mcp-hub remove --project <server>` | Remove an MCP server from the current project |
| `kimi-mcp-hub auth <server>` | OAuth with auto-browser |
| `kimi-mcp-hub auth --project <server>` | OAuth and save to the current project |
| `kimi-mcp-hub sync` | Merge project `.kimi/mcp.json` into global config |
| `kimi-mcp-hub repair` | Fix broken/outdated server configs |
| `kimi-mcp-hub import-claude` | Import from Claude Desktop |
| `kimi-mcp-hub install-plugin <repo>` | Install Claude/Codex plugin into Kimi |
| `kimi-mcp-hub install-plugin <repo> --yes` | Install plugin without confirmation |
| `kimi-mcp-hub update-plugin <name>` | Update an installed plugin |
| `kimi-mcp-hub uninstall-plugin <name>` | Remove an installed plugin and its artifacts |
| `kimi-mcp-hub list` | All servers + skills + memory |
| `kimi-mcp-hub list-skills` | All 57 available skills |
| `kimi-mcp-hub install-skill <name>` | Install a skill |
| `kimi-mcp-hub test <server>` | Check if server binary/HTTP endpoint is configured |
| `kimi-mcp-hub doctor` | System health check |
| `kimi-mcp-hub obsidian status` | Show configured Obsidian vaults |
| `kimi-mcp-hub obsidian add <path>` | Add an Obsidian vault path |
| `kimi-mcp-hub obsidian auto` | Create/switch to project vault in current git repo |
| `kimi-mcp-hub obsidian list` | List configured Obsidian vaults |
| `kimi-mcp-hub obsidian remove <slug>` | Remove an Obsidian vault from config |
| `kimi-mcp-hub obsidian sync-templates [--templates-dir PATH] <vault-slug>` | Copy templates into a vault |
| `kimi-mcp-hub pack [ROOT]` | Pack a repository into an AI-friendly markdown file |
| `kimi-mcp-hub pack -e '<pattern>'` | Exclude glob patterns (can be repeated) |
| `kimi-mcp-hub pack --max-size <bytes> -o <path>` | Set output size budget and write to file |
| `kimi-mcp-hub memory config-summary [--api-key ...] [--model ...] [--base-url ...]` | Configure LLM for session summaries |
| `kimi-mcp-hub memory add "<content>" [--category user\|project\|general] [--tags tag1,tag2]` | Save a long-term memory |
| `kimi-mcp-hub memory search "<query>" [--limit N] [--category ...]` | Search saved memories |
| `kimi-mcp-hub memory list [--limit N] [--category ...]` | List recent memories |
| `kimi-mcp-hub memory forget <id>` | Delete a memory by ID |

---

## 24 MCP Servers

| Server | Auth | Tools | Best for |
|--------|------|:-----:|----------|
| **Jira** | OAuth (Cloud) or API token | 8 | Tickets, sprints, worklogs |
| **Linear** | Official OAuth 2.1 or API key | 6 | Issues, projects, teams |
| **Confluence** | OAuth or API token | 5 | Docs, wiki, pages |
| **GitHub** | Device Flow / PAT | 6 | Repos, PRs, issues, code |
| **Slack** | Bot/User token (`slack-mcp-server`) | 5 | Channels, DMs, search |
| **Obsidian** | STDIO (npx) — vault path | 4 | Local memory, notes, knowledge base |
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
| **Perplexity** | **API key (paid, $5 trial credit)** | **3** | **Real-time web search with AI summaries + citations** |

---

## 57 Skills

### Core Skills (installed by default)

| Skill | Description |
|-------|-------------|
| **karpathy** | Clean, simple, readable code discipline |
| **superpowers** | 14 agentic workflows (plan, debug, test, deploy...) |
| **headroom** | Compress large tool outputs to save tokens |
| **context-mode** | Context window optimization and token budget |
| **cybersecurity** | Cybersecurity expert (OWASP, cloud, IR, pentest) |
| **caveman** | Ultra-compressed caveman communication mode |
| **kimi-mcp-hub-status** | Show MCP Hub version and status |

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
| **design-system** | Design tokens, component specs, and systematic design systems |
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
| **claude-compat** | Auto-load CLAUDE.md and CLAUDE.local.md at session start |
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

## Testing

The test suite lives in `tests/`:

```bash
pytest -q
```

- `tests/test_integration.py` covers end-to-end flows such as `init --yes`, server `add`, `remove`, and `test`.
- Unit tests cover config handling, Obsidian vault management, and the plugin installer.

---

## Architecture

```
+-----------------------------------------+
|         kimi-mcp-hub CLI                |
|  +---------------------------------+    |
|  |  (no args) -> welcome banner    |    |
|  |  install -> GitHub update       |    |
|  |  init -> interactive wizard     |    |
|  |  add  -> writes ~/.kimi-code/...|    |
|  |  add --project -> writes ./.kimi|    |
|  |  sync -> merge project + global |    |
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
|  |  Global: ~/.kimi-code/mcp.json  |    |
|  |  Project: ./.kimi/mcp.json      |    |
|  |  Project secrets: ./.kimi/mcp.env|   |
|  |  ~/.kimi-code/skills/ (57 skills)|    |
|  |  <config-dir>/kimi-mcp-hub/     |    |
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

- On macOS and Linux, sensitive files (`tokens.json`, `memory.db`, and `~/.kimi-code/mcp.json`) are written with `chmod 600` (owner read/write only).
- Run `kimi-mcp-hub doctor` to detect and fix overly permissive files.
- OAuth tokens are still stored as plain JSON inside those files. This keeps the tool dependency-free, but a process running as your user can read them while Kimi CLI is active.
- By default GitHub authentication uses a public OAuth app (`kimi-mcp-hub`). You can supply your own GitHub/Atlassian OAuth Client ID when running `kimi-mcp-hub auth <server>`.

---

## License

MIT
