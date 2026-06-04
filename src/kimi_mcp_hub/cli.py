"""Kimi MCP Hub CLI — one-click MCP server and skills manager."""

import json
import subprocess
import sys
import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from .config import KimiConfig
from .servers import (
    ChromeDevToolsServer,
    JiraServer, LinearServer, ConfluenceServer, GitHubServer,
    SlackServer, DatadogServer, FigmaServer, GmailServer,
    HubSpotServer, GrainServer,
)
from .auth.oauth import OAuthHandler
from .import_claude import import_claude_servers

console = Console()

SERVERS = {
    "jira": JiraServer,
    "linear": LinearServer,
    "confluence": ConfluenceServer,
    "github": GitHubServer,
    "slack": SlackServer,
    "datadog": DatadogServer,
    "figma": FigmaServer,
    "gmail": GmailServer,
    "hubspot": HubSpotServer,
    "grain": GrainServer,
    "chrome-devtools": ChromeDevToolsServer,
    "postgres": PostgreSQLServer,
    "playwright": PlaywrightServer,
    "sentry": SentryServer,
    "context7": Context7Server,
    "supabase": SupabaseServer,
}

SKILLS = {
    "superpowers": "🦸 14 agentic dev skills (plan, debug, test, deploy, audit...)",
    "ecc": "🛡️ Engineering Competence (perf, security, research)",
    "karpathy": "🧠 Code discipline (simple, readable, correct)",
    "caveman": "🪨 Terse mode (75% token reduction)",
    "ui-ux-pro-max": "🎨 Design intelligence (Tailwind, accessibility)",
    "headroom": "📉 Compress tool outputs (save tokens)",
    "context-mode": "🎯 Context window optimization",
    "hindsight": "🔮 Memory that learns from mistakes",
    "visual-explainer": "📊 HTML diagrams and slides",
    "task-master": "📋 Task management system",
    "gitnexus": "🕸️ Code knowledge graph (git blame, blast radius)",
    "ralph": "🔄 Autonomous loop with stop-hooks",
    "security-audit": "🔒 Security review checklist",
    "research-mode": "🔬 Research-driven development",
    "perf-optimization": "⚡ Performance profiling and fixes",
    "memory-palace": "🏛️ Advanced context management",
    "code-reviewer": "👀 Code review assistant",
    "api-designer": "🔌 REST/GraphQL API design",
    "docker-pro": "🐳 Docker and Kubernetes best practices",
    "database-expert": "🗄️ Database design and optimization",
    "security-guidance": "🔒 3-layer security scanning (file edit, model turn, commit)",
    "code-review": "👀 Multi-agent code review (explore + coder + plan sub-agents)",
}


def print_header():
    console.print(Panel.fit(
        "[bold cyan]Kimi MCP Hub[/bold cyan] — One-click MCP server & skills manager\n"
        "[dim]10 MCP Servers · 20 Skills · Persistent Memory[/dim]",
        border_style="cyan"
    ))


@click.group()
@click.version_option(version="0.1.0")
def main():
    """kimi-mcp-hub — Manage MCP servers and skills for Kimi CLI."""
    pass


@main.command()
def init():
    """Interactive setup wizard for servers, skills, and memory."""
    print_header()
    config = KimiConfig()

    console.print("\n[bold green]Welcome to Kimi MCP Hub![/bold green]\n")
    console.print("This wizard will set up MCP servers, skills, and optional memory.\n")

    # Step 1: MCP Servers
    console.print("[bold]Step 1: MCP Servers[/bold] (external tools)\n")
    for key, cls in SERVERS.items():
        icon = getattr(cls, "icon", "🔌")
        name = getattr(cls, "display_name", key.title())
        if Confirm.ask(f"{icon} Add [bold]{name}[/bold]?", default=False):
            add_server_interactive(key, config)

    # Step 2: Skills
    console.print("\n[bold]Step 2: Skills[/bold] (AI behavior patterns)\n")
    for key, desc in SKILLS.items():
        if Confirm.ask(f"{desc} — Install?", default=False):
            install_skill(key, config)

    # Step 3: Memory
    console.print("\n[bold]Step 3: Persistent Memory[/bold]\n")
    if Confirm.ask("Enable persistent memory across sessions?", default=True):
        enable_memory(config)

    console.print("\n[bold green]✅ Setup complete![/bold green]")
    console.print("Run [bold]kimi[/bold] and type:")
    console.print("  [bold]/mcp[/bold]    — see your tools")
    console.print("  [bold]/skills[/bold] — see installed skills")
    console.print("\n[dim]Type [bold]kimi-mcp-hub list[/bold] to see everything.[/dim]\n")


@main.command()
@click.argument("server_name")
def add(server_name: str):
    """Add an MCP server (jira, linear, confluence, github, slack, datadog, figma, gmail, hubspot, grain)."""
    print_header()
    config = KimiConfig()
    if server_name not in SERVERS:
        console.print(f"[red]Unknown server: {server_name}[/red]")
        console.print(f"Available: {', '.join(SERVERS.keys())}")
        sys.exit(1)
    add_server_interactive(server_name, config)


@main.command()
@click.argument("server_name")
def remove(server_name: str):
    """Remove an MCP server."""
    config = KimiConfig()
    config.remove_server(server_name)
    console.print(f"[green]Removed {server_name}[/green]")


@main.command()
def list():
    """List all configured MCP servers, skills, and memory status."""
    print_header()
    config = KimiConfig()

    # Servers
    servers = config.list_servers()
    if servers:
        table = Table(title="Configured MCP Servers", box=box.ROUNDED)
        table.add_column("Server", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Tools", style="green")
        for name, cfg in servers.items():
            transport = cfg.get("transport", "stdio")
            if "command" in cfg:
                transport = f"stdio ({cfg['command']})"
            elif "url" in cfg:
                transport = f"http ({cfg['url'][:40]}...)"
            tool_count = "?"
            if name in SERVERS:
                tool_count = f"{len(SERVERS[name].get_tools())} tools"
            table.add_row(name, transport, tool_count)
        console.print(table)
    else:
        console.print("[yellow]No MCP servers configured.[/yellow]")
        console.print("Run [bold]kimi-mcp-hub add <server>[/bold] or [bold]kimi-mcp-hub init[/bold].\n")

    # Skills
    skills_installed = list_installed_skills(config)
    if skills_installed:
        console.print(f"\n[green]✅ {len(skills_installed)} skills installed:[/green]")
        for s in skills_installed:
            desc = SKILLS.get(s, "")
            console.print(f"  [cyan]{s}[/cyan] {desc}")
    else:
        console.print("\n[yellow]No skills installed.[/yellow]")

    # Memory
    memory_db = Path.home() / ".kimi" / "mcp-hub" / "memory.db"
    if memory_db.exists():
        console.print(f"\n[green]🧠 Memory enabled:[/green] {memory_db}")
    else:
        console.print(f"\n[dim]🧠 Memory not enabled. Run [bold]kimi-mcp-hub init[/bold] to enable.[/dim]")

    console.print("\n[dim]In Kimi CLI, type [bold]/mcp[/bold] for tools, [bold]/skills[/bold] for skills.[/dim]\n")


@main.command()
@click.argument("skill_name")
def install_skill_cmd(skill_name: str):
    """Install a skill into ~/.kimi/skills/."""
    print_header()
    config = KimiConfig()
    if skill_name not in SKILLS:
        console.print(f"[red]Unknown skill: {skill_name}[/red]")
        console.print(f"Available: {', '.join(SKILLS.keys())}")
        sys.exit(1)
    install_skill(skill_name, config)


@main.command()
def list_skills():
    """List all available skills."""
    print_header()
    config = KimiConfig()
    installed = list_installed_skills(config)

    table = Table(title="Available Skills", box=box.ROUNDED)
    table.add_column("Skill", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    for key, desc in SKILLS.items():
        status = "[green]✅ installed[/green]" if key in installed else "[dim]not installed[/dim]"
        table.add_row(key, desc, status)

    console.print(table)
    console.print("\n[dim]Install with: [bold]kimi-mcp-hub install-skill <name>[/bold][/dim]\n")


@main.command()
@click.argument("server_name")
def auth(server_name: str):
    """Authorize an MCP server (OAuth flows)."""
    print_header()
    config = KimiConfig()

    if server_name == "jira":
        console.print("[bold]Jira OAuth[/bold] — Atlassian Cloud\n")
        console.print("  1. Run [bold]kimi mcp add --transport http --auth oauth jira https://mcp.atlassian.com/v1/mcp/authv2[/bold]")
        console.print("  2. Run [bold]kimi mcp auth jira[/bold]")
        console.print("\nOr use API token mode with [bold]kimi-mcp-hub add jira[/bold]\n")

    elif server_name == "confluence":
        console.print("[bold]Confluence OAuth[/bold] — Atlassian Cloud\n")
        console.print("Same as Jira — use Atlassian's OAuth MCP endpoint.\n")

    elif server_name == "slack":
        console.print("[bold]Slack OAuth[/bold]\n")
        console.print("  [bold]kimi mcp add --transport http --auth oauth slack https://mcp.slack.com/mcp[/bold]")
        console.print("  Then: [bold]kimi mcp auth slack[/bold]\n")

    elif server_name == "linear":
        console.print("[bold]Linear[/bold] uses API key.\n")
        console.print("Get key from: https://linear.app/settings/api")
        token = Prompt.ask("Linear API key", password=True)
        if token:
            cfg = LinearServer.get_stdio_config(token)
            config.add_server("linear", cfg)
            console.print("[green]✅ Linear configured![/green]\n")

    elif server_name == "github":
        console.print("[bold]GitHub[/bold] uses PAT.\n")
        console.print("Create at: https://github.com/settings/tokens")
        token = Prompt.ask("GitHub token", password=True)
        if token:
            cfg = GitHubServer.get_stdio_config(token)
            config.add_server("github", cfg)
            console.print("[green]✅ GitHub configured![/green]\n")

    elif server_name == "datadog":
        console.print("[bold]Datadog[/bold] uses API + App keys.\n")
        api_key = Prompt.ask("Datadog API key", password=True)
        app_key = Prompt.ask("Datadog App key", password=True)
        site = Prompt.ask("Datadog site", default="datadoghq.com")
        if api_key and app_key:
            cfg = DatadogServer.get_stdio_config(api_key, app_key, site)
            config.add_server("datadog", cfg)
            console.print("[green]✅ Datadog configured![/green]\n")

    elif server_name == "figma":
        console.print("[bold]Figma[/bold] — choose mode:\n")
        mode = Prompt.ask("Mode", choices=["official", "console"], default="console")
        if mode == "official":
            cfg = FigmaServer.get_official_config()
            config.add_server("figma", cfg)
            console.print("[green]✅ Figma Official configured (HTTP)[/green]")
        else:
            token = Prompt.ask("Figma PAT (figd_...)", password=True)
            if token:
                cfg = FigmaServer.get_console_config(token)
                config.add_server("figma", cfg)
                console.print("[green]✅ Figma Console configured[/green]")

    elif server_name == "gmail":
        console.print("[bold]Gmail[/bold] — choose implementation:\n")
        impl = Prompt.ask("Implementation", choices=["npx", "chrome", "python"], default="npx")
        if impl == "npx":
            cfg = GmailServer.get_npx_config()
        elif impl == "chrome":
            cfg = GmailServer.get_chrome_config()
        else:
            creds = Prompt.ask("Path to credentials.json")
            tokens = Prompt.ask("Path to tokens.json", default="~/.gmail-mcp/tokens.json")
            cfg = GmailServer.get_python_config(creds, tokens)
        config.add_server("gmail", cfg)
        console.print(f"[green]✅ Gmail configured ({impl})[/green]\n")

    elif server_name == "hubspot":
        console.print("[bold]HubSpot[/bold] — choose source:\n")
        src = Prompt.ask("Source", choices=["npx", "official", "docker"], default="npx")
        token = Prompt.ask("HubSpot Private App token", password=True)
        if token:
            if src == "npx":
                cfg = HubSpotServer.get_npx_config(token)
            elif src == "official":
                cfg = HubSpotServer.get_official_config(token)
            else:
                cfg = HubSpotServer.get_docker_config(token)
            config.add_server("hubspot", cfg)
            console.print(f"[green]✅ HubSpot configured ({src})[/green]\n")

    elif server_name == "grain":
        console.print("[bold]Grain[/bold] — uses browser automation.\n")
        data_dir = Prompt.ask("Browser data directory", default="~/.grain-mcp/data")
        cfg = GrainServer.get_uv_config(data_dir)
        config.add_server("grain", cfg)
        console.print("[green]✅ Grain configured![/green]\n")


@main.command()
@click.argument("server_name")
def test(server_name: str):
    """Test if an MCP server is responding."""
    config = KimiConfig()
    servers = config.list_servers()
    if server_name not in servers:
        console.print(f"[red]{server_name} not configured[/red]")
        sys.exit(1)

    console.print(f"[bold]Testing {server_name}...[/bold]")
    cfg = servers[server_name]
    if "command" in cfg:
        try:
            cmd = [cfg["command"]] + cfg.get("args", [])
            result = subprocess.run(
                ["which", cmd[0]],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                console.print(f"[green]✅ {cmd[0]} found at {result.stdout.strip()}[/green]")
            else:
                console.print(f"[red]❌ {cmd[0]} not found. Install with npm/npx.[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    elif "url" in cfg:
        console.print(f"[green]✅ HTTP endpoint configured: {cfg['url'][:60]}[/green]")
        console.print("[dim]   Use 'kimi mcp auth {server_name}' to complete OAuth.[/dim]")


@main.command(name="import-claude")
def import_claude_cmd():
    """Import MCP servers from Claude Desktop or Claude Code."""
    print_header()
    config = KimiConfig()
    import_claude_servers(config)


@main.command()
def doctor():
    """Check system health — node, npx, kimi CLI, docker."""
    print_header()
    table = Table(box=box.ROUNDED)
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Note", style="dim")

    checks = [
        ("node", ["node", "--version"]),
        ("npx", ["npx", "--version"]),
        ("kimi", ["kimi", "--version"]),
        ("npm", ["npm", "--version"]),
        ("docker", ["docker", "--version"]),
        ("uv", ["uv", "--version"]),
    ]

    for name, cmd in checks:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                ver = result.stdout.strip().split()[0] if result.stdout.strip() else "OK"
                table.add_row(name, f"[green]✅ {ver}[/green]", "Found")
            else:
                table.add_row(name, "[red]❌ Error[/red]", result.stderr[:50])
        except FileNotFoundError:
            table.add_row(name, "[red]❌ Missing[/red]", f"Install {name}")
        except Exception as e:
            table.add_row(name, "[red]❌ Fail[/red]", str(e)[:50])

    console.print(table)

    config = KimiConfig()
    servers = config.list_servers()
    if servers:
        console.print(f"\n[green]✅ {len(servers)} MCP server(s) in ~/.kimi/mcp.json[/green]")
    else:
        console.print("\n[yellow]⚠️ No MCP servers configured yet[/yellow]")

    skills_installed = list_installed_skills(config)
    if skills_installed:
        console.print(f"[green]✅ {len(skills_installed)} skills in ~/.kimi/skills/[/green]")
    else:
        console.print("[yellow]⚠️ No skills installed yet[/yellow]")

    memory_db = Path.home() / ".kimi" / "mcp-hub" / "memory.db"
    if memory_db.exists():
        console.print(f"[green]🧠 Memory database: {memory_db}[/green]")
    else:
        console.print("[dim]🧠 Memory not enabled[/dim]")

    console.print("\n[dim]Run [bold]kimi-mcp-hub init[/bold] to set up everything.[/dim]\n")


# ─── Helper functions ───

def add_server_interactive(name: str, config: KimiConfig):
    """Interactive prompt to add a server."""
    cls = SERVERS[name]
    icon = getattr(cls, "icon", "🔌")
    display = getattr(cls, "display_name", name.title())

    console.print(f"\n{icon} [bold]{display}[/bold]")
    console.print(f"[dim]{cls.description}[/dim]\n")

    if name in ("jira", "confluence"):
        choice = Prompt.ask("Auth method", choices=["oauth", "api-token"], default="oauth")
        if choice == "oauth":
            if name == "jira":
                cfg = JiraServer.get_oauth_config()
            else:
                cfg = ConfluenceServer.get_oauth_config()
            config.add_server(name, cfg)
            console.print(f"[green]✅ Added {display} (OAuth)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name}[/dim]")
        else:
            base = Prompt.ask("Base URL", default="https://yourcompany.atlassian.net")
            email = Prompt.ask("Email")
            token = Prompt.ask("API token", password=True)
            if name == "jira":
                cfg = JiraServer.get_stdio_config(base, token, email)
            else:
                cfg = ConfluenceServer.get_stdio_config(base, token, email)
            config.add_server(name, cfg)
            console.print(f"[green]✅ Added {display} (API token)[/green]")

    elif name == "linear":
        token = Prompt.ask("Linear API key (https://linear.app/settings/api)", password=True)
        cfg = LinearServer.get_stdio_config(token)
        config.add_server(name, cfg)
        console.print(f"[green]✅ Added {display}[/green]")

    elif name == "github":
        token = Prompt.ask("GitHub PAT (https://github.com/settings/tokens)", password=True)
        cfg = GitHubServer.get_stdio_config(token)
        config.add_server(name, cfg)
        console.print(f"[green]✅ Added {display}[/green]")

    elif name == "slack":
        choice = Prompt.ask("Auth method", choices=["oauth", "token"], default="token")
        if choice == "oauth":
            cfg = SlackServer.get_oauth_config()
            config.add_server(name, cfg)
            console.print(f"[green]✅ Added {display} (OAuth)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name}[/dim]")
        else:
            token = Prompt.ask("Slack Bot/User token (xoxb-... or xoxp-...)", password=True)
            cfg = SlackServer.get_stdio_config(token)
            config.add_server(name, cfg)
            console.print(f"[green]✅ Added {display} (token)[/green]")

    elif name == "datadog":
        api_key = Prompt.ask("Datadog API key", password=True)
        app_key = Prompt.ask("Datadog App key", password=True)
        site = Prompt.ask("Datadog site", default="datadoghq.com")
        use_docker = Confirm.ask("Use Docker?", default=True)
        if use_docker:
            cfg = DatadogServer.get_stdio_config(api_key, app_key, site)
        else:
            cfg = DatadogServer.get_uv_config(api_key, app_key)
        config.add_server(name, cfg)
        console.print(f"[green]✅ Added {display}[/green]")

    elif name == "figma":
        choice = Prompt.ask("Mode", choices=["official-http", "console-npx"], default="console-npx")
        if choice == "official-http":
            cfg = FigmaServer.get_official_config()
            config.add_server(name, cfg)
            console.print(f"[green]✅ Added {display} (Official HTTP)[/green]")
        else:
            token = Prompt.ask("Figma PAT (figd_...)", password=True)
            cfg = FigmaServer.get_console_config(token)
            config.add_server(name, cfg)
            console.print(f"[green]✅ Added {display} (Console)[/green]")

    elif name == "gmail":
        choice = Prompt.ask("Mode", choices=["npx-auto", "chrome-bridge", "python-sdk"], default="npx-auto")
        if choice == "npx-auto":
            cfg = GmailServer.get_npx_config()
        elif choice == "chrome-bridge":
            cfg = GmailServer.get_chrome_config()
        else:
            creds = Prompt.ask("Path to credentials.json")
            tokens = Prompt.ask("Path to tokens.json", default="~/.gmail-mcp/tokens.json")
            cfg = GmailServer.get_python_config(creds, tokens)
        config.add_server(name, cfg)
        console.print(f"[green]✅ Added {display} ({choice})[/green]")

    elif name == "hubspot":
        choice = Prompt.ask("Source", choices=["npx", "official", "docker"], default="npx")
        token = Prompt.ask("HubSpot Private App token", password=True)
        if choice == "npx":
            cfg = HubSpotServer.get_npx_config(token)
        elif choice == "official":
            cfg = HubSpotServer.get_official_config(token)
        else:
            cfg = HubSpotServer.get_docker_config(token)
        config.add_server(name, cfg)
        console.print(f"[green]✅ Added {display} ({choice})[/green]")

    elif name == "grain":
        data_dir = Prompt.ask("Browser data directory", default="~/.grain-mcp/data")
        cfg = GrainServer.get_uv_config(data_dir)
        config.add_server(name, cfg)
        console.print(f"[green]✅ Added {display}[/green]")
        console.print(f"[dim]   Login via browser on first use.[/dim]")

    elif name == "chrome-devtools":
        console.print("[bold]Chrome DevTools[/bold] — requires Node 22+ and Chrome.\n")
        if Confirm.ask("Install chrome-devtools-mcp?", default=True):
            cfg = ChromeDevToolsServer.get_stdio_config()
            config.add_server(name, cfg)
            console.print(f"[green]✅ Added {display}[/green]")
            console.print("[dim]   Make sure Chrome is installed and Node >= 22.[/dim]")


def install_skill(skill_name: str, config: KimiConfig):
    """Install a skill from package to ~/.kimi/skills/."""
    pkg_skills_dir = Path(__file__).parent / "skills" / skill_name
    user_skills_dir = config.skills_dir / skill_name

    if not pkg_skills_dir.exists():
        console.print(f"[red]Skill {skill_name} not found in package.[/red]")
        return

    if user_skills_dir.exists():
        if not Confirm.ask(f"Skill '{skill_name}' already installed. Overwrite?", default=False):
            return

    shutil.copytree(pkg_skills_dir, user_skills_dir, dirs_exist_ok=True)
    console.print(f"[green]✅ Installed skill: {skill_name}[/green]")
    console.print(f"[dim]   Location: {user_skills_dir}[/dim]")


def list_installed_skills(config: KimiConfig) -> list[str]:
    """Return list of installed skill names."""
    if not config.skills_dir.exists():
        return []
    return [d.name for d in config.skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]


def enable_memory(config: KimiConfig):
    """Enable persistent memory system."""
    memory_dir = Path.home() / ".kimi" / "mcp-hub"
    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_db = memory_dir / "memory.db"

    # Initialize SQLite with FTS5
    import sqlite3
    conn = sqlite3.connect(str(memory_db))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            type TEXT,
            content TEXT,
            summary TEXT,
            tags TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
            content, summary, tags,
            content='observations',
            content_rowid='id'
        )
    """)
    conn.commit()
    conn.close()

    console.print(f"[green]🧠 Memory database initialized: {memory_db}[/green]")
    console.print("[dim]   Memory will persist across sessions.[/dim]")


if __name__ == "__main__":
    main()
