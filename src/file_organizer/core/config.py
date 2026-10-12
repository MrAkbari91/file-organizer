"""Configuration management and custom rules loader for File Organizer."""

import fnmatch
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_CONFIG_FILENAME = "config.json"

DEFAULT_IGNORE_PATTERNS = [
    ".*",             # Hidden files & folders (.git, .vscode, etc.)
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "*.tmp",
    "*.part",
    "*.crdownload",
    "desktop.ini",
    "Thumbs.db",
    "_duplicates",
    ".file_organizer_history",
    "*.log",
    "file_organizer.log",
]


class ConfigManager:
    """Manages loading, parsing, and applying configuration rules."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.custom_categories: Dict[str, List[str]] = {}
        self.ignore_patterns: List[str] = list(DEFAULT_IGNORE_PATTERNS)
        self.default_mode: str = "category"
        self.sub_extension: bool = True
        self.load()

    def load(self) -> None:
        """Load configuration from file if specified or available."""
        if self.config_path and Path(self.config_path).exists():
            target = Path(self.config_path)
        else:
            # Check local working directory config.json
            local_cfg = Path(DEFAULT_CONFIG_FILENAME)
            if local_cfg.exists():
                target = local_cfg
            else:
                return

        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "categories" in data and isinstance(data["categories"], dict):
                self.custom_categories = data["categories"]

            if "ignore_patterns" in data and isinstance(data["ignore_patterns"], list):
                # Merge patterns uniquely
                for pat in data["ignore_patterns"]:
                    if pat not in self.ignore_patterns:
                        self.ignore_patterns.append(pat)

            if "default_mode" in data:
                self.default_mode = data["default_mode"]

            if "sub_extension" in data:
                self.sub_extension = bool(data["sub_extension"])

        except Exception as e:
            print(f"Warning: Failed to parse configuration file '{target}': {e}")

    def should_ignore(self, path: Path) -> bool:
        """Check if a file or directory matches any ignore pattern."""
        name = path.name
        rel_str = str(path)

        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_str, pattern):
                return True
        return False

    def save_default_config(self, save_path: Path) -> Path:
        """Save a clean template config.json for user editing."""
        data = {
            "default_mode": "category",
            "sub_extension": True,
            "ignore_patterns": self.ignore_patterns,
            "categories": {
                "Work": ["docx", "xlsx", "pptx", "pdf"],
                "Personal": ["jpg", "png", "mp4"],
            },
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return save_path
