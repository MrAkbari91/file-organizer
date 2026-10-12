"""Tests for Core FileOrganizer logic."""

from pathlib import Path
from file_organizer.core.organizer import FileOrganizer, OrganizeMode


def test_organize_files_by_extension(temp_dir: Path):
    # Setup sample files
    (temp_dir / "document.pdf").write_text("dummy pdf")
    (temp_dir / "photo.jpg").write_text("dummy photo")
    (temp_dir / "notes.txt").write_text("dummy note")
    (temp_dir / ".hidden").write_text("hidden file")

    organizer = FileOrganizer(temp_dir, mode=OrganizeMode.EXTENSION)
    stats = organizer.organize()

    # Verify files moved to correct extension folders
    assert (temp_dir / "pdf" / "document.pdf").exists()
    assert (temp_dir / "jpg" / "photo.jpg").exists()
    assert (temp_dir / "txt" / "notes.txt").exists()

    # Hidden file should remain untouched
    assert (temp_dir / ".hidden").exists()

    assert stats["moved"] == 3
    assert stats["skipped"] == 0


def test_organize_files_by_category(temp_dir: Path):
    # Setup sample files
    (temp_dir / "document.pdf").write_text("pdf")
    (temp_dir / "photo.png").write_text("photo")
    (temp_dir / "song.mp3").write_text("audio")
    (temp_dir / "script.py").write_text("code")
    (temp_dir / "archive.zip").write_text("zip")
    (temp_dir / "custom.unknown_ext").write_text("other")

    organizer = FileOrganizer(temp_dir, mode=OrganizeMode.CATEGORY)
    stats = organizer.organize()

    assert (temp_dir / "Documents" / "document.pdf").exists()
    assert (temp_dir / "Images" / "photo.png").exists()
    assert (temp_dir / "Audio" / "song.mp3").exists()
    assert (temp_dir / "Code" / "script.py").exists()
    assert (temp_dir / "Archives" / "archive.zip").exists()
    assert (temp_dir / "Others" / "custom.unknown_ext").exists()

    assert stats["moved"] == 6
    assert stats["skipped"] == 0


def test_organize_dry_run(temp_dir: Path):
    doc = temp_dir / "file.pdf"
    doc.write_text("pdf data")

    organizer = FileOrganizer(temp_dir, dry_run=True)
    stats = organizer.organize()

    # File should NOT be moved in dry run
    assert doc.exists()
    assert not (temp_dir / "pdf").exists()
    assert stats["moved"] == 1


def test_organize_skip_existing(temp_dir: Path):
    pdf_dir = temp_dir / "pdf"
    pdf_dir.mkdir()
    (pdf_dir / "test.pdf").write_text("existing")

    # Same file in root
    (temp_dir / "test.pdf").write_text("duplicate")

    organizer = FileOrganizer(temp_dir)
    stats = organizer.organize()

    # Should skip because destination already exists
    assert stats["skipped"] == 1
    assert (temp_dir / "test.pdf").exists()
