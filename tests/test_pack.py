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
