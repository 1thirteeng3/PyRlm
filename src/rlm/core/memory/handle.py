"""
Context Handle for memory-efficient file access.

This module provides the ContextHandle class that allows the LLM to work
with large context files without loading them entirely into memory.
Uses mmap for efficient random access and searching.
"""

import mmap
import os
import re
from pathlib import Path
from typing import Iterator, Optional

from rlm.core.exceptions import ContextError


class ContextHandle:
    """
    Memory-efficient handle for accessing large context files.

    This class is designed to be injected into the sandbox environment,
    allowing the LLM to search and read large files without loading
    everything into memory.

    The API is designed to encourage efficient patterns:
    - search() to find relevant sections
    - read_window() to read specific chunks
    - iterate_lines() for streaming access

    Example:
        >>> ctx = ContextHandle("/path/to/large_file.txt")
        >>> print(f"File size: {ctx.size} bytes")
        >>> matches = ctx.search(r"important.*pattern")
        >>> for offset, match in matches:
        ...     print(ctx.snippet(offset))
    """

    DEFAULT_WINDOW_SIZE = 500
    MAX_SEARCH_RESULTS = 10

    def __init__(self, path: str | Path) -> None:
        """
        Initialize the context handle.

        Args:
            path: Path to the context file

        Raises:
            ContextError: If the file doesn't exist or can't be accessed
        """
        self.path = Path(path)

        if not self.path.exists():
            raise ContextError(
                message=f"Context file not found: {path}",
                path=str(path),
            )

        if not self.path.is_file():
            raise ContextError(
                message=f"Context path is not a file: {path}",
                path=str(path),
            )

        try:
            self._size = self.path.stat().st_size
        except OSError as e:
            raise ContextError(
                message=f"Cannot access context file: {e}",
                path=str(path),
            ) from e

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
            try:
                self._file = open(self.path, "r+b")
                self._mmap = mmap.mmap(
                    self._file.fileno(),
                    0,
                    access=mmap.ACCESS_READ,
                )
            except Exception as e:
                if self._file:
                    self._file.close()
                raise ContextError(
                    message=f"Failed to memory-map context file: {e}",
                    path=str(self.path),
                ) from e
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

        # Clamp length to file size
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
            radius: Number of bytes on each side of the offset

        Returns:
            The text content in the window
        """
        start = max(0, offset - radius)
        length = radius * 2
        return self.read(start, length)

    def snippet(self, offset: int, window: int = DEFAULT_WINDOW_SIZE) -> str:
        """
        Get a snippet of text around an offset.

        This is an alias for read_window with different semantics -
        window is the total size, not the radius.

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
    ) -> list[tuple[int, str]]:
        """
        Search for a regex pattern in the file using memory mapping.

        This is memory-efficient as it doesn't load the entire file.

        Args:
            pattern: Regular expression pattern
            max_results: Maximum number of results to return
            ignore_case: Whether to ignore case

        Returns:
            List of (byte_offset, matched_text) tuples
        """
        matches: list[tuple[int, str]] = []

        try:
            mm = self._get_mmap()

            # Compile pattern for bytes
            flags = re.IGNORECASE if ignore_case else 0
            try:
                bytes_pattern = pattern.encode("utf-8")
                compiled = re.compile(bytes_pattern, flags)
            except re.error as e:
                raise ContextError(
                    message=f"Invalid regex pattern: {e}",
                    details={"pattern": pattern},
                ) from e

            for match in compiled.finditer(mm):
                if len(matches) >= max_results:
                    break

                try:
                    match_text = match.group().decode("utf-8", errors="replace")
                    matches.append((match.start(), match_text))
                except UnicodeDecodeError:
                    # Skip matches that can't be decoded
                    continue

        except Exception as e:
            if not isinstance(e, ContextError):
                raise ContextError(
                    message=f"Search failed: {e}",
                    path=str(self.path),
                ) from e
            raise

        return matches

    def search_lines(
        self,
        pattern: str,
        max_results: int = MAX_SEARCH_RESULTS,
        context_lines: int = 0,
    ) -> list[tuple[int, str, str]]:
        """
        Search for a pattern and return matching lines.

        Args:
            pattern: Regex pattern to search for
            max_results: Maximum number of results
            context_lines: Number of lines before/after to include

        Returns:
            List of (line_number, matching_line, context) tuples
        """
        matches: list[tuple[int, str, str]] = []
        compiled = re.compile(pattern, re.IGNORECASE)

        lines_buffer: list[str] = []

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

    def iterate_lines(self, start_line: int = 1) -> Iterator[tuple[int, str]]:
        """
        Iterate over lines in the file.

        This is memory-efficient as it reads line by line.

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
