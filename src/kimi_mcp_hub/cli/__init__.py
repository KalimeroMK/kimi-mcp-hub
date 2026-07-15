"""Kimi MCP Hub CLI -- one-click MCP server and skills manager.

The CLI is split into focused modules:

- ``base``          -- the click group, banners, shared prompts
- ``helpers``       -- server/skill/memory install helpers
- ``servers_cmds``  -- init, add, remove, list, auth, test, repair, sync
- ``skills_cmds``   -- install-skill, list-skills, claude-compat
- ``obsidian_cmds`` -- obsidian vault management
- ``memory_cmds``   -- memory add/search/list/forget/config-summary
- ``plugins_cmds``  -- plugin install/uninstall/update
- ``self_cmds``     -- install/update of the hub itself
- ``misc_cmds``     -- status, notify, welcome, doctor, pack

This package ``__init__`` registers all commands and re-exports the public
names that tests and external callers rely on (``kimi_mcp_hub.cli:main``).
"""

from ..registry import (
    AUTO_INSTALL_SERVERS,
    CORE_SKILLS,
    FRONTEND_SKILLS,
    OPTIONAL_SKILL_GROUPS,
    SERVERS,
    SKILLS,
)
from .base import (
    _confirm as _confirm,
    _get_installed_count as _get_installed_count,
    _require_project_root as _require_project_root,
    main,
    print_header,
    print_welcome,
)
from .common import console
from .helpers import (
    _authenticate_server as _authenticate_server,
    _install_memory_hooks as _install_memory_hooks,
    add_server_interactive,
    add_server_with_preflight,
    enable_memory,
    install_skill,
    list_installed_skills,
)
from .self_cmds import (
    _get_venv_info as _get_venv_info,
    _is_dev_install as _is_dev_install,
    _link_venv_binaries as _link_venv_binaries,
    _perform_upgrade as _perform_upgrade,
    _run_pip_upgrade as _run_pip_upgrade,
)
from .skills_cmds import apply_claude_compat_patch

# Command modules -- imported for their click registrations on `main`.
from . import memory_cmds  # noqa: F401,E402
from . import misc_cmds  # noqa: F401,E402
from . import obsidian_cmds  # noqa: F401,E402
from . import plugins_cmds  # noqa: F401,E402
from . import self_cmds  # noqa: F401,E402
from . import servers_cmds  # noqa: F401,E402
from . import skills_cmds  # noqa: F401,E402

__all__ = [
    "main",
    "console",
    "SERVERS",
    "SKILLS",
    "CORE_SKILLS",
    "FRONTEND_SKILLS",
    "OPTIONAL_SKILL_GROUPS",
    "AUTO_INSTALL_SERVERS",
    "print_header",
    "print_welcome",
    "add_server_interactive",
    "add_server_with_preflight",
    "enable_memory",
    "install_skill",
    "list_installed_skills",
    "apply_claude_compat_patch",
]
