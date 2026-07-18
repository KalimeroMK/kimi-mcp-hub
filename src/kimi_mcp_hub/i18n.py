"""Localization support via stdlib gettext.

Language resolution order:
1. ``KIMI_MCP_HUB_LANG`` env var (explicit override, e.g. ``mk``, ``en``)
2. Standard gettext env vars (``LANGUAGE``, ``LC_ALL``, ``LC_MESSAGES``, ``LANG``)
3. Fallback: English (the msgid itself)

Translations live in ``locale/<lang>/LC_MESSAGES/kimi-mcp-hub.mo`` inside the
package. Wrap user-facing strings with ``_()``:

    from ..i18n import _
    console.print(_("Setup complete!"))

Use ``.format()`` (not f-strings) for interpolated values so the msgid stays
stable:

    _("Synced {n} project MCP server(s)").format(n=len(servers))
"""

from __future__ import annotations

import gettext
import os
from pathlib import Path

LOCALEDIR = Path(__file__).parent / "locale"
DOMAIN = "kimi-mcp-hub"


def _load_translation() -> gettext.NullTranslations:
    override = os.environ.get("KIMI_MCP_HUB_LANG")
    languages = [override] if override else None
    return gettext.translation(
        DOMAIN, localedir=LOCALEDIR, languages=languages, fallback=True
    )


_translation = _load_translation()
_ = _translation.gettext
