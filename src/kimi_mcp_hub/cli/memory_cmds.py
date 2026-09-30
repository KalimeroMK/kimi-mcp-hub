"""Memory commands: config-summary, add, search, list, forget."""

from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path

import click
from rich import box
from rich.prompt import Prompt
from rich.table import Table

from ..config import KimiConfig
from ..memory.db import MemoryDB
from ..project import find_project_root
from .base import main, print_header
from .common import console


def _resolve_memory_project_path(path: str | None) -> str | None:
    """Return the resolved project path, or find the project root if none given."""
    if path:
        return str(Path(path).resolve())
    project_root = find_project_root()
    return str(project_root.resolve()) if project_root else None


def _validate_base_url(ctx, param, value):
    """Ensure the base URL has a scheme and netloc."""
    parsed = urllib.parse.urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise click.BadParameter(f"Invalid base URL: {value}")
    return value


@main.group(name="memory")
def memory():
    """Manage persistent memory settings."""


@memory.command(name="config-summary")
@click.option("--api-key", required=False, help="API key for the summary LLM provider.")
@click.option("--model", default="gpt-4o-mini", show_default=True, help="Model name.")
@click.option(
    "--base-url",
    default="https://api.openai.com/v1",
    show_default=True,
    callback=_validate_base_url,
    help="OpenAI-compatible base URL.",
)
@click.option("--enabled/--disabled", default=True, help="Enable or disable summaries.")
@click.option(
    "--test",
    "test_only",
    is_flag=True,
    help="Check the saved configuration against the provider and exit.",
)
def config_summary(
    api_key: str | None, model: str, base_url: str, enabled: bool, test_only: bool
):
    """Configure the LLM used for session summaries."""
    from ..memory.summarizer import Summarizer

    print_header("Memory Summary Configuration")
    config = KimiConfig()

    if test_only:
        if not config.is_memory_summary_enabled():
            console.print("[yellow]Session summaries are disabled.[/yellow]")
            sys.exit(1)
        ok, detail = Summarizer.from_config(config).check()
        if ok:
            console.print(f"[green]Summarization works:[/green] {detail}")
            return
        console.print(f"[red]Summarization is broken: {detail}[/red]")
        console.print(
            "[dim]Sessions are being saved without a summary. Re-run "
            "`kimi-mcp-hub memory config-summary` with a valid key.[/dim]"
        )
        sys.exit(1)

    if not enabled:
        data = config.load_toml_config()
        data.setdefault("memory", {})["summary_enabled"] = False
        config.save_toml_config(data)
        console.print("[green]Provider summaries disabled.[/green]")
        console.print(
            "[dim]The active model still writes summaries via memory_summarize.[/dim]"
        )
        return

    if not api_key:
        api_key = os.environ.get("KIMI_MEMORY_SUMMARY_API_KEY")
    if not api_key and Summarizer("", model, base_url).is_local:
        api_key = ""
    elif not api_key:
        if sys.stdin.isatty():
            api_key = Prompt.ask("API key", password=True)
        else:
            console.print("[red]API key is required.[/red]")
            sys.exit(1)

    config.set_memory_summary_config(
        api_key=api_key,
        model=model,
        base_url=base_url,
        enabled=enabled,
    )
    if api_key:
        masked = f"{api_key[:3]}...{api_key[-4:]}" if len(api_key) > 7 else "..."
    else:
        masked = "none (local server)"
    console.print("[green]Memory summary configuration saved.[/green]")
    console.print(f"[dim]API key:[/dim] {masked}")
    console.print(f"[dim]Model:[/dim] {model}")
    console.print(f"[dim]Base URL:[/dim] {base_url}")

    if not enabled:
        return

    # Verify now rather than let every session fail quietly inside the Stop hook.
    ok, detail = Summarizer(api_key, model, base_url).check()
    if ok:
        console.print(f"[green]Verified:[/green] {detail}")
    else:
        console.print(f"\n[red]This configuration does not work: {detail}[/red]")
        console.print(
            "[dim]Sessions will be saved without a summary until it is fixed. "
            "Re-check anytime with: kimi-mcp-hub memory config-summary --test[/dim]"
        )


@memory.command(name="add")
@click.argument("content")
@click.option(
    "--category",
    default="general",
    show_default=True,
    help="Memory category (user, project, general).",
)
@click.option("--tags", help="Comma-separated tags.")
@click.option(
    "--project-path",
    type=click.Path(path_type=Path),
    help="Project path for project-scoped memories.",
)
def add_memory_cmd(
    content: str,
    category: str,
    tags: str | None,
    project_path: Path | None,
):
    """Save a long-term memory."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    project = _resolve_memory_project_path(str(project_path) if project_path else None)
    db = MemoryDB()
    mem_id = db.add_memory(
        content=content,
        category=category,
        tags=tag_list,
        project_path=project,
    )
    console.print(f"[green]Saved memory {mem_id}[/green]")


@memory.command(name="search")
@click.argument("query")
@click.option(
    "--limit",
    default=10,
    show_default=True,
    type=click.IntRange(min=1),
    help="Max results.",
)
@click.option("--category", help="Filter by category.")
@click.option(
    "--project-path",
    type=click.Path(path_type=Path),
    help="Filter by project path.",
)
def search_memory_cmd(
    query: str,
    limit: int,
    category: str | None,
    project_path: Path | None,
):
    """Search saved memories."""
    project = _resolve_memory_project_path(str(project_path) if project_path else None)
    db = MemoryDB()
    results = db.search_memories(
        query=query,
        limit=limit,
        category=category,
        project_path=project,
    )
    if not results:
        console.print("[dim]No memories found.[/dim]")
        return
    for mem in results:
        console.print(f"[cyan]{mem['id']}[/cyan] [{mem['category']}] {mem['content']}")


@memory.command(name="list")
@click.option(
    "--limit",
    default=20,
    show_default=True,
    type=click.IntRange(min=1),
    help="Max results.",
)
@click.option("--category", help="Filter by category.")
@click.option(
    "--project-path",
    type=click.Path(path_type=Path),
    help="Filter by project path.",
)
def list_memory_cmd(
    limit: int,
    category: str | None,
    project_path: Path | None,
):
    """List recent memories."""
    project = _resolve_memory_project_path(str(project_path) if project_path else None)
    db = MemoryDB()
    results = db.get_memories(
        limit=limit,
        category=category,
        project_path=project,
    )
    if not results:
        console.print("[dim]No memories found.[/dim]")
        return
    for mem in results:
        console.print(f"[cyan]{mem['id']}[/cyan] [{mem['category']}] {mem['content']}")


@memory.command(name="forget")
@click.argument("memory_id", type=int)
def forget_memory_cmd(memory_id: int):
    """Delete a memory by ID."""
    db = MemoryDB()
    if db.delete_memory(memory_id):
        console.print(f"[green]Forgot memory {memory_id}[/green]")
    else:
        console.print(f"[red]Memory {memory_id} not found.[/red]")
        sys.exit(1)


@memory.command(name="viewer")
@click.option(
    "--port", default=None, type=int, help="Port to listen on. [default: 8765]"
)
@click.option("--no-open", is_flag=True, help="Do not open a browser automatically.")
@click.option("--daemon", is_flag=True, help="Start in the background and return.")
@click.option("--stop", is_flag=True, help="Stop the background viewer.")
@click.option("--status", is_flag=True, help="Show whether the viewer is running.")
@click.option(
    "--autostart/--no-autostart",
    default=None,
    help="Start the viewer automatically with every Kimi session.",
)
@click.option(
    "--rotate-token", is_flag=True, help="Invalidate previously shared links."
)
@click.option(
    "--token/--no-token",
    "require_token",
    default=None,
    help="Require an access token. On by default; --no-token opens the viewer to every local account.",
)
def memory_viewer_cmd(
    port: int | None,
    no_open: bool,
    daemon: bool,
    stop: bool,
    status: bool,
    autostart: bool | None,
    rotate_token: bool,
    require_token: bool | None,
):
    """Browse memory in your web browser.

    Serves a read-only viewer on localhost. The database holds raw tool output,
    so the server never binds to a public interface. The first visit through
    the printed link leaves a session cookie, after which the bare address
    works on its own.
    """
    from ..memory import viewer as viewer_module
    from ..memory.viewer import serve

    config = KimiConfig()
    port = port if port is not None else config.get_viewer_port()

    if require_token is not None:
        config.set_viewer_token_required(require_token)
        if require_token:
            console.print("[green]Access token required.[/green]")
        else:
            console.print("[yellow]Access token disabled.[/yellow]")
            console.print(
                "[dim]   Any account on this machine can now read the database over HTTP.[/dim]"
            )
        if viewer_module.viewer_status()["state"] == "running":
            console.print("[dim]   Restart the viewer to apply.[/dim]")
    token_required = config.is_viewer_token_required()

    if rotate_token:
        viewer_module.rotate_token()
        console.print(
            "[green]New token generated. Previous links no longer work.[/green]"
        )
        if viewer_module.viewer_status()["state"] == "running":
            console.print("[dim]Restart the viewer to serve the new token.[/dim]")

    if autostart is not None:
        config.set_viewer_autostart(autostart, port=port)
        if autostart:
            console.print(
                f"[green]Autostart enabled — the viewer will come up with each Kimi session on port {port}.[/green]"
            )
        else:
            console.print("[green]Autostart disabled.[/green]")

    if status:
        _print_viewer_status(viewer_module, config)
        return

    if stop:
        result = viewer_module.stop_daemon()
        if result.get("stopped"):
            console.print(f"[green]Viewer stopped (pid {result['pid']}).[/green]")
        elif result.get("cleaned_stale"):
            console.print(
                "[yellow]Viewer was not running; cleared a stale pidfile.[/yellow]"
            )
        else:
            console.print("[dim]Viewer was not running.[/dim]")
        return

    if daemon:
        result = viewer_module.start_daemon(port=port)
        if result["state"] == "running" and result.get("started"):
            console.print(f"[green]Memory viewer:[/green] {result['url']}")
            console.print(
                f"[dim]   Running in the background, pid {result['pid']}.[/dim]"
            )
            console.print(
                "[dim]   Stop it with: kimi-mcp-hub memory viewer --stop[/dim]"
            )
        elif result["state"] == "running":
            console.print(
                f"[dim]Already running (pid {result['pid']}): {result['url']}[/dim]"
            )
        elif result["state"] == "port_busy":
            console.print(
                f"[red]Port {port} is already in use by another process.[/red]"
            )
            console.print("[dim]Pick another with --port.[/dim]")
            sys.exit(1)
        else:
            console.print(
                f"[red]Could not start the viewer: {result.get('reason', 'unknown error')}[/red]"
            )
            sys.exit(1)
        return

    if autostart is not None or rotate_token or require_token is not None:
        # Those were configuration-only invocations; do not also block on a server.
        return

    def announce(url: str) -> None:
        console.print(f"[green]Memory viewer:[/green] {url}")
        console.print(f"[dim]   Database: {config.memory_db}[/dim]")
        if token_required:
            console.print(
                "[dim]   Opening this link authorizes this browser for good.[/dim]"
            )
        console.print("[dim]   Local only. Press Ctrl+C to stop.[/dim]")

    def browser_failed(reason: str) -> None:
        # Headless Linux and SSH sessions land here. Say so, otherwise the user
        # is left waiting for a window that is never going to open.
        console.print(f"[yellow]Could not open a browser ({reason}).[/yellow]")
        console.print("[dim]   Open the URL above yourself, or forward the port:[/dim]")
        console.print(f"[dim]   ssh -L {port}:127.0.0.1:{port} <user>@<host>[/dim]")

    try:
        serve(
            db_path=config.memory_db,
            port=port,
            open_browser=not no_open,
            on_ready=announce,
            on_open_failed=browser_failed,
            require_token=token_required,
        )
    except OSError as exc:
        console.print(f"[red]Could not start viewer on port {port}: {exc}[/red]")
        console.print("[dim]Try a different port with --port.[/dim]")
        sys.exit(1)
    console.print("[dim]Viewer stopped.[/dim]")


def _print_viewer_status(viewer_module, config: KimiConfig) -> None:
    """Print whether the background viewer is up, and how it is configured."""
    state = viewer_module.viewer_status()
    autostart = config.is_viewer_autostart_enabled()

    if state["state"] == "running":
        health = "responding" if state.get("responding") else "not responding"
        colour = "green" if state.get("responding") else "yellow"
        console.print(f"[{colour}]running[/{colour}]  pid {state['pid']}  ({health})")
        console.print(f"   {state['url']}")
    elif state["state"] == "stale":
        console.print(
            f"[yellow]not running[/yellow]  (stale pidfile for pid {state['pid']})"
        )
        console.print("[dim]   It will be cleaned up on the next start.[/dim]")
    else:
        console.print("[dim]not running[/dim]")
        console.print(
            "[dim]   Start it with: kimi-mcp-hub memory viewer --daemon[/dim]"
        )

    console.print(
        f"[dim]   Autostart with Kimi sessions: {'on' if autostart else 'off'}[/dim]"
    )
    if not config.is_viewer_token_required():
        console.print(
            "[yellow]   Access token: disabled (open to local accounts)[/yellow]"
        )
    console.print(f"[dim]   Database: {config.memory_db}[/dim]")


@memory.command(name="context")
@click.option(
    "--project-path",
    type=click.Path(path_type=Path),
    help="Project to render for. [default: the current project]",
)
@click.option("--sessions", type=int, help="How many past sessions to show.")
@click.option("--notes", type=int, help="How many project notes to show.")
@click.option("--all-projects", is_flag=True, help="Render without a project scope.")
def memory_context_cmd(
    project_path: Path | None,
    sessions: int | None,
    notes: int | None,
    all_projects: bool,
):
    """Show the memory block that gets injected at session start.

    Useful for tuning the limits: whatever this prints is spent from every
    session's context window.
    """
    from ..memory.context import build_context

    config = KimiConfig()
    scope = (
        None
        if all_projects
        else _resolve_memory_project_path(str(project_path) if project_path else None)
    )

    block = build_context(
        MemoryDB(db_path=config.memory_db),
        scope,
        max_sessions=sessions
        if sessions is not None
        else config.get_context_sessions(),
        max_notes=notes if notes is not None else config.get_context_notes(),
    )
    if not block.strip():
        console.print("[dim]Nothing to inject yet for this project.[/dim]")
        return

    # markup=False: the block contains literal brackets like memory_get([id]),
    # which rich would otherwise swallow as a style tag and misrepresent what
    # actually gets injected.
    console.print(block, markup=False, highlight=False)
    console.print(
        f"\n[dim]{len(block)} characters, roughly {len(block) // 4} tokens per session.[/dim]"
    )


@memory.command(name="backfill-projects")
@click.option(
    "--vault",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    help="Obsidian vault to read session notes from. [default: the configured memory vault]",
)
@click.option("--dry-run", is_flag=True, help="Report what would change and stop.")
@click.option("--yes", is_flag=True, help="Skip the confirmation prompt.")
def backfill_projects_cmd(vault: Path | None, dry_run: bool, yes: bool):
    """Recover project attribution for older observations.

    Observations captured before project tracking existed have no project, so
    project-scoped recall cannot see them. The session notes in your Obsidian
    vault record which project each session ran in; this reads them back.

    Only rows that still lack a project are touched, so it is safe to re-run.
    """
    from ..memory.backfill import apply_plan, build_plan, parse_session_notes

    print_header("Backfill Project Attribution")
    config = KimiConfig()

    vault_path = vault or (
        Path(config.get_default_memory_vault()).expanduser()
        if config.get_default_memory_vault()
        else None
    )
    if vault_path is None:
        console.print("[red]No memory vault configured.[/red]")
        console.print(
            "[dim]Pass one with --vault, or set one with: kimi-mcp-hub obsidian set-default[/dim]"
        )
        sys.exit(1)

    db = MemoryDB(db_path=config.memory_db)
    unattributed = db.count_unattributed()
    if unattributed == 0:
        console.print("[green]Every observation already has a project.[/green]")
        return

    mapping, plan = parse_session_notes(vault_path)
    plan = build_plan(db, mapping, plan)

    console.print(f"[dim]Vault:[/dim] {vault_path}")
    console.print(f"[dim]Notes scanned:[/dim] {plan.notes_scanned}")
    console.print(f"[dim]Sessions with a project:[/dim] {plan.sessions_mapped}")
    if plan.notes_without_project:
        console.print(
            f"[dim]Notes with no project recorded:[/dim] {plan.notes_without_project}"
        )
    if plan.conflicts:
        console.print(
            f"[yellow]Skipped {len(plan.conflicts)} session(s) whose notes disagree on the project.[/yellow]"
        )
    console.print()

    if plan.is_empty:
        console.print(
            f"[yellow]Nothing to backfill.[/yellow] "
            f"{unattributed} observation(s) lack a project, but none belong to a session these notes cover."
        )
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Project")
    table.add_column("Observations", justify="right")
    for project, count in sorted(
        plan.per_project.items(), key=lambda item: item[1], reverse=True
    ):
        table.add_row(project, str(count))
    console.print(table)

    remaining = unattributed - plan.observations_to_update
    console.print(
        f"[bold]{plan.observations_to_update}[/bold] of {unattributed} unattributed "
        f"observation(s) would be updated across {plan.sessions_matched} session(s)."
    )
    if remaining:
        console.print(
            f"[dim]{remaining} would stay unattributed — no note records their session.[/dim]"
        )

    if dry_run:
        console.print("\n[dim]Dry run: nothing was written.[/dim]")
        return

    if not yes and not click.confirm("\nApply these changes?", default=False):
        console.print("[dim]Cancelled.[/dim]")
        return

    updated = apply_plan(db, mapping)
    console.print(f"\n[green]Updated {updated} observation(s).[/green]")
    console.print(f"[dim]Still unattributed: {db.count_unattributed()}[/dim]")


@memory.command(name="serve-mcp")
def memory_serve_mcp_cmd():
    """Run the memory MCP server on stdio (used by Kimi, not by humans)."""
    from ..memory.mcp_server import serve

    sys.exit(serve())
