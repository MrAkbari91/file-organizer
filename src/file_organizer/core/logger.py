"""Logging configuration and utilities for File Organizer."""

import logging
from pathlib import Path
from typing import Callable, Optional

DEFAULT_LOG_FILENAME = "file_organizer.log"


class CallbackHandler(logging.Handler):
    """Custom logging handler to route logs to GUI text components or callbacks."""

    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.callback(msg)
        except Exception:
            self.handleError(record)


def setup_logger(
    target_folder: Optional[Path] = None,
    log_file: Optional[Path] = None,
    gui_callback: Optional[Callable[[str], None]] = None,
    verbose: bool = False,
) -> logging.Logger:
    """Setup and return a configured logger."""
    logger = logging.getLogger("file_organizer")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Safely close existing handlers to avoid file locks (especially on Windows)
    for h in list(logger.handlers):
        try:
            h.close()
        except Exception:
            pass
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler
    if log_file:
        file_path = log_file
    elif target_folder:
        file_path = target_folder / DEFAULT_LOG_FILENAME
    else:
        file_path = None

    if file_path:
        try:
            file_handler = logging.FileHandler(str(file_path), encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass

    # 3. Optional GUI callback handler
    if gui_callback:
        cb_handler = CallbackHandler(gui_callback)
        cb_handler.setLevel(logging.INFO)
        cb_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(cb_handler)

    return logger


def close_logger(logger: Optional[logging.Logger] = None) -> None:
    """Close all handlers attached to the logger to release file locks."""
    log = logger or logging.getLogger("file_organizer")
    for handler in list(log.handlers):
        try:
            handler.close()
            log.removeHandler(handler)
        except Exception:
            pass
