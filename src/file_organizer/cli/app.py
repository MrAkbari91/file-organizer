"""CLI entry point module."""

import argparse
import sys
from pathlib import Path
from file_organizer import __version__
from file_organizer.core.organizer import FileOrganizer


def main() -> None:
    """Entry point for CLI interface."""
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description="Organize files in a directory into subfolders by extension.",
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=".",
        help="Path to folder to organize (default: current working directory)",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Preview file moves without actually moving anything",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    target_path = Path(args.folder).resolve()
    if not target_path.exists() or not target_path.is_dir():
        print(f"Error: Path is not a valid directory: {target_path}", file=sys.stderr)
        sys.exit(1)

    try:
        organizer = FileOrganizer(target_folder=target_path, dry_run=args.dry_run)
        organizer.organize()
    except Exception as exc:
        print(f"Failed to organize files: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
