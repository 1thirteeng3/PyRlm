"""Tests for ContextHandle memory-efficient file access."""

from pathlib import Path

import pytest

from rlm.core.exceptions import ContextError
from rlm.core.memory.handle import ContextHandle


class TestContextHandleInit:
    """Tests for ContextHandle initialization."""

    def test_init_valid_file(self, temp_context_file):
        """Should initialize with a valid file."""
        handle = ContextHandle(temp_context_file)
        assert handle.size > 0
        assert handle.path == temp_context_file

    def test_init_nonexistent_file(self):
        """Should raise ContextError for nonexistent file."""
        with pytest.raises(ContextError) as exc_info:
            ContextHandle("/nonexistent/path/file.txt")
        assert "not found" in str(exc_info.value)

    def test_init_directory(self, tmp_path):
        """Should raise ContextError for directory."""
        with pytest.raises(ContextError) as exc_info:
            ContextHandle(tmp_path)
        assert "not a file" in str(exc_info.value)


class TestContextHandleRead:
    """Tests for reading functionality."""

    def test_read_beginning(self, temp_context_file):
        """Should read from the beginning of file."""
        handle = ContextHandle(temp_context_file)
        content = handle.read(0, 10)
        assert content == "This is a "

    def test_read_middle(self, temp_context_file):
        """Should read from the middle of file."""
        handle = ContextHandle(temp_context_file)
        # Read a chunk from the middle
        content = handle.read(10, 10)
        assert len(content) == 10

    def test_read_window(self, temp_context_file):
        """Should read a window around an offset."""
        handle = ContextHandle(temp_context_file)
        # Read window around position 20
        content = handle.read_window(20, radius=10)
        assert len(content) <= 20  # 2 * radius

    def test_head(self, temp_context_file):
        """Should read the first n bytes."""
        handle = ContextHandle(temp_context_file)
        content = handle.head(20)
        assert content.startswith("This is")

    def test_tail(self, temp_context_file):
        """Should read the last n bytes."""
        handle = ContextHandle(temp_context_file)
        content = handle.tail(20)
        assert len(content) <= 20


class TestContextHandleSearch:
    """Tests for search functionality."""

    def test_search_simple_pattern(self, temp_context_file):
        """Should find simple patterns."""
        handle = ContextHandle(temp_context_file)
        matches = handle.search(r"test")
        assert len(matches) > 0
        assert all(isinstance(m, tuple) for m in matches)
        assert all(len(m) == 2 for m in matches)

    def test_search_regex_pattern(self, temp_context_file):
        """Should find regex patterns."""
        handle = ContextHandle(temp_context_file)
        matches = handle.search(r"SECRET_KEY=\w+")
        assert len(matches) > 0
        assert "SECRET_KEY" in matches[0][1]

    def test_search_no_match(self, temp_context_file):
        """Should return empty list for no matches."""
        handle = ContextHandle(temp_context_file)
        matches = handle.search(r"NONEXISTENT_PATTERN_XYZ")
        assert len(matches) == 0

    def test_search_max_results(self, temp_context_file):
        """Should respect max_results limit."""
        handle = ContextHandle(temp_context_file)
        # Search for common pattern
        matches = handle.search(r".", max_results=3)
        assert len(matches) <= 3


class TestContextHandleSearchLines:
    """Tests for line-based search functionality."""

    def test_search_lines_basic(self, temp_context_file):
        """Should find matching lines."""
        handle = ContextHandle(temp_context_file)
        matches = handle.search_lines(r"test")
        assert len(matches) > 0
        # Each match is (line_number, line, context)
        assert all(len(m) == 3 for m in matches)

    def test_search_lines_with_line_number(self, temp_context_file):
        """Should return correct line numbers."""
        handle = ContextHandle(temp_context_file)
        matches = handle.search_lines(r"SECRET_KEY")
        assert len(matches) > 0
        line_num, line, _ = matches[0]
        assert isinstance(line_num, int)
        assert "SECRET_KEY" in line


class TestContextHandleMemoryEfficiency:
    """Tests for memory-efficient file handling."""

    def test_large_file_size(self, large_context_file):
        """Should report correct size for large files."""
        handle = ContextHandle(large_context_file)
        assert handle.size > 1_000_000  # > 1MB

    def test_large_file_search_marker(self, large_context_file):
        """Should find marker in large file without loading all."""
        handle = ContextHandle(large_context_file)
        matches = handle.search(r"MARKER_IN_MIDDLE")
        assert len(matches) > 0

    def test_large_file_read_window(self, large_context_file):
        """Should read window from large file efficiently."""
        handle = ContextHandle(large_context_file)
        # Read around the middle
        content = handle.read_window(5 * 1024 * 1024, radius=100)
        assert "MARKER" in content


class TestContextHandleContextManager:
    """Tests for context manager functionality."""

    def test_with_statement(self, temp_context_file):
        """Should work with 'with' statement."""
        with ContextHandle(temp_context_file) as handle:
            content = handle.head(10)
            assert len(content) > 0

    def test_close(self, temp_context_file):
        """Should close cleanly."""
        handle = ContextHandle(temp_context_file)
        _ = handle.search(r"test")  # Force mmap creation
        handle.close()
        # Should not raise after close


class TestContextHandleIterator:
    """Tests for line iteration."""

    def test_iterate_lines(self, temp_context_file):
        """Should iterate over lines."""
        handle = ContextHandle(temp_context_file)
        lines = list(handle.iterate_lines())
        assert len(lines) > 0
        assert all(isinstance(l, tuple) for l in lines)
        assert all(len(l) == 2 for l in lines)  # (line_num, content)

    def test_iterate_lines_from_offset(self, temp_context_file):
        """Should start iteration from specified line."""
        handle = ContextHandle(temp_context_file)
        lines_all = list(handle.iterate_lines(start_line=1))
        lines_from_2 = list(handle.iterate_lines(start_line=2))
        assert len(lines_from_2) == len(lines_all) - 1
