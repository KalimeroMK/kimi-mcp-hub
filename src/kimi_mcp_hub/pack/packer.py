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
            if not self._is_text(path):
                continue
            rel = self._relative(root, path)
            if self.respect_gitignore and rel == ".gitignore":
                continue
            if gitignore is not None and gitignore.match_file(rel):
                continue
            if not self._matches_include(rel):
                continue
            if self._matches_exclude(rel):
                continue
            files.append(path)
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
        "dist",
        "build",
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
        from fnmatch import fnmatch

        parts = rel.split("/")
        for part in parts:
            if part in self.SKIP_DIRS or part.endswith(".egg-info"):
                return True

        for pat in self.patterns:
            if self._match_pattern(rel, parts, pat):
                return True
        return False

    def _match_pattern(self, rel: str, parts: list[str], pat: str) -> bool:
        from fnmatch import fnmatch

        # Directory-only pattern.
        if pat.endswith("/"):
            name = pat.rstrip("/")
            if name in parts:
                return True
            if rel.startswith(name + "/"):
                return True
            return False

        # Anchored pattern (contains / or starts with /).
        raw_pat = pat.lstrip("/")
        if "/" in pat:
            if fnmatch(rel, raw_pat):
                return True
            if not any(c in raw_pat for c in "*?[") and (rel == raw_pat or rel.startswith(raw_pat + "/")):
                return True
            return False

        # Unanchored pattern: match any path component or the whole relative path.
        for part in parts:
            if fnmatch(part, pat):
                return True
        if fnmatch(rel, pat):
            return True
        return False
