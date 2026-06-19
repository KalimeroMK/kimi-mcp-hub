"""Kimi MCP Hub CLI -- one-click MCP server and skills manager."""

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

from . import __version__, __title__, TOTAL_SERVERS, TOTAL_SKILLS
from .config import KimiConfig
from .servers import (
    ChromeDevToolsServer,
    JiraServer, LinearServer, ConfluenceServer, GitHubServer,
    SlackServer, DatadogServer, FigmaServer, FigmaContextServer,
    GitLabServer, GmailServer, HubSpotServer, GrainServer,
    PostgreSQLServer, PlaywrightServer, SentryServer,
    Context7Server, SupabaseServer, PerplexityServer, StripeServer,
    DesktopCommanderServer, DBHubServer, MobileMCPServer,
)
from .auth.oauth import OAuthHandler
from .auth.providers import (
    authenticate_github,
    authenticate_atlassian,
    authenticate_slack,
    authenticate_figma,
)
from .import_claude import import_claude_servers
from ._post_install import check_first_run
from .memory.db import MemoryDB

console = Console()

SERVERS = {
    "jira": JiraServer,
    "linear": LinearServer,
    "confluence": ConfluenceServer,
    "github": GitHubServer,
    "slack": SlackServer,
    "datadog": DatadogServer,
    "figma": FigmaServer,
    "figma-context": FigmaContextServer,
    "gitlab": GitLabServer,
    "gmail": GmailServer,
    "hubspot": HubSpotServer,
    "grain": GrainServer,
    "chrome-devtools": ChromeDevToolsServer,
    "postgres": PostgreSQLServer,
    "playwright": PlaywrightServer,
    "sentry": SentryServer,
    "context7": Context7Server,
    "supabase": SupabaseServer,
    "perplexity": PerplexityServer,
    "stripe": StripeServer,
    "desktop-commander": DesktopCommanderServer,
    "dbhub": DBHubServer,
    "mobile": MobileMCPServer,
}

# Core skills are installed by default
CORE_SKILLS = [
    "karpathy",
    "superpowers",
    "headroom",
    "context-mode",
    "cybersecurity",
    "kimi-mcp-hub-status",
]

# Frontend skills are installed together as a recommended frontend stack
FRONTEND_SKILLS = [
    "react-coder",
    "ts-coder",
    "ui-engineer",
    "ui-ux-pro-max",
    "vercel-react-best-practices",
    "web-design-guidelines",
    "agent-browser",
]

SKILLS = {
    # ---- Core skills ----
    "karpathy": "Clean, simple, readable code discipline",
    "superpowers": "14 agentic workflows (plan, debug, test, deploy...)",
    "headroom": "Compress large tool outputs to save tokens",
    "context-mode": "Context window optimization and token budget",
    "cybersecurity": "Cybersecurity expert (OWASP, cloud, IR, pentest)",
    "kimi-mcp-hub-status": "Show MCP Hub version and status",
    # ---- Frontend skills ----
    "react-coder": "React 19 specialist (RSC, hooks)",
    "ts-coder": "TypeScript specialist (strict, generics)",
    "ui-engineer": "UI component implementation (Tailwind, a11y)",
    "ui-ux-pro-max": "UI/UX design intelligence and design systems",
    "vercel-react-best-practices": "React/Next.js performance optimization",
    "web-design-guidelines": "Audit UI code against Vercel guidelines",
    "agent-browser": "Browser automation for web tasks and testing",
    # ---- Optional skills ----
    "caveman": "Terse mode (75% token reduction)",
    "ecc": "Engineering competence (perf, security, research)",
    "visual-explainer": "HTML diagrams and slides",
    "task-master": "Task management system",
    "gitnexus": "Code knowledge graph and blast radius",
    "ralph": "Autonomous loop with stop-hooks",
    "security-audit": "Security review checklist",
    "security-guidance": "3-layer security scanning guidance",
    "research-mode": "Research-driven development",
    "perf-optimization": "Performance profiling and optimization",
    "memory-palace": "Advanced memory and context retrieval",
    "code-reviewer": "Quick single-agent code review",
    "code-review": "Multi-agent code review (explore/coder/plan)",
    "api-designer": "REST/GraphQL API design",
    "docker-pro": "Docker and Kubernetes best practices",
    "database-expert": "Database design and optimization",
    "backend-architect": "Backend architecture and system design",
    "backend-typescript-architect": "TypeScript/Bun backend architecture",
    "python-engineer": "Python specialist (FastAPI, Django, async)",
    "laravel-engineer": "Laravel specialist (Eloquent, Blade, Livewire)",
    "php-pro": "Senior PHP development (strict typing, Laravel/Symfony, PSR)",
    "wp-plugin-development": "WordPress plugin development with hooks and Settings API",
    "hindsight": "Memory that learns from past decisions",
    "find-skills": "Discover and install agent skills",
}


def _get_installed_count(config: KimiConfig) -> dict:
    """Get counts of installed servers, skills for display."""
    servers = config.list_servers()
    skills_installed = list_installed_skills(config)
    return {
        "servers_configured": len(servers),
        "skills_installed": len(skills_installed),
        "total_servers": len(SERVERS),
        "total_skills": len(SKILLS),
    }


def print_welcome():
    """Print the full welcome banner with version and status."""
    config = KimiConfig()
    counts = _get_installed_count(config)

    # Build status line
    server_line = (
        f"[green]{counts['servers_configured']} configured[/green]"
        if counts['servers_configured'] > 0
        else f"[dim]0 configured[/dim]"
    )
    skill_line = (
        f"[green]{counts['skills_installed']} installed[/green]"
        if counts['skills_installed'] > 0
        else f"[dim]0 installed[/dim]"
    )

    welcome_text = (
        f"[bold cyan]{__title__}[/bold cyan] [dim]v{__version__}[/dim]\n"
        f"[dim]One-click MCP server & skills manager for Kimi CLI[/dim]\n"
        f"\n"
        f"[cyan]{len(SERVERS)}[/cyan] MCP Servers available  ({server_line})\n"
        f"[cyan]{len(SKILLS)}[/cyan] Skills available       ({skill_line})\n"
        f"[cyan]1[/cyan]  Persistent memory"
    )

    console.print(Panel.fit(
        welcome_text,
        title=f"[bold]Kimi MCP Hub v{__version__}[/bold]",
        subtitle="[dim]Run: kimi-mcp-hub init[/dim]",
        border_style="cyan"
    ))


def print_header():
    """Print compact header (used by subcommands)."""
    console.print(Panel.fit(
        f"[bold cyan]{__title__}[/bold cyan] [dim]v{__version__}[/dim]\n"
        f"[dim]{len(SERVERS)} MCP Servers  |  {len(SKILLS)} Skills  |  Persistent Memory[/dim]",
        border_style="cyan"
    ))


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="kimi-mcp-hub")
@click.pass_context
def main(ctx):
    """kimi-mcp-hub -- Manage MCP servers and skills for Kimi CLI.

    When called without a command, prints the welcome banner and status.
    """
    # Show first-install or upgrade message only when the CLI is invoked.
    try:
        check_first_run()
    except Exception:
        pass

    if ctx.invoked_subcommand is None:
        print_welcome()
        console.print("\n[dim]Tip: Run [bold]kimi-mcp-hub init[/bold] for interactive setup,[/dim]")
        console.print("[dim]     or [bold]kimi-mcp-hub --help[/bold] to see all commands.[/dim]\n")


@main.command()
def init():
    """Interactive setup wizard for servers, skills, and memory."""
    config = KimiConfig()
    print_welcome()

    console.print("\n[bold green]Welcome to Kimi MCP Hub![/bold green]\n")
    console.print("This wizard will set up MCP servers, skills, and optional memory.\n")

    # Step 1: MCP Servers
    console.print("[bold]Step 1: MCP Servers[/bold] (external tools)\n")
    for key, cls in SERVERS.items():
        icon = getattr(cls, "icon", "")
        name = getattr(cls, "display_name", key.title())
        if Confirm.ask(f"{icon} Add [bold]{name}[/bold]?", default=False):
            add_server_interactive(key, config)

    # Step 2: Skills
    console.print("\n[bold]Step 2: Skills[/bold] (AI behavior patterns)\n")

    # Core skills -- recommended, default=True
    console.print("[bold cyan]Core Skills (Recommended)[/bold cyan]\n")
    for key in CORE_SKILLS:
        if key in SKILLS:
            if Confirm.ask(f"  {SKILLS[key]} -- Install?", default=True):
                install_skill(key, config)

    # Frontend skills -- installed as a recommended stack, default=True
    console.print("\n[bold cyan]Frontend Skills (Recommended)[/bold cyan]\n")
    frontend_desc = ", ".join(SKILLS[k] for k in FRONTEND_SKILLS if k in SKILLS)
    if Confirm.ask(
        f"Install recommended frontend stack ({len(FRONTEND_SKILLS)} skills)?",
        default=True,
    ):
        for key in FRONTEND_SKILLS:
            install_skill(key, config, overwrite=False)

    # Optional skills -- default=False
    console.print("\n[bold cyan]Optional Skills[/bold cyan]\n")
    for key, desc in SKILLS.items():
        if key not in CORE_SKILLS and key not in FRONTEND_SKILLS:
            if Confirm.ask(f"  {desc} -- Install?", default=False):
                install_skill(key, config)

    # Step 3: Memory
    console.print("\n[bold]Step 3: Persistent Memory[/bold]\n")
    if Confirm.ask("Enable persistent memory across sessions?", default=True):
        enable_memory(config)

    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("Run [bold]kimi[/bold] and type:")
    console.print("  [bold]/mcp[/bold]    -- see your tools")
    console.print("  [bold]/skills[/bold] -- see installed skills")
    console.print("\n[dim]Type [bold]kimi-mcp-hub list[/bold] to see everything.[/dim]\n")


@main.command()
def install():
    """Install or update Kimi MCP Hub."""
    print_header()
    
    console.print("[bold cyan]Installing Kimi MCP Hub...[/bold cyan]\n")
    
    # Check if running from repo or pip
    repo_dir = Path(__file__).parent.parent.parent.parent
    if (repo_dir / ".git").exists():
        console.print("[dim]Detected development install (git repo)[/dim]")
        console.print("Run: [bold]pip install -e .[/bold] from repo root\n")
        return
    
    # Try to install from PyPI
    console.print("[cyan]Installing from PyPI...[/cyan]")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--user", "kimi-mcp-hub"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            console.print("[green]Kimi MCP Hub installed from PyPI![/green]\n")
        else:
            # Fallback to GitHub
            console.print("[yellow]PyPI not available, trying GitHub...[/yellow]")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "--user",
                 "git+https://github.com/KalimeroMK/kimi-mcp-hub.git"],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode == 0:
                console.print("[green]Kimi MCP Hub installed from GitHub![/green]\n")
            else:
                console.print("[red]Install failed. Try:[/red]")
                console.print("  [bold]pip install git+https://github.com/KalimeroMK/kimi-mcp-hub.git[/bold]\n")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[dim]Try: pip install git+https://github.com/KalimeroMK/kimi-mcp-hub.git[/dim]\n")


@main.command()
def status():
    """Show Kimi MCP Hub status: version, servers, skills, memory."""
    config = KimiConfig()
    counts = _get_installed_count(config)

    table = Table(box=box.ROUNDED)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="bold")

    table.add_row("Version", f"[cyan]{__version__}[/cyan]")
    table.add_row("MCP Servers", f"{counts['servers_configured']} / {counts['total_servers']} configured")
    table.add_row("Skills", f"{counts['skills_installed']} / {counts['total_skills']} installed")

    memory_db = Path.home() / ".kimi" / "mcp-hub" / "memory.db"
    table.add_row("Memory", "[green]enabled[/green]" if memory_db.exists() else "[dim]disabled[/dim]")

    # Check if Kimi CLI is installed
    try:
        result = subprocess.run(["kimi", "--version"], capture_output=True, text=True, timeout=5)
        kimi_ver = result.stdout.strip() if result.returncode == 0 else "not found"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        kimi_ver = "[red]not installed[/red]"
    table.add_row("Kimi CLI", kimi_ver)

    console.print(Panel.fit(
        table,
        title=f"[bold]{__title__} Status[/bold]",
        border_style="green" if counts['servers_configured'] > 0 else "yellow"
    ))

    if counts['servers_configured'] == 0:
        console.print("\n[dim]Tip: Run [bold]kimi-mcp-hub init[/bold] to set up your first MCP server.[/dim]\n")


@main.command()
def notify():
    """Print a short startup notification for shell wrappers."""
    console.print(
        f"[bold green]●[/bold green] [bold]{__title__} v{__version__}[/bold] [dim]plugin installed[/dim]"
    )


@main.command()
def welcome():
    """Display the welcome banner with version and installation info."""
    print_welcome()

    # Print installed servers detail
    config = KimiConfig()
    servers = config.list_servers()
    if servers:
        console.print("\n[bold]Configured MCP Servers:[/bold]")
        for name, cfg in servers.items():
            console.print(f"  [green]{name}[/green] -- {cfg.get('transport', 'stdio')}")

    # Print installed skills
    skills = list_installed_skills(config)
    if skills:
        console.print(f"\n[bold]Installed Skills ({len(skills)}):[/bold]")
        for s in skills:
            desc = SKILLS.get(s, "")
            console.print(f"  [green]{s}[/green] {desc}")

    console.print(f"\n[bold green]Kimi MCP Hub v{__version__} is ready![/bold green]")
    console.print("[dim]Start Kimi CLI with: [bold]kimi[/bold][/dim]\n")


@main.command()
@click.argument("server_name")
def add(server_name: str):
    """Add an MCP server (jira, linear, confluence, github, slack, datadog,
    figma, gmail, hubspot, grain, chrome-devtools, postgres, playwright,
    sentry, context7, supabase, perplexity)."""
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
        console.print(f"\n[green]{len(skills_installed)} skills installed:[/green]")
        for s in skills_installed:
            desc = SKILLS.get(s, "")
            console.print(f"  [cyan]{s}[/cyan] {desc}")
    else:
        console.print("\n[yellow]No skills installed.[/yellow]")

    # Memory
    memory_db = Path.home() / ".kimi" / "mcp-hub" / "memory.db"
    if memory_db.exists():
        console.print(f"\n[green]Memory enabled:[/green] {memory_db}")
    else:
        console.print(f"\n[dim]Memory not enabled. Run [bold]kimi-mcp-hub init[/bold] to enable.[/dim]")

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
        status = "[green]installed[/green]" if key in installed else "[dim]not installed[/dim]"
        marker = "[bold]*[/bold]" if key in CORE_SKILLS else " "
        table.add_row(f"{marker} {key}", desc, status)

    console.print(table)
    console.print("\n[dim]* = core skill | Install with: [bold]kimi-mcp-hub install-skill <name>[/bold][/dim]\n")


@main.command()
@click.argument("server_name")
def auth(server_name: str):
    """Authorize an MCP server with auto browser open (OAuth/Device Flow)."""
    print_header()
    config = KimiConfig()

    # Servers with new auto-browser OAuth
    oauth_servers = {"github", "jira", "confluence", "gmail", "slack", "figma"}

    if server_name in oauth_servers:
        from .auth.providers import authenticate, AUTH_HANDLERS

        console.print(f"\n[bold cyan]>{server_name.title()} Authorization[/bold cyan]")
        console.print(f"[dim]Auto-browser mode (like Claude Code CLI)[/dim]\n")

        # Show available methods
        if server_name == "github":
            console.print("[bold]Method:[/bold] Device Flow -- auto browser + code")
            console.print("[dim]Alternative: Personal Access Token (PAT)[/dim]\n")
        elif server_name in ("jira", "confluence"):
            console.print("[bold]Method:[/bold] API Token or Official MCP OAuth")
        elif server_name == "gmail":
            console.print("[bold]Method:[/bold] Google OAuth 2.0 or npx")
        elif server_name == "slack":
            console.print("[bold]Method:[/bold] Bot Token or OAuth 2.0")
        elif server_name == "figma":
            console.print("[bold]Method:[/bold] Personal Access Token or OAuth 2.0")

        token_data = authenticate(server_name)

        if token_data:
            # Write to mcp.json if we got server config back
            if "server_config" in token_data:
                config.add_server(server_name, token_data["server_config"])
            console.print(f"\n[bold green]>{server_name.title()} is ready![/bold green]")
            console.print(f"[dim]Run 'kimi-mcp-hub list' to verify.[/dim]\n")
        else:
            console.print(f"\n[yellow]Authorization cancelled or failed.[/yellow]")
            console.print(f"[dim]Try: kimi-mcp-hub add {server_name} (manual mode)[/dim]\n")
        return

    # --- Legacy manual auth for API-key based servers ---

    if server_name == "linear":
        console.print("[bold]Linear[/bold] has two auth options:\n")
        console.print("[bold]1. Official remote MCP (OAuth 2.1):[/bold]")
        console.print("   Run [bold]kimi-mcp-hub add linear[/bold] and choose 'official-oauth' or 'official-stdio'.")
        console.print("   Then trigger the browser login from Kimi CLI with [bold]kimi mcp auth linear[/bold].\n")
        console.print("[bold]2. API key (local stdio server):[/bold]")
        console.print("   Get key from: https://linear.app/settings/api\n")

        choice = Prompt.ask("Option", choices=["api-key", "official"], default="api-key")
        if choice == "api-key":
            token = Prompt.ask("Linear API key", password=True)
            if token:
                cfg = LinearServer.get_stdio_config(token)
                config.add_server("linear", cfg)
                console.print("[green]Linear configured (API key)![/green]\n")
        else:
            cfg = LinearServer.get_official_config()
            config.add_server("linear", cfg)
            console.print("[green]Linear configured (Official OAuth).[/green]")
            console.print("[dim]   Run: kimi mcp auth linear[/dim]\n")

    elif server_name == "datadog":
        console.print("[bold]Datadog[/bold] uses API + App keys.\n")
        api_key = Prompt.ask("Datadog API key", password=True)
        app_key = Prompt.ask("Datadog App key", password=True)
        site = Prompt.ask("Datadog site", default="datadoghq.com")
        if api_key and app_key:
            cfg = DatadogServer.get_stdio_config(api_key, app_key, site)
            config.add_server("datadog", cfg)
            console.print("[green]Datadog configured![/green]\n")

    elif server_name == "hubspot":
        console.print("[bold]HubSpot[/bold] -- choose source:\n")
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
            console.print(f"[green]HubSpot configured ({src})[/green]\n")

    elif server_name == "grain":
        console.print("[bold]Grain[/bold] -- uses browser automation.\n")
        data_dir = Prompt.ask("Browser data directory", default="~/.grain-mcp/data")
        cfg = GrainServer.get_uv_config(data_dir)
        config.add_server("grain", cfg)
        console.print("[green]Grain configured![/green]\n")

    elif server_name == "perplexity":
        console.print("[bold]Perplexity[/bold] -- real-time web search.\n")
        console.print("Get free API key at: https://www.perplexity.ai/settings/api")
        token = Prompt.ask("Perplexity API key (ppx-...)", password=True)
        if token:
            cfg = PerplexityServer.get_stdio_config(token)
            config.add_server("perplexity", cfg)
            console.print("[green]Perplexity configured![/green]\n")

    elif server_name in ("postgres", "playwright", "sentry", "context7", "supabase", "chrome-devtools"):
        console.print(f"[bold]{server_name.title()}[/bold] does not require OAuth.\n")
        console.print(f"Use: [bold]kimi-mcp-hub add {server_name}[/bold] instead.\n")

    else:
        console.print(f"[red]Unknown server: {server_name}[/red]")
        console.print(f"[dim]Supported auth: {', '.join(sorted(oauth_servers))}[/dim]")
        console.print(f"[dim]API-key servers: linear, datadog, hubspot, grain, perplexity[/dim]")


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
                console.print(f"[green]{cmd[0]} found at {result.stdout.strip()}[/green]")
            else:
                console.print(f"[red]{cmd[0]} not found. Install with npm/npx.[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    elif "url" in cfg:
        console.print(f"[green]HTTP endpoint configured: {cfg['url'][:60]}[/green]")
        console.print("[dim]   Use 'kimi mcp auth {server_name}' to complete OAuth.[/dim]")


@main.command(name="import-claude")
def import_claude_cmd():
    """Import MCP servers from Claude Desktop or Claude Code."""
    print_header()
    config = KimiConfig()
    import_claude_servers(config)


@main.command()
def doctor():
    """Check system health -- node, npx, kimi CLI, docker."""
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
                table.add_row(name, f"[green]{ver}[/green]", "Found")
            else:
                table.add_row(name, "[red]Error[/red]", result.stderr[:50])
        except FileNotFoundError:
            table.add_row(name, "[red]Missing[/red]", f"Install {name}")
        except Exception as e:
            table.add_row(name, "[red]Fail[/red]", str(e)[:50])

    console.print(table)

    config = KimiConfig()
    servers = config.list_servers()
    if servers:
        console.print(f"\n[green]{len(servers)} MCP server(s) in ~/.kimi/mcp.json[/green]")
    else:
        console.print("\n[yellow]No MCP servers configured yet[/yellow]")

    skills_installed = list_installed_skills(config)
    if skills_installed:
        console.print(f"[green]{len(skills_installed)} skills in ~/.kimi/skills/[/green]")
    else:
        console.print("[yellow]No skills installed yet[/yellow]")

    memory_db = Path.home() / ".kimi" / "mcp-hub" / "memory.db"
    if memory_db.exists():
        console.print(f"[green]Memory database: {memory_db}[/green]")
    else:
        console.print("[dim]Memory not enabled[/dim]")

    console.print("\n[dim]Run [bold]kimi-mcp-hub init[/bold] to set up everything.[/dim]\n")


@main.command()
def repair():
    """Fix broken/outdated MCP server configs in ~/.kimi/mcp.json."""
    print_header()
    config = KimiConfig()
    servers = config.list_servers()

    if not servers:
        console.print("[yellow]No MCP servers configured.[/yellow]")
        return

    fixed = []

    for name, cfg in list(servers.items()):
        args = cfg.get("args", [])
        env = cfg.get("env", {})

        # Fix Slack: old @korotovsky/slack-mcp-server package
        if name == "slack" and any("@korotovsky/slack-mcp-server" in str(a) for a in args):
            console.print(f"[yellow]Fixing Slack config...[/yellow]")
            token = env.get("SLACK_TOKEN") or env.get("SLACK_BOT_TOKEN") or Prompt.ask("Slack Bot token (xoxb-...)", password=True)
            team_id = Prompt.ask("Slack Team ID (T0...)")
            new_cfg = SlackServer.get_stdio_config(token, team_id)
            config.add_server(name, new_cfg)
            fixed.append("slack")

        # Fix Supabase: old @supabase/mcp-server package
        elif name == "supabase" and any("@supabase/mcp-server" in str(a) for a in args):
            # Avoid matching the correct @supabase/mcp-server-supabase package
            if not any("@supabase/mcp-server-supabase" in str(a) for a in args):
                console.print(f"[yellow]Fixing Supabase config...[/yellow]")
                choice = Prompt.ask("Supabase mode", choices=["official-oauth", "stdio-token"], default="official-oauth")
                if choice == "official-oauth":
                    project_ref = Prompt.ask("Supabase project ref (optional)", default="")
                    read_only = Confirm.ask("Read-only mode?", default=True)
                    new_cfg = SupabaseServer.get_official_config(
                        project_ref=project_ref or None,
                        read_only=read_only,
                    )
                else:
                    console.print("Get token at: https://supabase.com/dashboard/account/tokens")
                    token = Prompt.ask("Supabase access token (sbp_...)", password=True)
                    project_ref = Prompt.ask("Supabase project ref (optional)", default="")
                    read_only = Confirm.ask("Read-only mode?", default=True)
                    new_cfg = SupabaseServer.get_stdio_config(
                        access_token=token,
                        project_ref=project_ref or None,
                        read_only=read_only,
                    )
                config.add_server(name, new_cfg)
                fixed.append("supabase")

    if fixed:
        console.print(f"\n[green]Fixed: {', '.join(fixed)}[/green]")
        console.print("[dim]Restart Kimi CLI to apply changes.[/dim]\n")
    else:
        console.print("\n[green]No broken configs found.[/green]\n")


# -- Helper functions --

def add_server_interactive(name: str, config: KimiConfig):
    """Interactive prompt to add a server."""
    cls = SERVERS[name]
    icon = getattr(cls, "icon", "")
    display = getattr(cls, "display_name", name.title())

    console.print(f"\n{display}")
    console.print(f"[dim]{cls.description}[/dim]\n")

    if name in ("jira", "confluence"):
        choice = Prompt.ask(
            "Auth method",
            choices=["official", "api-token"],
            default="official",
        )
        if choice == "official":
            cfg = JiraServer.get_oauth_config() if name == "jira" else ConfluenceServer.get_oauth_config()
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official")
        else:
            base = Prompt.ask("Base URL", default="https://yourcompany.atlassian.net")
            email = Prompt.ask("Email")
            token = Prompt.ask("API token", password=True)
            cfg = JiraServer.get_stdio_config(base, token, email) if name == "jira" else ConfluenceServer.get_stdio_config(base, token, email)
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (API token)[/green]")

    elif name == "linear":
        choice = Prompt.ask(
            "Linear mode",
            choices=["official-oauth", "official-stdio", "api-key"],
            default="official-oauth",
        )
        if choice == "official-oauth":
            cfg = LinearServer.get_official_config()
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official-oauth")
        elif choice == "official-stdio":
            cfg = LinearServer.get_official_stdio_config()
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official via mcp-remote)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name} to complete OAuth[/dim]")
        else:
            token = Prompt.ask("Linear API key (https://linear.app/settings/api)", password=True)
            cfg = LinearServer.get_stdio_config(token)
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (API key)[/green]")

    elif name == "github":
        choice = Prompt.ask(
            "Auth method",
            choices=["pat", "oauth-device"],
            default="pat",
        )
        if choice == "oauth-device":
            token_data = authenticate_github()
            if token_data and "access_token" in token_data:
                cfg = GitHubServer.get_stdio_config(token_data["access_token"])
                config.add_server(name, cfg)
                console.print(f"[green]Added {display} (OAuth device flow)[/green]")
            else:
                console.print(f"[yellow]{display} OAuth not completed.[/yellow]")
        else:
            token = Prompt.ask("GitHub PAT (https://github.com/settings/tokens)", password=True)
            cfg = GitHubServer.get_stdio_config(token)
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (PAT)[/green]")

    elif name == "slack":
        choice = Prompt.ask(
            "Token type",
            choices=["bot", "user"],
            default="bot",
        )
        token = Prompt.ask(
            "Slack token (xoxb-... for bot, xoxp-... for user)",
            password=True,
        )
        cfg = SlackServer.get_stdio_config(token, token_type=choice)
        config.add_server(name, cfg)
        console.print(f"[green]Added {display} ({choice} token)[/green]")

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
        console.print(f"[green]Added {display}[/green]")

    elif name == "figma":
        choice = Prompt.ask(
            "Mode",
            choices=["official-oauth", "official-stdio", "console-npx"],
            default="official-oauth",
        )
        if choice == "official-oauth":
            cfg = FigmaServer.get_official_config()
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official-oauth")
        elif choice == "official-stdio":
            cfg = FigmaServer.get_official_stdio_config()
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official via mcp-remote)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name} to complete OAuth[/dim]")
        else:
            token = Prompt.ask("Figma PAT (figd_...)", password=True)
            cfg = FigmaServer.get_console_config(token)
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Console)[/green]")

    elif name == "figma-context":
        token = Prompt.ask("Figma API access token (figd_...)", password=True)
        cfg = FigmaContextServer.get_stdio_config(token)
        config.add_server(name, cfg)
        console.print(f"[green]Added {display}[/green]")

    elif name == "gitlab":
        choice = Prompt.ask(
            "GitLab mode",
            choices=["official-oauth", "official-stdio", "pat-stdio"],
            default="official-oauth",
        )
        if choice == "official-oauth":
            instance_url = Prompt.ask("GitLab URL", default="https://gitlab.com")
            cfg = GitLabServer.get_official_config(instance_url)
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official-oauth")
        elif choice == "official-stdio":
            instance_url = Prompt.ask("GitLab URL", default="https://gitlab.com")
            cfg = GitLabServer.get_official_stdio_config(instance_url)
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official via mcp-remote)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name} to complete OAuth[/dim]")
        else:
            instance_url = Prompt.ask("GitLab URL", default="https://gitlab.com")
            token = Prompt.ask("GitLab Personal Access Token", password=True)
            cfg = GitLabServer.get_stdio_config(token, instance_url)
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (PAT stdio)[/green]")

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
        console.print(f"[green]Added {display} ({choice})[/green]")

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
        console.print(f"[green]Added {display} ({choice})[/green]")

    elif name == "stripe":
        choice = Prompt.ask(
            "Stripe mode",
            choices=["official-oauth", "official-stdio", "api-key", "docker"],
            default="official-oauth",
        )
        if choice == "official-oauth":
            cfg = StripeServer.get_official_config()
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official-oauth")
        elif choice == "official-stdio":
            cfg = StripeServer.get_official_stdio_config()
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official via mcp-remote)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name} to complete OAuth[/dim]")
        elif choice == "api-key":
            api_key = Prompt.ask("Stripe restricted API key (rk_...)", password=True)
            tools = Prompt.ask("Enabled tools", default="all")
            cfg = StripeServer.get_stdio_config(api_key, tools)
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (API key)[/green]")
        else:
            api_key = Prompt.ask("Stripe restricted API key (rk_...)", password=True)
            tools = Prompt.ask("Enabled tools", default="all")
            cfg = StripeServer.get_docker_config(api_key, tools)
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Docker)[/green]")

    elif name == "grain":
        data_dir = Prompt.ask("Browser data directory", default="~/.grain-mcp/data")
        cfg = GrainServer.get_uv_config(data_dir)
        config.add_server(name, cfg)
        console.print(f"[green]Added {display}[/green]")
        console.print(f"[dim]   Login via browser on first use.[/dim]")

    elif name == "chrome-devtools":
        console.print("[bold]Chrome DevTools[/bold] -- requires Node 22+ and Chrome.\n")
        if Confirm.ask("Install chrome-devtools-mcp?", default=True):
            cfg = ChromeDevToolsServer.get_stdio_config()
            config.add_server(name, cfg)
            console.print(f"[green]Added {display}[/green]")
            console.print("[dim]   Make sure Chrome is installed and Node >= 22.[/dim]")

    elif name == "desktop-commander":
        choice = Prompt.ask("Mode", choices=["npx", "docker"], default="npx")
        if choice == "npx":
            cfg = DesktopCommanderServer.get_stdio_config()
        else:
            cfg = DesktopCommanderServer.get_docker_config()
        config.add_server(name, cfg)
        console.print(f"[green]Added {display} ({choice})[/green]")
        console.print("[dim]   Warning: this server can execute arbitrary commands.[/dim]")

    elif name == "mobile":
        cfg = MobileMCPServer.get_stdio_config()
        config.add_server(name, cfg)
        console.print(f"[green]Added {display}[/green]")
        console.print("[dim]   Requires iOS Simulator/Android Emulator or a connected device.[/dim]")

    elif name == "postgres":
        dsn = Prompt.ask("PostgreSQL DSN", default="postgresql://user:pass@localhost/db")
        cfg = PostgreSQLServer.get_stdio_config(dsn)
        config.add_server(name, cfg)
        console.print(f"[green]Added {display}[/green]")

    elif name == "dbhub":
        choice = Prompt.ask("Mode", choices=["dsn", "demo", "docker"], default="dsn")
        if choice == "dsn":
            dsn = Prompt.ask("Database DSN", default="postgresql://user:pass@localhost/db")
            readonly = Confirm.ask("Read-only mode?", default=True)
            cfg = DBHubServer.get_stdio_config(dsn, readonly)
        elif choice == "docker":
            dsn = Prompt.ask("Database DSN", default="postgresql://user:pass@host.docker.internal/db")
            readonly = Confirm.ask("Read-only mode?", default=True)
            cfg = DBHubServer.get_docker_config(dsn, readonly)
        else:
            cfg = DBHubServer.get_demo_config()
        config.add_server(name, cfg)
        console.print(f"[green]Added {display} ({choice})[/green]")

    elif name == "playwright":
        console.print("[bold]Playwright[/bold] -- browser automation.\n")
        cfg = PlaywrightServer.get_stdio_config()
        config.add_server(name, cfg)
        console.print(f"[green]Added {display}[/green]")

    elif name == "sentry":
        token = Prompt.ask("Sentry Auth token", password=True)
        org = Prompt.ask("Sentry organization slug")
        cfg = SentryServer.get_stdio_config(token, org)
        config.add_server(name, cfg)
        console.print(f"[green]Added {display}[/green]")

    elif name == "context7":
        console.print("[bold]Context7[/bold] -- live library docs.\n")
        cfg = Context7Server.get_stdio_config()
        config.add_server(name, cfg)
        console.print(f"[green]Added {display}[/green]")

    elif name == "supabase":
        choice = Prompt.ask(
            "Supabase mode",
            choices=["official-oauth", "stdio-token"],
            default="official-oauth",
        )
        if choice == "official-oauth":
            project_ref = Prompt.ask("Supabase project ref (optional, e.g. abcdefghijklmn)", default="")
            read_only = Confirm.ask("Read-only mode?", default=True)
            cfg = SupabaseServer.get_official_config(
                project_ref=project_ref or None,
                read_only=read_only,
            )
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official-oauth")
        else:
            console.print("Get token at: https://supabase.com/dashboard/account/tokens")
            token = Prompt.ask("Supabase access token (sbp_...)", password=True)
            project_ref = Prompt.ask("Supabase project ref (optional)", default="")
            read_only = Confirm.ask("Read-only mode?", default=True)
            cfg = SupabaseServer.get_stdio_config(
                access_token=token,
                project_ref=project_ref or None,
                read_only=read_only,
            )
            config.add_server(name, cfg)
            console.print(f"[green]Added {display} (stdio token)[/green]")

    elif name == "perplexity":
        console.print("[bold]Perplexity[/bold] -- real-time web search with AI summaries.\n")
        console.print("Get free API key at: https://www.perplexity.ai/settings/api")
        token = Prompt.ask("Perplexity API key (ppx-...)", password=True)
        cfg = PerplexityServer.get_stdio_config(token)
        config.add_server(name, cfg)
        console.print(f"[green]Added {display}[/green]")


def _run_kimi_mcp_auth(server_name: str) -> bool:
    """Try to run `kimi mcp auth <server>` to trigger the browser popup.

    Returns True if the Kimi CLI command executed successfully.
    """
    try:
        console.print(f"[dim]Opening browser for {server_name} via Kimi CLI...[/dim]")
        result = subprocess.run(
            ["kimi", "mcp", "auth", server_name],
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _authenticate_server(name: str, method: str = "auto"):
    """Trigger browser/popup auth after a server has been added.

    For official remote MCP servers we delegate to Kimi CLI (`kimi mcp auth`).
    If Kimi CLI is missing we print the manual command.
    """
    if method in ("official", "official-oauth"):
        if not _run_kimi_mcp_auth(name):
            console.print(f"[yellow]Kimi CLI not found or auth failed.[/yellow]")
            console.print(f"[dim]   Run manually: kimi mcp auth {name}[/dim]")
    elif method == "custom-oauth":
        # Caller is responsible for invoking the provider-specific web flow.
        pass
    elif method == "oauth-device":
        # Caller is responsible for invoking the device flow.
        pass
    else:
        console.print(f"[dim]   Run: kimi mcp auth {name}[/dim]")


def install_skill(skill_name: str, config: KimiConfig, overwrite: bool | None = None):
    """Install a skill from package to ~/.kimi/skills/.

    Args:
        skill_name: Name of the skill directory inside the package.
        config: KimiConfig instance.
        overwrite: If True, always overwrite an existing install. If False,
            skip when already installed. If None (default), ask the user.
    """
    pkg_skills_dir = Path(__file__).parent / "skills" / skill_name
    user_skills_dir = config.skills_dir / skill_name

    if not pkg_skills_dir.exists():
        console.print(f"[red]Skill {skill_name} not found in package.[/red]")
        return

    if user_skills_dir.exists():
        if overwrite is False:
            console.print(f"[dim]Skill '{skill_name}' already installed, skipping.[/dim]")
            return
        if overwrite is None:
            if not Confirm.ask(f"Skill '{skill_name}' already installed. Overwrite?", default=False):
                return

    shutil.copytree(pkg_skills_dir, user_skills_dir, dirs_exist_ok=True)
    console.print(f"[green]Installed skill: {skill_name}[/green]")
    console.print(f"[dim]   Location: {user_skills_dir}[/dim]")


def list_installed_skills(config: KimiConfig) -> list:
    """Return list of installed skill names."""
    if not config.skills_dir.exists():
        return []
    return [d.name for d in config.skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]


def enable_memory(config: KimiConfig):
    """Enable persistent memory system."""
    memory_dir = Path.home() / ".kimi" / "mcp-hub"
    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_db = memory_dir / "memory.db"

    # Initialize SQLite with FTS5 using the canonical schema from memory/db.py
    MemoryDB(db_path=memory_db)

    console.print(f"[green]Memory database initialized: {memory_db}[/green]")
    console.print("[dim]   Memory will persist across sessions.[/dim]")


if __name__ == "__main__":
    main()
