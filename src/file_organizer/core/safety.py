"""Shared file-operation safety, cancellation and immutable scan records."""

from dataclasses import dataclass
import os
from pathlib import Path


class OperationCancelled(Exception):
    pass


def check_cancel(event):
    if event is not None and event.is_set():
        raise OperationCancelled("Operation cancelled")


def fingerprint(path):
    stat = Path(path).stat()
    return (stat.st_size, stat.st_mtime_ns, stat.st_ino)


def is_link(path):
    path = Path(path)
    return path.is_symlink() or bool(
        getattr(path.lstat(), "st_file_attributes", 0) & 0x400
    )


def validate_inside(path, root):
    path, root = Path(path), Path(root).resolve()
    path.resolve().relative_to(root)
    current = path
    while current != root:
        if current.exists() or current.is_symlink():
            if is_link(current):
                raise ValueError(f"Linked paths are not processed: {current}")
        if current.parent == current:
            raise ValueError("Path is outside the selected folder")
        current = current.parent
    return path


def move_no_replace(source, destination):
    """Never overwrite an existing name; preserve source if copying fails."""
    source, destination = Path(source), Path(destination)
    if os.name == "nt":
        # Windows rename is atomic and fails if the destination exists.
        os.rename(source, destination)
        return
    _move_posix_no_replace(source, destination)


def _move_posix_no_replace(source, destination):
    """Link/unlink is no-clobber and keeps the inode recorded by the journal.

    A cross-filesystem move fails safely, as Windows rename does. Copy/delete
    would change identity and silently invalidate the undo record.
    """
    os.link(source, destination, follow_symlinks=False)
    try:
        source.unlink()
    except BaseException:
        if destination.exists() and os.path.samefile(source, destination):
            destination.unlink(missing_ok=True)
        raise


@dataclass(frozen=True)
class PlannedMove:
    source: Path
    destination: Path | None
    signature: tuple | None
    status: str = "Ready"


def iter_files(root, recursive=False, config=None, cancel_event=None):
    """Never follow links, junctions, ignored subtrees or the quarantine folder."""
    root = Path(root).resolve()

    def allowed(path):
        return not is_link(path) and (config is None or not config.should_ignore(path))

    if recursive:

        def onerror(error):
            raise error

        for directory, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            check_cancel(cancel_event)
            base = Path(directory)
            dirs[:] = [d for d in dirs if allowed(base / d)]
            for name in files:
                check_cancel(cancel_event)
                path = base / name
                if allowed(path) and path.is_file():
                    yield path
    else:
        for path in root.iterdir():
            check_cancel(cancel_event)
            if allowed(path) and path.is_file():
                yield path
