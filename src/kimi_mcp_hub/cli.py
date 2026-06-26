"""Kimi MCP Hub CLI -- one-click MCP server and skills manager."""

import json
import stat
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
from .preflight import maybe_install_npx_deps
from .project import ProjectConfig, find_project_root, merge_mcp_configs, resolve_placeholders

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
    "caveman",
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

# Servers that are installed automatically during `init` if npx is available
# (no API key required, broadly useful, low risk)
AUTO_INSTALL_SERVERS = ["chrome-devtools", "context7", "playwright"]

# Optional skills are presented in category groups during `init`
OPTIONAL_SKILL_GROUPS = [
    ("Code Quality & Review", [
        "code-reviewer", "code-review", "surgical-refactoring", "tdd",
        "perf-optimization", "security-audit", "security-guidance",
    ]),
    ("Architecture & Design", [
        "api-designer", "backend-architect", "backend-typescript-architect",
        "codebase-design", "domain-modeling", "database-expert", "api-design",
    ]),
    ("DevOps & Deployment", [
        "docker-pro", "gitnexus", "resolving-merge-conflicts", "deployment-patterns",
    ]),
    ("Language / Framework", [
        "python-engineer", "laravel-engineer", "php-pro", "wp-plugin-development",
        "react-coder", "ts-coder", "ui-engineer", "ui-ux-pro-max",
    ]),
    ("Data & Migrations", ["database-migrations"]),
    ("Testing & Browser", [
        "playwright-best-practices", "chrome-devtools-skill",
    ]),
    ("Research & Automation", [
        "search-first", "regex-vs-llm-structured-text",
    ]),
    ("Productivity & Meta", [
        "memory-palace", "hindsight", "task-master", "ralph", "grill-me",
        "visual-explainer", "research-mode", "ecc",
        "skill-creator", "agent-automation-recommender", "find-skills",
        "claude-compat",
    ]),
    ("Integration", ["stripe-best-practices"]),
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
    "design-system": "Design tokens, component specs, and systematic design systems",
    "vercel-react-best-practices": "React/Next.js performance optimization",
    "web-design-guidelines": "Audit UI code against Vercel guidelines",
    "agent-browser": "Browser automation for web tasks and testing",
    # ---- Optional skills ----
    "caveman": "Ultra-compressed caveman communication mode",
    "caveman-review": "Ultra-compressed code review comments",
    "caveman-commit": "Ultra-compressed Conventional Commits messages",
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
    "surgical-refactoring": "Surgical code refactoring without behavior change",
    "stripe-best-practices": "Stripe integration best practices",
    "chrome-devtools-skill": "Chrome DevTools MCP debugging and automation",
    "playwright-best-practices": "Playwright testing best practices",
    "skill-creator": "Create and optimize agent skills",
    "agent-automation-recommender": "Recommend agent automations for codebases",
    "tdd": "Test-driven development with red-green-refactor",
    "codebase-design": "Design deep modules and testable interfaces",
    "domain-modeling": "Build domain models and ubiquitous language",
    "grill-me": "Stress-test a plan or design",
    "resolving-merge-conflicts": "Resolve git merge/rebase conflicts",
    "search-first": "Research-before-coding workflow",
    "database-migrations": "Safe database migration patterns",
    "api-design": "REST API design patterns",
    "deployment-patterns": "CI/CD and deployment best practices",
    "regex-vs-llm-structured-text": "Regex vs LLM parsing decision framework",
    "claude-compat": "Auto-load CLAUDE.md and CLAUDE.local.md at session start",
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
@click.option("--project", is_flag=True, help="Save servers to the current project config (.kimi/mcp.json) instead of global.")
def init(project: bool):
    """Interactive setup wizard for servers, skills, and memory."""
    config = KimiConfig()
    print_welcome()

    project_root = None
    if project:
        project_root = find_project_root()
        if not project_root:
            console.print("[red]No project root found.[/red]")
            console.print("[dim]Run inside a git repo or a directory with a .kimi/ folder.[/dim]")
            sys.exit(1)
        console.print(f"\n[dim]Saving MCP servers to project: {project_root}[/dim]\n")

    console.print("\n[bold green]Welcome to Kimi MCP Hub![/bold green]\n")
    console.print("This wizard will set up MCP servers, skills, and optional memory.\n")

    # Step 1: MCP Servers
    console.print("[bold]Step 1: MCP Servers[/bold] (external tools)\n")

    # Auto-install safe, no-key servers if npx is available
    npx_available = shutil.which("npx") is not None
    auto_installed = []
    existing_servers = config.list_servers()
    if project_root:
        pc = ProjectConfig(project_root)
        existing_servers.update(pc.load_mcp().get("mcpServers", {}))
    for key in AUTO_INSTALL_SERVERS:
        if key in existing_servers:
            continue
        if not npx_available:
            continue
        cls = SERVERS[key]
        cfg = cls.get_stdio_config()
        add_server_with_preflight(key, cfg, config, project_root=project_root)
        auto_installed.append(getattr(cls, "display_name", key.title()))
    if auto_installed:
        console.print(f"[green]Auto-installed:[/green] {', '.join(auto_installed)}\n")

    # Prompt for remaining servers
    for key, cls in SERVERS.items():
        if key in AUTO_INSTALL_SERVERS:
            continue
        icon = getattr(cls, "icon", "")
        name = getattr(cls, "display_name", key.title())
        if Confirm.ask(f"{icon} Add [bold]{name}[/bold]?", default=False):
            add_server_interactive(key, config, project_root=project_root)

    # Step 2: Skills
    console.print("\n[bold]Step 2: Skills[/bold] (AI behavior patterns)\n")

    # Core skills -- recommended, default=True
    console.print("[bold cyan]Core Skills (Recommended)[/bold cyan]\n")
    for key in CORE_SKILLS:
        if key in SKILLS:
            if Confirm.ask(f"  {SKILLS[key]} -- Install?", default=True):
                install_skill(key, config, overwrite=False)

    # Frontend skills -- installed as a recommended stack, default=True
    console.print("\n[bold cyan]Frontend Skills (Recommended)[/bold cyan]\n")
    frontend_desc = ", ".join(SKILLS[k] for k in FRONTEND_SKILLS if k in SKILLS)
    if Confirm.ask(
        f"Install recommended frontend stack ({len(FRONTEND_SKILLS)} skills)?",
        default=True,
    ):
        for key in FRONTEND_SKILLS:
            install_skill(key, config, overwrite=False)

    # Optional skills -- grouped by category, default=False
    console.print("\n[bold cyan]Optional Skills[/bold cyan] (pick categories)\n")
    for category, keys in OPTIONAL_SKILL_GROUPS:
        available = [k for k in keys if k in SKILLS and k not in CORE_SKILLS and k not in FRONTEND_SKILLS]
        if not available:
            continue
        if Confirm.ask(
            f"Install [bold]{category}[/bold] skills ({len(available)} skills)?",
            default=False,
        ):
            for key in available:
                install_skill(key, config, overwrite=False)

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

    project_root = find_project_root()
    if project_root:
        pc = ProjectConfig(project_root)
        project_status = f"[green]{project_root.name}[/green]" if pc.exists() else f"[dim]{project_root.name} (no .kimi/mcp.json)[/dim]"
        table.add_row("Project", project_status)

    config = KimiConfig()
    table.add_row("Memory", "[green]enabled[/green]" if config.memory_db.exists() else "[dim]disabled[/dim]")

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
@click.option("--project", is_flag=True, help="Add to the current project config (.kimi/mcp.json) instead of global.")
def add(server_name: str, project: bool):
    """Add an MCP server (jira, linear, confluence, github, slack, datadog,
    figma, gmail, hubspot, grain, chrome-devtools, postgres, playwright,
    sentry, context7, supabase, perplexity)."""
    print_header()
    config = KimiConfig()
    if server_name not in SERVERS:
        console.print(f"[red]Unknown server: {server_name}[/red]")
        console.print(f"Available: {', '.join(SERVERS.keys())}")
        sys.exit(1)

    project_root = None
    if project:
        project_root = find_project_root()
        if not project_root:
            console.print("[red]No project root found.[/red]")
            console.print("[dim]Run inside a git repo or a directory with a .kimi/ folder.[/dim]")
            sys.exit(1)
        console.print(f"[dim]Adding to project: {project_root}[/dim]\n")

    add_server_interactive(server_name, config, project_root=project_root)


@main.command()
@click.argument("server_name")
@click.option("--project", is_flag=True, help="Remove from the current project config (.kimi/mcp.json) instead of global.")
def remove(server_name: str, project: bool):
    """Remove an MCP server."""
    if project:
        project_root = find_project_root()
        if not project_root:
            console.print("[red]No project root found.[/red]")
            sys.exit(1)
        pc = ProjectConfig(project_root)
        pc.remove_server(server_name)
        console.print(f"[green]Removed {server_name} from project config[/green]")
        console.print(f"[dim]{pc.mcp_json}[/dim]")
    else:
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
    config = KimiConfig()
    if config.memory_db.exists():
        console.print(f"\n[green]Memory enabled:[/green] {config.memory_db}")
    else:
        console.print(f"\n[dim]Memory not enabled. Run [bold]kimi-mcp-hub init[/bold] to enable.[/dim]")

    console.print("\n[dim]In Kimi CLI, type [bold]/mcp[/bold] for tools, [bold]/skills[/bold] for skills.[/dim]\n")


@main.command()
@click.argument("skill_name")
def install_skill_cmd(skill_name: str):
    """Install a skill into ~/.kimi-code/skills/."""
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


@main.command(name="claude-compat")
def claude_compat_cmd():
    """Patch ~/.kimi-code/AGENTS.md to auto-load CLAUDE.md and CLAUDE.local.md."""
    print_header()

    MARKER_START = "<!-- claude-compat -->"
    MARKER_END = "<!-- /claude-compat -->"
    PATCH = f"""\n{MARKER_START}\n## Claude Code Compatibility — Auto-load CLAUDE.md\n\nAt the start of every session, before doing anything else, check for the\nfollowing files in the current working directory (project root):\n\n| Priority | File | Purpose |\n|----------|------|---------|\n| 1 | `CLAUDE.local.md` | Local overrides — machine-specific, gitignored |\n| 2 | `CLAUDE.md` | Project-wide instructions — committed to the repo |\n\n**Discovery logic (in order):**\n1. `<cwd>/CLAUDE.local.md` — read if exists\n2. `<cwd>/CLAUDE.md` — read if exists\n3. If neither exists, skip silently\n\n**How to apply the content:**\n- Treat both files as authoritative project instructions, equivalent to `AGENTS.md`.\n- `CLAUDE.local.md` takes precedence over `CLAUDE.md` when they conflict.\n- Never modify these files unless the user explicitly asks.\n- If a file is found, print one line: `📋 Loaded <filename> (N lines)`\n{MARKER_END}\n"""

    agents_md = Path.home() / ".kimi-code" / "AGENTS.md"

    existing = ""
    if agents_md.exists():
        existing = agents_md.read_text(encoding="utf-8")

    if MARKER_START in existing:
        console.print("[yellow]⚠️  claude-compat patch already present in ~/.kimi-code/AGENTS.md[/yellow]")
        console.print("[dim]Nothing to do. To re-apply, remove the <!-- claude-compat --> block first.[/dim]")
        return

    console.print("\n[bold cyan]Claude Code Compatibility Patch[/bold cyan]\n")
    console.print("This will append the following block to [bold]~/.kimi-code/AGENTS.md[/bold]:\n")
    console.print(Panel(
        PATCH.strip(),
        title="Patch preview",
        border_style="dim",
        padding=(1, 2),
    ))

    if not Confirm.ask("\nDodaj go ova vo ~/.kimi-code/AGENTS.md?", default=True):
        console.print("[dim]Cancelled.[/dim]")
        return

    agents_md.parent.mkdir(parents=True, exist_ok=True)
    with open(agents_md, "a", encoding="utf-8") as f:
        f.write(PATCH)

    console.print("\n[green]✅ Patch applied to ~/.kimi-code/AGENTS.md[/green]")
    console.print("[dim]Kimi will now auto-read CLAUDE.local.md and CLAUDE.md at session start.[/dim]")
    console.print("[dim]Restart Kimi CLI for the change to take effect.[/dim]\n")


@main.command()
@click.argument("server_name")
@click.option("--project", is_flag=True, help="Save to the current project config (.kimi/mcp.json) instead of global.")
def auth(server_name: str, project: bool):
    """Authorize an MCP server with auto browser open (OAuth/Device Flow)."""
    print_header()
    config = KimiConfig()

    project_root = None
    if project:
        project_root = find_project_root()
        if not project_root:
            console.print("[red]No project root found.[/red]")
            sys.exit(1)
        console.print(f"[dim]Saving to project: {project_root}[/dim]\n")

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
                add_server_with_preflight(server_name, token_data["server_config"], config, project_root=project_root)
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
                add_server_with_preflight("linear", cfg, config, project_root=project_root)
                console.print("[green]Linear configured (API key)![/green]\n")
        else:
            cfg = LinearServer.get_official_config()
            add_server_with_preflight("linear", cfg, config, project_root=project_root)
            console.print("[green]Linear configured (Official OAuth).[/green]")
            console.print("[dim]   Run: kimi mcp auth linear[/dim]\n")

    elif server_name == "datadog":
        console.print("[bold]Datadog[/bold] uses API + App keys.\n")
        api_key = Prompt.ask("Datadog API key", password=True)
        app_key = Prompt.ask("Datadog App key", password=True)
        if api_key and app_key:
            cfg = DatadogServer.get_official_config(api_key, app_key)
            add_server_with_preflight("datadog", cfg, config, project_root=project_root)
            console.print("[green]Datadog configured (official remote MCP).[/green]\n")

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
            add_server_with_preflight("hubspot", cfg, config, project_root=project_root)
            console.print(f"[green]HubSpot configured ({src})[/green]\n")

    elif server_name == "grain":
        console.print("[bold]Grain[/bold] -- uses browser automation.\n")
        data_dir = Prompt.ask("Browser data directory", default="~/.grain-mcp/data")
        cfg = GrainServer.get_uv_config(data_dir)
        add_server_with_preflight("grain", cfg, config, project_root=project_root)
        console.print("[green]Grain configured![/green]\n")

    elif server_name == "perplexity":
        console.print("[bold]Perplexity[/bold] -- real-time web search.\n")
        console.print("Get free API key at: https://www.perplexity.ai/settings/api")
        token = Prompt.ask("Perplexity API key (ppx-...)", password=True)
        if token:
            cfg = PerplexityServer.get_stdio_config(token)
            add_server_with_preflight("perplexity", cfg, config, project_root=project_root)
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

    # Permission check / fix for sensitive files
    if sys.platform != "win32":
        config = KimiConfig()
        fixed_files = []
        for sensitive_path in (config.mcp_json, config.tokens_file, config.memory_db):
            if sensitive_path.exists():
                try:
                    mode = sensitive_path.stat().st_mode
                    if mode & stat.S_IRWXG or mode & stat.S_IRWXO:
                        sensitive_path.chmod(0o600)
                        fixed_files.append(str(sensitive_path))
                except OSError:
                    pass
        if fixed_files:
            console.print("\n[yellow]Fixed permissions (chmod 600):[/yellow]")
            for fp in fixed_files:
                console.print(f"  {fp}")

    config = KimiConfig()
    servers = config.list_servers()
    if servers:
        console.print(f"\n[green]{len(servers)} MCP server(s) in ~/.kimi-code/mcp.json[/green]")
    else:
        console.print("\n[yellow]No MCP servers configured yet[/yellow]")

    skills_installed = list_installed_skills(config)
    if skills_installed:
        console.print(f"[green]{len(skills_installed)} skills in ~/.kimi-code/skills/[/green]")
    else:
        console.print("[yellow]No skills installed yet[/yellow]")

    if config.memory_db.exists():
        console.print(f"[green]Memory database: {config.memory_db}[/green]")
    else:
        console.print("[dim]Memory not enabled[/dim]")

    console.print("\n[dim]Run [bold]kimi-mcp-hub init[/bold] to set up everything.[/dim]\n")


@main.command()
def repair():
    """Fix broken/outdated MCP server configs in ~/.kimi-code/mcp.json."""
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
            add_server_with_preflight(name, new_cfg, config)
            fixed.append("slack")

        # Fix Datadog: old Docker/uvx configs -> official remote
        elif name == "datadog" and (cfg.get("command") in ("docker", "uvx") or "magistersart" in str(args)):
            console.print("[yellow]Fixing Datadog config to official remote MCP...[/yellow]")
            api_key = Prompt.ask("Datadog API key", password=True)
            app_key = Prompt.ask("Datadog App key", password=True)
            if api_key and app_key:
                new_cfg = DatadogServer.get_official_config(api_key, app_key)
                add_server_with_preflight(name, new_cfg, config)
                fixed.append("datadog")

        # Fix Perplexity: old @perplexityai/mcp-server-perplexity package
        elif name == "perplexity" and any("@perplexityai/mcp-server-perplexity" in str(a) for a in args):
            console.print("[yellow]Fixing Perplexity config...[/yellow]")
            token = env.get("PERPLEXITY_API_KEY") or Prompt.ask("Perplexity API key (ppx-...)", password=True)
            if token:
                new_cfg = PerplexityServer.get_stdio_config(token)
                add_server_with_preflight(name, new_cfg, config)
                fixed.append("perplexity")

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
                add_server_with_preflight(name, new_cfg, config)
                fixed.append("supabase")

    if fixed:
        console.print(f"\n[green]Fixed: {', '.join(fixed)}[/green]")
        console.print("[dim]Restart Kimi CLI to apply changes.[/dim]\n")
    else:
        console.print("\n[green]No broken configs found.[/green]\n")


@main.command()
@click.argument("project_path", required=False, type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
def sync(project_path: Path | None):
    """Merge project-level .kimi/mcp.json into ~/.kimi/mcp.json.

    When run inside a project (git root or directory with .kimi/), reads the
    project's MCP config and environment file, resolves ${VAR} placeholders,
    and writes the merged result to the global Kimi config.
    """
    print_header()
    config = KimiConfig()

    start_dir = project_path or Path.cwd()
    project_root = find_project_root(start_dir)
    if not project_root:
        console.print("[yellow]No project root found.[/yellow]")
        console.print("[dim]Run inside a git repo or a directory with a .kimi/ folder.[/dim]")
        sys.exit(1)

    pc = ProjectConfig(project_root)
    if not pc.exists():
        console.print(f"[yellow]No {pc.mcp_json} found.[/yellow]")
        console.print("[dim]Run 'kimi-mcp-hub add --project <server>' to create one.[/dim]")
        sys.exit(1)

    global_cfg = config.load_mcp()
    project_cfg = pc.load_mcp()
    env = pc.load_env()
    resolved_cfg = resolve_placeholders(project_cfg, env)
    merged_cfg = merge_mcp_configs(global_cfg, resolved_cfg)
    config.save_mcp(merged_cfg)

    project_servers = resolved_cfg.get("mcpServers", {})
    if project_servers:
        console.print(f"\n[green]Synced {len(project_servers)} project MCP server(s)[/green]")
        for name in project_servers:
            console.print(f"  [cyan]{name}[/cyan]")
    else:
        console.print("\n[yellow]Project config exists but contains no servers.[/yellow]")

    console.print(f"\n[dim]Project:[/dim] {project_root}")
    console.print(f"[dim]Global config updated:[/dim] {config.mcp_json}\n")


# -- Helper functions --

def add_server_with_preflight(
    name: str,
    cfg: dict,
    config: KimiConfig,
    project_root: Path | None = None,
):
    """Add a server after prompting to install any missing npx packages."""
    maybe_install_npx_deps(cfg, console)
    if project_root:
        pc = ProjectConfig(project_root)
        pc.add_server(name, cfg)
        console.print(f"[dim]Saved to {pc.mcp_json}[/dim]")
    else:
        add_server_with_preflight(name, cfg, config, project_root=project_root)


def add_server_interactive(
    name: str,
    config: KimiConfig,
    project_root: Path | None = None,
):
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
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official")
        else:
            base = Prompt.ask("Base URL", default="https://yourcompany.atlassian.net")
            email = Prompt.ask("Email")
            token = Prompt.ask("API token", password=True)
            cfg = JiraServer.get_stdio_config(base, token, email) if name == "jira" else ConfluenceServer.get_stdio_config(base, token, email)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (API token)[/green]")

    elif name == "linear":
        choice = Prompt.ask(
            "Linear mode",
            choices=["official-oauth", "official-stdio", "api-key"],
            default="official-oauth",
        )
        if choice == "official-oauth":
            cfg = LinearServer.get_official_config()
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official-oauth")
        elif choice == "official-stdio":
            cfg = LinearServer.get_official_stdio_config()
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official via mcp-remote)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name} to complete OAuth[/dim]")
        else:
            token = Prompt.ask("Linear API key (https://linear.app/settings/api)", password=True)
            cfg = LinearServer.get_stdio_config(token)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
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
                add_server_with_preflight(name, cfg, config, project_root=project_root)
                console.print(f"[green]Added {display} (OAuth device flow)[/green]")
            else:
                console.print(f"[yellow]{display} OAuth not completed.[/yellow]")
        else:
            token = Prompt.ask("GitHub PAT (https://github.com/settings/tokens)", password=True)
            cfg = GitHubServer.get_stdio_config(token)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
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
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display} ({choice} token)[/green]")

    elif name == "datadog":
        api_key = Prompt.ask("Datadog API key", password=True)
        app_key = Prompt.ask("Datadog App key", password=True)
        if api_key and app_key:
            cfg = DatadogServer.get_official_config(api_key, app_key)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (official remote MCP)[/green]")

    elif name == "figma":
        choice = Prompt.ask(
            "Mode",
            choices=["official-oauth", "official-stdio", "console-npx"],
            default="official-oauth",
        )
        if choice == "official-oauth":
            cfg = FigmaServer.get_official_config()
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official-oauth")
        elif choice == "official-stdio":
            cfg = FigmaServer.get_official_stdio_config()
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official via mcp-remote)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name} to complete OAuth[/dim]")
        else:
            token = Prompt.ask("Figma PAT (figd_...)", password=True)
            cfg = FigmaServer.get_console_config(token)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Console)[/green]")

    elif name == "figma-context":
        token = Prompt.ask("Figma API access token (figd_...)", password=True)
        cfg = FigmaContextServer.get_stdio_config(token)
        add_server_with_preflight(name, cfg, config, project_root=project_root)
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
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official-oauth")
        elif choice == "official-stdio":
            instance_url = Prompt.ask("GitLab URL", default="https://gitlab.com")
            cfg = GitLabServer.get_official_stdio_config(instance_url)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official via mcp-remote)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name} to complete OAuth[/dim]")
        else:
            instance_url = Prompt.ask("GitLab URL", default="https://gitlab.com")
            token = Prompt.ask("GitLab Personal Access Token", password=True)
            cfg = GitLabServer.get_stdio_config(token, instance_url)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
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
        add_server_with_preflight(name, cfg, config, project_root=project_root)
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
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display} ({choice})[/green]")

    elif name == "stripe":
        choice = Prompt.ask(
            "Stripe mode",
            choices=["official-oauth", "official-stdio", "api-key", "docker"],
            default="official-oauth",
        )
        if choice == "official-oauth":
            cfg = StripeServer.get_official_config()
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official-oauth")
        elif choice == "official-stdio":
            cfg = StripeServer.get_official_stdio_config()
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official via mcp-remote)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name} to complete OAuth[/dim]")
        elif choice == "api-key":
            api_key = Prompt.ask("Stripe restricted API key (rk_...)", password=True)
            tools = Prompt.ask("Enabled tools", default="all")
            cfg = StripeServer.get_stdio_config(api_key, tools)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (API key)[/green]")
        else:
            api_key = Prompt.ask("Stripe restricted API key (rk_...)", password=True)
            tools = Prompt.ask("Enabled tools", default="all")
            cfg = StripeServer.get_docker_config(api_key, tools)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Docker)[/green]")

    elif name == "grain":
        data_dir = Prompt.ask("Browser data directory", default="~/.grain-mcp/data")
        cfg = GrainServer.get_uv_config(data_dir)
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display}[/green]")
        console.print(f"[dim]   Login via browser on first use.[/dim]")

    elif name == "chrome-devtools":
        console.print("[bold]Chrome DevTools[/bold] -- requires Node 22+ and Chrome.\n")
        if Confirm.ask("Install chrome-devtools-mcp?", default=True):
            cfg = ChromeDevToolsServer.get_stdio_config()
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display}[/green]")
            console.print("[dim]   Make sure Chrome is installed and Node >= 22.[/dim]")

    elif name == "desktop-commander":
        choice = Prompt.ask("Mode", choices=["npx", "docker"], default="npx")
        if choice == "npx":
            cfg = DesktopCommanderServer.get_stdio_config()
        else:
            cfg = DesktopCommanderServer.get_docker_config()
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display} ({choice})[/green]")
        console.print("[dim]   Warning: this server can execute arbitrary commands.[/dim]")

    elif name == "mobile":
        cfg = MobileMCPServer.get_stdio_config()
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display}[/green]")
        console.print("[dim]   Requires iOS Simulator/Android Emulator or a connected device.[/dim]")

    elif name == "postgres":
        dsn = Prompt.ask("PostgreSQL DSN", default="postgresql://user:pass@localhost/db")
        cfg = PostgreSQLServer.get_stdio_config(dsn)
        add_server_with_preflight(name, cfg, config, project_root=project_root)
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
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display} ({choice})[/green]")

    elif name == "playwright":
        console.print("[bold]Playwright[/bold] -- browser automation.\n")
        cfg = PlaywrightServer.get_stdio_config()
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display}[/green]")

    elif name == "sentry":
        token = Prompt.ask("Sentry Auth token", password=True)
        org = Prompt.ask("Sentry organization slug")
        cfg = SentryServer.get_stdio_config(token, org)
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display}[/green]")

    elif name == "context7":
        console.print("[bold]Context7[/bold] -- live library docs.\n")
        cfg = Context7Server.get_stdio_config()
        add_server_with_preflight(name, cfg, config, project_root=project_root)
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
            add_server_with_preflight(name, cfg, config, project_root=project_root)
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
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (stdio token)[/green]")

    elif name == "perplexity":
        console.print("[bold]Perplexity[/bold] -- real-time web search with AI summaries.\n")
        console.print("Get free API key at: https://www.perplexity.ai/settings/api")
        token = Prompt.ask("Perplexity API key (ppx-...)", password=True)
        cfg = PerplexityServer.get_stdio_config(token)
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display}[/green]")


def _authenticate_server(name: str, method: str = "auto"):
    """Tell the user how to trigger browser/popup auth after a server is added.

    Official remote MCP servers must be authorized from *inside* Kimi CLI so the
    popup is attached to the active session. Running `kimi mcp auth` from a
    separate terminal does not open the UI popup.
    """
    if method in ("official", "official-oauth"):
        console.print("\n[bold]Next step:[/bold] restart Kimi CLI, then run:")
        console.print(f"  [cyan]/mcp-config login {name}[/cyan]")
        console.print("   or")
        console.print(f"  [cyan]kimi mcp auth {name}[/cyan]")
        console.print("[dim]This will open the browser OAuth popup.[/dim]\n")
    elif method == "custom-oauth":
        # Caller is responsible for invoking the provider-specific web flow.
        pass
    elif method == "oauth-device":
        # Caller is responsible for invoking the device flow.
        pass
    else:
        console.print(f"[dim]   Run: kimi mcp auth {name}[/dim]")


def install_skill(skill_name: str, config: KimiConfig, overwrite: bool | None = None):
    """Install a skill from package to ~/.kimi-code/skills/.

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
    config.memory_db.parent.mkdir(parents=True, exist_ok=True)

    # Initialize SQLite with FTS5 using the canonical schema from memory/db.py
    MemoryDB(db_path=config.memory_db)

    console.print(f"[green]Memory database initialized: {config.memory_db}[/green]")
    console.print("[dim]   Memory will persist across sessions.[/dim]")


if __name__ == "__main__":
    main()
