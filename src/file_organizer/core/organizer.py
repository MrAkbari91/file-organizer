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
from file_organizer.core.undo import UndoManager, MoveJournal
from file_organizer.core.safety import (
    PlannedMove,
    fingerprint,
    iter_files,
    validate_inside,
    check_cancel,
    OperationCancelled,
)
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
        self.logger = logger or setup_logger(
            target_folder=None if dry_run else self.target_folder
        )
        self.undo_manager = UndoManager(self.target_folder)
        self.stats = {
            "moved": 0,
            "skipped": 0,
            "errors": 0,
            "cleaned_dirs": 0,
        }

    def _get_target_files(self, cancel_event=None):
        return list(
            iter_files(self.target_folder, self.recursive, self.config, cancel_event)
        )

    def plan(self, cancel_event=None, progress=None):
        if not self.target_folder.is_dir():
            raise NotADirectoryError(f"Folder is unavailable: {self.target_folder}")
        files = self._get_target_files(cancel_event)
        plan, reserved = [], set()
        for index, source in enumerate(files):
            check_cancel(cancel_event)
            try:
                relative = self._determine_relative_destination_dir(source)
                destination = (
                    self.target_folder / relative / source.name
                    if relative is not None
                    else None
                )
                signature = fingerprint(source)
                status = "Ready"
                if destination is None:
                    status = "Skip · no extension"
                elif source == destination:
                    status = "Skip · already organized"
                else:
                    validate_inside(destination, self.target_folder)
                    if destination.exists() or destination in reserved:
                        status = "Skip · destination exists"
                    reserved.add(destination)
                plan.append(PlannedMove(source, destination, signature, status))
            except (OSError, ValueError) as error:
                plan.append(PlannedMove(source, None, None, f"Error · {error}"))
            if progress:
                progress(index + 1, len(files), "Scanning files")
        return plan

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

    def organize(self, plan=None, cancel_event=None, progress=None):
        """Apply a reviewed plan, revalidating each file and destination first."""
        if not self.target_folder.is_dir():
            raise NotADirectoryError(f"Folder is unavailable: {self.target_folder}")
        self.stats = dict(
            moved=0, skipped=0, errors=0, cleaned_dirs=0, scanned=0, cancelled=False
        )
        try:
            plan = self.plan(cancel_event, progress) if plan is None else plan
        except OperationCancelled:
            self.stats["cancelled"] = True
            return self.stats
        self.stats["scanned"] = len(plan)
        journal = MoveJournal(self.undo_manager)
        for index, item in enumerate(plan):
            if cancel_event is not None and cancel_event.is_set():
                self.stats["cancelled"] = True
                break
            try:
                if item.status != "Ready":
                    self.stats[
                        "errors" if item.status.startswith("Error") else "skipped"
                    ] += 1
                    self.logger.info(f"{item.status}: {item.source}")
                else:
                    validate_inside(item.source, self.target_folder)
                    validate_inside(item.destination, self.target_folder)
                    if fingerprint(item.source) != item.signature:
                        raise ValueError(
                            f"File changed since preview; scan again: {item.source}"
                        )
                    if item.destination.exists():
                        self.stats["skipped"] += 1
                        self.logger.warning(
                            f"Skipped existing destination: {item.destination}"
                        )
                    else:
                        if not self.dry_run:
                            item.destination.parent.mkdir(parents=True, exist_ok=True)
                            journal.move(item.source, item.destination)
                        self.stats["moved"] += 1
                        self.logger.info(
                            f"{'Would move' if self.dry_run else 'Moved'}: {item.source} → {item.destination}"
                        )
            except (OSError, ValueError) as error:
                self.stats["errors"] += 1
                self.logger.error(str(error))
            if progress:
                progress(
                    index + 1, len(plan), "Previewing" if self.dry_run else "Organizing"
                )
        if self.clean_empty and not self.dry_run and not self.stats["cancelled"]:
            self.stats["cleaned_dirs"] = remove_empty_folders(
                self.target_folder, config=self.config
            )
        self.logger.info(
            f"Finished · moved {self.stats['moved']} · skipped {self.stats['skipped']} · errors {self.stats['errors']}"
        )
        return self.stats

    def undo(self):
        """Revert the last organize operation."""
        return self.undo_manager.undo_last()
