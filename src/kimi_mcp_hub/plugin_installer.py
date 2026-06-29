"""Install Claude Code / Codex plugins into Kimi CLI.

Plugins such as Ponytail ship lifecycle hooks in Claude-format JSON
(`hooks.json`, `.claude/settings.json`) and skills. Kimi CLI reads the same
JSON wire protocol, but expects hooks in `~/.kimi-code/config.toml`.
This module converts and merges those artifacts.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


# Map Claude/Codex tool names to Kimi tool-name regexes.
# Kimi matcher is a regex; alternation lets one matcher cover synonyms.
TOOL_NAME_MAP: dict[str, str] = {
    "Write": "WriteFile|StrReplaceFile",
    "Edit": "Edit|StrReplaceFile",
    "MultiEdit": "MultiEdit",
    "Read": "ReadFile",
    "Bash": "Shell|Bash",
    "Shell": "Shell|Bash",
    "WebFetch": "WebFetch",
    "Agent": "Agent",
}


def _map_matcher(matcher: str) -> str:
    """Convert a Claude matcher expression to a Kimi regex.

    Simple pipe-separated tool names are mapped individually.
    Anything containing regex metacharacters is passed through unchanged.
    """
    if not matcher or matcher == "*":
        return ""
    # If it looks like a regex already, preserve it.
    if re.search(r"[.^$+*?()\[\]\\|]", matcher):
        # Still try to map bare tool names that appear inside the regex.
        for claude_name, kimi_names in TOOL_NAME_MAP.items():
            matcher = re.sub(rf"\b{re.escape(claude_name)}\b", kimi_names, matcher)
        return matcher
    parts = [p.strip() for p in matcher.split("|")]
    mapped = []
    for part in parts:
        mapped.append(TOOL_NAME_MAP.get(part, part))
    return "|".join(mapped)


def resolve_repo(repo: str) -> tuple[str, str]:
    """Resolve a repo specifier to (clone_url, plugin_name).

    Supports:
        owner/repo          -> https://github.com/owner/repo
        https://...         -> as-is
        /local/path         -> as-is
    """
    repo = repo.strip()
    path = Path(repo)
    if path.exists() and path.is_dir():
        return str(path.resolve()), path.name

    if repo.startswith(("http://", "https://", "git@", "ssh://")):
        url = repo
        if not url.endswith(".git"):
            url = url + ".git"
    elif "/" in repo and " " not in repo and not repo.startswith("."):
        url = f"https://github.com/{repo}.git"
    else:
        raise ValueError(f"Unable to resolve plugin repo: {repo}")

    name = url.rstrip(".git").split("/")[-1]
    if not name:
        raise ValueError(f"Unable to determine plugin name from: {repo}")
    return url, name


def clone_or_update_repo(url: str, plugin_dir: Path) -> None:
    """Clone a git repo into plugin_dir, or pull if it already exists.

    If url points to a local directory, copy it instead of cloning so that
    plain directories (e.g. during tests or local plugin development) work.
    """
    source_path = Path(url)
    if source_path.exists() and source_path.is_dir():
        if (plugin_dir / ".git").exists() or plugin_dir.exists():
            shutil.rmtree(plugin_dir, ignore_errors=True)
        shutil.copytree(source_path, plugin_dir)
        return

    if (plugin_dir / ".git").exists():
        console.print(f"[dim]Updating existing plugin at {plugin_dir}[/dim]")
        subprocess.run(
            ["git", "-C", str(plugin_dir), "pull", "--ff-only"],
            check=True,
            capture_output=True,
            text=True,
        )
        return

    plugin_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", url, str(plugin_dir)],
        check=True,
        capture_output=True,
        text=True,
    )


def discover_plugin_layout(plugin_dir: Path) -> dict[str, Any]:
    """Inspect plugin directory and return discovered artifacts."""
    layout: dict[str, Any] = {
        "plugin_dir": plugin_dir,
        "agents_md": None,
        "hooks_config": None,
        "hooks_format": None,
        "skills_dirs": [],
    }

    candidates = [
        (plugin_dir / "AGENTS.md", None),
        (plugin_dir / ".claude" / "AGENTS.md", None),
    ]
    for candidate, _ in candidates:
        if candidate.exists():
            layout["agents_md"] = candidate
            break

    hook_candidates = [
        (plugin_dir / "hooks.json", "hooks.json"),
        (plugin_dir / ".claude" / "settings.json", "claude-settings"),
        (plugin_dir / "hooks" / "hooks.json", "hooks/hooks.json"),
        (plugin_dir / "gemini-extension.json", "gemini-extension"),
    ]
    for candidate, fmt in hook_candidates:
        if candidate.exists():
            layout["hooks_config"] = candidate
            layout["hooks_format"] = fmt
            break

    skill_candidates = [
        plugin_dir / "skills",
        plugin_dir / ".claude" / "skills",
    ]
    for candidate in skill_candidates:
        if candidate.exists() and candidate.is_dir():
            layout["skills_dirs"].append(candidate)

    return layout


def _load_hooks_json(config_path: Path, fmt: str | None) -> dict[str, Any]:
    """Load hooks configuration from a plugin file."""
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if fmt == "hooks.json":
        return data.get("hooks", data)
    if fmt in ("claude-settings", "hooks/hooks.json"):
        return data.get("hooks", {})
    if fmt == "gemini-extension":
        # Gemini extension may nest hooks under a hooks key.
        return data.get("hooks", {})
    return data


def convert_hooks(
    hooks_data: dict[str, Any],
    plugin_dir: Path,
    plugin_name: str,
) -> list[dict[str, Any]]:
    """Convert Claude/Codex hooks data to Kimi [[hooks]] entries."""
    kimi_hooks: list[dict[str, Any]] = []
    if not hooks_data:
        return kimi_hooks

    for event, entries in hooks_data.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            matcher = entry.get("matcher", "")
            hooks = entry.get("hooks", [])
            if isinstance(hooks, dict):
                hooks = [hooks]
            for hook in hooks:
                if hook.get("type") != "command":
                    console.print(
                        f"[yellow]Skipping non-command {event} hook in {plugin_name}[/yellow]"
                    )
                    continue
                raw_command = hook.get("command", "")
                if not raw_command:
                    continue
                # Run the original command from inside the plugin directory so
                # relative paths and node_modules resolve correctly.
                command = f'cd "{plugin_dir}" && {raw_command}'
                kimi_hooks.append({
                    "event": event,
                    "matcher": _map_matcher(matcher),
                    "command": command,
                    "timeout": hook.get("timeout", 30),
                })
    return kimi_hooks


def _copy_skills(
    skills_dirs: list[Path],
    target_dir: Path,
    plugin_name: str,
) -> list[str]:
    """Copy plugin skills into Kimi skills directory.

    Skills are installed as <plugin>-<skill> to avoid collisions.
    """
    installed: list[str] = []
    for source_dir in skills_dirs:
        for skill_path in source_dir.iterdir():
            if not skill_path.is_dir():
                continue
            if not (skill_path / "SKILL.md").exists():
                continue
            skill_name = skill_path.name
            prefixed = skill_name
            if not skill_name.startswith(f"{plugin_name}-") and skill_name != plugin_name:
                prefixed = f"{plugin_name}-{skill_name}"
            dest = target_dir / prefixed
            shutil.copytree(skill_path, dest, dirs_exist_ok=True)
            installed.append(prefixed)
    return installed


def install_plugin(
    repo: str,
    config: Any,
    *,
    yes: bool = False,
    name: str | None = None,
) -> dict[str, Any]:
    """Install a Claude/Codex-style plugin into Kimi CLI.

    Returns a dict describing installed artifacts.
    """
    url, plugin_name = resolve_repo(repo)
    plugin_name = (name or plugin_name).strip()
    plugin_dir = config.plugin_dir(plugin_name)

    console.print(f"[bold cyan]Installing plugin: {plugin_name}[/bold cyan]")
    console.print(f"[dim]Source: {url}[/dim]")
    console.print(f"[dim]Install directory: {plugin_dir}[/dim]")

    if plugin_dir.exists() and any(plugin_dir.iterdir()) and not yes:
        # In interactive mode, confirm overwrite of an existing plugin dir.
        # We do not block; callers should ask before invoking install_plugin.
        pass

    clone_or_update_repo(url, plugin_dir)

    layout = discover_plugin_layout(plugin_dir)
    result: dict[str, Any] = {
        "plugin_name": plugin_name,
        "plugin_dir": plugin_dir,
        "agents_md_installed": False,
        "hooks_installed": 0,
        "skills_installed": [],
    }

    # Merge AGENTS.md
    if layout["agents_md"]:
        content = layout["agents_md"].read_text(encoding="utf-8")
        if content.strip():
            changed = config.merge_agents_md(content, marker=plugin_name)
            result["agents_md_installed"] = changed
            if changed:
                console.print(f"[green]Merged AGENTS.md from {plugin_name}[/green]")
            else:
                console.print(f"[dim]AGENTS.md from {plugin_name} already present[/dim]")

    # Convert and write hooks
    if layout["hooks_config"]:
        hooks_data = _load_hooks_json(layout["hooks_config"], layout["hooks_format"])
        kimi_hooks = convert_hooks(hooks_data, plugin_dir, plugin_name)
        if kimi_hooks:
            toml_data = config.load_toml_config()
            existing = toml_data.setdefault("hooks", [])
            if not isinstance(existing, list):
                existing = []
                toml_data["hooks"] = existing

            # Remove old hooks belonging to this plugin to keep reinstalls idempotent.
            plugin_prefix = f'cd "{plugin_dir}" &&'
            existing[:] = [h for h in existing if plugin_prefix not in h.get("command", "")]
            existing.extend(kimi_hooks)
            config.save_toml_config(toml_data)
            result["hooks_installed"] = len(kimi_hooks)
            console.print(f"[green]Installed {len(kimi_hooks)} hook(s) from {plugin_name}[/green]")
        else:
            console.print(f"[dim]No command hooks found in {plugin_name}[/dim]")

    # Copy skills
    if layout["skills_dirs"]:
        installed = _copy_skills(layout["skills_dirs"], config.skills_dir, plugin_name)
        result["skills_installed"] = installed
        if installed:
            console.print(f"[green]Installed skills: {', '.join(installed)}[/green]")

    console.print(f"\n[bold green]Plugin '{plugin_name}' installed successfully.[/bold green]")
    console.print("[dim]Restart Kimi CLI for hook changes to take effect.[/dim]")
    return result
