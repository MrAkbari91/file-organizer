"""Headless watcher entry point shared by source and packaged sign-in launchers."""

import json
import time
from pathlib import Path
from file_organizer.core.config import ConfigManager
from file_organizer.core.logger import setup_logger, close_logger
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.watcher import FolderWatcher


def run_background(settings_path):
    settings_path = Path(settings_path)
    logger = setup_logger(log_file=settings_path.parent / "startup.log")
    watcher = None
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        cfg = ConfigManager(config_path=settings_path)
        organizer = FileOrganizer(
            Path(data["folder"]),
            mode=OrganizeMode(data["mode"]),
            recursive=data.get("recursive", False),
            sub_extension=data.get("sub_extension", True),
            clean_empty=data.get("clean_empty", False),
            config=cfg,
            logger=logger,
        )
        watcher = FolderWatcher(organizer, interval=5)
        watcher.start()
        while watcher.is_running():
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        logger.error(f"Startup watcher failed: {error}")
    finally:
        if watcher:
            watcher.stop(timeout=None)
        close_logger(logger)
