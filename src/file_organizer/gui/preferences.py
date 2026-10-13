"""Persistent desktop preferences, isolated from the existing sorting config."""

import json
import os
from pathlib import Path


def preferences_path():
    return (
        Path(
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("XDG_CONFIG_HOME")
            or Path.home() / ".config"
        )
        / "FileOrganizer"
        / "appearance.json"
    )


class Preferences:
    def __init__(self, path=None):
        self.path = Path(path) if path else preferences_path()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.data = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            self.data = {}

    def save(self, **values):
        self.data.update(values)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)
