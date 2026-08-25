"""Tests for the pre-PR review context collector."""

import json
import subprocess
from unittest import mock

import pytest
from click.testing import CliRunner

from kimi_mcp_hub.cli import main
from kimi_mcp_hub.review import (
    ReviewContext,
    collect_context,
    detect_base_ref,
    find_repo_root,
    render_text,
)

# Pinned so the fixtures behave the same on a machine with no git config and
# on one with signing, a different default branch, or a template dir.
GIT_CONFIG = [
    "-c",
    "init.defaultBranch=main",
    "-c",
    "user.email=test@example.com",
    "-c",
    "user.name=Test User",
    "-c",
    "commit.gpgsign=false",
]


def git(cwd, *args):
    """Run a git command in ``cwd``, failing the test if git fails."""
    return subprocess.run(
        ["git", *GIT_CONFIG, *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def commit(cwd, message):
    git(cwd, "add", "-A")
    git(cwd, "commit", "-m", message)


@pytest.fixture
def repo(tmp_path):
    """A repo on branch `feature`, one commit ahead of nothing yet."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    (root / "base.txt").write_text("one\ntwo\n", encoding="utf-8")
    commit(root, "base")
    git(root, "checkout", "-b", "feature")
    return root


def set_origin(root, branch="main"):
    """Fake an `origin/<branch>` ref and origin/HEAD without a real remote."""
    sha = git(root, "rev-parse", branch).strip()
    git(root, "update-ref", f"refs/remotes/origin/{branch}", sha)
    git(root, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{branch}")


class TestFindRepoRoot:
    def test_resolves_from_a_subdirectory(self, repo):
        nested = repo / "a" / "b"
        nested.mkdir(parents=True)
        assert find_repo_root(nested).resolve() == repo.resolve()

    def test_rejects_a_non_repository(self, tmp_path):
        outside = tmp_path / "plain"
        outside.mkdir()
        with pytest.raises(ValueError, match="not a git"):
            find_repo_root(outside)


class TestDetectBaseRef:
    def test_origin_head_is_preferred_over_the_fallback_list(self, repo):
        set_origin(repo)
        assert detect_base_ref(repo) == ("origin/main", "origin-head")

    def test_falls_back_to_a_local_branch(self, repo):
        assert detect_base_ref(repo) == ("main", "fallback")

    def test_an_open_pr_wins(self, repo):
        set_origin(repo)
        sha = git(repo, "rev-parse", "main").strip()
        git(repo, "update-ref", "refs/remotes/origin/release", sha)
        with mock.patch(
            "kimi_mcp_hub.review._gh_pr",
            return_value={"baseRefName": "release", "number": 7},
        ):
            assert detect_base_ref(repo) == ("origin/release", "gh-pr")

    def test_raises_when_no_candidate_exists(self, repo):
        git(repo, "branch", "-m", "main", "solo")
        with pytest.raises(ValueError, match="could not determine a base branch"):
            detect_base_ref(repo)


class TestCollectContext:
    def test_committed_changes_against_the_base(self, repo):
        (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
        commit(repo, "add new")

        ctx = collect_context(base="main", cwd=repo, use_gh=False)

        assert ctx.base_ref == "main"
        assert ctx.base_source == "explicit"
        assert ctx.head_branch == "feature"
        assert not ctx.includes_uncommitted
        assert [(f.status, f.path, f.added, f.removed) for f in ctx.files] == [
            ("A", "new.py", 1, 0)
        ]
        assert ctx.diff_total_lines == 1
        assert "x = 1" in ctx.diff

    def test_rename_keeps_both_paths(self, repo):
        git(repo, "mv", "base.txt", "renamed.txt")
        commit(repo, "rename")

        ctx = collect_context(base="main", cwd=repo, use_gh=False)

        assert len(ctx.files) == 1
        renamed = ctx.files[0]
        assert renamed.status.startswith("R")
        assert renamed.path == "renamed.txt"
        assert renamed.old_path == "base.txt"
        # A pure rename really is 0/0 -- it must not be dropped as "no change".
        assert (renamed.added, renamed.removed) == (0, 0)

    def test_binary_files_report_no_line_counts(self, repo):
        (repo / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01\x02\x03")
        commit(repo, "add binary")

        ctx = collect_context(base="main", cwd=repo, use_gh=False)

        binary = next(f for f in ctx.files if f.path == "logo.png")
        assert binary.added is None
        assert binary.removed is None

    def test_untracked_files_are_diffed_when_nothing_is_committed(self, repo):
        (repo / "fresh.py").write_text("a = 1\nb = 2\n", encoding="utf-8")

        ctx = collect_context(base="main", cwd=repo, use_gh=False)

        assert ctx.includes_uncommitted
        assert "reviewing uncommitted work" in " ".join(ctx.warnings)
        fresh = next(f for f in ctx.files if f.path == "fresh.py")
        assert fresh.status == "??"
        assert fresh.added == 2
        # git diff alone never shows untracked content; this is the whole point.
        assert "a = 1" in ctx.diff

    def test_uncommitted_files_are_listed_but_excluded_by_default(self, repo):
        (repo / "committed.py").write_text("x = 1\n", encoding="utf-8")
        commit(repo, "commit one")
        (repo / "base.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")

        ctx = collect_context(base="main", cwd=repo, use_gh=False)

        assert not ctx.includes_uncommitted
        assert [f.path for f in ctx.files] == ["committed.py"]
        assert any("base.txt" in line for line in ctx.dirty)

    def test_include_uncommitted_widens_the_diff(self, repo):
        (repo / "committed.py").write_text("x = 1\n", encoding="utf-8")
        commit(repo, "commit one")
        (repo / "base.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")

        ctx = collect_context(
            base="main", cwd=repo, include_uncommitted=True, use_gh=False
        )

        assert ctx.includes_uncommitted
        assert {f.path for f in ctx.files} == {"committed.py", "base.txt"}

    def test_truncation_stops_at_a_file_boundary(self, repo):
        (repo / "first.txt").write_text("\n".join(f"a{i}" for i in range(40)) + "\n", encoding="utf-8")
        (repo / "second.txt").write_text("\n".join(f"b{i}" for i in range(40)) + "\n", encoding="utf-8")
        commit(repo, "two big files")

        ctx = collect_context(base="main", cwd=repo, max_diff_lines=25, use_gh=False)

        assert ctx.diff_truncated
        # The file list stays complete even though the body was cut.
        assert len(ctx.files) == 2
        assert "second.txt" in ctx.omitted_files
        assert "diff --git" in ctx.diff

    def test_no_truncation_within_budget(self, repo):
        (repo / "small.txt").write_text("one\n", encoding="utf-8")
        commit(repo, "small")

        ctx = collect_context(base="main", cwd=repo, use_gh=False)

        assert not ctx.diff_truncated
        assert ctx.omitted_files == []

    def test_identical_head_and_base_warns(self, repo):
        ctx = collect_context(base="main", cwd=repo, use_gh=False)

        assert any("identical to main" in w for w in ctx.warnings)
        assert any("no changes detected" in w for w in ctx.warnings)

    def test_status_list_is_capped(self, repo, monkeypatch):
        monkeypatch.setattr("kimi_mcp_hub.review.MAX_STATUS_ENTRIES", 2)
        for index in range(5):
            (repo / f"u{index}.txt").write_text("x\n", encoding="utf-8")

        ctx = collect_context(base="main", cwd=repo, use_gh=False)

        assert len(ctx.dirty) == 2
        assert any("only the first 2 are listed" in w for w in ctx.warnings)

    def test_unknown_base_is_rejected(self, repo):
        with pytest.raises(ValueError, match="base ref does not exist"):
            collect_context(base="origin/nope", cwd=repo, use_gh=False)

    def test_repository_without_commits_is_rejected(self, tmp_path):
        root = tmp_path / "empty"
        root.mkdir()
        git(root, "init")
        with pytest.raises(ValueError, match="no commits"):
            collect_context(cwd=root, use_gh=False)

    def test_long_history_warns_about_a_wrong_base(self, repo):
        for index in range(52):
            (repo / f"f{index}.txt").write_text("x\n", encoding="utf-8")
            commit(repo, f"commit {index}")

        ctx = collect_context(base="main", cwd=repo, max_diff_lines=5, use_gh=False)

        assert any("that is a lot for one PR" in w for w in ctx.warnings)


class TestRenderText:
    def test_renders_every_section(self, repo):
        (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
        commit(repo, "add new")

        text = render_text(collect_context(base="main", cwd=repo, use_gh=False))

        assert "# Pre-PR review context" in text
        assert "Base:       main  (via explicit)" in text
        assert "## Changed files (1, 1 lines)" in text
        assert "new.py" in text
        assert "## Diff" in text

    def test_binary_counts_render_as_bin(self, repo):
        (repo / "logo.png").write_bytes(b"\x89PNG\x00\x01")
        commit(repo, "binary")

        text = render_text(collect_context(base="main", cwd=repo, use_gh=False))

        assert "bin" in text

    def test_fence_grows_past_backticks_in_the_diff(self):
        ctx = ReviewContext(
            repo_root="/tmp/x",
            head_branch="feature",
            base_ref="main",
            base_source="explicit",
            merge_base="abc123",
            diff="+```diff\n+nested\n",
        )

        text = render_text(ctx)

        assert "````diff" in text
        assert text.rstrip().endswith("````")


class TestReviewContextCommand:
    def test_prints_the_markdown_block(self, repo, monkeypatch):
        (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
        commit(repo, "add new")
        monkeypatch.chdir(repo)

        result = CliRunner().invoke(
            main, ["review-context", "--base", "main", "--no-gh"]
        )

        assert result.exit_code == 0, result.output
        assert "Pre-PR review context" in result.output
        assert "new.py" in result.output

    def test_json_output_is_parseable(self, repo, monkeypatch):
        (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
        commit(repo, "add new")
        monkeypatch.chdir(repo)

        result = CliRunner().invoke(
            main, ["review-context", "--base", "main", "--no-gh", "--json"]
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["base_ref"] == "main"
        assert payload["base_source"] == "explicit"
        assert [f["path"] for f in payload["files"]] == ["new.py"]

    def test_no_diff_drops_the_body(self, repo, monkeypatch):
        (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
        commit(repo, "add new")
        monkeypatch.chdir(repo)

        result = CliRunner().invoke(
            main, ["review-context", "--base", "main", "--no-gh", "--no-diff"]
        )

        assert result.exit_code == 0, result.output
        assert "new.py" in result.output
        assert "## Diff" not in result.output

    def test_exits_nonzero_outside_a_repository(self, tmp_path, monkeypatch):
        plain = tmp_path / "plain"
        plain.mkdir()
        monkeypatch.chdir(plain)

        result = CliRunner().invoke(main, ["review-context", "--no-gh"])

        assert result.exit_code == 1
        assert "Error:" in result.output
