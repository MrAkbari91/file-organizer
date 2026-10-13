"""CLI entry point module."""

import argparse
import sys
import time
from pathlib import Path
from file_organizer import __version__
from file_organizer.core.autostart import (
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
)
from file_organizer.core.config import ConfigManager
from file_organizer.core.duplicates import (
    DuplicateMethod,
    calculate_duplicate_space,
    find_duplicates,
    move_duplicates,
)
from file_organizer.core.logger import setup_logger, close_logger
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.undo import UndoManager
from file_organizer.core.watcher import FolderWatcher


def format_bytes(num_bytes: int) -> str:
    """Format bytes into readable string (KB, MB, GB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def main() -> None:
    """Entry point for CLI interface."""
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description="Organize files in a directory into subfolders by extension, category, or date.",
    )
    parser.add_argument(
        "--background-watch", metavar="SETTINGS", help=argparse.SUPPRESS
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

    # Watch Mode options
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Continuous auto-organize mode (Ctrl+C to stop)",
    )
    parser.add_argument(
        "--watch-interval",
        type=float,
        default=3.0,
        help="Polling interval in seconds for watch mode (default: 3.0)",
    )

    # System Startup options
    parser.add_argument(
        "--enable-startup",
        action="store_true",
        help="Enable silent background auto-watch on system boot (requires confirmation)",
    )
    parser.add_argument(
        "--disable-startup",
        action="store_true",
        help="Disable and remove background auto-watch from system boot",
    )

    # Config & Ignore options
    parser.add_argument(
        "--config",
        dest="config_file",
        help="Path to custom JSON configuration file",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Add pattern to ignore (can be used multiple times, e.g. --ignore '*.bak')",
    )

    # Duplicate options
    parser.add_argument(
        "--find-duplicates",
        action="store_true",
        help="Scan and report duplicate files without organizing",
    )
    parser.add_argument(
        "--move-duplicates",
        action="store_true",
        help="Find and isolate redundant duplicate files into _duplicates/ folder",
    )
    parser.add_argument(
        "--dup-method",
        choices=["exact", "converted", "visual"],
        default="exact",
        help="Duplicate detection method: 'exact' (SHA-256), 'converted' (same name across formats), 'visual' (pixel hash)",
    )

    parser.add_argument(
        "--no-sub-extension",
        action="store_true",
        help="Do not create extension subfolders inside Category or Date folders",
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
    if args.background_watch:
        from file_organizer.gui.startup import run_background

        run_background(Path(args.background_watch))
        return
    if args.watch_interval <= 0:
        parser.error("--watch-interval must be greater than zero")
    if args.dry_run and (args.undo or args.enable_startup or args.disable_startup):
        parser.error("--dry-run cannot be combined with undo or startup registration")
    if (args.enable_startup or args.disable_startup) and sys.platform != "win32":
        parser.error(
            "Sign-in registration is supported on Windows only. Use --watch on macOS/Linux."
        )
    try:
        _execute(args)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        close_logger()


def _execute(args):

    target_path = Path(args.folder).resolve()
    if not target_path.exists() or not target_path.is_dir():
        print(f"Error: Path is not a valid directory: {target_path}", file=sys.stderr)
        sys.exit(1)

    # Setup Logger & Config
    cfg_path = Path(args.config_file) if args.config_file else None
    config = ConfigManager(config_path=cfg_path)
    for pat in args.ignore:
        if pat not in config.ignore_patterns:
            config.ignore_patterns.append(pat)

    logger = setup_logger(
        target_folder=None if args.dry_run or args.find_duplicates else target_path
    )

    # Handle Startup Commands
    if args.enable_startup:
        mode_str = (
            "category"
            if args.by_category
            else (
                "date"
                if args.by_date
                else "extension" if args.by_extension else config.default_mode
            )
        )
        confirm = (
            input(
                f"Enable silent background auto-organize for '{target_path}' on system boot? (y/N): "
            )
            .strip()
            .lower()
        )
        if confirm == "y":
            if enable_autostart(
                target_path,
                mode=mode_str,
                recursive=args.recursive,
                sub_extension=False if args.no_sub_extension else config.sub_extension,
                clean_empty=args.clean_empty,
                ignore_patterns=config.ignore_patterns,
                config=config,
            ):
                logger.info("✅ Startup auto-watch enabled successfully!")
            else:
                logger.error("❌ Failed to enable startup auto-watch.")
                raise SystemExit(1)
        else:
            print("Cancelled by user.")
        return

    if args.disable_startup:
        if disable_autostart():
            logger.info("✅ Startup auto-watch disabled and removed.")
        else:
            logger.error("❌ Failed to disable startup auto-watch.")
            raise SystemExit(1)
        return

    # Handle Undo
    if args.undo:
        undo_mgr = UndoManager(target_path)
        reverted, error_count, errors = undo_mgr.undo_last()
        if error_count > 0 and reverted == 0:
            logger.error(f"Undo failed: {errors[0]}")
            sys.exit(1)
        logger.info(f"↩️  Undo Complete! Reverted {reverted} file(s).")
        if errors:
            for err in errors:
                logger.warning(f"  - {err}")
        if error_count:
            raise SystemExit(1)
        return

    # Handle Duplicate Detection
    if args.find_duplicates or args.move_duplicates:
        method = DuplicateMethod(args.dup_method)
        logger.info(
            f"Scanning duplicates in: {target_path} (Method: {method.value}, Recursive: {args.recursive})"
        )
        signatures = {}
        dups = find_duplicates(
            target_path,
            method=method,
            recursive=args.recursive,
            config=config,
            signatures=signatures,
        )

        if not dups:
            logger.info("🎉 No duplicate or converted format files found!")
            return

        wasted = calculate_duplicate_space(dups)
        total_dup_files = sum(len(files) - 1 for files in dups.values())
        logger.info(
            f"⚠️  Found {len(dups)} duplicate group(s) ({total_dup_files} redundant files, ~{format_bytes(wasted)} can be saved):"
        )

        for idx, (key, files) in enumerate(dups.items(), 1):
            label = key if len(key) < 30 else f"{key[:20]}..."
            logger.info(f"Group #{idx} [{label}]:")
            logger.info(
                f"  [Keep/Original] -> {files[0].name} ({format_bytes(files[0].stat().st_size)})"
            )
            for extra in files[1:]:
                logger.info(
                    f"  [Duplicate/Copy] -> {extra.name} ({format_bytes(extra.stat().st_size)})"
                )

        if args.move_duplicates:
            undo_mgr = UndoManager(target_path)
            moved_count, _ = move_duplicates(
                target_path,
                dups,
                undo_manager=undo_mgr,
                dry_run=args.dry_run,
                signatures=signatures,
            )
            action = "[DRY-RUN] Would move" if args.dry_run else "Moved"
            logger.info(
                f"📦 {action} {moved_count} redundant file(s) into '_duplicates/' folder."
            )
            if not args.dry_run:
                logger.info("💡 You can revert this anytime using `--undo`.")
        return

    # Normal Organize / Watch workflow
    if args.by_category:
        mode = OrganizeMode.CATEGORY
    elif args.by_date:
        mode = OrganizeMode.DATE
    elif args.by_extension:
        mode = OrganizeMode.EXTENSION
    else:
        mode = OrganizeMode(config.default_mode)

    sub_ext = (
        not args.no_sub_extension if args.no_sub_extension else config.sub_extension
    )

    organizer = FileOrganizer(
        target_folder=target_path,
        mode=mode,
        sub_extension=sub_ext,
        recursive=args.recursive,
        clean_empty=args.clean_empty,
        dry_run=args.dry_run,
        config=config,
        logger=logger,
    )

    if args.watch:
        logger.info(
            f"👀 Starting Watch Mode on: {target_path} (Interval: {args.watch_interval}s, Press Ctrl+C to exit)..."
        )
        watcher = FolderWatcher(organizer, interval=args.watch_interval)
        watcher.start()
        try:
            while watcher.is_running():
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("\nStopping watcher...")
            watcher.stop(timeout=None)
            logger.info("Watcher stopped cleanly.")
        if watcher.last_error:
            logger.error(watcher.last_error)
            raise SystemExit(1)
    else:
        try:
            result = organizer.organize()
            if result["errors"]:
                raise SystemExit(1)
        except Exception as exc:
            logger.error(f"Failed to organize files: {exc}")
            sys.exit(1)


if __name__ == "__main__":
    main()
