"""Pytest configuration and shared test fixtures."""

import tempfile
from pathlib import Path
from typing import Generator
import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a clean temporary directory for filesystem testing."""
    with tempfile.TemporaryDirectory() as tmp_path:
        yield Path(tmp_path)
