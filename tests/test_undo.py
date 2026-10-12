"""Unit tests for UndoManager and rollback operations."""

from pathlib import Path
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.undo import UndoManager


def test_undo_manager_records_and_reverts(temp_dir: Path):
    f1 = temp_dir / "report.pdf"
    f2 = temp_dir / "photo.png"
    f1.write_text("pdf content")
    f2.write_text("photo content")

    # Step 1: Organize files
    organizer = FileOrganizer(temp_dir, mode=OrganizeMode.EXTENSION)
    organizer.organize()

    # Verify moved
    assert (temp_dir / "pdf" / "report.pdf").exists()
    assert (temp_dir / "png" / "photo.png").exists()
    assert not f1.exists()
    assert not f2.exists()

    # Step 2: Trigger Undo
    undo_mgr = UndoManager(temp_dir)
    reverted, error_count, errors = undo_mgr.undo_last()

    assert reverted == 2
    assert error_count == 0
    assert not errors

    # Verify files are restored back to root
    assert f1.exists()
    assert f2.exists()
    assert f1.read_text() == "pdf content"
    assert f2.read_text() == "photo content"

    # Verify destination folders cleaned up
    assert not (temp_dir / "pdf").exists()
    assert not (temp_dir / "png").exists()


def test_undo_when_no_history(temp_dir: Path):
    undo_mgr = UndoManager(temp_dir)
    reverted, error_count, errors = undo_mgr.undo_last()
    assert reverted == 0
    assert error_count == 0
    assert "No history manifests found" in errors[0]
