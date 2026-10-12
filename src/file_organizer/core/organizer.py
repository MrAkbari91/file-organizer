"""Core file organizer logic supporting extension, category, and date modes, config rules, ignore patterns, logging, and undo."""

import logging
import os
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from file_organizer.core.categories import get_file_category
from file_organizer.core.config import ConfigManager
from file_organizer.core.logger import setup_logger
from file_organizer.core.undo import UndoManager
from file_organizer.core.utils import (
    can_read_write,
    get_safe_destination,
    is_hidden_file,
    normalize_extension,
    remove_empty_folders,
)


class OrganizeMode(str, Enum):
    EXTENSION = "extension"
    CATEGORY = "category"
    DATE = "date"


class FileOrganizer:
    """Handles organizing files within folders with custom configs and ignore rules."""

    def __init__(
        self,
        target_folder: Path,
        mode: OrganizeMode = OrganizeMode.EXTENSION,
        sub_extension: bool = True,
        recursive: bool = False,
        clean_empty: bool = False,
        dry_run: bool = False,
        config: Optional[ConfigManager] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.target_folder = Path(target_folder).resolve()
        self.mode = mode
        self.sub_extension = sub_extension
        self.recursive = recursive
        self.clean_empty = clean_empty
        self.dry_run = dry_run
        self.config = config or ConfigManager()
        self.logger = logger or setup_logger(target_folder=self.target_folder)
        self.undo_manager = UndoManager(self.target_folder)
        self.stats = {
            "moved": 0,
            "skipped": 0,
            "errors": 0,
            "cleaned_dirs": 0,
        }

    def _get_target_files(self) -> List[Path]:
        """Collect files to organize while respecting ignore patterns."""
        files: List[Path] = []
        if self.recursive:
            for root, dirs, filenames in os.walk(str(self.target_folder)):
                current_dir = Path(root)

                # Skip ignored directories
                if self.config.should_ignore(current_dir):
                    dirs.clear()  # Do not recurse into ignored directories
                    continue

                for fname in filenames:
                    file_path = current_dir / fname
                    if not self.config.should_ignore(file_path):
                        files.append(file_path)
        else:
            for item in self.target_folder.iterdir():
                if item.is_file() and not self.config.should_ignore(item):
                    files.append(item)
        return files

    def _determine_relative_destination_dir(self, file_path: Path) -> Optional[Path]:
        """Determine destination folder relative to target_folder."""
        ext = normalize_extension(file_path)

        if self.mode == OrganizeMode.CATEGORY:
            # Check custom categories first
            category_name = get_file_category(
                file_path,
                custom_categories=self.config.custom_categories or None,
            )
            if self.sub_extension and ext:
                return Path(category_name) / ext
            return Path(category_name)

        elif self.mode == OrganizeMode.DATE:
            try:
                mtime = file_path.stat().st_mtime
                dt = datetime.fromtimestamp(mtime)
                year = dt.strftime("%Y")
                month = dt.strftime("%B")
                date_path = Path(year) / month
                if self.sub_extension and ext:
                    return date_path / ext
                return date_path
            except Exception:
                fallback = Path("Unknown_Date")
                if self.sub_extension and ext:
                    return fallback / ext
                return fallback

        else:
            # EXTENSION mode
            if not ext:
                return None
            return Path(ext)

    def organize(self) -> Dict[str, int]:
        """Organize files by extension, category, or date into subdirectories."""
        if not self.target_folder.exists() or not self.target_folder.is_dir():
            raise NotADirectoryError(f"Target folder does not exist or is not a directory: {self.target_folder}")

        self.logger.info(f"Organizing folder: {self.target_folder}")
        self.logger.info(
            f"Mode: {self.mode.value} | Sub-extension: {self.sub_extension} | "
            f"Recursive: {self.recursive} | Clean empty: {self.clean_empty}"
        )
        if self.dry_run:
            self.logger.info("[DRY RUN MODE] - No files will actually be moved.")

        files_to_process = self._get_target_files()
        recorded_moves: List[Dict[str, str]] = []

        for item in files_to_process:
            rel_dest_dir = self._determine_relative_destination_dir(item)
            if rel_dest_dir is None:
                self.logger.info(f"Skipped (no extension): {item.name}")
                self.stats["skipped"] += 1
                continue

            dest_folder = self.target_folder / rel_dest_dir
            dest_file = dest_folder / item.name

            # Skip if already at destination
            if item.resolve() == dest_file.resolve():
                continue

            # Collision handling
            if dest_file.exists():
                self.logger.warning(f"Skipped (already exists): {item.name} -> {rel_dest_dir.as_posix()}/")
                self.stats["skipped"] += 1
                continue

            try:
                if not self.dry_run:
                    dest_folder.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(dest_file))
                    recorded_moves.append({
                        "source": str(item),
                        "destination": str(dest_file),
                    })

                action = "[DRY-RUN] Would move" if self.dry_run else "Moved"
                self.logger.info(f"{action}: {item.name} -> {rel_dest_dir.as_posix()}/")
                self.stats["moved"] += 1
            except Exception as e:
                self.logger.error(f"Error moving {item.name}: {e}")
                self.stats["errors"] += 1

        # Record manifest for undo
        if not self.dry_run and recorded_moves:
            self.undo_manager.record_manifest(recorded_moves)

        # Clean empty folders if requested
        if self.clean_empty and not self.dry_run:
            cleaned = remove_empty_folders(self.target_folder)
            self.stats["cleaned_dirs"] = cleaned
            if cleaned > 0:
                self.logger.info(f"Cleaned up {cleaned} empty folder(s).")

        summary = f"Done! Moved: {self.stats['moved']}, Skipped: {self.stats['skipped']}, Errors: {self.stats['errors']}"
        self.logger.info(summary)
        return self.stats

    def undo(self):
        """Revert the last organize operation."""
        return self.undo_manager.undo_last()
