"""Folder watcher using polling for continuous auto-organizing."""

import threading
import time
from pathlib import Path
from typing import Callable, Optional
from file_organizer.core.organizer import FileOrganizer


class FolderWatcher:
    """Watches a target directory and triggers FileOrganizer when changes are detected."""

    def __init__(
        self,
        organizer: FileOrganizer,
        interval: float = 3.0,
        on_cycle: Optional[Callable[[int], None]] = None,
    ):
        self.organizer = organizer
        self.interval = interval
        self.on_cycle = on_cycle
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start watcher in a background thread."""
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop watcher thread gracefully."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def is_running(self) -> bool:
        """Check if watcher thread is active."""
        return self._thread is not None and self._thread.is_alive()

    def _watch_loop(self) -> None:
        """Internal polling loop."""
        while not self._stop_event.is_set():
            try:
                stats = self.organizer.organize()
                if self.on_cycle and stats["moved"] > 0:
                    self.on_cycle(stats["moved"])
            except Exception as e:
                if self.organizer.logger:
                    self.organizer.logger.error(f"Watcher cycle error: {e}")

            # Sleep in small increments for responsive stop
            sleep_slices = int(self.interval / 0.2)
            for _ in range(max(1, sleep_slices)):
                if self._stop_event.is_set():
                    break
                time.sleep(0.2)
