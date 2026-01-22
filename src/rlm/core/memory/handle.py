"""
Context Handle for memory-efficient file access (v3.0).

v3.0 Changes:
- Binary file detection (null bytes, control chars)
- Fail-fast on PDFs, images, binaries
- Prevents LLM hallucination on garbage input

Uses mmap for efficient random access and searching.
"""

import mmap
import os
import re
from pathlib import Path
from typing import Iterator, Optional

from rlm.core.exceptions import ContextError


# v3.0: Binary detection constants
BINARY_THRESHOLD = 0.05  # 5% control chars indicates binary
CONTROL_CHARS = set(range(0, 9)) | set(range(14, 32))  # Exclude \t \n \r


class ContextHandle:
    """
    Memory-efficient handle for accessing large context files.

    v3.0: Detects binary files to prevent LLM hallucination.
    Raises ContextError if you try to load a PDF, image, or compiled binary.

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
            ContextError: If the file doesn't exist, is binary, or can't be accessed
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
        
        # v3.0: Validate text content on init
        self._validate_not_binary()

    def _validate_not_binary(self) -> None:
        """
        Validate that the file is text, not binary.
        
        v3.0: Prevents loading PDFs, images, or binaries as context.
        Checks first 8KB for null bytes and control characters.
        
        Raises:
            ContextError: If binary content is detected
        """
        sample_size = min(8192, self._size)
        if sample_size == 0:
            return  # Empty file is OK
        
        with open(self.path, "rb") as f:
            sample = f.read(sample_size)
        
        # Check for null bytes (definitive binary indicator)
        if b'\x00' in sample:
            raise ContextError(
                message="Binary file detected via null bytes. ContextHandle only supports text files.",
                path=str(self.path),
                details={"hint": "Cannot load PDFs, images, or compiled binaries as context."},
            )
        
        # Check for excessive control characters
        control_count = sum(1 for b in sample if b in CONTROL_CHARS)
        ratio = control_count / len(sample)
        
        if ratio > BINARY_THRESHOLD:
            raise ContextError(
                message=f"Binary file detected ({ratio:.1%} control characters). ContextHandle only supports text.",
                path=str(self.path),
                details={"control_char_ratio": ratio, "threshold": BINARY_THRESHOLD},
            )

    def _validate_text_content(self, chunk: str) -> None:
        """
        Runtime validation of text content.
        
        v3.0: Additional check during reads to catch late-detected binary.
        
        Raises:
            ContextError: If binary content is found
        """
        if '\x00' in chunk:
            raise ContextError(
                message="Binary content detected via null bytes during read.",
                path=str(self.path),
            )

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

        v3.0: Validates content is text, not binary.

        Args:
            start: Starting byte offset
            length: Number of bytes to read

        Returns:
            The decoded text content
            
        Raises:
            ContextError: If binary content is detected
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
            content = f.read(actual_length)
        
        # v3.0: Validate no binary garbage
        self._validate_text_content(content)
        
        return content

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
        # v3.0: Safe attribute access (handle partial init on validation failure)
        if getattr(self, '_mmap', None):
            self._mmap.close()
            self._mmap = None
        if getattr(self, '_file', None):
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
