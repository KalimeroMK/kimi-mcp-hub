# Repo Packer (`kimi-mcp-hub pack`) Design

## Overview

A `repomix`-inspired command that packs a codebase into a single AI-friendly markdown file. Useful for feeding a repository to an LLM with limited context, sharing code snapshots, or creating offline context bundles.

## Goals

- Produce a single markdown file containing the repository structure and file contents.
- Respect `.gitignore` so generated files and dependencies are excluded by default.
- Skip binary files automatically.
- Allow size limits to avoid accidentally creating huge files.
- Provide optional include/exclude glob filters.

## Non-Goals

- No LLM summarization of the codebase in the first version.
- No compression or encryption.
- No remote upload.

## Command Interface

```bash
kimi-mcp-hub pack
kimi-mcp-hub pack --output context.md
kimi-mcp-hub pack --max-size 500KB
kimi-mcp-hub pack --include "*.py" --exclude "tests/"
kimi-mcp-hub pack --no-gitignore
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output`, `-o` | `packed-repo.md` | Output file path |
| `--max-size` | `500KB` | Maximum total output size (e.g., `100KB`, `1MB`) |
| `--include` | `*` | Glob patterns to include (comma-separated) |
| `--exclude` | none | Glob patterns to exclude (comma-separated) |
| `--no-gitignore` | false | Ignore `.gitignore` rules |

## Output Format

```markdown
# Repository Pack: my-project

## File Tree

```
my-project/
├── README.md
├── pyproject.toml
└── src/
    └── kimi_mcp_hub/
        └── cli.py
```

## Files

### `README.md`

```markdown
# Kimi MCP Hub
...
```

### `src/kimi_mcp_hub/cli.py`

```python
...
```
```

## Size Handling

- If the output exceeds `--max-size`, the packer stops adding files and appends a warning note explaining which files were omitted.
- Size is measured in bytes of the output markdown file.

## Binary Detection

A file is considered binary if:
- It contains a null byte (`\0`) in the first 8KB, OR
- It fails UTF-8 decoding.

Binary files are listed in the file tree but skipped in the Files section.

## Implementation Notes

- New module: `src/kimi_mcp_hub/pack/packer.py`
- CLI integration: add `pack` command in `src/kimi_mcp_hub/cli.py`
- Tests: `tests/test_pack.py`
- Use `pathspec` library for `.gitignore` matching (already commonly available; otherwise implement minimal glob matching).
