"""Test configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_context_file() -> Generator[Path, None, None]:
    """Create a temporary context file for testing."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write("This is a test context file.\n")
        f.write("It contains some sample data for testing.\n")
        f.write("SECRET_KEY=abc123def456\n")
        f.write("The quick brown fox jumps over the lazy dog.\n")
        f.write("More content here for searching.\n")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def large_context_file() -> Generator[Path, None, None]:
    """Create a large temporary context file for testing memory efficiency."""
    with tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=".txt",
        delete=False,
    ) as f:
        # Write 10MB of data
        chunk = b"Lorem ipsum dolor sit amet. " * 1000
        for _ in range(400):
            f.write(chunk)
        # Write a marker in the middle
        f.seek(5 * 1024 * 1024)
        f.write(b"MARKER_IN_MIDDLE")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("RLM_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("RLM_API_PROVIDER", "openai")
    monkeypatch.setenv("RLM_MODEL_NAME", "gpt-4o")
    monkeypatch.setenv("RLM_EXECUTION_MODE", "docker")
