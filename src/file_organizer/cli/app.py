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
        description="Organize files in a directory into subfolders by extension, category, or date.",
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
        help="Organize files by extension directly (e.g., jpg/, pdf/) [default]",
    )
    mode_group.add_argument(
        "--by-category",
        action="store_true",
        help="Organize files by category and extension (e.g., Images/jpg/, Code/liquid/)",
    )
    mode_group.add_argument(
        "--by-date",
        action="store_true",
        help="Organize files by modification date (e.g., 2026/October/)",
    )

    parser.add_argument(
        "--no-sub-extension",
        action="store_true",
        help="In Category mode, do not create extension subfolders (put directly in Category/)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Process subdirectories recursively",
    )
    parser.add_argument(
        "--clean-empty",
        action="store_true",
        help="Remove empty directories after organizing",
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

    # Determine sorting mode
    if args.by_category:
        mode = OrganizeMode.CATEGORY
    elif args.by_date:
        mode = OrganizeMode.DATE
    else:
        mode = OrganizeMode.EXTENSION

    sub_ext = not args.no_sub_extension

    try:
        organizer = FileOrganizer(
            target_folder=target_path,
            mode=mode,
            sub_extension=sub_ext,
            recursive=args.recursive,
            clean_empty=args.clean_empty,
            dry_run=args.dry_run,
        )
        organizer.organize()
    except Exception as exc:
        print(f"Failed to organize files: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
