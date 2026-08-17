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
def isolate_xdg_dirs(monkeypatch):
    """Ensure XDG overrides cannot pull tests out of their temporary HOME."""
    for name in _XDG_VARS:
        monkeypatch.delenv(name, raising=False)
