"""Memory commands: config-summary, add, search, list, forget."""

from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path

import click
from rich.prompt import Prompt

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
@click.option(
    "--api-key", required=False, help="API key for the summary LLM provider."
)
@click.option("--model", default="gpt-4o-mini", show_default=True, help="Model name.")
@click.option(
    "--base-url",
    default="https://api.openai.com/v1",
    show_default=True,
    callback=_validate_base_url,
    help="OpenAI-compatible base URL.",
)
@click.option("--enabled/--disabled", default=True, help="Enable or disable summaries.")
def config_summary(api_key: str | None, model: str, base_url: str, enabled: bool):
    """Configure the LLM used for session summaries."""
    print_header("Memory Summary Configuration")
    config = KimiConfig()

    if not api_key:
        api_key = os.environ.get("KIMI_MEMORY_SUMMARY_API_KEY")
    if not api_key:
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
    masked = (
        f"{api_key[:3]}...{api_key[-4:]}"
        if len(api_key) > 7
        else "..."
    )
    console.print("[green]Memory summary configuration saved.[/green]")
    console.print(f"[dim]API key:[/dim] {masked}")
    console.print(f"[dim]Model:[/dim] {model}")
    console.print(f"[dim]Base URL:[/dim] {base_url}")


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
    "--limit", default=10, show_default=True, type=click.IntRange(min=1), help="Max results."
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
        console.print(
            f"[cyan]{mem['id']}[/cyan] [{mem['category']}] {mem['content']}"
        )


@memory.command(name="list")
@click.option(
    "--limit", default=20, show_default=True, type=click.IntRange(min=1), help="Max results."
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
        console.print(
            f"[cyan]{mem['id']}[/cyan] [{mem['category']}] {mem['content']}"
        )


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
