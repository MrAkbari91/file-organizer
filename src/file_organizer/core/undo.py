"""Undo and rollback management for File Organizer."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HISTORY_DIR_NAME = ".file_organizer_history"


class UndoManager:
    """Manages recording and reverting file organize operations."""

    def __init__(self, target_folder: Path):
        self.target_folder = Path(target_folder).resolve()
        self.history_dir = self.target_folder / HISTORY_DIR_NAME

    def _ensure_history_dir(self) -> Path:
        """Create history directory if missing."""
        self.history_dir.mkdir(parents=True, exist_ok=True)
        return self.history_dir

    def record_manifest(self, moves: List[Dict[str, str]]) -> Optional[Path]:
        """
        Record a list of moves as a timestamped JSON manifest.
        moves format: [{'source': '/orig/path', 'destination': '/dest/path'}]
        """
        if not moves:
            return None

        self._ensure_history_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        manifest_file = self.history_dir / f"manifest_{timestamp}.json"

        data = {
            "timestamp": datetime.now().isoformat(),
            "target_folder": str(self.target_folder),
            "moves_count": len(moves),
            "moves": moves,
        }

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return manifest_file

    def get_latest_manifest(self) -> Optional[Path]:
        """Find the most recent manifest file in the history directory."""
        if not self.history_dir.exists():
            return None

        manifests = sorted(
            self.history_dir.glob("manifest_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return manifests[0] if manifests else None

    def undo_last(self) -> Tuple[int, int, List[str]]:
        """
        Roll back the most recent organize operation.
        Returns (reverted_count, error_count, list_of_errors).
        """
        latest = self.get_latest_manifest()
        if not latest:
            return 0, 0, ["No history manifests found to undo."]

        try:
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return 0, 1, [f"Failed to read manifest {latest.name}: {e}"]

        moves = data.get("moves", [])
        reverted = 0
        errors: List[str] = []

        # Revert in reverse order
        for move in reversed(moves):
            src = Path(move["source"])
            dest = Path(move["destination"])

            if not dest.exists():
                errors.append(f"Destination file no longer exists: {dest}")
                continue

            try:
                # Ensure original directory exists
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(src))
                reverted += 1

                # Clean up empty destination folder if empty
                if dest.parent != self.target_folder and dest.parent.exists():
                    try:
                        dest.parent.rmdir()
                    except OSError:
                        # Directory not empty, leave it
                        pass
            except Exception as e:
                errors.append(f"Failed to revert {dest} -> {src}: {e}")

        # Remove the applied manifest
        try:
            latest.unlink()
            # If history folder is empty, clean it up
            if not any(self.history_dir.iterdir()):
                self.history_dir.rmdir()
        except Exception:
            pass

        return reverted, len(errors), errors
