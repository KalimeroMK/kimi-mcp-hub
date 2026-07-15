"""Install/configure helpers shared by the command modules."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from rich.prompt import Confirm, Prompt

from ..auth.providers import authenticate_github
from ..config import KimiConfig
from ..memory.db import MemoryDB
from ..preflight import maybe_install_npx_deps
from ..project import ProjectConfig
from ..registry import SERVERS
from ..servers import (
    ChromeDevToolsServer,
    ConfluenceServer,
    Context7Server,
    DatadogServer,
    DBHubServer,
    DesktopCommanderServer,
    FigmaContextServer,
    FigmaServer,
    GitHubServer,
    GitLabServer,
    GmailServer,
    GrainServer,
    HubSpotServer,
    JiraServer,
    LinearServer,
    MobileMCPServer,
    ObsidianServer,
    PerplexityServer,
    PlaywrightServer,
    PostgreSQLServer,
    SentryServer,
    SlackServer,
    StripeServer,
    SupabaseServer,
)
from .common import console


def add_server_with_preflight(
    name: str,
    cfg: dict,
    config: KimiConfig,
    project_root: Path | None = None,
    assume_yes: bool = False,
):
    """Add a server after prompting to install any missing npx packages."""
    maybe_install_npx_deps(cfg, console, assume_yes=assume_yes)
    if project_root:
        pc = ProjectConfig(project_root)
        pc.add_server(name, cfg)
        console.print(f"[dim]Saved to {pc.mcp_json}[/dim]")
    else:
        config.add_server(name, cfg)


def add_server_interactive(
    name: str,
    config: KimiConfig,
    project_root: Path | None = None,
):
    """Interactive prompt to add a server."""
    cls = SERVERS[name]
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
            cfg = (
                JiraServer.get_oauth_config()
                if name == "jira"
                else ConfluenceServer.get_oauth_config()
            )
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official OAuth)[/green]")
            _authenticate_server(name, "official")
        else:
            base = Prompt.ask("Base URL", default="https://yourcompany.atlassian.net")
            email = Prompt.ask("Email")
            token = Prompt.ask("API token", password=True)
            cfg = (
                JiraServer.get_stdio_config(base, token, email)
                if name == "jira"
                else ConfluenceServer.get_stdio_config(base, token, email)
            )
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
            token = Prompt.ask(
                "Linear API key (https://linear.app/settings/api)", password=True
            )
            cfg = LinearServer.get_stdio_config(token)
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (API key)[/green]")

    elif name == "github":
        choice = Prompt.ask(
            "Auth method",
            choices=["official-oauth", "pat", "oauth-device"],
            default="official-oauth",
        )
        if choice == "official-oauth":
            cfg = GitHubServer.get_official_config()
            add_server_with_preflight(name, cfg, config, project_root=project_root)
            console.print(f"[green]Added {display} (Official remote MCP)[/green]")
            console.print(f"[dim]   Run: kimi mcp auth {name} to complete OAuth[/dim]")
        elif choice == "oauth-device":
            token_data = authenticate_github()
            if token_data and "access_token" in token_data:
                cfg = GitHubServer.get_stdio_config(token_data["access_token"])
                add_server_with_preflight(name, cfg, config, project_root=project_root)
                console.print(f"[green]Added {display} (OAuth device flow)[/green]")
            else:
                console.print(f"[yellow]{display} OAuth not completed.[/yellow]")
        else:
            token = Prompt.ask(
                "GitHub PAT (https://github.com/settings/tokens)", password=True
            )
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
        choice = Prompt.ask(
            "Mode",
            choices=["npx-auto", "chrome-bridge", "python-sdk"],
            default="npx-auto",
        )
        if choice == "npx-auto":
            cfg = GmailServer.get_npx_config()
        elif choice == "chrome-bridge":
            cfg = GmailServer.get_chrome_config()
        else:
            creds = Prompt.ask("Path to credentials.json")
            tokens = Prompt.ask(
                "Path to tokens.json", default="~/.gmail-mcp/tokens.json"
            )
            cfg = GmailServer.get_python_config(creds, tokens)
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display} ({choice})[/green]")

    elif name == "hubspot":
        choice = Prompt.ask(
            "Source", choices=["npx", "official", "docker"], default="npx"
        )
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
        console.print("[dim]   Login via browser on first use.[/dim]")

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
        console.print(
            "[dim]   Warning: this server can execute arbitrary commands.[/dim]"
        )

    elif name == "mobile":
        cfg = MobileMCPServer.get_stdio_config()
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display}[/green]")
        console.print(
            "[dim]   Requires iOS Simulator/Android Emulator or a connected device.[/dim]"
        )

    elif name == "postgres":
        dsn = Prompt.ask(
            "PostgreSQL DSN", default="postgresql://user:pass@localhost/db"
        )
        cfg = PostgreSQLServer.get_stdio_config(dsn)
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display}[/green]")

    elif name == "dbhub":
        choice = Prompt.ask("Mode", choices=["dsn", "demo", "docker"], default="dsn")
        if choice == "dsn":
            dsn = Prompt.ask(
                "Database DSN", default="postgresql://user:pass@localhost/db"
            )
            readonly = Confirm.ask("Read-only mode?", default=True)
            cfg = DBHubServer.get_stdio_config(dsn, readonly)
        elif choice == "docker":
            dsn = Prompt.ask(
                "Database DSN", default="postgresql://user:pass@host.docker.internal/db"
            )
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
            project_ref = Prompt.ask(
                "Supabase project ref (optional, e.g. abcdefghijklmn)", default=""
            )
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
        console.print(
            "[bold]Perplexity[/bold] -- real-time web search with AI summaries.\n"
        )
        console.print("Get free API key at: https://www.perplexity.ai/settings/api")
        token = Prompt.ask("Perplexity API key (ppx-...)", password=True)
        cfg = PerplexityServer.get_stdio_config(token)
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display}[/green]")

    elif name == "obsidian":
        default_vault = str(Path.home() / "Documents" / "Kimi-Memory")
        vault = Prompt.ask("Obsidian vault path", default=default_vault)
        vault_path = Path(vault).expanduser().resolve()
        ObsidianServer.scaffold_vault(vault_path)
        cfg = ObsidianServer.get_stdio_config(str(vault_path))
        add_server_with_preflight(name, cfg, config, project_root=project_root)
        console.print(f"[green]Added {display}[/green]")
        console.print(f"[dim]   Vault: {vault_path}[/dim]")
        console.print(
            "[yellow]Install Obsidian from https://obsidian.md and open this vault to browse notes.[/yellow]"
        )


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
    pkg_skills_dir = Path(__file__).parent.parent / "skills" / skill_name
    user_skills_dir = config.skills_dir / skill_name

    if not pkg_skills_dir.exists():
        console.print(f"[red]Skill {skill_name} not found in package.[/red]")
        return

    if user_skills_dir.exists():
        if overwrite is False:
            console.print(
                f"[dim]Skill '{skill_name}' already installed, skipping.[/dim]"
            )
            return
        if overwrite is None:
            if not Confirm.ask(
                f"Skill '{skill_name}' already installed. Overwrite?", default=False
            ):
                return

    shutil.copytree(pkg_skills_dir, user_skills_dir, dirs_exist_ok=True)
    console.print(f"[green]Installed skill: {skill_name}[/green]")
    console.print(f"[dim]   Location: {user_skills_dir}[/dim]")


def list_installed_skills(config: KimiConfig) -> list:
    """Return list of installed skill names."""
    if not config.skills_dir.exists():
        return []
    return [
        d.name
        for d in config.skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    ]


def _install_memory_hooks(config: KimiConfig) -> None:
    """Register Kimi CLI hooks that write memory to SQLite and Obsidian."""
    toml_data = config.load_toml_config()
    hooks = toml_data.setdefault("hooks", [])
    if not hasattr(hooks, "append"):
        hooks = []
        toml_data["hooks"] = hooks

    marker = "kimi_mcp_hub.memory_hook"
    hooks[:] = [h for h in hooks if marker not in h.get("command", "")]

    # Per-event timeouts: Stop/SessionEnd write notes and may call the summary
    # LLM over the network, so they need far more headroom than the fast
    # SessionStart/PostToolUse hooks.
    hook_events = {
        "session_start": ("SessionStart", 5),
        "post_tool_use": ("PostToolUse", 5),
        "stop": ("Stop", 60),
        "session_end": ("SessionEnd", 60),
    }
    for event, (kimi_event, timeout) in hook_events.items():
        hooks.append(
            {
                "event": kimi_event,
                "command": f"{sys.executable} -m kimi_mcp_hub.memory_hook {event}",
                "timeout": timeout,
            }
        )

    config.save_toml_config(toml_data)


def enable_memory(config: KimiConfig):
    """Enable persistent memory system."""
    config.memory_db.parent.mkdir(parents=True, exist_ok=True)

    # Initialize SQLite with FTS5 using the canonical schema from memory/db.py
    MemoryDB(db_path=config.memory_db)

    _install_memory_hooks(config)

    console.print(f"[green]Memory database initialized: {config.memory_db}[/green]")
    console.print("[dim]   Memory will persist across sessions.[/dim]")
