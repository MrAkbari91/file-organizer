"""Unit tests for category mappings and resolution."""

from pathlib import Path
from file_organizer.core.categories import get_file_category, build_extension_map


def test_get_file_category_standard():
    assert get_file_category(Path("photo.JPG")) == "Images"
    assert get_file_category(Path("vector.svg")) == "Images"
    assert get_file_category(Path("doc.pdf")) == "Documents"
    assert get_file_category(Path("sheet.xlsx")) == "Documents"
    assert get_file_category(Path("song.mp3")) == "Audio"
    assert get_file_category(Path("movie.mkv")) == "Videos"
    assert get_file_category(Path("backup.zip")) == "Archives"
    assert get_file_category(Path("script.py")) == "Code"
    assert get_file_category(Path("installer.exe")) == "Executables"


def test_get_file_category_unmapped():
    # Unknown extensions should fallback to 'Others'
    assert get_file_category(Path("unknown_file.xyz123")) == "Others"


def test_get_file_category_no_extension():
    assert get_file_category(Path("LICENSE")) == "Others"


def test_custom_categories():
    custom = {
        "Photos": ["jpg", "png"],
        "Office": ["docx", "xlsx"],
    }
    assert get_file_category(Path("pic.jpg"), custom_categories=custom) == "Photos"
    assert get_file_category(Path("sheet.xlsx"), custom_categories=custom) == "Office"
    assert get_file_category(Path("song.mp3"), custom_categories=custom) == "Others"
