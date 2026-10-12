"""Category mappings and resolution logic for files."""

from pathlib import Path
from typing import Dict, List, Optional
from file_organizer.core.utils import normalize_extension

# Standard category mappings
DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    "Images": [
        "jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "tiff", "ico", "raw", "heic"
    ],
    "Documents": [
        "pdf", "doc", "docx", "txt", "rtf", "odt", "xls", "xlsx", "csv", "ppt", "pptx", "ods", "odp"
    ],
    "Audio": [
        "mp3", "wav", "aac", "flac", "ogg", "m4a", "wma"
    ],
    "Videos": [
        "mp4", "mkv", "mov", "avi", "wmv", "flv", "webm", "m4v"
    ],
    "Archives": [
        "zip", "tar", "gz", "bz2", "7z", "rar", "iso", "xz"
    ],
    "Code": [
        "py", "js", "ts", "html", "css", "json", "xml", "yaml", "yml", "md",
        "c", "cpp", "h", "java", "cs", "php", "rb", "go", "rs", "sh", "bat", "ps1", "sql"
    ],
    "Executables": [
        "exe", "msi", "dmg", "pkg", "deb", "rpm", "apk"
    ],
}


def build_extension_map(categories: Optional[Dict[str, List[str]]] = None) -> Dict[str, str]:
    """Invert categories mapping so lookup by extension is O(1)."""
    mapping = categories or DEFAULT_CATEGORIES
    ext_to_cat: Dict[str, str] = {}
    for category, extensions in mapping.items():
        for ext in extensions:
            ext_to_cat[ext.lower().lstrip(".")] = category
    return ext_to_cat


# Pre-built lookup table
EXTENSION_TO_CATEGORY: Dict[str, str] = build_extension_map()


def get_file_category(
    file_path: Path,
    custom_categories: Optional[Dict[str, List[str]]] = None,
    fallback_folder: str = "Others",
) -> str:
    """
    Get the category folder name for a given file.
    If the extension is not mapped, returns fallback_folder (default 'Others').
    """
    ext = normalize_extension(file_path)
    if not ext:
        return fallback_folder

    if custom_categories:
        ext_map = build_extension_map(custom_categories)
        return ext_map.get(ext, fallback_folder)

    return EXTENSION_TO_CATEGORY.get(ext, fallback_folder)
