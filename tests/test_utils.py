"""Tests for cross-platform utilities."""

import os
from pathlib import Path
from file_organizer.core.utils import (
    is_hidden_file,
    normalize_extension,
    can_read_write,
    get_safe_destination,
    is_path_inside,
)


def test_normalize_extension():
    assert normalize_extension(Path("file.TXT")) == "txt"
    assert normalize_extension(Path("archive.tar.gz")) == "gz"
    assert normalize_extension(Path("no_extension")) == ""
    # In standard Python pathlib, .gitignore is treated as stem without extension
    assert normalize_extension(Path(".gitignore")) == ""


def test_is_hidden_unix_style(temp_dir: Path):
    hidden_file = temp_dir / ".hidden_file"
    hidden_file.touch()
    normal_file = temp_dir / "normal_file.txt"
    normal_file.touch()

    assert is_hidden_file(hidden_file) is True
    assert is_hidden_file(normal_file) is False


def test_can_read_write(temp_dir: Path):
    test_file = temp_dir / "write_test.txt"
    test_file.write_text("hello")
    assert can_read_write(test_file) is True


def test_get_safe_destination(temp_dir: Path):
    file1 = temp_dir / "doc.pdf"
    file1.write_text("version 1")

    # If destination exists, should return non-colliding file
    safe1 = get_safe_destination(file1)
    assert safe1.name == "doc_1.pdf"

    # If destination does not exist yet, should return as-is
    not_existing = temp_dir / "other.pdf"
    assert get_safe_destination(not_existing) == not_existing


def test_is_path_inside(temp_dir: Path):
    sub = temp_dir / "subfolder"
    sub.mkdir()
    file_inside = sub / "item.txt"
    file_outside = temp_dir.parent / "outside.txt"

    assert is_path_inside(file_inside, temp_dir) is True
    assert is_path_inside(file_outside, temp_dir) is False
