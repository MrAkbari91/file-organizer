"""Duplicate file detection: Exact Binary (SHA-256), Converted Formats (Same Name/Stem), and Visual Similarity."""

import hashlib
import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from file_organizer.core.categories import get_file_category
from file_organizer.core.undo import UndoManager
from file_organizer.core.utils import is_hidden_file

CHUNK_SIZE = 64 * 1024  # 64 KB chunks
DUPLICATES_FOLDER_NAME = "_duplicates"


class DuplicateMethod(str, Enum):
    EXACT = "exact"            # SHA-256 content hash
    CONVERTED = "converted"    # Same base filename with different extensions (e.g. photo.jpg vs photo.webp)
    VISUAL = "visual"          # Pixel-based perceptual similarity (if Pillow installed)


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file efficiently using chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_exact_duplicates(target_folder: Path, recursive: bool = False) -> Dict[str, List[Path]]:
    """Find exact binary duplicates using size filtering + SHA-256 hashing."""
    target = Path(target_folder).resolve()
    size_groups: Dict[int, List[Path]] = {}

    def collect_files():
        if recursive:
            for root, dirs, files in os.walk(str(target)):
                current = Path(root)
                if any(part.startswith(".") for part in current.relative_to(target).parts):
                    continue
                if current.name == DUPLICATES_FOLDER_NAME:
                    continue
                for fname in files:
                    fp = current / fname
                    if not is_hidden_file(fp) and fp.name != DUPLICATES_FOLDER_NAME:
                        yield fp
        else:
            for item in target.iterdir():
                if item.is_file() and not is_hidden_file(item) and item.name != DUPLICATES_FOLDER_NAME:
                    yield item

    for file_path in collect_files():
        try:
            size = file_path.stat().st_size
            if size > 0:
                size_groups.setdefault(size, []).append(file_path)
        except OSError:
            pass

    duplicate_groups: Dict[str, List[Path]] = {}
    for size, file_list in size_groups.items():
        if len(file_list) > 1:
            hash_groups: Dict[str, List[Path]] = {}
            for fp in file_list:
                try:
                    h = get_file_hash(fp)
                    hash_groups.setdefault(h, []).append(fp)
                except OSError:
                    pass

            for h, matches in hash_groups.items():
                if len(matches) > 1:
                    duplicate_groups[h] = matches

    return duplicate_groups


def find_converted_duplicates(target_folder: Path, recursive: bool = False) -> Dict[str, List[Path]]:
    """
    Find converted file duplicates where the base name (stem) is identical,
    especially across image, video, audio, or document formats.
    Example: banner.jpg, banner.webp, banner.png
    """
    target = Path(target_folder).resolve()
    stem_groups: Dict[str, List[Path]] = {}

    def collect_files():
        if recursive:
            for root, dirs, files in os.walk(str(target)):
                current = Path(root)
                if any(part.startswith(".") for part in current.relative_to(target).parts):
                    continue
                if current.name == DUPLICATES_FOLDER_NAME:
                    continue
                for fname in files:
                    fp = current / fname
                    if not is_hidden_file(fp) and fp.name != DUPLICATES_FOLDER_NAME:
                        yield fp
        else:
            for item in target.iterdir():
                if item.is_file() and not is_hidden_file(item) and item.name != DUPLICATES_FOLDER_NAME:
                    yield item

    for file_path in collect_files():
        # Normalized lower stem (base name without extension)
        stem = file_path.stem.lower().strip()
        category = get_file_category(file_path)

        # Key by stem and broad category so photo.jpg and photo.txt aren't marked as converted images
        key = f"{category}::{stem}"
        stem_groups.setdefault(key, []).append(file_path)

    converted_groups: Dict[str, List[Path]] = {}
    for key, file_list in stem_groups.items():
        # Multiple files with different extensions under the same category
        unique_extensions = {fp.suffix.lower() for fp in file_list}
        if len(file_list) > 1 and len(unique_extensions) > 1:
            # Sort so largest file is first (or smallest depending on retention, keep files sorted by size descending)
            sorted_files = sorted(file_list, key=lambda f: f.stat().st_size if f.exists() else 0, reverse=True)
            converted_groups[key] = sorted_files

    return converted_groups


def find_duplicates(
    target_folder: Path,
    method: DuplicateMethod = DuplicateMethod.EXACT,
    recursive: bool = False,
) -> Dict[str, List[Path]]:
    """Master entry point for duplicate detection based on selected method."""
    if method == DuplicateMethod.CONVERTED:
        return find_converted_duplicates(target_folder, recursive=recursive)
    elif method == DuplicateMethod.VISUAL:
        # If pillow is available, perform perceptual visual hashing; otherwise fallback to converted
        try:
            from PIL import Image
            # Fast perceptual difference hash (dHash) implementation
            return _find_visual_duplicates_pillow(target_folder, recursive=recursive)
        except ImportError:
            print("Note: Pillow is not installed. Using converted format matching instead.")
            return find_converted_duplicates(target_folder, recursive=recursive)
    else:
        return find_exact_duplicates(target_folder, recursive=recursive)


def _find_visual_duplicates_pillow(target_folder: Path, recursive: bool = False) -> Dict[str, List[Path]]:
    """Find visually similar images by computing 64-bit difference hash (dHash)."""
    from PIL import Image

    target = Path(target_folder).resolve()
    image_hashes: Dict[str, List[Path]] = {}

    def collect_images():
        if recursive:
            for root, dirs, files in os.walk(str(target)):
                current = Path(root)
                if any(part.startswith(".") for part in current.relative_to(target).parts):
                    continue
                if current.name == DUPLICATES_FOLDER_NAME:
                    continue
                for fname in files:
                    fp = current / fname
                    if not is_hidden_file(fp) and get_file_category(fp) == "Images":
                        yield fp
        else:
            for item in target.iterdir():
                if item.is_file() and not is_hidden_file(item) and get_file_category(item) == "Images":
                    yield item

    def dhash(image_path: Path, hash_size: int = 8) -> Optional[str]:
        try:
            with Image.open(image_path) as img:
                img = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                diff = []
                for row in range(hash_size):
                    for col in range(hash_size):
                        pixel_left = pixels[row * (hash_size + 1) + col]
                        pixel_right = pixels[row * (hash_size + 1) + col + 1]
                        diff.append("1" if pixel_left > pixel_right else "0")
                return hex(int("".join(diff), 2))[2:].zfill(hash_size * hash_size // 4)
        except Exception:
            return None

    for img_path in collect_images():
        h = dhash(img_path)
        if h:
            image_hashes.setdefault(h, []).append(img_path)

    return {h: files for h, files in image_hashes.items() if len(files) > 1}


def calculate_duplicate_space(duplicate_groups: Dict[str, List[Path]]) -> int:
    """Calculate total redundant bytes that can be freed by removing duplicate copies."""
    wasted_bytes = 0
    for key, files in duplicate_groups.items():
        if len(files) > 1:
            try:
                # Assuming keeping the first file, sum the sizes of the rest
                for copy in files[1:]:
                    wasted_bytes += copy.stat().st_size
            except OSError:
                pass
    return wasted_bytes


def move_duplicates(
    target_folder: Path,
    duplicate_groups: Dict[str, List[Path]],
    undo_manager: Optional[UndoManager] = None,
    dry_run: bool = False,
) -> Tuple[int, List[Dict[str, str]]]:
    """
    Move redundant duplicate copies to target_folder/_duplicates/, keeping the first file in place.
    Returns: (moved_count, recorded_moves)
    """
    target = Path(target_folder).resolve()
    duplicates_dir = target / DUPLICATES_FOLDER_NAME

    recorded_moves: List[Dict[str, str]] = []
    moved_count = 0

    for key, files in duplicate_groups.items():
        redundant_copies = files[1:]

        for copy in redundant_copies:
            dest_file = duplicates_dir / copy.name

            counter = 1
            stem = copy.stem
            suffix = copy.suffix
            while dest_file.exists():
                dest_file = duplicates_dir / f"{stem}_dup{counter}{suffix}"
                counter += 1

            if not dry_run:
                duplicates_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(copy), str(dest_file))
                recorded_moves.append({
                    "source": str(copy),
                    "destination": str(dest_file),
                })
            moved_count += 1

    if not dry_run and recorded_moves and undo_manager:
        undo_manager.record_manifest(recorded_moves)

    return moved_count, recorded_moves
