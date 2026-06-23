"""Preflight checks for MCP server dependencies.

Prevents first-run timeouts by prompting the user to install npx packages
before Kimi CLI tries to launch them.
"""

import shutil
import subprocess
from typing import Optional


PLACEHOLDER_RE = None  # avoid circular import; defined locally where needed


def get_npx_package(args: list[str]) -> Optional[str]:
    """Extract the npm package specifier from npx args.

    Example:
        ["-y", "@scope/pkg@1.2.3", "--flag", "value"] -> "@scope/pkg@1.2.3"
        ["-y", "chrome-devtools-mcp@latest", "--port", "9229"] -> "chrome-devtools-mcp@latest"
    """
    for arg in args:
        if arg.startswith("-"):
            continue
        return arg
    return None


def normalize_package_name(package_spec: str) -> str:
    """Strip version/tag from a package specifier for local checks.

    Examples:
        "pkg@latest" -> "pkg"
        "@scope/pkg@1.0.0" -> "@scope/pkg"
        "pkg" -> "pkg"
    """
    if "@" not in package_spec:
        return package_spec

    # Scoped packages start with @, e.g. @scope/pkg@1.0.0
    if package_spec.startswith("@"):
        rest = package_spec[1:]
        if "@" in rest:
            return "@" + rest.split("@", 1)[0]
        return package_spec

    return package_spec.split("@", 1)[0]


def is_package_installed_globally(package_spec: str) -> bool:
    """Check whether an npm package is installed globally."""
    npm = shutil.which("npm")
    if not npm:
        return False

    package_name = normalize_package_name(package_spec)
    try:
        result = subprocess.run(
            [npm, "ls", "-g", package_name, "--depth=0"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def ensure_npx_package(args: list, console, timeout: int = 120) -> bool:
    """Prompt to install an npx package locally if it is missing.

    Returns True when the package is (or was already) available, and the caller
    can safely write the MCP config. Returns False if the installation failed
    and the caller may still proceed at its own discretion.
    """
    package_spec = get_npx_package(args)
    if not package_spec:
        return True

    if is_package_installed_globally(package_spec):
        return True

    from rich.prompt import Confirm

    console.print(
        f"[yellow]Package [bold]{package_spec}[/bold] is not installed locally.[/yellow]"
    )
    if not Confirm.ask(
        f"Install {package_spec} now to avoid first-run timeouts?",
        default=True,
    ):
        console.print(
            "[dim]Continuing without install. First launch may timeout while npx downloads the package.[/dim]"
        )
        return True

    npm = shutil.which("npm")
    if not npm:
        console.print("[red]npm not found. Cannot install package.[/red]")
        return False

    console.print(f"[dim]Installing {package_spec}...[/dim]")
    try:
        result = subprocess.run(
            [npm, "install", "-g", package_spec],
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            console.print(f"[green]{package_spec} installed successfully.[/green]")
            return True
        else:
            console.print(
                f"[red]Failed to install {package_spec} (exit {result.returncode}).[/red]"
            )
            return False
    except subprocess.TimeoutExpired:
        console.print(f"[red]Installation timed out after {timeout}s.[/red]")
        return False
    except OSError as e:
        console.print(f"[red]Installation error: {e}[/red]")
        return False


def maybe_install_npx_deps(server_config: dict, console) -> bool:
    """Check and optionally install npx package dependencies for a server config.

    Returns True if the caller should proceed with saving the config.
    Returns False only if the installation attempt failed.
    """
    if server_config.get("command") != "npx":
        return True
    return ensure_npx_package(server_config.get("args", []), console)
