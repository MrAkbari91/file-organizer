"""CLI entry point module."""

import argparse
import sys
from pathlib import Path
from file_organizer import __version__
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.undo import UndoManager


def main() -> None:
    """Entry point for CLI interface."""
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description="Organize files in a directory into subfolders by extension or category.",
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=".",
        help="Path to folder to organize (default: current working directory)",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--by-extension",
        action="store_true",
        default=True,
        help="Organize files by extension (e.g., jpg/, pdf/) [default]",
    )
    mode_group.add_argument(
        "--by-category",
        action="store_true",
        help="Organize files by category (e.g., Images/, Documents/, Videos/)",
    )

    parser.add_argument(
        "-u",
        "--undo",
        action="store_true",
        help="Undo/revert the last organize operation in the target folder",
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

    # Handle Undo
    if args.undo:
        undo_mgr = UndoManager(target_path)
        reverted, error_count, errors = undo_mgr.undo_last()
        if error_count > 0 and reverted == 0:
            print(f"Undo failed: {errors[0]}", file=sys.stderr)
            sys.exit(1)
        print(f"\n↩️  Undo Complete! Reverted {reverted} file(s).")
        if errors:
            print("Encountered errors:")
            for err in errors:
                print(f"  - {err}")
        return

    mode = OrganizeMode.CATEGORY if args.by_category else OrganizeMode.EXTENSION

    try:
        organizer = FileOrganizer(target_folder=target_path, mode=mode, dry_run=args.dry_run)
        organizer.organize()
    except Exception as exc:
        print(f"Failed to organize files: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
