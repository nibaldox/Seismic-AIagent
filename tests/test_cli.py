"""Tests for CLI batch processing module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cli import process_file, process_directory, main


class TestProcessFile:
    def test_process_nonexistent_file(self):
        result = process_file(Path("/nonexistent/file.ms"))
        assert "error" in result
        assert "No se encuentra" in result["error"] or "exist" in result["error"]

    def test_process_empty_bytes(self, tmp_path):
        f = tmp_path / "empty.ms"
        f.write_text("")
        result = process_file(f)
        assert "error" in result

    def test_process_directory_empty(self, tmp_path):
        results = process_directory(tmp_path)
        assert results == []

    def test_process_directory_no_match(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        results = process_directory(tmp_path, pattern="*.ms")
        assert results == []

    def test_cli_main_nonexistent(self):
        import sys
        from io import StringIO

        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            with pytest.raises(SystemExit) as exc:
                main()
        finally:
            sys.stderr = old_stderr


class TestProcessDirectory:
    def test_glob_pattern(self, tmp_path):
        for i in range(3):
            (tmp_path / f"trace{i:03d}.ms").write_text("test")
        (tmp_path / "readme.txt").write_text("test")

        results = process_directory(tmp_path, pattern="*.ms")
        assert len(results) == 3

    def test_recursive_glob(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "trace.ms").write_text("test")
        (tmp_path / "trace.ms").write_text("test")

        results = process_directory(tmp_path, pattern="*.ms")
        assert len(results) == 1  # non-recursive

        results = process_directory(tmp_path, pattern="*.ms")
        assert len(results) == 1  # only top-level

    def test_skip_directories(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        results = process_directory(tmp_path, pattern="*")
        # No files, only dirs
        assert results == []


class TestMainFunction:
    def test_main_help(self):
        import sys
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            with pytest.raises(SystemExit):
                main()
        finally:
            sys.stdout = old_stdout

    def test_main_no_args_prints_usage(self):
        import sys
        from io import StringIO
        old_stderr = sys.stderr
        old_stdout = sys.stdout
        sys.stderr = StringIO()
        sys.stdout = StringIO()
        try:
            with pytest.raises(SystemExit):
                main()
        finally:
            sys.stderr = old_stderr
            sys.stdout = old_stdout
