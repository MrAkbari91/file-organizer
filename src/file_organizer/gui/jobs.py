"""Single-job coordinator. Workers never call Tk, including Tk.after()."""

import queue
import threading
import time
from file_organizer.core.safety import OperationCancelled


class JobRunner:
    def __init__(self):
        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.thread = None
        self.busy = False
        self.last_progress = 0

    def start(self, name, work):
        if self.busy:
            return False
        self.busy = True
        self.cancel_event.clear()

        def run():
            try:
                result = work(self.cancel_event, self.progress)
                self.events.put(("result", (name, result)))
            except OperationCancelled:
                self.events.put(("cancelled", name))
            except Exception as error:
                self.events.put(("error", (name, str(error))))
            finally:
                self.events.put(("finished", name))

        self.thread = threading.Thread(target=run, name="organizer-job", daemon=False)
        self.thread.start()
        return True

    def progress(self, done, total, text):
        now = time.monotonic()
        if now - self.last_progress >= 0.05 or done == total:
            self.last_progress = now
            self.events.put(("progress", (done, total, text)))

    def cancel(self):
        self.cancel_event.set()
