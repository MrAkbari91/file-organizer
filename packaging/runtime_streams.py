"""Give windowed dependencies a writable diagnostic stream before importing UI."""

import os
import sys
from pathlib import Path

if sys.stderr is None or sys.stdout is None:
    try:
        log_dir = (
            Path(
                os.environ.get("LOCALAPPDATA")
                or os.environ.get("XDG_CONFIG_HOME")
                or Path.home() / ".config"
            )
            / "FileOrganizer"
        )
        log_dir.mkdir(parents=True, exist_ok=True)
        stream = (log_dir / "bootstrap.log").open("a", encoding="utf-8", buffering=1)
    except OSError:
        stream = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = stream
    if sys.stdout is None:
        sys.stdout = stream
