"""Cross-platform utility functions for file path, permission, and attribute handling."""

import os
import sys
from pathlib import Path


def is_hidden_file(path: Path) -> bool:
    """Check if a file or directory is hidden across platforms (Windows / Unix)."""
    # 1. Standard Unix check (starts with dot)
    if path.name.startswith("."):
        return True

    # 2. Windows specific hidden attribute check
    if sys.platform == "win32":
        try:
            import ctypes

            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            # 0x02 is FILE_ATTRIBUTE_HIDDEN
            if attrs != -1 and bool(attrs & 2):
                return True
        except Exception:
            pass

    return False


def normalize_extension(path: Path) -> str:
    """Return lowercase extension without leading dot."""
    ext = path.suffix.lower()
    return ext.lstrip(".")


def can_read_write(path: Path) -> bool:
    """Verify read and write permissions for a given file or directory."""
    if not path.exists():
        # Check parent folder write permission
        parent = path.parent
        return parent.exists() and os.access(parent, os.W_OK)
    return os.access(path, os.R_OK) and os.access(path, os.W_OK)


def get_safe_destination(destination: Path) -> Path:
    """
    Ensure destination does not overwrite existing file by appending a counter.
    Example: report.pdf -> report_1.pdf -> report_2.pdf
    """
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent

    counter = 1
    while True:
        new_dest = parent / f"{stem}_{counter}{suffix}"
        if not new_dest.exists():
            return new_dest
        counter += 1


def is_path_inside(child: Path, parent: Path) -> bool:
    """Check whether a path is strictly inside or equal to a directory."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
