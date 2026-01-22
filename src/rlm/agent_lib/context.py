"""
Context Handle for memory-efficient file access inside the sandbox.

This module is designed to run INSIDE the Docker container.
It provides the agent with efficient access to large context files
without loading them entirely into memory.
"""

import mmap
import os
import re
from pathlib import Path
from typing import Iterator, List, Optional, Tuple


class ContextError(Exception):
    """Error accessing context file."""
    pass


class ContextHandle:
    """
    Memory-efficient handle for accessing large context files.

    This class uses mmap for efficient random access, allowing the agent
    to search and read gigabyte-scale files without memory issues.

    API:
        - ctx.size: Total file size in bytes
        - ctx.search(pattern): Find regex matches
        - ctx.read_window(offset, radius): Read around an offset
        - ctx.snippet(offset): Alias for read_window
        - ctx.head(n): First n bytes
        - ctx.tail(n): Last n bytes

    Example:
        >>> ctx = ContextHandle("/mnt/context")
        >>> matches = ctx.search(r"important.*pattern")
        >>> for offset, match in matches:
        ...     print(ctx.snippet(offset))
    """

    DEFAULT_WINDOW_SIZE = 500
    MAX_SEARCH_RESULTS = 10
    DEFAULT_PATH = "/mnt/context"

    def __init__(self, path: str = DEFAULT_PATH) -> None:
        """
        Initialize the context handle.

        Args:
            path: Path to the context file (default: /mnt/context)
        """
        self.path = Path(path)

        if not self.path.exists():
            raise ContextError(f"Context file not found: {path}")

        if not self.path.is_file():
            raise ContextError(f"Context path is not a file: {path}")

        self._size = self.path.stat().st_size
        self._mmap: Optional[mmap.mmap] = None
        self._file = None

    @property
    def size(self) -> int:
        """Return the total size of the context file in bytes."""
        return self._size

    @property
    def size_mb(self) -> float:
        """Return the size in megabytes."""
        return self._size / (1024 * 1024)

    def _get_mmap(self) -> mmap.mmap:
        """Get or create the memory-mapped file."""
        if self._mmap is None:
            self._file = open(self.path, "r+b")
            self._mmap = mmap.mmap(
                self._file.fileno(),
                0,
                access=mmap.ACCESS_READ,
            )
        return self._mmap

    def read(self, start: int, length: int) -> str:
        """
        Read a specific chunk of the file.

        Args:
            start: Starting byte offset
            length: Number of bytes to read

        Returns:
            The decoded text content
        """
        if start < 0:
            start = 0
        if start >= self._size:
            return ""

        end = min(start + length, self._size)
        actual_length = end - start

        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(start)
            return f.read(actual_length)

    def read_window(self, offset: int, radius: int = DEFAULT_WINDOW_SIZE) -> str:
        """
        Read a window of text centered around an offset.

        Args:
            offset: Center point (byte offset)
            radius: Number of bytes on each side

        Returns:
            The text content in the window
        """
        start = max(0, offset - radius)
        length = radius * 2
        return self.read(start, length)

    def snippet(self, offset: int, window: int = DEFAULT_WINDOW_SIZE) -> str:
        """
        Get a snippet of text around an offset.

        Args:
            offset: Center point (byte offset)
            window: Total window size in bytes

        Returns:
            The text snippet
        """
        return self.read_window(offset, window // 2)

    def search(
        self,
        pattern: str,
        max_results: int = MAX_SEARCH_RESULTS,
        ignore_case: bool = True,
    ) -> List[Tuple[int, str]]:
        """
        Search for a regex pattern using memory mapping.

        Args:
            pattern: Regular expression pattern
            max_results: Maximum results to return
            ignore_case: Whether to ignore case

        Returns:
            List of (byte_offset, matched_text) tuples
        """
        matches: List[Tuple[int, str]] = []

        mm = self._get_mmap()

        flags = re.IGNORECASE if ignore_case else 0
        bytes_pattern = pattern.encode("utf-8")
        compiled = re.compile(bytes_pattern, flags)

        for match in compiled.finditer(mm):
            if len(matches) >= max_results:
                break

            try:
                match_text = match.group().decode("utf-8", errors="replace")
                matches.append((match.start(), match_text))
            except UnicodeDecodeError:
                continue

        return matches

    def search_lines(
        self,
        pattern: str,
        max_results: int = MAX_SEARCH_RESULTS,
        context_lines: int = 0,
    ) -> List[Tuple[int, str, str]]:
        """
        Search for a pattern and return matching lines.

        Args:
            pattern: Regex pattern
            max_results: Maximum results
            context_lines: Lines before/after to include

        Returns:
            List of (line_number, matching_line, context) tuples
        """
        matches: List[Tuple[int, str, str]] = []
        compiled = re.compile(pattern, re.IGNORECASE)

        lines_buffer: List[str] = []

        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                lines_buffer.append(line)
                if len(lines_buffer) > context_lines * 2 + 1:
                    lines_buffer.pop(0)

                if compiled.search(line):
                    context = "".join(lines_buffer)
                    matches.append((line_no, line.strip(), context))

                    if len(matches) >= max_results:
                        break

        return matches

    def iterate_lines(self, start_line: int = 1) -> Iterator[Tuple[int, str]]:
        """
        Iterate over lines in the file.

        Args:
            start_line: Line number to start from (1-indexed)

        Yields:
            Tuples of (line_number, line_content)
        """
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                if line_no >= start_line:
                    yield line_no, line

    def head(self, n_bytes: int = 1000) -> str:
        """Read the first n bytes of the file."""
        return self.read(0, n_bytes)

    def tail(self, n_bytes: int = 1000) -> str:
        """Read the last n bytes of the file."""
        start = max(0, self._size - n_bytes)
        return self.read(start, n_bytes)

    def close(self) -> None:
        """Close the memory-mapped file."""
        if self._mmap:
            self._mmap.close()
            self._mmap = None
        if self._file:
            self._file.close()
            self._file = None

    def __enter__(self) -> "ContextHandle":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"ContextHandle(path='{self.path}', size={self.size_mb:.2f}MB)"

    def __del__(self) -> None:
        self.close()


# Convenience: auto-create ctx if context file exists
ctx: Optional[ContextHandle] = None
if Path(ContextHandle.DEFAULT_PATH).exists():
    ctx = ContextHandle()
