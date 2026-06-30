"""Tests for the repo packer."""

import pytest
from click.testing import CliRunner

from kimi_mcp_hub.cli import main
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
        tree, _, files_section = result.partition("## Files")
        assert "binary.bin" in tree
        assert "\x00" not in files_section

    def test_respects_gitignore(self, tmp_path):
        (tmp_path / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
        (tmp_path / "public.txt").write_text("ok", encoding="utf-8")
        (tmp_path / "secret.txt").write_text("hidden", encoding="utf-8")

        result = RepoPacker().pack(tmp_path)
        tree, _, files_section = result.partition("## Files")

        assert "public.txt" in result
        assert "secret.txt" not in tree
        assert "### `secret.txt`" not in files_section

    def test_respects_gitignore_anchored_directory(self, tmp_path):
        (tmp_path / ".gitignore").write_text("/build/\n", encoding="utf-8")
        (tmp_path / "build").mkdir()
        (tmp_path / "build" / "artifact.txt").write_text("x", encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "build").mkdir()
        (tmp_path / "src" / "build" / "keep.txt").write_text("y", encoding="utf-8")

        result = RepoPacker().pack(tmp_path)
        tree_section = result.split("## File Tree")[1].split("## Files")[0]
        tree_lines = [line for line in tree_section.splitlines() if line.strip()]
        top_level_lines = [line.strip() for line in tree_lines if not line.startswith("    ")]

        assert "build/" not in top_level_lines
        assert "artifact.txt" not in result
        assert "keep.txt" in result

    def test_include_globs(self, tmp_path):
        (tmp_path / "a.py").write_text("a", encoding="utf-8")
        (tmp_path / "b.txt").write_text("b", encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "c.py").write_text("c", encoding="utf-8")
        (tmp_path / "src" / "d.txt").write_text("d", encoding="utf-8")

        result = RepoPacker(include=["*.py"]).pack(tmp_path)

        assert "a.py" in result
        assert "src/c.py" in result
        assert "b.txt" not in result
        assert "d.txt" not in result

    def test_include_recursive_glob(self, tmp_path):
        (tmp_path / "a.py").write_text("a", encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "deep").mkdir()
        (tmp_path / "src" / "deep" / "b.py").write_text("b", encoding="utf-8")

        result = RepoPacker(include=["src/**/*.py"]).pack(tmp_path)

        assert "a.py" not in result
        assert "src/deep/b.py" in result

    def test_exclude_globs(self, tmp_path):
        (tmp_path / "a.py").write_text("a", encoding="utf-8")
        (tmp_path / "secret.txt").write_text("s", encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "secret.txt").write_text("s", encoding="utf-8")

        result = RepoPacker(exclude=["secret.txt"]).pack(tmp_path)

        assert "a.py" in result
        assert "secret.txt" not in result

    def test_exclude_directory(self, tmp_path):
        (tmp_path / "ok.txt").write_text("ok", encoding="utf-8")
        (tmp_path / "build").mkdir()
        (tmp_path / "build" / "skip.txt").write_text("skip", encoding="utf-8")

        result = RepoPacker(exclude=["build/"]).pack(tmp_path)

        assert "ok.txt" in result
        assert "build/" not in result
        assert "skip.txt" not in result

    def test_max_size_limit(self, tmp_path):
        (tmp_path / "small.txt").write_text("small", encoding="utf-8")
        (tmp_path / "large.txt").write_text("x" * 2000, encoding="utf-8")

        result = RepoPacker(max_size=500).pack(tmp_path)

        tree, _, files_section = result.partition("## Files")
        assert "### `small.txt`" in files_section
        assert "### `large.txt`" not in files_section
        assert "large.txt" in tree
        assert "Warning" in result
        assert "omitted files due to size limit" in result

    def test_directory_with_only_binary_shows_in_tree(self, tmp_path):
        (tmp_path / "bin_dir").mkdir()
        (tmp_path / "bin_dir" / "data.bin").write_bytes(b"\x00\x01\x02")

        result = RepoPacker().pack(tmp_path)

        assert "bin_dir/" in result
        assert "data.bin" in result
        assert "\x00" not in result

    def test_empty_repository(self, tmp_path):
        result = RepoPacker().pack(tmp_path)

        assert "# Repository Pack" in result
        assert "(no files)" in result

    def test_pack_root_must_exist(self, tmp_path):
        missing = tmp_path / "missing"
        with pytest.raises(ValueError, match="does not exist"):
            RepoPacker().pack(missing)

    def test_pack_root_must_be_directory(self, tmp_path):
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("hello", encoding="utf-8")
        with pytest.raises(ValueError, match="not a directory"):
            RepoPacker().pack(file_path)


class TestPackCommand:
    def test_default_pack_current_directory(self, tmp_path, monkeypatch):
        (tmp_path / "README.md").write_text("# Hello\n", encoding="utf-8")
        (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["pack"])

        assert result.exit_code == 0
        assert "# Repository Pack" in result.output
        assert "README.md" in result.output
        assert "main.py" in result.output
        assert "# Hello" in result.output
        assert "print('hi')" in result.output

    def test_exclude_pattern_excludes_files(self, tmp_path):
        (tmp_path / "keep.txt").write_text("keep me", encoding="utf-8")
        (tmp_path / "skip.txt").write_text("skip me", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["pack", str(tmp_path), "--exclude", "skip.txt"],
        )

        assert result.exit_code == 0
        assert "keep.txt" in result.output
        assert "skip.txt" not in result.output

    def test_output_writes_to_file(self, tmp_path):
        (tmp_path / "README.md").write_text("# Hello\n", encoding="utf-8")
        output_path = tmp_path / "out.md"

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["pack", str(tmp_path), "--output", str(output_path)],
        )

        assert result.exit_code == 0
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "# Repository Pack" in content
        assert "README.md" in content
        assert "Wrote pack to" in result.output
        assert output_path.name in result.output

    def test_no_gitignore_includes_ignored_file(self, tmp_path):
        (tmp_path / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
        (tmp_path / "secret.txt").write_text("hidden", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["pack", str(tmp_path), "--no-gitignore"],
        )

        assert result.exit_code == 0
        tree, _, files_section = result.output.partition("## Files")
        assert "secret.txt" in tree
        assert "### `secret.txt`" in files_section

    def test_invalid_root_returns_error(self, tmp_path):
        missing = tmp_path / "missing"

        runner = CliRunner()
        result = runner.invoke(main, ["pack", str(missing)])

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "does not exist" in result.output
