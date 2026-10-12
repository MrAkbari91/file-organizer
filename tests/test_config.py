"""Unit tests for configuration manager and ignore patterns."""

import json
from pathlib import Path
from file_organizer.core.config import ConfigManager


def test_default_config_ignore_patterns(temp_dir: Path):
    config = ConfigManager()

    # Hidden files
    assert config.should_ignore(temp_dir / ".git") is True
    assert config.should_ignore(temp_dir / ".hidden_file") is True
    assert config.should_ignore(temp_dir / "node_modules") is True
    assert config.should_ignore(temp_dir / "cache.tmp") is True

    # Normal files
    assert config.should_ignore(temp_dir / "document.pdf") is False
    assert config.should_ignore(temp_dir / "photo.jpg") is False


def test_custom_config_loading(temp_dir: Path):
    cfg_file = temp_dir / "my_config.json"
    custom_data = {
        "categories": {
            "WorkDocs": ["doc", "docx"],
        },
        "ignore_patterns": ["secret_*", "*.draft"],
    }
    cfg_file.write_text(json.dumps(custom_data))

    config = ConfigManager(config_path=cfg_file)

    assert "WorkDocs" in config.custom_categories
    assert config.should_ignore(temp_dir / "secret_file.pdf") is True
    assert config.should_ignore(temp_dir / "notes.draft") is True
    assert config.should_ignore(temp_dir / "regular.pdf") is False
