# Repo Packer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `kimi-mcp-hub pack` command that packs a codebase into a single AI-friendly markdown file.

**Architecture:** A focused `RepoPacker` class in `src/kimi_mcp_hub/pack/packer.py` handles directory walking, `.gitignore` filtering, binary detection, markdown generation, and size limiting. The CLI command in `src/kimi_mcp_hub/cli.py` parses options and delegates to the packer.

**Tech Stack:** Python 3.11+, `pathspec` for `.gitignore` parsing, `fnmatch` for glob filters, pytest for tests.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/kimi_mcp_hub/pack/packer.py` | New. Core packing logic. |
| `src/kimi_mcp_hub/pack/__init__.py` | New. Package init, exports `RepoPacker`. |
| `src/kimi_mcp_hub/cli.py` | Modified. Adds `pack` command. |
| `tests/test_pack.py` | New. Unit tests for packer and CLI. |

---

## Task 1: Core packer with binary detection and markdown output

**Files:**
- Create: `src/kimi_mcp_hub/pack/__init__.py`
- Create: `src/kimi_mcp_hub/pack/packer.py`
- Test: `tests/test_pack.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pack.py`:

```python
"""Tests for the repo packer."""

from pathlib import Path

import pytest

from kimi_mcp_hub.pack.packer import RepoPacker


class TestRepoPacker:
    def test_packs_text_files(self, tmp_path):
        (tmp_path / "README.md").write_text("# Hello\n", encoding="utf-8")
        (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")

        result = RepoPacker().pack(tmp_path)

        assert "# Repository Pack" in result
        assert "README.md" in result
        assert "main.py" in result
        assert "# Hello" in result
        assert "print('hi')" in result

    def test_skips_binary_files(self, tmp_path):
        (tmp_path / "text.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02\x03")

        result = RepoPacker().pack(tmp_path)

        assert "text.txt" in result
        assert "binary.bin" not in result

    def test_respects_gitignore(self, tmp_path):
        (tmp_path / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
        (tmp_path / "public.txt").write_text("ok", encoding="utf-8")
        (tmp_path / "secret.txt").write_text("hidden", encoding="utf-8")

        result = RepoPacker().pack(tmp_path)

        assert "public.txt" in result
        assert "secret.txt" not in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate && python -m pytest tests/test_pack.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'kimi_mcp_hub.pack'`

- [ ] **Step 3: Implement RepoPacker**

Create `src/kimi_mcp_hub/pack/__init__.py`:

```python
"""Repo packing utilities."""

from .packer import RepoPacker

__all__ = ["RepoPacker"]
```

Create `src/kimi_mcp_hub/pack/packer.py`:

```python
"""Pack a repository into a single AI-friendly markdown file."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class RepoPacker:
    """Pack a directory tree into a markdown document."""

    def __init__(
        self,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        respect_gitignore: bool = True,
        max_size: int = 500 * 1024,
    ):
        self.include = include or ["*"]
        self.exclude = exclude or []
        self.respect_gitignore = respect_gitignore
        self.max_size = max_size

    def pack(self, root: Path) -> str:
        root = root.resolve()
        lines: list[str] = [
            f"# Repository Pack: {root.name}",
            "",
            "## File Tree",
            "",
            "```",
        ]

        gitignore = self._load_gitignore(root) if self.respect_gitignore else None
        files = self._collect_files(root, gitignore)

        lines.extend(self._build_tree(root, files))
        lines.append("```")
        lines.append("")
        lines.append("## Files")
        lines.append("")

        content_size = sum(len(line) + 1 for line in lines)
        omitted: list[str] = []

        for file_path in files:
            if not self._is_text(file_path):
                continue

            file_header = f"### `{self._relative(root, file_path)}`"
            file_lines = ["", file_header, ""]
            lang = self._detect_language(file_path)
            file_lines.append(f"```{lang}")
            file_lines.append(file_path.read_text(encoding="utf-8"))
            file_lines.append("```")

            added = sum(len(line) + 1 for line in file_lines)
            if content_size + added > self.max_size:
                omitted.append(self._relative(root, file_path))
                continue

            lines.extend(file_lines)
            content_size += added

        if omitted:
            lines.append("")
            lines.append("> **Warning:** omitted files due to size limit: " + ", ".join(omitted))

        return "\n".join(lines) + "\n"

    def _collect_files(self, root: Path, gitignore: Any | None) -> list[Path]:
        files: list[Path] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = self._relative(root, path)
            if gitignore is not None and gitignore.match_file(rel):
                continue
            if not self._matches_include(rel):
                continue
            if self._matches_exclude(rel):
                continue
            files.append(path)
        return files

    def _load_gitignore(self, root: Path) -> Any:
        try:
            import pathspec
        except ImportError:
            pathspec = None

        gitignore_path = root / ".gitignore"
        if gitignore_path.exists() and pathspec is not None:
            lines = gitignore_path.read_text(encoding="utf-8").splitlines()
            return pathspec.PathSpec.from_lines("gitwildmatch", lines)

        # Minimal fallback: skip common directories/files
        return _FallbackGitignore()

    def _matches_include(self, rel: str) -> bool:
        from fnmatch import fnmatch

        return any(fnmatch(rel, pat) or fnmatch(rel, f"**/{pat}") for pat in self.include)

    def _matches_exclude(self, rel: str) -> bool:
        from fnmatch import fnmatch

        return any(fnmatch(rel, pat) or fnmatch(rel, f"**/{pat}") for pat in self.exclude)

    def _is_text(self, path: Path) -> bool:
        try:
            with path.open("rb") as f:
                chunk = f.read(8192)
            if b"\0" in chunk:
                return False
            chunk.decode("utf-8")
            return True
        except Exception:
            return False

    def _relative(self, root: Path, path: Path) -> str:
        return path.relative_to(root).as_posix()

    def _build_tree(self, root: Path, files: list[Path]) -> list[str]:
        if not files:
            return ["(no files)"]

        entries: set[str] = set()
        for file_path in files:
            rel = self._relative(root, file_path)
            parts = rel.split("/")
            for i in range(len(parts)):
                entries.add("/".join(parts[: i + 1]))

        sorted_entries = sorted(entries)
        lines: list[str] = []
        for entry in sorted_entries:
            depth = entry.count("/")
            name = entry.split("/")[-1]
            prefix = "    " * depth
            is_dir = any(
                self._relative(root, f).startswith(entry + "/") for f in files
            )
            lines.append(f"{prefix}{name}{'/' if is_dir else ''}")
        return lines

    def _detect_language(self, path: Path) -> str:
        ext = path.suffix.lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".sh": "bash",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
        }
        return mapping.get(ext, "")


class _FallbackGitignore:
    """Minimal fallback that skips common non-source directories."""

    SKIP_DIRS = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".idea",
        ".vscode",
        "dist",
        "build",
        ".eggs",
        "*.egg-info",
    }

    def match_file(self, rel: str) -> bool:
        parts = rel.split("/")
        for part in parts:
            if part in self.SKIP_DIRS or part.endswith(".egg-info"):
                return True
        return False
```

- [ ] **Step 4: Run test to verify it passes**

```bash
source .venv/bin/activate && python -m pytest tests/test_pack.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kimi_mcp_hub/pack/ tests/test_pack.py
git commit -m "feat(pack): add RepoPacker core logic"
```

---

## Task 2: CLI command `kimi-mcp-hub pack`

**Files:**
- Modify: `src/kimi_mcp_hub/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli.py`:

```python

class TestPackCommand:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        return tmp_path

    def test_pack_creates_output_file(self, home, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Repo\n", encoding="utf-8")
        (repo / "main.py").write_text("print(1)\n", encoding="utf-8")

        runner = CliRunner()
        output = home / "out.md"
        result = runner.invoke(
            main,
            ["pack", str(repo), "--output", str(output)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        assert output.exists()
        text = output.read_text(encoding="utf-8")
        assert "# Repo" in text
        assert "print(1)" in text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate && python -m pytest tests/test_cli.py::TestPackCommand::test_pack_creates_output_file -v
```

Expected: FAIL because `pack` command does not exist.

- [ ] **Step 3: Implement CLI command**

Add to `src/kimi_mcp_hub/cli.py` after the `memory` group definitions:

```python
import re


def _parse_size(size_str: str) -> int:
    """Parse a human-readable size string like '500KB' or '2MB' into bytes."""
    size_str = size_str.strip().upper()
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(B|KB|MB|GB)?$", size_str)
    if not match:
        raise click.BadParameter(f"Invalid size: {size_str}")
    value = float(match.group(1))
    unit = match.group(2) or "B"
    multiplier = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}[unit]
    return int(value * multiplier)


@main.command(name="pack")
@click.argument("path", default=".", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", default="packed-repo.md", help="Output markdown file.")
@click.option(
    "--max-size",
    default="500KB",
    help="Maximum output size (e.g., 100KB, 1MB).",
    callback=lambda _ctx, _param, value: _parse_size(value),
)
@click.option(
    "--include",
    help="Comma-separated glob patterns to include.",
)
@click.option(
    "--exclude",
    help="Comma-separated glob patterns to exclude.",
)
@click.option(
    "--no-gitignore",
    is_flag=True,
    help="Do not respect .gitignore rules.",
)
def pack_command(
    path: Path,
    output: str,
    max_size: int,
    include: str | None,
    exclude: str | None,
    no_gitignore: bool,
):
    """Pack a repository into a single AI-friendly markdown file."""
    from .pack.packer import RepoPacker

    print_header("Repository Pack")
    packer = RepoPacker(
        include=[p.strip() for p in include.split(",")] if include else None,
        exclude=[p.strip() for p in exclude.split(",")] if exclude else None,
        respect_gitignore=not no_gitignore,
        max_size=max_size,
    )
    result = packer.pack(path)
    output_path = Path(output)
    output_path.write_text(result, encoding="utf-8")
    console.print(f"[green]Packed repository to {output_path}[/green]")
    console.print(f"[dim]Size: {len(result)} bytes[/dim]")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
source .venv/bin/activate && python -m pytest tests/test_cli.py::TestPackCommand -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kimi_mcp_hub/cli.py tests/test_cli.py
git commit -m "feat(cli): add kimi-mcp-hub pack command"
```

---

## Task 3: Verify and document

- [ ] **Step 1: Run full test suite**

```bash
source .venv/bin/activate && python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Manual smoke test**

```bash
cd /Users/zoran/PhpstormProjects/kimi-mcp-hub
kimi-mcp-hub pack --output /tmp/pack-test.md
head -50 /tmp/pack-test.md
```

Expected: markdown file with file tree and code blocks.

- [ ] **Step 3: Update README**

Add `kimi-mcp-hub pack` to the Quick Start and All Commands sections.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): document kimi-mcp-hub pack"
```

---

## Self-Review

1. **Spec coverage:**
   - Markdown output with file tree and code blocks → Task 1.
   - `.gitignore` respect → Task 1.
   - Binary skip → Task 1.
   - Size limit → Task 1 and Task 2.
   - CLI options → Task 2.
   - Tests → all tasks.

2. **Placeholder scan:** no TBD/TODO. All code and commands are concrete.

3. **Type consistency:** `RepoPacker.pack()` returns `str`; CLI writes to file. `_parse_size` returns `int`. Consistent.
