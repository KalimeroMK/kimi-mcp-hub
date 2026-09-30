"""Shared test setup.

Most tests isolate themselves by pointing ``HOME`` at ``tmp_path``. That works
on macOS, where ``platformdirs`` derives its paths from the home directory, but
not on Linux: there ``XDG_CONFIG_HOME`` takes precedence, and CI runners set it.
The result was tests quietly writing into the real user config directory and
colliding with each other -- a failure that only ever showed up on Linux.

Clearing the XDG variables makes ``platformdirs`` fall back to ``$HOME``, so the
isolation the tests already ask for actually holds on every platform.
"""

import pytest

_XDG_VARS = (
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
    "XDG_STATE_HOME",
)


@pytest.fixture(autouse=True)
def isolate_home(monkeypatch, tmp_path_factory):
    """Give every test an empty HOME unless it sets its own.

    Hooks read ``~/.kimi-code/config.toml`` and write notes to the configured
    Obsidian vault, so a test that never set HOME was writing ``*-s1.md`` files
    into the developer's real vault. XDG overrides are cleared so the new HOME
    is the one ``platformdirs`` actually uses, and the first-run banner is
    marked as seen so it cannot land in front of ``--json`` output.
    """
    for name in _XDG_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))

    import json

    from kimi_mcp_hub import __version__
    from kimi_mcp_hub._post_install import _get_state_file

    _get_state_file().write_text(json.dumps({"version": __version__}), encoding="utf-8")
