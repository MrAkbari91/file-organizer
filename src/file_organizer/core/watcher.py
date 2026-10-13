"""Polling watcher with truthful lifecycle and cooperative shutdown."""

import threading
from file_organizer.core.safety import OperationCancelled


class FolderWatcher:
    def __init__(self, organizer, interval=3.0, on_cycle=None):
        self.organizer = organizer
        self.interval = max(0.2, interval)
        self.on_cycle = on_cycle
        self._stop_event = threading.Event()
        self._thread = None
        self.last_error = None

    def start(self):
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watch_loop, name="folder-watcher", daemon=False
        )
        self._thread.start()

    def request_stop(self):
        self._stop_event.set()

    def stop(self, timeout=2.0):
        self.request_stop()
        if self._thread:
            self._thread.join(timeout=timeout)
        return not self.is_running()

    def is_running(self):
        return bool(self._thread and self._thread.is_alive())

    def _watch_loop(self):
        while not self._stop_event.is_set():
            try:
                stats = self.organizer.organize(cancel_event=self._stop_event)
                self.last_error = None
                if self.on_cycle and stats["moved"]:
                    self.on_cycle(stats["moved"])
            except OperationCancelled:
                break
            except Exception as error:
                self.last_error = str(error)
                self.organizer.logger.error(f"Watcher error: {error}")
            self._stop_event.wait(self.interval)
