"""Self-management commands: install and update the hub itself."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .base import main, print_header
from .common import console


def _is_dev_install() -> bool:
    """Return True if running from a git checkout."""
    repo_dir = Path(__file__).resolve().parents[3]
    return (repo_dir / ".git").exists()


def _venv_python(venv_dir: Path) -> Path:
    """Return the venv interpreter path for the current platform."""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _get_venv_info() -> tuple[str, Path | None, bool]:
    """Return (target_python, venv_dir, in_existing_venv).

    If already inside a venv, upgrade in-place. Otherwise create/use
    ~/.kimi-mcp-hub/.venv.
    """
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        return sys.executable, None, True

    venv_dir = Path.home() / ".kimi-mcp-hub" / ".venv"
    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    venv_python = _venv_python(venv_dir)
    if not venv_python.exists():
        console.print(f"[cyan]Creating isolated environment at {venv_dir}...[/cyan]")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            console.print("[red]Timed out creating virtual environment.[/red]")
            raise RuntimeError("venv creation timed out")
        except subprocess.CalledProcessError as e:
            console.print(
                f"[red]Failed to create virtual environment:[/red]\n{e.stderr}"
            )
            raise RuntimeError("venv creation failed")
    return str(venv_python), venv_dir, False


def _link_venv_binaries(venv_dir: Path) -> None:
    """Symlink scripts from venv into ~/.local/bin (POSIX only).

    On Windows there is no ~/.local/bin convention and symlinks need elevated
    privileges, so instead point the user at the venv's Scripts directory.
    """
    if sys.platform == "win32":
        scripts_dir = venv_dir / "Scripts"
        console.print(
            f"[dim]Binaries are in {scripts_dir}. Add it to your PATH, or run via:[/dim]"
        )
        console.print(f"[dim]  {scripts_dir / 'kimi-mcp-hub.exe'}[/dim]\n")
        return

    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    for script in ["kimi-mcp-hub", "kmcp"]:
        src = venv_dir / "bin" / script
        dst = bin_dir / script
        if not src.exists():
            console.print(
                f"[yellow]Skipping {script}: source binary not found in venv.[/yellow]"
            )
            continue
        try:
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            dst.symlink_to(src)
        except OSError as e:
            console.print(
                f"[yellow]Warning: could not link {script} to {bin_dir}: {e}[/yellow]"
            )
    console.print(
        f"[dim]Linked binaries to {bin_dir}. Ensure it is in your PATH.[/dim]\n"
    )


def _run_pip_upgrade(target_python: str, sources: list[tuple[str, str]]) -> bool:
    """Try to upgrade kimi-mcp-hub from the given sources. Return True on success."""
    pip_cmd = [target_python, "-m", "pip", "install", "--upgrade"]
    for idx, (source, package) in enumerate(sources):
        console.print(f"[cyan]Installing from {source}...[/cyan]")
        try:
            result = subprocess.run(
                pip_cmd + [package],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode == 0:
                console.print(f"[green]Kimi MCP Hub installed from {source}![/green]\n")
                return True
            if result.stderr:
                console.print(
                    f"[red]Error output from {source}:[/red]\n{result.stderr}"
                )
            if result.stdout:
                console.print(f"[dim]Output from {source}:[/dim]\n{result.stdout}")
            if idx < len(sources) - 1:
                console.print("[yellow]Install failed, trying next source...[/yellow]")
        except Exception as e:
            console.print(f"[red]Error installing from {source}: {e}[/red]")
    return False


def _perform_upgrade(
    sources: list[tuple[str, str]],
    success_message: str,
    failure_message: str,
) -> None:
    """Shared upgrade logic for install and update commands."""
    try:
        target_python, venv_dir, in_venv = _get_venv_info()
    except RuntimeError:
        console.print("[red]Failed to prepare virtual environment.[/red]")
        sys.exit(1)

    if _run_pip_upgrade(target_python, sources):
        if venv_dir and not in_venv:
            _link_venv_binaries(venv_dir)
        if success_message:
            console.print(f"[green]{success_message}[/green]\n")
    else:
        console.print(f"[red]{failure_message}[/red]")
        console.print(
            "  [bold]bash <(curl -fsSL https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.sh)[/bold]\n"
        )
        sys.exit(1)


@main.command()
def install():
    """Install or update Kimi MCP Hub."""
    print_header()
    console.print("[bold cyan]Installing Kimi MCP Hub...[/bold cyan]\n")

    if _is_dev_install():
        console.print("[dim]Detected development install (git repo)[/dim]")
        console.print(
            "Run: [bold]python3 -m venv .venv && source .venv/bin/activate && pip install -e .[/bold] from repo root\n"
        )
        return

    sources = [
        ("GitHub", "git+https://github.com/KalimeroMK/kimi-mcp-hub.git"),
    ]
    _perform_upgrade(
        sources,
        success_message="Installation complete.",
        failure_message="Install failed. Try the curl installer:",
    )


@main.command()
def update():
    """Update Kimi MCP Hub to the latest version."""
    print_header()
    console.print("[bold cyan]Updating Kimi MCP Hub...[/bold cyan]\n")

    if _is_dev_install():
        console.print("[dim]Detected development install (git repo)[/dim]")
        console.print("Run: [bold]git pull && pip install -e .[/bold] from repo root\n")
        return

    sources = [
        ("GitHub", "git+https://github.com/KalimeroMK/kimi-mcp-hub.git"),
    ]
    _perform_upgrade(
        sources,
        success_message="Update complete. Restart your terminal to use the new version.",
        failure_message="Update failed. Try the curl installer:",
    )
