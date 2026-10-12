"""Pytest configuration and shared test fixtures."""

import tempfile
from pathlib import Path
from typing import Generator
import pytest
from file_organizer.core.logger import close_logger


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a clean temporary directory for filesystem testing."""
    with tempfile.TemporaryDirectory() as tmp_path:
        yield Path(tmp_path)
        # Ensure any open loggers release file handles before temporary directory cleanup on Windows
        close_logger()
