"""Core file organizer logic."""

import shutil
from pathlib import Path
from typing import Dict, List, Optional
from file_organizer.core.utils import is_hidden_file, normalize_extension, get_safe_destination, can_read_write


class FileOrganizer:
    """Handles organizing files within folders."""

    def __init__(self, target_folder: Path, dry_run: bool = False):
        self.target_folder = Path(target_folder).resolve()
        self.dry_run = dry_run
        self.stats = {
            "moved": 0,
            "skipped": 0,
            "errors": 0,
        }

    def organize(self) -> Dict[str, int]:
        """Organize files by extension into subdirectories."""
        if not self.target_folder.exists() or not self.target_folder.is_dir():
            raise NotADirectoryError(f"Target folder does not exist or is not a directory: {self.target_folder}")

        print(f"\n📂 Organizing folder: {self.target_folder}")
        if self.dry_run:
            print("🔍 [DRY RUN MODE] - No files will actually be moved.\n")

        for item in list(self.target_folder.iterdir()):
            # Only process files directly under the target directory
            if not item.is_file():
                continue

            # Skip hidden files like .gitignore, .DS_Store
            if is_hidden_file(item):
                continue

            # Get normalized extension
            ext = normalize_extension(item)
            if not ext:
                # File has no extension
                print(f"⏩ Skipped (no extension): {item.name}")
                self.stats["skipped"] += 1
                continue

            dest_folder = self.target_folder / ext
            dest_file = dest_folder / item.name

            # Collision handling: if file already exists in destination
            if dest_file.exists():
                print(f"⚠️  Skipped (already exists): {item.name} -> {ext}/")
                self.stats["skipped"] += 1
                continue

            try:
                if not self.dry_run:
                    dest_folder.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(dest_file))
                
                action = "[DRY-RUN] Would move" if self.dry_run else "Moved"
                print(f"✅ {action}: {item.name} -> {ext}/")
                self.stats["moved"] += 1
            except Exception as e:
                print(f"❌ Error moving {item.name}: {e}")
                self.stats["errors"] += 1

        print(f"\nDone! Moved: {self.stats['moved']}, Skipped: {self.stats['skipped']}, Errors: {self.stats['errors']}")
        return self.stats
