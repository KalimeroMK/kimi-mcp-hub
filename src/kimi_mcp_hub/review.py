"""Collect the diff context for a pre-PR code review.

The review skills know how to *judge* a diff; nothing in the hub knew how to
*produce* one. This module answers the mechanical questions -- which base
branch, what changed against it, how big the diff is -- so every review starts
from the same deterministic context instead of an agent improvising with git.

Read-only by construction: every git invocation here inspects, none mutate.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

GIT_TIMEOUT = 30
# `gh pr view` is a network call, so it gets a much shorter leash than git.
GH_TIMEOUT = 5

DEFAULT_MAX_DIFF_LINES = 2000

# Above this many changed lines the diff body is skipped rather than read into
# memory -- a vendored dependency bump or lockfile churn can be millions.
HARD_LINE_CEILING = 200_000
# A line cap alone does not bound memory: one minified-JS line can be megabytes.
MAX_DIFF_BYTES = 4 * 1024 * 1024
# `git status -uall` in a repo with an unignored node_modules returns tens of
# thousands of entries; nobody reviews that list.
MAX_STATUS_ENTRIES = 200
MAX_UNTRACKED_DIFFS = 50

# Tried in order when neither `gh` nor origin/HEAD can name the base branch.
FALLBACK_BASES = (
    "origin/main",
    "origin/master",
    "origin/develop",
    "origin/trunk",
    "main",
    "master",
)

# A range this long usually means the base branch is wrong (e.g. a gitflow
# branch cut from `develop` compared against `master`).
SUSPICIOUS_COMMIT_COUNT = 50

# Pinned config so a developer's ~/.gitconfig cannot change the output:
# color.ui=always would leak ANSI escapes into the diff, quotepath would
# octal-escape non-ASCII paths, and an external diff driver (delta,
# difftastic) would replace the unified diff entirely.
GIT_BASE = [
    "git",
    "-c",
    "color.ui=false",
    "-c",
    "core.quotepath=false",
    "-c",
    "diff.external=",
    "--no-pager",
]

_GIT_ERRORS = (
    subprocess.CalledProcessError,
    subprocess.TimeoutExpired,
    FileNotFoundError,
    OSError,
)


@dataclass
class ChangedFile:
    """One file in the diff.

    ``added`` and ``removed`` are ``None`` for binary files, because git
    reports ``-`` instead of a line count for those. A pure rename legitimately
    reports ``0``/``0``.
    """

    path: str
    status: str
    added: int | None
    removed: int | None
    old_path: str | None = None


@dataclass
class ReviewContext:
    """Everything a reviewer needs to know before reading the diff."""

    repo_root: str
    head_branch: str
    base_ref: str
    base_source: str
    merge_base: str
    diff_scope: str = ""
    files: list[ChangedFile] = field(default_factory=list)
    diff: str = ""
    diff_truncated: bool = False
    diff_total_lines: int = 0
    omitted_files: list[str] = field(default_factory=list)
    dirty: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    includes_uncommitted: bool = False
    pr: dict | None = None
    warnings: list[str] = field(default_factory=list)


def _run(args: list[str], cwd: Path | str, *, check: bool = True, timeout: int = GIT_TIMEOUT) -> str | None:
    """Run a command and return its stdout, or ``None`` if it failed.

    Never raises: a missing tool, a timeout, and a non-zero exit all mean the
    same thing to every caller here -- the information is not available.
    """
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=check,
        )
    except _GIT_ERRORS:
        return None
    return result.stdout


def _git(args: list[str], cwd: Path | str, *, check: bool = True) -> str | None:
    """Run a git command with output-affecting config pinned."""
    return _run([*GIT_BASE, *args], cwd, check=check)


def _stat(value: str) -> int | None:
    """Parse a --numstat count. Binary files report ``-``."""
    try:
        return int(value)
    except ValueError:
        return None


def find_repo_root(cwd: Path | str | None = None) -> Path:
    """Locate the git work tree containing ``cwd``.

    Uses ``git rev-parse --show-toplevel`` rather than walking for a ``.git``
    directory, so linked worktrees and submodules resolve correctly.

    Args:
        cwd: Directory to start from. Defaults to the process working directory.

    Returns:
        Absolute path to the work tree root.

    Raises:
        ValueError: If ``cwd`` is not inside a git work tree.
    """
    start = Path(cwd) if cwd else Path.cwd()
    if (_git(["rev-parse", "--is-inside-work-tree"], start) or "").strip() != "true":
        raise ValueError(f"not a git work tree: {start}")
    out = _git(["rev-parse", "--show-toplevel"], start)
    if out is None:
        raise ValueError(f"not a git repository: {start}")
    return Path(out.strip())


def _ref_exists(ref: str, root: Path) -> bool:
    """Whether ``ref`` resolves to a commit."""
    return _git(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], root) is not None


def _head_branch(root: Path) -> str:
    """Current branch name, or a readable label when HEAD is detached.

    ``symbolic-ref`` is used instead of ``rev-parse --abbrev-ref``, which
    returns the literal string "HEAD" when detached, and instead of
    ``branch --show-current``, which needs git 2.22.
    """
    name = (_git(["symbolic-ref", "-q", "--short", "HEAD"], root) or "").strip()
    if name:
        return name
    sha = (_git(["rev-parse", "--short", "HEAD"], root) or "").strip()
    return f"HEAD detached at {sha}" if sha else "HEAD"


def _origin_is_github(root: Path) -> bool:
    """Whether origin points at GitHub, so `gh` is worth invoking at all."""
    url = (_git(["remote", "get-url", "origin"], root) or "").strip()
    return "github.com" in url or "github" in url.split("/")[0]


def _gh_pr(root: Path) -> dict | None:
    """Metadata for the PR open on this branch, if `gh` can tell us.

    Returns ``None`` when gh is absent, unauthenticated, the remote is not
    GitHub, or no PR exists -- all normal for a *pre*-PR review.
    """
    if not shutil.which("gh") or not _origin_is_github(root):
        return None
    out = _run(
        ["gh", "pr", "view", "--json", "baseRefName,number,title,url,isCrossRepository"],
        root,
        timeout=GH_TIMEOUT,
    )
    if not out:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    return data if data.get("baseRefName") else None


def _detect_base_ref(root: Path, pr: dict | None) -> tuple[str, str]:
    """Resolve the base branch, most authoritative source first."""
    if pr:
        name = pr["baseRefName"]
        for candidate in (f"origin/{name}", name):
            if _ref_exists(candidate, root):
                return candidate, "gh-pr"

    symref = (_git(["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"], root) or "").strip()
    if symref and _ref_exists(symref, root):
        return symref, "origin-head"

    for candidate in FALLBACK_BASES:
        if _ref_exists(candidate, root):
            return candidate, "fallback"

    raise ValueError(
        "could not determine a base branch: no open PR, origin/HEAD is unset, and none of "
        f"{', '.join(FALLBACK_BASES)} exist. Pass an explicit base."
    )


def detect_base_ref(cwd: Path | str | None = None, use_gh: bool = True) -> tuple[str, str]:
    """Resolve the base branch for the branch checked out in ``cwd``.

    Args:
        cwd: Directory inside the repository. Defaults to the working directory.
        use_gh: Consult `gh` for an open PR before falling back to git refs.

    Returns:
        ``(ref, source)`` where source is one of ``gh-pr``, ``origin-head``,
        or ``fallback``.

    Raises:
        ValueError: If ``cwd`` is not a work tree or no base can be determined.
    """
    root = find_repo_root(cwd)
    return _detect_base_ref(root, _gh_pr(root) if use_gh else None)


def _parse_name_status(out: str) -> list[tuple[str, str | None, str]]:
    """Parse ``git diff --name-status -z`` into (status, old_path, path).

    Records are NUL-separated. A rename or copy spends three tokens
    (``R100``, old, new); everything else spends two.
    """
    tokens = out.split("\0")
    records: list[tuple[str, str | None, str]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        if not status:
            index += 1
            continue
        if status[0] in ("R", "C") and index + 2 < len(tokens):
            records.append((status, tokens[index + 1], tokens[index + 2]))
            index += 3
        elif index + 1 < len(tokens):
            records.append((status, None, tokens[index + 1]))
            index += 2
        else:
            break
    return records


def _parse_numstat(out: str) -> list[tuple[int | None, int | None]]:
    """Parse ``git diff --numstat -z`` into (added, removed) pairs.

    A rename leaves the path field empty and spends two extra tokens, which
    are skipped -- the paths come from --name-status instead.
    """
    tokens = out.split("\0")
    counts: list[tuple[int | None, int | None]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token:
            index += 1
            continue
        parts = token.split("\t")
        if len(parts) < 2:
            index += 1
            continue
        counts.append((_stat(parts[0]), _stat(parts[1])))
        # Empty third field means the two following tokens are old/new paths.
        index += 3 if len(parts) > 2 and parts[2] == "" else 1
    return counts


def _changed_files(root: Path, spec: str) -> list[ChangedFile]:
    """List the files in ``spec`` with their status letter and line counts.

    ``--numstat`` carries the counts but no status letter and ``--name-status``
    the reverse, and the two formats do not combine in one invocation, so both
    run and are zipped by position -- git emits the same file order for both.
    """
    flags = ["--no-color", "--no-ext-diff", "-M", "-z", spec]
    names = _git(["diff", "--name-status", *flags], root)
    if not names:
        return []
    numbers = _parse_numstat(_git(["diff", "--numstat", *flags], root) or "")

    files: list[ChangedFile] = []
    for index, (status, old_path, path) in enumerate(_parse_name_status(names)):
        added, removed = numbers[index] if index < len(numbers) else (None, None)
        files.append(
            ChangedFile(
                path=path,
                status=status,
                added=added,
                removed=removed,
                old_path=old_path,
            )
        )
    return files


def _status_entries(root: Path) -> tuple[list[str], list[str], int]:
    """Porcelain status lines.

    Returns:
        ``(entries, untracked_paths, total)`` where entries and untracked are
        capped -- a repo with an unignored node_modules reports tens of
        thousands of paths, and nobody reviews that list.
    """
    out = _git(["status", "--porcelain", "-uall"], root) or ""
    lines = [line for line in out.splitlines() if line.strip()]
    capped = lines[:MAX_STATUS_ENTRIES]
    untracked = [line[3:] for line in capped if line.startswith("??")]
    return capped, untracked, len(lines)


def _untracked_files_diff(
    root: Path, paths: list[str], budget: int
) -> tuple[list[ChangedFile], str, list[str]]:
    """Diff untracked files against nothing.

    ``git diff`` never shows untracked files at any scope, so a brand-new file
    -- the normal case when reviewing before committing -- would otherwise be
    invisible. ``--no-index`` against the null device fills that gap.

    Returns:
        ``(files, diff, omitted)``.
    """
    files: list[ChangedFile] = []
    parts: list[str] = []
    omitted: list[str] = []
    used = 0

    for path in paths[:MAX_UNTRACKED_DIFFS]:
        out = _git(
            ["diff", "--no-color", "--no-ext-diff", "--no-index", "--", os.devnull, path],
            root,
            # --no-index implies --exit-code, so a difference exits 1.
            check=False,
        )
        if out is None:
            omitted.append(path)
            continue
        binary = "Binary files" in out.split("\n", 1)[0] if out else False
        added = None if binary else sum(
            1 for line in out.splitlines() if line.startswith("+") and not line.startswith("+++")
        )
        files.append(
            ChangedFile(
                path=path,
                status="??",
                added=added,
                removed=None if binary else 0,
            )
        )
        line_count = len(out.splitlines())
        if used + line_count > budget:
            omitted.append(path)
            continue
        parts.append(out)
        used += line_count

    omitted.extend(paths[MAX_UNTRACKED_DIFFS:])
    return files, "".join(parts), omitted


def _truncate_diff(diff: str, max_lines: int) -> tuple[str, bool, int]:
    """Cut a unified diff at a file boundary.

    Cutting mid-hunk would hand the reader something that parses as a diff but
    describes a change that was never made, so whole per-file chunks are kept.

    Returns:
        ``(diff, truncated, chunks_omitted)``.
    """
    lines = diff.splitlines(keepends=True)
    if max_lines <= 0 or len(lines) <= max_lines:
        return diff, False, 0

    chunks: list[list[str]] = []
    for line in lines:
        if line.startswith("diff --git ") or not chunks:
            chunks.append([])
        chunks[-1].append(line)

    kept: list[str] = []
    used = 0
    for index, chunk in enumerate(chunks):
        if used + len(chunk) <= max_lines:
            kept.extend(chunk)
            used += len(chunk)
            continue
        if used == 0:
            # One file bigger than the whole budget: keep a prefix so the
            # reader sees something rather than nothing.
            kept.extend(chunk[:max_lines])
            return "".join(kept), True, len(chunks) - index - 1
        return "".join(kept), True, len(chunks) - index
    return "".join(kept), False, 0


def _base_sanity_warnings(root: Path, base_ref: str, base_source: str, merge_base: str) -> list[str]:
    """Warn about the ways a detected base branch is commonly wrong."""
    warnings: list[str] = []

    if base_source == "fallback" and not base_ref.startswith("origin/"):
        age = (_git(["log", "-1", "--format=%cr", base_ref], root) or "unknown age").strip()
        warnings.append(
            f"{base_ref} is a local branch last committed {age} -- if it is stale the diff "
            "will include other people's merged commits. Pass an explicit base to be sure."
        )

    if merge_base:
        bases = (_git(["merge-base", "--all", base_ref, "HEAD"], root) or "").split()
        if len(bases) > 1:
            warnings.append(
                f"{len(bases)} merge bases with {base_ref} (criss-cross history) -- git picked one"
            )
        count = (_git(["rev-list", "--count", f"{merge_base}..HEAD"], root) or "").strip()
        if count.isdigit() and int(count) > SUSPICIOUS_COMMIT_COUNT:
            warnings.append(
                f"{count} commits between {base_ref} and HEAD -- that is a lot for one PR, "
                "so the base may be wrong (a branch cut from develop compared against master, say)"
            )
    return warnings


def collect_context(
    base: str | None = None,
    cwd: Path | str | None = None,
    max_diff_lines: int = DEFAULT_MAX_DIFF_LINES,
    include_uncommitted: bool = False,
    use_gh: bool = True,
) -> ReviewContext:
    """Gather the review context for the current branch.

    The default scope is what the PR would actually contain -- the committed
    range ``merge_base..HEAD``, which is the same set GitHub shows under
    "Files changed". Uncommitted work is reported separately unless
    ``include_uncommitted`` widens the diff to the working tree; if there are
    no committed changes at all, it widens automatically, because that is the
    normal state of a branch that has not been committed yet.

    Args:
        base: Base ref to compare against. Auto-detected when omitted.
        cwd: Directory inside the repository. Defaults to the working directory.
        max_diff_lines: Line budget for the diff body. Non-positive disables truncation.
        include_uncommitted: Diff the working tree instead of just HEAD.
        use_gh: Consult `gh` for an open PR. Disable for hermetic or offline runs.

    Returns:
        The populated :class:`ReviewContext`.

    Raises:
        ValueError: If ``cwd`` is not a work tree, the repository has no
            commits, ``base`` does not exist, or no base can be detected.
    """
    root = find_repo_root(cwd)
    warnings: list[str] = []

    if not _ref_exists("HEAD", root):
        raise ValueError(f"repository has no commits yet: {root}")

    pr = _gh_pr(root) if use_gh else None
    if pr and pr.get("isCrossRepository"):
        warnings.append(
            "the PR comes from a fork -- origin/<base> may not be the repository it targets"
        )

    if base:
        if not _ref_exists(base, root):
            raise ValueError(f"base ref does not exist: {base}")
        base_ref, base_source = base, "explicit"
    else:
        base_ref, base_source = _detect_base_ref(root, pr)

    shallow = (_git(["rev-parse", "--is-shallow-repository"], root) or "").strip() == "true"
    merge_base = (_git(["merge-base", base_ref, "HEAD"], root) or "").strip()

    if merge_base:
        committed_spec = f"{merge_base}..HEAD"
    elif shallow:
        # In a --depth 1 clone the base and HEAD share no ancestor locally, so
        # diffing against the base tip would produce garbage.
        committed_spec = "HEAD~1..HEAD" if _ref_exists("HEAD~1", root) else "HEAD"
        warnings.append(
            f"shallow clone: no merge base with {base_ref}, showing the last commit only. "
            "Run `git fetch --unshallow` for full review context."
        )
    else:
        committed_spec = f"{base_ref}..HEAD"
        warnings.append(
            f"no common ancestor with {base_ref} -- comparing against its tip directly"
        )

    if shallow and merge_base:
        warnings.append("shallow clone -- the merge base may be wrong")

    warnings.extend(_base_sanity_warnings(root, base_ref, base_source, merge_base))

    base_sha = (_git(["rev-parse", base_ref], root) or "x").strip()
    head_sha = (_git(["rev-parse", "HEAD"], root) or "y").strip()
    if base_sha == head_sha:
        warnings.append(
            f"HEAD is identical to {base_ref} -- nothing is committed on top of the base"
        )

    files = _changed_files(root, committed_spec)
    dirty, untracked, dirty_total = _status_entries(root)
    if dirty_total > len(dirty):
        warnings.append(
            f"{dirty_total} uncommitted entries; only the first {len(dirty)} are listed "
            "(is something large unignored?)"
        )

    includes_uncommitted = include_uncommitted
    if not files and dirty and not include_uncommitted:
        includes_uncommitted = True
        warnings.append(
            "no committed changes against the base -- reviewing uncommitted work instead"
        )

    # Diffing a bare commit (no `..HEAD`) compares the working tree against it.
    if includes_uncommitted:
        spec = merge_base or committed_spec
        files = _changed_files(root, spec)
        scope = f"{spec} + worktree"
    else:
        spec = committed_spec
        scope = committed_spec

    total_lines = sum((f.added or 0) + (f.removed or 0) for f in files)
    diff = ""
    truncated = False
    omitted: list[str] = []

    if total_lines > HARD_LINE_CEILING:
        warnings.append(
            f"{total_lines} changed lines exceeds the {HARD_LINE_CEILING}-line ceiling -- "
            "diff body omitted; narrow the review with an explicit base or per directory"
        )
        omitted = [f.path for f in files]
    elif files:
        raw = _git(["diff", "--no-color", "--no-ext-diff", "-M", spec], root) or ""
        if len(raw) > MAX_DIFF_BYTES:
            raw = raw[:MAX_DIFF_BYTES]
            truncated = True
            warnings.append(f"diff body capped at {MAX_DIFF_BYTES} bytes")
        diff, cut, chunks_omitted = _truncate_diff(raw, max_diff_lines)
        truncated = truncated or cut
        if cut and chunks_omitted:
            omitted = [f.path for f in files[len(files) - chunks_omitted :]]
            warnings.append(
                f"diff body truncated to {max_diff_lines} lines; {chunks_omitted} file(s) omitted "
                "from the body -- the file list above is still complete"
            )
        elif cut:
            warnings.append(
                f"diff body truncated to {max_diff_lines} lines partway through the first file -- "
                "raise the line budget to see the rest"
            )

    if includes_uncommitted and untracked:
        budget = max(max_diff_lines - len(diff.splitlines()), 0) if max_diff_lines > 0 else -1
        extra_files, extra_diff, extra_omitted = _untracked_files_diff(
            root, untracked, budget if budget >= 0 else HARD_LINE_CEILING
        )
        files.extend(extra_files)
        total_lines += sum(f.added or 0 for f in extra_files)
        diff = diff + extra_diff
        omitted.extend(extra_omitted)
        if extra_omitted:
            truncated = True
            warnings.append(
                f"{len(extra_omitted)} untracked file(s) listed but not shown in the diff body"
            )
    elif untracked and not includes_uncommitted:
        warnings.append(
            f"{len(untracked)} untracked file(s) are not part of the PR and are not diffed"
        )

    if not files:
        warnings.append("no changes detected")

    return ReviewContext(
        repo_root=str(root),
        head_branch=_head_branch(root),
        base_ref=base_ref,
        base_source=base_source,
        merge_base=merge_base,
        diff_scope=scope,
        files=files,
        diff=diff,
        diff_truncated=truncated,
        diff_total_lines=total_lines,
        omitted_files=omitted,
        dirty=dirty,
        untracked=untracked,
        includes_uncommitted=includes_uncommitted,
        pr=pr,
        warnings=warnings,
    )


def _fence(text: str) -> str:
    """Pick a code fence long enough to survive backticks inside ``text``.

    Diffs of markdown files contain fences of their own, which would otherwise
    close the block early.
    """
    longest = 0
    for line in text.splitlines():
        stripped = line.lstrip("+- ")
        if stripped.startswith("```"):
            longest = max(longest, len(stripped) - len(stripped.lstrip("`")))
    return "`" * max(3, longest + 1)


def render_text(ctx: ReviewContext) -> str:
    """Render a review context as the markdown block an agent reads.

    Args:
        ctx: Context returned by :func:`collect_context`.

    Returns:
        Markdown text: header, file list, uncommitted files, warnings, diff.
    """
    out = [
        "# Pre-PR review context",
        "",
        f"Repo:       {ctx.repo_root}",
        f"Branch:     {ctx.head_branch}",
        f"Base:       {ctx.base_ref}  (via {ctx.base_source})",
    ]
    if ctx.merge_base:
        out.append(f"Merge base: {ctx.merge_base}")
    if ctx.pr:
        out.append(
            f"Open PR:    #{ctx.pr.get('number')} {ctx.pr.get('title')}  {ctx.pr.get('url')}"
        )
    out.extend([f"Scope:      {ctx.diff_scope}", ""])

    out.append(f"## Changed files ({len(ctx.files)}, {ctx.diff_total_lines} lines)")
    if ctx.files:
        for f in ctx.files:
            added = "bin" if f.added is None else f"+{f.added}"
            removed = "bin" if f.removed is None else f"-{f.removed}"
            rename = f"  (was {f.old_path})" if f.old_path else ""
            out.append(f"{f.status:<5}{added:>8}{removed:>8}  {f.path}{rename}")
    else:
        out.append("(none)")
    out.append("")

    if ctx.dirty:
        included = "in the diff" if ctx.includes_uncommitted else "NOT part of the PR"
        out.append(f"## Uncommitted ({included})")
        out.extend(ctx.dirty)
        out.append("")

    if ctx.omitted_files:
        out.append(f"## Not shown in the diff body ({len(ctx.omitted_files)})")
        out.extend(f"- {path}" for path in ctx.omitted_files)
        out.append("")

    if ctx.warnings:
        out.append("## Warnings")
        out.extend(f"- {w}" for w in ctx.warnings)
        out.append("")

    if ctx.diff:
        fence = _fence(ctx.diff)
        out.extend(["## Diff", f"{fence}diff", ctx.diff.rstrip("\n"), fence])

    return "\n".join(out) + "\n"
