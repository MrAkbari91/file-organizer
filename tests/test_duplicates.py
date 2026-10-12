"""Unit tests for duplicate detection and management."""

from pathlib import Path
from file_organizer.core.duplicates import (
    DuplicateMethod,
    calculate_duplicate_space,
    find_duplicates,
    get_file_hash,
    move_duplicates,
)
from file_organizer.core.undo import UndoManager


def test_get_file_hash(temp_dir: Path):
    f1 = temp_dir / "a.txt"
    f2 = temp_dir / "b.txt"
    f3 = temp_dir / "c.txt"

    f1.write_text("identical text")
    f2.write_text("identical text")
    f3.write_text("different text")

    assert get_file_hash(f1) == get_file_hash(f2)
    assert get_file_hash(f1) != get_file_hash(f3)


def test_find_exact_duplicates(temp_dir: Path):
    f1 = temp_dir / "image.png"
    f2 = temp_dir / "image_copy.png"
    f3 = temp_dir / "different.png"

    content = b"sample image binary bytes"
    f1.write_bytes(content)
    f2.write_bytes(content)
    f3.write_bytes(b"completely different bytes")

    dups = find_duplicates(temp_dir, method=DuplicateMethod.EXACT)
    assert len(dups) == 1
    h = list(dups.keys())[0]
    assert len(dups[h]) == 2


def test_find_converted_format_duplicates(temp_dir: Path):
    # Same photo saved as .jpg, .webp, and .png
    f1 = temp_dir / "hero-banner.jpg"
    f2 = temp_dir / "hero-banner.webp"
    f3 = temp_dir / "hero-banner.png"
    f4 = temp_dir / "other-image.jpg"

    # Write different byte sizes (as would happen in real conversions)
    f1.write_bytes(b"large jpeg data" * 100)
    f2.write_bytes(b"small webp data" * 20)
    f3.write_bytes(b"medium png data" * 50)
    f4.write_bytes(b"another different picture")

    dups = find_duplicates(temp_dir, method=DuplicateMethod.CONVERTED)
    assert len(dups) == 1
    key = list(dups.keys())[0]
    assert "hero-banner" in key
    # Should contain all 3 converted formats of hero-banner
    assert len(dups[key]) == 3

    # Test moving converted duplicates
    undo_mgr = UndoManager(temp_dir)
    moved_count, _ = move_duplicates(temp_dir, dups, undo_manager=undo_mgr)

    # Largest is kept in place, smaller 2 are isolated
    assert moved_count == 2
    assert f1.exists()  # Kept in place
    assert not f2.exists()
    assert not f3.exists()
    assert (temp_dir / "_duplicates" / "hero-banner.webp").exists()

    # Test Undo
    reverted, errs, _ = undo_mgr.undo_last()
    assert reverted == 2
    assert f2.exists()
    assert f3.exists()
