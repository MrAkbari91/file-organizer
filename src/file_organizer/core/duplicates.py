"""Cancellable duplicate scans with size filtering and stat-validated hash caching."""

import hashlib
from enum import Enum
from pathlib import Path
from file_organizer.core.categories import get_file_category
from file_organizer.core.config import ConfigManager
from file_organizer.core.safety import (
    iter_files,
    fingerprint,
    check_cancel,
    validate_inside,
)
from file_organizer.core.undo import UndoManager, MoveJournal

CHUNK_SIZE = 1024 * 1024
DUPLICATES_FOLDER_NAME = "_duplicates"


class DuplicateMethod(str, Enum):
    EXACT = "exact"
    CONVERTED = "converted"
    VISUAL = "visual"


def get_file_hash(file_path, cancel_event=None):
    digest = hashlib.sha256()
    with Path(file_path).open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            check_cancel(cancel_event)
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(
    target_folder,
    method=DuplicateMethod.EXACT,
    recursive=False,
    cancel_event=None,
    progress=None,
    cache=None,
    signatures=None,
    config=None,
):
    target = Path(target_folder).resolve()
    if not target.is_dir():
        raise NotADirectoryError(f"Folder is unavailable: {target}")
    # Match historical hidden/quarantine exclusions and skip generated logs.
    config = config or ConfigManager()
    files = list(iter_files(target, recursive, config, cancel_event))
    groups, sizes = {}, {}
    cache = {} if cache is None else cache
    for path in files:
        check_cancel(cancel_event)
        sizes.setdefault(path.stat().st_size, []).append(path)
    if method == DuplicateMethod.EXACT:
        candidates = [
            p
            for size, paths in sizes.items()
            if size > 0 and len(paths) > 1
            for p in paths
        ]
    else:
        candidates = files
    for index, path in enumerate(candidates):
        check_cancel(cancel_event)
        before = fingerprint(path)
        if method == DuplicateMethod.CONVERTED:
            key = f"{get_file_category(path)}::{path.stem.lower().strip()}"
        elif method == DuplicateMethod.VISUAL:
            if get_file_category(path) != "Images":
                continue
            from PIL import Image, UnidentifiedImageError

            try:
                with Image.open(path) as image:
                    image = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
                    pixels = list(
                        image.get_flattened_data()
                        if hasattr(image, "get_flattened_data")
                        else image.getdata()
                    )
                    bits = [
                        (
                            "1"
                            if pixels[row * 9 + col] > pixels[row * 9 + col + 1]
                            else "0"
                        )
                        for row in range(8)
                        for col in range(8)
                    ]
                    key = hex(int("".join(bits), 2))
            except (UnidentifiedImageError, OSError):
                continue
        else:
            cache_key = (str(path), before, path.stat().st_ctime_ns)
            key = cache.get(cache_key)
            if key is None:
                key = get_file_hash(path, cancel_event)
                cache[cache_key] = key
        if fingerprint(path) != before:
            raise ValueError(f"File changed during scan; scan again: {path}")
        if signatures is not None:
            signatures[str(path)] = before
        groups.setdefault(key, []).append(path)
        if progress:
            progress(index + 1, len(candidates), "Comparing files")
    if len(cache) > 10000:
        cache.clear()
    results = {}
    for key, paths in groups.items():
        if len(paths) < 2:
            continue
        if method == DuplicateMethod.CONVERTED:
            if len({p.suffix.lower() for p in paths}) < 2:
                continue
            paths.sort(key=lambda p: p.stat().st_size, reverse=True)
        results[key] = paths
    return results


def find_exact_duplicates(target_folder, recursive=False):
    return find_duplicates(target_folder, DuplicateMethod.EXACT, recursive)


def find_converted_duplicates(target_folder, recursive=False):
    return find_duplicates(target_folder, DuplicateMethod.CONVERTED, recursive)


def _find_visual_duplicates_pillow(target_folder, recursive=False):
    return find_duplicates(target_folder, DuplicateMethod.VISUAL, recursive)


def calculate_duplicate_space(duplicate_groups):
    return sum(
        p.stat().st_size
        for paths in duplicate_groups.values()
        for p in paths[1:]
        if p.exists()
    )


def move_duplicates(
    target_folder,
    duplicate_groups,
    undo_manager=None,
    dry_run=False,
    cancel_event=None,
    progress=None,
    signatures=None,
):
    target = Path(target_folder).resolve()
    destination = validate_inside(target / DUPLICATES_FOLDER_NAME, target)
    journal = MoveJournal(undo_manager or UndoManager(target))
    moved, records, reserved = 0, [], set()
    total = sum(max(0, len(paths) - 1) for paths in duplicate_groups.values())
    # A reviewed group must still contain the same files before any action starts.
    for paths in duplicate_groups.values():
        for path in paths:
            validate_inside(path, target)
            if signatures is not None and fingerprint(path) != signatures[str(path)]:
                raise ValueError(f"File changed since scan; scan again: {path}")
    for paths in duplicate_groups.values():
        for source in paths[1:]:
            if cancel_event is not None and cancel_event.is_set():
                return moved, records
            if signatures is not None:
                for member in (paths[0], source):
                    if fingerprint(member) != signatures[str(member)]:
                        raise ValueError(f"File changed since scan: {member}")
            dest = destination / source.name
            counter = 1
            while dest.exists() or dest in reserved:
                dest = destination / f"{source.stem}_dup{counter}{source.suffix}"
                counter += 1
            reserved.add(dest)
            if not dry_run:
                destination.mkdir(exist_ok=True)
                records.append(journal.move(source, dest))
            moved += 1
            if progress:
                progress(
                    moved,
                    total,
                    "Previewing copies" if dry_run else "Moving extra copies",
                )
    return moved, records
