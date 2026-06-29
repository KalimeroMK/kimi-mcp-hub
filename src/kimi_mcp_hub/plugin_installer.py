"""Install Claude Code / Codex plugins into Kimi CLI.

Plugins such as Ponytail ship lifecycle hooks in Claude-format JSON
(`hooks.json`, `.claude/settings.json`) and skills. Kimi CLI reads the same
JSON wire protocol, but expects hooks in `~/.kimi-code/config.toml`.
This module converts and merges those artifacts.
"""

from __future__ import annotations

import json
import re
import shlex
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
        if plugin_dir.exists():
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

    # A half-populated directory without .git would cause git clone to fail.
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir, ignore_errors=True)

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
        (
            plugin_dir / "hooks" / "claude-codex-hooks.json",
            "hooks/claude-codex-hooks.json",
        ),
        (plugin_dir / ".codex" / "hooks.json", ".codex/hooks.json"),
        (plugin_dir / ".claude-plugin" / "plugin.json", "claude-plugin"),
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


def _load_hooks_json(config_path: Path, fmt: str | None) -> dict[str, Any] | None:
    """Load hooks configuration from a plugin file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        console.print(
            f"[yellow]Skipping malformed hooks config {config_path}: {exc}[/yellow]"
        )
        return None

    if not isinstance(data, dict):
        console.print(
            f"[yellow]Skipping hooks config {config_path}: expected object, got {type(data).__name__}[/yellow]"
        )
        return None

    if fmt == "hooks.json":
        return data.get("hooks", data)
    if fmt in (
        "claude-settings",
        "hooks/hooks.json",
        "hooks/claude-codex-hooks.json",
        ".codex/hooks.json",
    ):
        return data.get("hooks", {})
    if fmt == "gemini-extension":
        # Gemini extension may nest hooks under a hooks key.
        return data.get("hooks", {})
    if fmt == "claude-plugin":
        return _normalize_claude_plugin_manifest(data)
    return data


def _normalize_claude_plugin_manifest(data: dict[str, Any]) -> dict[str, Any]:
    """Convert a `.claude-plugin/plugin.json` manifest to the internal hook format."""
    internal: dict[str, Any] = {}
    hooks = data.get("hooks", [])
    if not isinstance(hooks, list):
        return internal

    for hook in hooks:
        if not isinstance(hook, dict):
            continue
        command = hook.get("command", "")
        if isinstance(command, list):
            command = " ".join(shlex.quote(str(part)) for part in command)
        args = hook.get("args", [])
        if isinstance(args, list) and args:
            arg_str = " ".join(shlex.quote(str(arg)) for arg in args)
            command = f"{command} {arg_str}" if command else arg_str
        if not command:
            continue

        event = "PreToolUse"
        entry = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                    "timeout": hook.get("timeout", 30),
                }
            ],
        }
        internal.setdefault(event, []).append(entry)
    return internal


def _relativize_path_token(token: str, plugin_dir: Path) -> str | None:
    """Relativize a single path token if it points inside plugin_dir.

    Returns ``None`` if the token does not need to be changed.
    """
    token_path = Path(token)
    if token_path.is_relative_to(plugin_dir):
        rel = token_path.relative_to(plugin_dir)
        rel_str = "./" if str(rel) == "." else str(rel)
        return rel_str
    return None


def _reconstruct_with_replacements(
    value: str,
    tokens: list[str],
    replacements: dict[str, str],
) -> str:
    """Rebuild *value* replacing *tokens* while preserving original quoting."""
    result_parts: list[str] = []
    pos = 0
    for token in tokens:
        replacement = replacements.get(token)
        if replacement is None:
            replacement = token

        escaped = re.escape(token)
        pattern = rf'"{escaped}"|\'{escaped}\'|{escaped}'
        match = re.search(pattern, value[pos:])
        if not match:
            # Token not found in remaining string; stop reconstructing.
            result_parts.append(value[pos:])
            break

        start = pos + match.start()
        matched = match.group(0)
        result_parts.append(value[pos:start])

        if matched.startswith('"') and matched.endswith('"'):
            new_text = f'"{replacement}"'
        elif matched.startswith("'") and matched.endswith("'"):
            new_text = f"'{replacement}'"
        elif _token_needs_quoting(replacement):
            new_text = shlex.quote(replacement)
        else:
            new_text = replacement

        result_parts.append(new_text)
        pos = start + len(matched)

    result_parts.append(value[pos:])
    return "".join(result_parts)


# Tokens that are shell operators/control characters should not be quoted
# during reconstruction, otherwise commands like ``a && b`` become ``a '&&' b``.
_SHELL_OPERATORS: frozenset[str] = frozenset(
    {
        "&&",
        "||",
        "|",
        ";",
        "&",
        "(",
        ")",
        "<",
        ">",
        "<<",
        ">>",
        "&>",
        ">&",
        ">|",
        "<>",
        ";;",
        ";&",
        "|&",
    }
)


def _token_needs_quoting(token: str) -> bool:
    """Return True if *token* must be quoted to remain a single shell word."""
    if token in _SHELL_OPERATORS:
        return False
    if not token:
        return True
    if any(c.isspace() for c in token):
        return True
    # Safe characters according to POSIX filename/word characters.
    return not re.match(r"^[\w@%+=:,./-]+$", token)


def _relativize_plugin_paths(value: str, plugin_dir: Path) -> str:
    """Replace absolute paths inside plugin_dir with relative paths.

    The returned command is intended to run after ``cd plugin_dir &&``,
    so relative paths resolve correctly without hardcoding the install location.

    Uses ``shlex.split`` so quoted tokens containing spaces stay intact, and
    also handles ``--flag=/abs/path`` style arguments.
    """
    plugin_dir_str = str(plugin_dir)
    if plugin_dir_str not in value:
        return value

    try:
        tokens = shlex.split(value, posix=True)
    except ValueError:
        # Unbalanced quotes or other malformed shell syntax: leave as-is.
        return value

    replacements: dict[str, str] = {}
    for token in tokens:
        if "=" in token and not token.startswith("="):
            key, sep, val = token.partition("=")
            new_val = _relativize_path_token(val, plugin_dir)
            if new_val is not None:
                replacements[token] = f"{key}{sep}{new_val}"
        else:
            new_token = _relativize_path_token(token, plugin_dir)
            if new_token is not None:
                replacements[token] = new_token

    if not replacements:
        return value

    return _reconstruct_with_replacements(value, tokens, replacements)


def convert_hooks(
    hooks_data: Any,
    plugin_dir: Path,
    plugin_name: str,
) -> list[dict[str, Any]]:
    """Convert Claude/Codex hooks data to Kimi [[hooks]] entries."""
    kimi_hooks: list[dict[str, Any]] = []
    if not isinstance(hooks_data, dict):
        return kimi_hooks
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
            elif not isinstance(hooks, list):
                continue
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
                # Replace plugin-root variables with the actual path and avoid
                # hardcoding the install location by relativizing absolute paths
                # that still point inside the plugin directory.
                command = raw_command.replace("${PLUGIN_ROOT}", str(plugin_dir))
                command = command.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_dir))
                command = command.replace("${CLAUDE_CODE_PLUGIN_ROOT}", str(plugin_dir))
                command = _relativize_plugin_paths(command, plugin_dir)
                command = f'cd "{plugin_dir}" && {command}'
                kimi_hooks.append(
                    {
                        "event": event,
                        "matcher": _map_matcher(matcher),
                        "command": command,
                        "timeout": hook.get("timeout", 30),
                    }
                )
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
            if (
                not skill_name.startswith(f"{plugin_name}-")
                and skill_name != plugin_name
            ):
                prefixed = f"{plugin_name}-{skill_name}"
            dest = target_dir / prefixed
            shutil.copytree(skill_path, dest, dirs_exist_ok=True)
            installed.append(prefixed)
    return installed


def install_plugin(
    repo: str,
    config: Any,
    *,
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
                console.print(
                    f"[dim]AGENTS.md from {plugin_name} already present[/dim]"
                )

    # Convert and write hooks
    if layout["hooks_config"]:
        hooks_data = _load_hooks_json(layout["hooks_config"], layout["hooks_format"])
        if hooks_data is None:
            console.print(
                f"[yellow]No hooks loaded from {plugin_name} due to malformed config[/yellow]"
            )
        else:
            kimi_hooks = convert_hooks(hooks_data, plugin_dir, plugin_name)
            if kimi_hooks:
                toml_data = config.load_toml_config()
                existing = toml_data.setdefault("hooks", [])
                if not isinstance(existing, list):
                    existing = []
                    toml_data["hooks"] = existing

                # Remove old hooks belonging to this plugin to keep reinstalls idempotent.
                plugin_prefix = f'cd "{plugin_dir}" &&'
                existing[:] = [
                    h for h in existing if plugin_prefix not in h.get("command", "")
                ]
                existing.extend(kimi_hooks)
                config.save_toml_config(toml_data)
                result["hooks_installed"] = len(kimi_hooks)
                console.print(
                    f"[green]Installed {len(kimi_hooks)} hook(s) from {plugin_name}[/green]"
                )
            else:
                console.print(f"[dim]No command hooks found in {plugin_name}[/dim]")

    # Copy skills
    if layout["skills_dirs"]:
        installed = _copy_skills(layout["skills_dirs"], config.skills_dir, plugin_name)
        result["skills_installed"] = installed
        if installed:
            console.print(f"[green]Installed skills: {', '.join(installed)}[/green]")

    console.print(
        f"\n[bold green]Plugin '{plugin_name}' installed successfully.[/bold green]"
    )
    console.print("[dim]Restart Kimi CLI for hook changes to take effect.[/dim]")
    return result
