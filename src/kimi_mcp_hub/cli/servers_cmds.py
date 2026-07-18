"""MCP server commands: init, add, remove, list, auth, test, repair, import, sync."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import click
from rich import box
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..auth.providers import authenticate
from ..config import KimiConfig
from ..i18n import _
from ..import_claude import import_claude_servers
from ..project import (
    ProjectConfig,
    find_project_root,
    merge_mcp_configs,
    resolve_placeholders,
)
from ..registry import (
    AUTO_INSTALL_SERVERS,
    CORE_SKILLS,
    FRONTEND_SKILLS,
    OPTIONAL_SKILL_GROUPS,
    SERVERS,
    SKILLS,
)
from ..servers import (
    DatadogServer,
    GrainServer,
    HubSpotServer,
    LinearServer,
    PerplexityServer,
    SlackServer,
    SupabaseServer,
)
from .base import (
    _confirm,
    _resolve_project_root,
    main,
    print_header,
    print_welcome,
)
from .common import console
from .helpers import (
    add_server_interactive,
    add_server_with_preflight,
    enable_memory,
    install_skill,
    list_installed_skills,
)
from .skills_cmds import apply_claude_compat_patch


@main.command()
@click.option(
    "--project",
    is_flag=True,
    help="Save servers to the current project config (.kimi/mcp.json) instead of global. Default when .kimi/ exists.",
)
@click.option(
    "--global",
    "global_",
    is_flag=True,
    help="Save servers to the global config (~/.kimi-code/mcp.json) even inside a project.",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Non-interactive mode: accept defaults, auto-install core + frontend skills, enable memory, and apply claude-compat.",
)
def init(project: bool, global_: bool, yes: bool):
    """Interactive setup wizard for servers, skills, and memory."""
    config = KimiConfig()
    print_welcome()

    project_root = _resolve_project_root(project, global_)
    if project_root:
        console.print(
            _("\n[dim]Saving MCP servers to project: {root}[/dim]\n").format(
                root=project_root
            )
        )

    console.print(_("\n[bold green]Welcome to Kimi MCP Hub![/bold green]\n"))
    console.print(
        _("This wizard will set up MCP servers, skills, and optional memory.\n")
    )

    # Step 1: MCP Servers
    console.print(_("[bold]Step 1: MCP Servers[/bold] (external tools)\n"))

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
        add_server_with_preflight(key, cfg, config, project_root=project_root, assume_yes=yes)
        auto_installed.append(getattr(cls, "display_name", key.title()))
    if auto_installed:
        console.print(
            _("[green]Auto-installed:[/green] {names}\n").format(
                names=", ".join(auto_installed)
            )
        )

    # Prompt for remaining servers (skipped in non-interactive mode)
    if not yes:
        for key, cls in SERVERS.items():
            if key in AUTO_INSTALL_SERVERS:
                continue
            icon = getattr(cls, "icon", "")
            name = getattr(cls, "display_name", key.title())
            if Confirm.ask(
                _("{icon} Add [bold]{name}[/bold]?").format(icon=icon, name=name),
                default=False,
            ):
                add_server_interactive(key, config, project_root=project_root)
    else:
        console.print(
            _("[dim]Skipping interactive server selection in --yes mode.[/dim]")
        )

    # Step 2: Skills
    console.print(_("\n[bold]Step 2: Skills[/bold] (AI behavior patterns)\n"))

    # Core skills -- recommended, default=True
    console.print(_("[bold cyan]Core Skills (Recommended)[/bold cyan]\n"))
    for key in CORE_SKILLS:
        if key in SKILLS:
            if _confirm(
                _("  {skill} -- Install?").format(skill=SKILLS[key]),
                default=True,
                yes=yes,
            ):
                install_skill(key, config, overwrite=False)

    # Frontend skills -- installed as a recommended stack, default=True
    console.print(_("\n[bold cyan]Frontend Skills (Recommended)[/bold cyan]\n"))
    if _confirm(
        _("Install recommended frontend stack ({n} skills)?").format(
            n=len(FRONTEND_SKILLS)
        ),
        default=True,
        yes=yes,
    ):
        for key in FRONTEND_SKILLS:
            install_skill(key, config, overwrite=False)

    # Optional skills -- grouped by category, default=False
    console.print(_("\n[bold cyan]Optional Skills[/bold cyan] (pick categories)\n"))
    for category, keys in OPTIONAL_SKILL_GROUPS:
        available = [
            k
            for k in keys
            if k in SKILLS and k not in CORE_SKILLS and k not in FRONTEND_SKILLS
        ]
        if not available:
            continue
        if _confirm(
            _("Install [bold]{category}[/bold] skills ({n} skills)?").format(
                category=category, n=len(available)
            ),
            default=False,
            yes=yes,
        ):
            for key in available:
                install_skill(key, config, overwrite=False)

    # Step 3: Memory
    console.print(_("\n[bold]Step 3: Persistent Memory[/bold]\n"))
    if _confirm(
        _("Enable persistent memory across sessions?"), default=True, yes=yes
    ):
        enable_memory(config)

    # Auto-apply claude-compat patch in non-interactive mode
    if yes:
        console.print(_("\n[dim]Auto-applying claude-compat patch...[/dim]"))
        apply_claude_compat_patch(yes=True)

    console.print(_("\n[bold green]Setup complete![/bold green]"))
    console.print(_("Run [bold]kimi[/bold] and type:"))
    console.print(_("  [bold]/mcp[/bold]    -- see your tools"))
    console.print(_("  [bold]/skills[/bold] -- see installed skills"))
    console.print(
        _("\n[dim]Type [bold]kimi-mcp-hub list[/bold] to see everything.[/dim]\n")
    )


@main.command(
    help="Add an MCP server. Available: " + ", ".join(sorted(SERVERS)) + "."
)
@click.argument("server_name")
@click.option(
    "--project",
    is_flag=True,
    help="Add to the current project config (.kimi/mcp.json) instead of global. Default when .kimi/ exists.",
)
@click.option(
    "--global",
    "global_",
    is_flag=True,
    help="Add to the global config (~/.kimi-code/mcp.json) even inside a project.",
)
def add(server_name: str, project: bool, global_: bool):
    """Add an MCP server."""
    print_header()
    config = KimiConfig()
    if server_name not in SERVERS:
        console.print(_("[red]Unknown server: {name}[/red]").format(name=server_name))
        console.print(_("Available: {names}").format(names=", ".join(SERVERS.keys())))
        sys.exit(1)

    project_root = _resolve_project_root(project, global_)
    if project_root:
        console.print(_("[dim]Adding to project: {root}[/dim]\n").format(root=project_root))

    add_server_interactive(server_name, config, project_root=project_root)


@main.command()
@click.argument("server_name")
@click.option(
    "--project",
    is_flag=True,
    help="Remove from the current project config (.kimi/mcp.json) instead of global. Default when .kimi/ exists.",
)
@click.option(
    "--global",
    "global_",
    is_flag=True,
    help="Remove from the global config (~/.kimi-code/mcp.json) even inside a project.",
)
def remove(server_name: str, project: bool, global_: bool):
    """Remove an MCP server."""
    project_root = _resolve_project_root(project, global_)
    if project_root:
        pc = ProjectConfig(project_root)
        pc.remove_server(server_name)
        console.print(
            _("[green]Removed {name} from project config[/green]").format(
                name=server_name
            )
        )
        console.print(f"[dim]{pc.mcp_json}[/dim]")
    else:
        config = KimiConfig()
        config.remove_server(server_name)
        console.print(_("[green]Removed {name}[/green]").format(name=server_name))


@main.command()
def list():
    """List all configured MCP servers, skills, and memory status."""
    print_header()
    config = KimiConfig()

    # Servers
    servers = config.list_servers()
    if servers:
        table = Table(title=_("Configured MCP Servers"), box=box.ROUNDED)
        table.add_column(_("Server"), style="cyan", no_wrap=True)
        table.add_column(_("Type"), style="magenta")
        table.add_column(_("Tools"), style="green")
        for name, cfg in servers.items():
            transport = cfg.get("transport", "stdio")
            if "command" in cfg:
                transport = f"stdio ({cfg['command']})"
            elif "url" in cfg:
                transport = f"http ({cfg['url'][:40]}...)"
            tool_count = "?"
            if name in SERVERS:
                tool_count = _("{n} tools").format(n=len(SERVERS[name].get_tools()))
            table.add_row(name, transport, tool_count)
        console.print(table)
    else:
        console.print(_("[yellow]No MCP servers configured.[/yellow]"))
        console.print(
            _("Run [bold]kimi-mcp-hub add <server>[/bold] or [bold]kimi-mcp-hub init[/bold].\n")
        )

    # Skills
    skills_installed = list_installed_skills(config)
    if skills_installed:
        console.print(
            _("\n[green]{n} skills installed:[/green]").format(n=len(skills_installed))
        )
        for s in skills_installed:
            desc = SKILLS.get(s, "")
            console.print(f"  [cyan]{s}[/cyan] {desc}")
    else:
        console.print(_("\n[yellow]No skills installed.[/yellow]"))

    # Memory
    if config.memory_db.exists():
        console.print(
            _("\n[green]Memory enabled:[/green] {path}").format(path=config.memory_db)
        )
    else:
        console.print(
            _("\n[dim]Memory not enabled. Run [bold]kimi-mcp-hub init[/bold] to enable.[/dim]")
        )

    console.print(
        _("\n[dim]In Kimi CLI, type [bold]/mcp[/bold] for tools, [bold]/skills[/bold] for skills.[/dim]\n")
    )


@main.command()
@click.argument("server_name")
@click.option(
    "--project",
    is_flag=True,
    help="Save to the current project config (.kimi/mcp.json) instead of global. Default when .kimi/ exists.",
)
@click.option(
    "--global",
    "global_",
    is_flag=True,
    help="Save to the global config (~/.kimi-code/mcp.json) even inside a project.",
)
def auth(server_name: str, project: bool, global_: bool):
    """Authorize an MCP server with auto browser open (OAuth/Device Flow)."""
    print_header()
    config = KimiConfig()

    project_root = _resolve_project_root(project, global_)
    if project_root:
        console.print(f"[dim]Saving to project: {project_root}[/dim]\n")

    # Servers with new auto-browser OAuth
    oauth_servers = {"github", "jira", "confluence", "gmail", "slack", "figma"}

    if server_name in oauth_servers:
        console.print(f"\n[bold cyan]>{server_name.title()} Authorization[/bold cyan]")
        console.print("[dim]Auto-browser mode (like Claude Code CLI)[/dim]\n")

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
                add_server_with_preflight(
                    server_name,
                    token_data["server_config"],
                    config,
                    project_root=project_root,
                )
            console.print(
                f"\n[bold green]>{server_name.title()} is ready![/bold green]"
            )
            console.print("[dim]Run 'kimi-mcp-hub list' to verify.[/dim]\n")
        else:
            console.print("\n[yellow]Authorization cancelled or failed.[/yellow]")
            console.print(
                f"[dim]Try: kimi-mcp-hub add {server_name} (manual mode)[/dim]\n"
            )
        return

    # --- Legacy manual auth for API-key based servers ---

    if server_name == "linear":
        console.print("[bold]Linear[/bold] has two auth options:\n")
        console.print("[bold]1. Official remote MCP (OAuth 2.1):[/bold]")
        console.print(
            "   Run [bold]kimi-mcp-hub add linear[/bold] and choose 'official-oauth' or 'official-stdio'."
        )
        console.print(
            "   Then trigger the browser login from Kimi CLI with [bold]kimi mcp auth linear[/bold].\n"
        )
        console.print("[bold]2. API key (local stdio server):[/bold]")
        console.print("   Get key from: https://linear.app/settings/api\n")

        choice = Prompt.ask(
            "Option", choices=["api-key", "official"], default="api-key"
        )
        if choice == "api-key":
            token = Prompt.ask("Linear API key", password=True)
            if token:
                cfg = LinearServer.get_stdio_config(token)
                add_server_with_preflight(
                    "linear", cfg, config, project_root=project_root
                )
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
            add_server_with_preflight(
                "perplexity", cfg, config, project_root=project_root
            )
            console.print("[green]Perplexity configured![/green]\n")

    elif server_name in (
        "postgres",
        "playwright",
        "sentry",
        "context7",
        "supabase",
        "chrome-devtools",
    ):
        console.print(f"[bold]{server_name.title()}[/bold] does not require OAuth.\n")
        console.print(f"Use: [bold]kimi-mcp-hub add {server_name}[/bold] instead.\n")

    else:
        console.print(f"[red]Unknown server: {server_name}[/red]")
        console.print(f"[dim]Supported auth: {', '.join(sorted(oauth_servers))}[/dim]")
        console.print(
            "[dim]API-key servers: linear, datadog, hubspot, grain, perplexity[/dim]"
        )


@main.command()
@click.argument("server_name")
def test(server_name: str):
    """Check if a configured MCP server's binary or HTTP endpoint is present."""
    config = KimiConfig()
    servers = config.list_servers()
    if server_name not in servers:
        console.print(_("[red]{name} not configured[/red]").format(name=server_name))
        sys.exit(1)

    console.print(_("[bold]Testing {name}...[/bold]").format(name=server_name))
    cfg = servers[server_name]
    if "command" in cfg:
        cmd = [cfg["command"]] + cfg.get("args", [])
        found = shutil.which(cmd[0])
        if found:
            console.print(_("[green]{cmd} found at {path}[/green]").format(cmd=cmd[0], path=found))
        else:
            console.print(
                _("[red]{cmd} not found. Install with npm/npx.[/red]").format(cmd=cmd[0])
            )
            sys.exit(1)
    elif "url" in cfg:
        console.print(
            _("[green]HTTP endpoint configured: {url}[/green]").format(url=cfg["url"][:60])
        )
        console.print(
            _("[dim]   Use 'kimi mcp auth {name}' to complete OAuth.[/dim]").format(
                name=server_name
            )
        )


@main.command(name="import-claude")
def import_claude_cmd():
    """Import MCP servers from Claude Desktop or Claude Code."""
    print_header()
    config = KimiConfig()
    import_claude_servers(config)


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
        if name == "slack" and any(
            "@korotovsky/slack-mcp-server" in str(a) for a in args
        ):
            console.print("[yellow]Fixing Slack config...[/yellow]")
            token = (
                env.get("SLACK_TOKEN")
                or env.get("SLACK_BOT_TOKEN")
                or Prompt.ask("Slack Bot token (xoxb-...)", password=True)
            )
            team_id = Prompt.ask("Slack Team ID (T0...)")
            new_cfg = SlackServer.get_stdio_config(token, team_id)
            add_server_with_preflight(name, new_cfg, config)
            fixed.append("slack")

        # Fix Datadog: old Docker/uvx configs -> official remote
        elif name == "datadog" and (
            cfg.get("command") in ("docker", "uvx") or "magistersart" in str(args)
        ):
            console.print(
                "[yellow]Fixing Datadog config to official remote MCP...[/yellow]"
            )
            api_key = Prompt.ask("Datadog API key", password=True)
            app_key = Prompt.ask("Datadog App key", password=True)
            if api_key and app_key:
                new_cfg = DatadogServer.get_official_config(api_key, app_key)
                add_server_with_preflight(name, new_cfg, config)
                fixed.append("datadog")

        # Fix Perplexity: old @perplexityai/mcp-server-perplexity package
        elif name == "perplexity" and any(
            "@perplexityai/mcp-server-perplexity" in str(a) for a in args
        ):
            console.print("[yellow]Fixing Perplexity config...[/yellow]")
            token = env.get("PERPLEXITY_API_KEY") or Prompt.ask(
                "Perplexity API key (ppx-...)", password=True
            )
            if token:
                new_cfg = PerplexityServer.get_stdio_config(token)
                add_server_with_preflight(name, new_cfg, config)
                fixed.append("perplexity")

        # Fix Supabase: old @supabase/mcp-server package
        elif name == "supabase" and any("@supabase/mcp-server" in str(a) for a in args):
            # Avoid matching the correct @supabase/mcp-server-supabase package
            if not any("@supabase/mcp-server-supabase" in str(a) for a in args):
                console.print("[yellow]Fixing Supabase config...[/yellow]")
                choice = Prompt.ask(
                    "Supabase mode",
                    choices=["official-oauth", "stdio-token"],
                    default="official-oauth",
                )
                if choice == "official-oauth":
                    project_ref = Prompt.ask(
                        "Supabase project ref (optional)", default=""
                    )
                    read_only = Confirm.ask("Read-only mode?", default=True)
                    new_cfg = SupabaseServer.get_official_config(
                        project_ref=project_ref or None,
                        read_only=read_only,
                    )
                else:
                    console.print(
                        "Get token at: https://supabase.com/dashboard/account/tokens"
                    )
                    token = Prompt.ask("Supabase access token (sbp_...)", password=True)
                    project_ref = Prompt.ask(
                        "Supabase project ref (optional)", default=""
                    )
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
@click.argument(
    "project_path",
    required=False,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
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
        console.print(_("[yellow]No project root found.[/yellow]"))
        console.print(
            _("[dim]Run inside a git repo or a directory with a .kimi/ folder.[/dim]")
        )
        sys.exit(1)

    pc = ProjectConfig(project_root)
    if not pc.exists() and not pc.skills_json.exists():
        console.print(_("[yellow]No {path} found.[/yellow]").format(path=pc.mcp_json))
        console.print(
            _("[dim]Run 'kimi-mcp-hub add --project <server>' to create one.[/dim]")
        )
        sys.exit(1)

    global_cfg = config.load_mcp()
    project_cfg = pc.load_mcp()
    env = pc.load_env()
    resolved_cfg = resolve_placeholders(project_cfg, env)
    merged_cfg = merge_mcp_configs(global_cfg, resolved_cfg)
    config.save_mcp(merged_cfg)

    project_servers = resolved_cfg.get("mcpServers", {})
    if project_servers:
        console.print(
            _("\n[green]Synced {n} project MCP server(s)[/green]").format(
                n=len(project_servers)
            )
        )
        for name in project_servers:
            console.print(f"  [cyan]{name}[/cyan]")
    elif pc.exists():
        console.print(
            _("\n[yellow]Project config exists but contains no servers.[/yellow]")
        )

    # Install skills declared in .kimi/skills.json
    project_skills = [s for s in pc.load_skills() if s in SKILLS]
    if project_skills:
        installed_now = []
        for skill_name in project_skills:
            install_skill(skill_name, config, overwrite=False)
            installed_now.append(skill_name)
        console.print(
            _("[green]Ensured {n} project skill(s) installed:[/green] {names}").format(
                n=len(installed_now), names=", ".join(installed_now)
            )
        )

    console.print(_("\n[dim]Project:[/dim] {root}").format(root=project_root))
    console.print(
        _("[dim]Global config updated:[/dim] {path}\n").format(path=config.mcp_json)
    )
