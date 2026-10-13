"""Durable move journals and conservative rollback of existing manifests."""

import json
import os
from datetime import datetime
from pathlib import Path
from file_organizer.core.safety import (
    fingerprint,
    validate_inside,
    move_no_replace,
    check_cancel,
)

HISTORY_DIR_NAME = ".file_organizer_history"


class MoveJournal:
    """Flush each intent before moving. A crash leaves a recoverable record."""

    def __init__(self, manager):
        self.manager = manager
        self.path = None

    def move(self, source, destination):
        signature = fingerprint(source)
        if self.path is None:
            folder = self.manager._ensure_history_dir()
            self.path = folder / (
                "manifest_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".jsonl"
            )
        entry = {
            "source": str(source),
            "destination": str(destination),
            "signature": signature,
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry) + "\n")
            file.flush()
            os.fsync(file.fileno())
        move_no_replace(source, destination)
        return entry


class UndoManager:
    def __init__(self, target_folder):
        self.target_folder = Path(target_folder).resolve()
        self.history_dir = self.target_folder / HISTORY_DIR_NAME

    def _ensure_history_dir(self):
        validate_inside(self.history_dir, self.target_folder)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        return self.history_dir

    def record_manifest(self, moves):
        if not moves:
            return None
        self._ensure_history_dir()
        path = self.history_dir / (
            "manifest_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json"
        )
        self._save(path, moves)
        return path

    def _save(self, path, moves):
        temporary = path.with_suffix(".tmp")
        data = {
            "timestamp": datetime.now().isoformat(),
            "target_folder": str(self.target_folder),
            "moves_count": len(moves),
            "moves": moves,
        }
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)

    def manifests(self):
        if not self.history_dir.exists():
            return []
        validate_inside(self.history_dir, self.target_folder)
        return sorted(
            [
                *self.history_dir.glob("manifest_*.json"),
                *self.history_dir.glob("manifest_*.jsonl"),
            ],
            key=lambda p: p.name,
            reverse=True,
        )

    def get_latest_manifest(self):
        return next(iter(self.manifests()), None)

    def read_manifest(self, path):
        validate_inside(path, self.target_folder)
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".jsonl":
            moves = []
            for line in text.splitlines():
                try:
                    moves.append(json.loads(line))
                except ValueError:
                    # An incomplete final append cannot describe a completed move.
                    break
            return moves
        return json.loads(text).get("moves", [])

    def undo_last(self, cancel_event=None, progress=None):
        latest = self.get_latest_manifest()
        if latest is None:
            return 0, 0, ["No history manifests found to undo."]
        try:
            moves = self.read_manifest(latest)
        except (OSError, ValueError) as error:
            return 0, 1, [f"Failed to read history: {error}"]
        reverted, errors, remaining = 0, [], []
        for index, move in enumerate(reversed(moves)):
            if cancel_event is not None and cancel_event.is_set():
                remaining.extend(list(reversed(moves))[index:])
                break
            try:
                src = validate_inside(Path(move["source"]), self.target_folder)
                dest = validate_inside(Path(move["destination"]), self.target_folder)
                if not dest.exists():
                    if src.exists():
                        continue  # intent failed, or already restored before a crash
                    raise FileNotFoundError(f"Moved file is missing: {dest}")
                if src.exists():
                    raise FileExistsError(f"Original location is occupied: {src}")
                if move.get("signature") and tuple(move["signature"]) != fingerprint(
                    dest
                ):
                    raise ValueError(f"Moved file has changed; left untouched: {dest}")
                src.parent.mkdir(parents=True, exist_ok=True)
                move_no_replace(dest, src)
                reverted += 1
                if dest.parent != self.target_folder:
                    try:
                        dest.parent.rmdir()
                    except OSError:
                        pass
            except (OSError, ValueError, KeyError, TypeError) as error:
                errors.append(str(error))
                remaining.append(move)
            if progress:
                progress(index + 1, len(moves), "Restoring files")
        if remaining:
            # Preserve unsuccessful entries for a later retry, with original order.
            replacement = latest.with_suffix(".json")
            self._save(replacement, list(reversed(remaining)))
            if replacement != latest:
                latest.unlink()
        else:
            latest.unlink()
            try:
                self.history_dir.rmdir()
            except OSError:
                pass
        return reverted, len(errors), errors
