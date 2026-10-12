"""Tests for Core FileOrganizer logic."""

from datetime import datetime
from pathlib import Path
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.utils import remove_empty_folders


def test_organize_files_by_extension(temp_dir: Path):
    (temp_dir / "document.pdf").write_text("dummy pdf")
    (temp_dir / "photo.jpg").write_text("dummy photo")
    (temp_dir / "notes.txt").write_text("dummy note")
    (temp_dir / ".hidden").write_text("hidden file")

    organizer = FileOrganizer(temp_dir, mode=OrganizeMode.EXTENSION)
    stats = organizer.organize()

    assert (temp_dir / "pdf" / "document.pdf").exists()
    assert (temp_dir / "jpg" / "photo.jpg").exists()
    assert (temp_dir / "txt" / "notes.txt").exists()
    assert (temp_dir / ".hidden").exists()

    assert stats["moved"] == 3
    assert stats["skipped"] == 0


def test_organize_files_by_category_with_sub_extensions(temp_dir: Path):
    (temp_dir / "document.pdf").write_text("pdf")
    (temp_dir / "photo.png").write_text("photo")
    (temp_dir / "icon.svg").write_text("svg")
    (temp_dir / "style.css").write_text("css")
    (temp_dir / "product.liquid").write_text("liquid")

    # Default sub_extension is True -> Category/extension/file
    organizer = FileOrganizer(temp_dir, mode=OrganizeMode.CATEGORY, sub_extension=True)
    stats = organizer.organize()

    assert (temp_dir / "Documents" / "pdf" / "document.pdf").exists()
    assert (temp_dir / "Images" / "png" / "photo.png").exists()
    assert (temp_dir / "Images" / "svg" / "icon.svg").exists()
    assert (temp_dir / "Code" / "css" / "style.css").exists()
    assert (temp_dir / "Code" / "liquid" / "product.liquid").exists()

    assert stats["moved"] == 5
    assert stats["skipped"] == 0


def test_organize_files_by_category_without_sub_extensions(temp_dir: Path):
    (temp_dir / "photo.jpg").write_text("photo")
    (temp_dir / "script.py").write_text("py")

    organizer = FileOrganizer(temp_dir, mode=OrganizeMode.CATEGORY, sub_extension=False)
    stats = organizer.organize()

    assert (temp_dir / "Images" / "photo.jpg").exists()
    assert (temp_dir / "Code" / "script.py").exists()
    assert stats["moved"] == 2


def test_organize_files_by_date_with_sub_extensions(temp_dir: Path):
    file1 = temp_dir / "receipt.pdf"
    file2 = temp_dir / "photo.jpg"
    file1.write_text("receipt data")
    file2.write_text("photo data")

    dt = datetime.fromtimestamp(file1.stat().st_mtime)
    expected_year = dt.strftime("%Y")
    expected_month = dt.strftime("%B")

    organizer = FileOrganizer(temp_dir, mode=OrganizeMode.DATE, sub_extension=True)
    stats = organizer.organize()

    assert stats["moved"] == 2
    assert (temp_dir / expected_year / expected_month / "pdf" / "receipt.pdf").exists()
    assert (temp_dir / expected_year / expected_month / "jpg" / "photo.jpg").exists()


def test_organize_files_by_date_without_sub_extensions(temp_dir: Path):
    file1 = temp_dir / "receipt.pdf"
    file1.write_text("receipt data")

    dt = datetime.fromtimestamp(file1.stat().st_mtime)
    expected_year = dt.strftime("%Y")
    expected_month = dt.strftime("%B")

    organizer = FileOrganizer(temp_dir, mode=OrganizeMode.DATE, sub_extension=False)
    stats = organizer.organize()

    assert stats["moved"] == 1
    assert (temp_dir / expected_year / expected_month / "receipt.pdf").exists()


def test_organize_recursive_and_clean_empty(temp_dir: Path):
    sub1 = temp_dir / "folder_a" / "sub_folder"
    sub1.mkdir(parents=True)
    sub2 = temp_dir / "folder_b"
    sub2.mkdir()

    file_nested = sub1 / "nested_doc.pdf"
    file_nested.write_text("nested")
    file_b = sub2 / "image.png"
    file_b.write_text("image")

    organizer = FileOrganizer(
        temp_dir,
        mode=OrganizeMode.EXTENSION,
        recursive=True,
        clean_empty=True,
    )
    stats = organizer.organize()

    assert stats["moved"] == 2
    assert (temp_dir / "pdf" / "nested_doc.pdf").exists()
    assert (temp_dir / "png" / "image.png").exists()

    # Empty source folders should be removed
    assert not sub1.exists()
    assert not sub2.exists()
    assert stats["cleaned_dirs"] >= 2


def test_organize_dry_run(temp_dir: Path):
    doc = temp_dir / "file.pdf"
    doc.write_text("pdf data")

    organizer = FileOrganizer(temp_dir, dry_run=True)
    stats = organizer.organize()

    assert doc.exists()
    assert not (temp_dir / "pdf").exists()
    assert stats["moved"] == 1


def test_organize_skip_existing(temp_dir: Path):
    pdf_dir = temp_dir / "pdf"
    pdf_dir.mkdir()
    (pdf_dir / "test.pdf").write_text("existing")

    (temp_dir / "test.pdf").write_text("duplicate")

    organizer = FileOrganizer(temp_dir)
    stats = organizer.organize()

    assert stats["skipped"] == 1
    assert (temp_dir / "test.pdf").exists()
