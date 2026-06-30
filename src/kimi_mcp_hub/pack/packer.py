"""Pack a repository into a single AI-friendly markdown file."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Any


def _match_pattern(rel: str, parts: list[str], pat: str) -> bool:
    """Match a gitignore-style or glob pattern against a relative path.

    Supports:
    - ``**`` recursive globs (e.g. ``**/*.py``)
    - Patterns without ``/`` match any path component (e.g. ``*.py`` matches
      ``a.py``, ``src/a.py`` and ``src/deep/a.py``)
    - A leading ``/`` anchors the pattern to the repository root
    - A trailing ``/`` restricts matches to directories
    """
    if pat.endswith("/"):
        name = pat.rstrip("/")
        is_anchored = name.startswith("/")
        name = name.lstrip("/")
        if is_anchored:
            return rel == name or rel.startswith(name + "/")
        return name in parts or rel.startswith(name + "/")

    pat = pat.lstrip("/")
    if "/" in pat or "**" in pat:
        return _match_glob_parts(pat.split("/"), parts)

    for part in parts:
        if fnmatch(part, pat):
            return True
    return False


def _match_glob_parts(pat_parts: list[str], path_parts: list[str]) -> bool:
    """Match ``pat_parts`` against ``path_parts`` from the start.

    ``**`` in the pattern matches zero or more path components. Other parts
    are matched with :func:`fnmatch.fnmatch`.
    """
    pat_n = len(pat_parts)
    path_n = len(path_parts)
    dp = [False] * (path_n + 1)
    dp[path_n] = True

    for i in range(pat_n - 1, -1, -1):
        new_dp = [False] * (path_n + 1)
        for j in range(path_n, -1, -1):
            if pat_parts[i] == "**":
                if j < path_n:
                    new_dp[j] = new_dp[j + 1] or dp[j]
                else:
                    new_dp[j] = dp[j]
            elif j < path_n and fnmatch(path_parts[j], pat_parts[i]):
                new_dp[j] = dp[j + 1]
        dp = new_dp

    return dp[0]


class RepoPacker:
    """Pack a directory tree into a markdown document."""

    def __init__(
        self,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        respect_gitignore: bool = True,
        max_size: int = 500 * 1024,
    ) -> None:
        """Initialize a RepoPacker.

        Args:
            include: Glob patterns for files to include. Defaults to ``["*"]``.
            exclude: Glob patterns for files or directories to exclude.
            respect_gitignore: Whether to respect ``.gitignore`` files.
            max_size: Maximum output size in bytes.
        """
        self.include = include or ["*"]
        self.exclude = exclude or []
        self.respect_gitignore = respect_gitignore
        self.max_size = max_size

    def pack(self, root: Path) -> str:
        """Pack a repository into a markdown document.

        Args:
            root: Path to the repository root directory.

        Returns:
            Markdown string containing the file tree and file contents.

        Raises:
            ValueError: If ``root`` does not exist or is not a directory.
        """
        root = root.resolve()
        if not root.exists():
            raise ValueError(f"root does not exist: {root}")
        if not root.is_dir():
            raise ValueError(f"root is not a directory: {root}")

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

            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "\0" in content:
                continue

            file_header = f"### `{self._relative(root, file_path)}`"
            file_lines = ["", file_header, ""]
            lang = self._detect_language(file_path)
            file_lines.append(f"```{lang}")
            file_lines.append(content)
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

        def walk(path: Path) -> None:
            rel = self._relative(root, path)
            if gitignore is not None and gitignore.match_file(rel):
                return
            if self._matches_exclude(rel):
                return

            if path.is_file():
                if self._matches_include(rel):
                    files.append(path)
                return

            for child in sorted(path.iterdir()):
                walk(child)

        for child in sorted(root.iterdir()):
            walk(child)
        return files

    def _load_gitignore(self, root: Path) -> Any:
        gitignore_path = root / ".gitignore"
        lines = gitignore_path.read_text(encoding="utf-8").splitlines() if gitignore_path.exists() else []

        try:
            import pathspec
            return pathspec.PathSpec.from_lines("gitwildmatch", lines)
        except ImportError:
            return _FallbackGitignore(lines)

    def _matches_include(self, rel: str) -> bool:
        parts = rel.split("/")
        return any(_match_pattern(rel, parts, pat) for pat in self.include)

    def _matches_exclude(self, rel: str) -> bool:
        parts = rel.split("/")
        return any(_match_pattern(rel, parts, pat) for pat in self.exclude)

    def _is_text(self, path: Path) -> bool:
        try:
            with path.open("rb") as f:
                chunk = f.read(8192)
            if b"\0" in chunk:
                return False
            chunk.decode("utf-8")
            return True
        except (OSError, UnicodeDecodeError):
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
    """Minimal fallback that skips common non-source directories and simple .gitignore patterns."""

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
        ".eggs",
    }

    def __init__(self, patterns: list[str] | None = None):
        self.patterns: list[str] = []
        for line in patterns or []:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            self.patterns.append(line)

    def match_file(self, rel: str) -> bool:
        parts = rel.split("/")
        for part in parts:
            if part in self.SKIP_DIRS or part.endswith(".egg-info"):
                return True

        for pat in self.patterns:
            if _match_pattern(rel, parts, pat):
                return True
        return False
