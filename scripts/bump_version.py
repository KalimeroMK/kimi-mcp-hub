#!/usr/bin/env python3
"""Bump the project version across all manifest files.

Single source of truth: ``src/kimi_mcp_hub/__init__.py`` (``__version__``).

Usage:
    python scripts/bump_version.py 0.4.0
    python scripts/bump_version.py --check   # only verify all files are in sync
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_PY = ROOT / "src" / "kimi_mcp_hub" / "__init__.py"
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_JSON = ROOT / "package.json"
PLUGIN_JSON = ROOT / "kimi.plugin.json"
SKILL_VERSION = (
    ROOT
    / "src"
    / "kimi_mcp_hub"
    / "skills"
    / "kimi-mcp-hub-status"
    / ".kimi-mcp-hub-version"
)

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+([.-].+)?$")


def read_source_version() -> str:
    match = re.search(
        r'^__version__\s*=\s*"([^"]+)"', INIT_PY.read_text(encoding="utf-8"), re.M
    )
    if not match:
        sys.exit(f"Could not find __version__ in {INIT_PY}")
    return match.group(1)


def current_versions() -> dict[Path, str]:
    pyproject = re.search(
        r'^version\s*=\s*"([^"]+)"', PYPROJECT.read_text(encoding="utf-8"), re.M
    ).group(1)
    return {
        INIT_PY: read_source_version(),
        PYPROJECT: pyproject,
        PACKAGE_JSON: json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["version"],
        PLUGIN_JSON: json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"],
        SKILL_VERSION: SKILL_VERSION.read_text(encoding="utf-8").strip(),
    }


def set_version(new: str) -> None:
    init_text = INIT_PY.read_text(encoding="utf-8")
    INIT_PY.write_text(
        re.sub(r'^__version__\s*=\s*"[^"]+"', f'__version__ = "{new}"', init_text, count=1, flags=re.M),
        encoding="utf-8",
    )

    pyproject = PYPROJECT.read_text(encoding="utf-8")
    PYPROJECT.write_text(
        re.sub(r'^version\s*=\s*"[^"]+"', f'version = "{new}"', pyproject, count=1, flags=re.M),
        encoding="utf-8",
    )

    for json_path in (PACKAGE_JSON, PLUGIN_JSON):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        data["version"] = new
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    SKILL_VERSION.write_text(new + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--check":
        versions = current_versions()
        unique = set(versions.values())
        for path, ver in versions.items():
            print(f"  {path.relative_to(ROOT)}: {ver}")
        if len(unique) == 1:
            print("All versions in sync.")
            return 0
        print("ERROR: versions out of sync!")
        return 1

    if len(sys.argv) != 2 or not VERSION_RE.match(sys.argv[1]):
        sys.exit("Usage: bump_version.py <x.y.z> | --check")

    new = sys.argv[1]
    set_version(new)
    print(f"Bumped all manifests to {new}:")
    for path, ver in current_versions().items():
        print(f"  {path.relative_to(ROOT)}: {ver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
