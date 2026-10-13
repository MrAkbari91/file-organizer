"""Unit tests for FolderWatcher and autostart components."""

import time
from pathlib import Path
from file_organizer.core.autostart import disable_autostart, is_autostart_enabled
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.watcher import FolderWatcher


def test_folder_watcher_detects_and_moves_new_file(temp_dir: Path):
    organizer = FileOrganizer(temp_dir, mode=OrganizeMode.EXTENSION)
    cycles = []
    watcher = FolderWatcher(
        organizer, interval=0.5, on_cycle=lambda count: cycles.append(count)
    )

    watcher.start()
    assert watcher.is_running() is True

    # Drop a new file into watched folder
    new_file = temp_dir / "invoice.pdf"
    new_file.write_text("sample content")

    # Wait for watcher poll
    time.sleep(1.2)
    watcher.stop()
    assert watcher.is_running() is False

    # Check file was auto-organized
    assert (temp_dir / "pdf" / "invoice.pdf").exists()
    assert not new_file.exists()
    assert len(cycles) > 0


def test_autostart_disable_safe(monkeypatch, temp_dir):
    monkeypatch.setattr(
        "file_organizer.core.autostart.get_windows_startup_bat",
        lambda: temp_dir / "test-startup.bat",
    )
    # Disabling should never crash and return a boolean
    result = disable_autostart()
    assert isinstance(result, bool)
