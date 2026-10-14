"""Regression tests for preview, journaling, conflict, cancel and link safety."""

import json
import threading
from pathlib import Path
import pytest
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.undo import UndoManager
from file_organizer.core.duplicates import (
    find_duplicates,
    move_duplicates,
    DuplicateMethod,
)
from file_organizer.core.safety import fingerprint, OperationCancelled
from file_organizer.core.config import ConfigManager
from file_organizer.core.watcher import FolderWatcher


def test_preview_conflicts_and_changes_are_not_moved(temp_dir):
    file = temp_dir / "a.txt"
    file.write_text("old")
    org = FileOrganizer(temp_dir)
    plan = org.plan()
    file.write_text("changed")
    assert org.organize(plan)["errors"] == 1
    assert file.read_text() == "changed"
    plan = org.plan()
    (temp_dir / "txt").mkdir()
    (temp_dir / "txt" / "a.txt").write_text("occupied")
    assert org.organize(plan)["skipped"] == 1
    assert file.exists() and (temp_dir / "txt" / "a.txt").read_text() == "occupied"


def test_duplicate_names_in_plan_are_reserved(temp_dir):
    for name in ("first", "second"):
        (temp_dir / name).mkdir()
        (temp_dir / name / "same.txt").write_text(name)
    org = FileOrganizer(temp_dir, recursive=True)
    plan = org.plan()
    assert sum(item.status == "Ready" for item in plan) == 1
    assert org.organize(plan)["moved"] == 1


def test_cancel_after_one_move_keeps_undo(temp_dir):
    for name in ("a.txt", "b.txt", "c.txt"):
        (temp_dir / name).write_text(name)
    org = FileOrganizer(temp_dir)
    plan = org.plan()
    cancel = threading.Event()
    stats = org.organize(plan, cancel, lambda *a: cancel.set())
    assert stats["moved"] == 1 and stats["cancelled"]
    restored, errors, _ = UndoManager(temp_dir).undo_last()
    assert restored == 1 and errors == 0
    assert all((temp_dir / name).exists() for name in ("a.txt", "b.txt", "c.txt"))


def test_undo_conflict_retains_failed_record(temp_dir):
    source = temp_dir / "a.txt"
    source.write_text("original")
    FileOrganizer(temp_dir).organize()
    source.write_text("new content")
    manager = UndoManager(temp_dir)
    assert manager.undo_last()[1] == 1
    assert manager.get_latest_manifest() is not None
    assert source.read_text() == "new content"
    source.unlink()
    assert manager.undo_last()[0] == 1
    assert source.read_text() == "original"


def test_undo_changed_destination_is_preserved(temp_dir):
    (temp_dir / "a.txt").write_text("original")
    FileOrganizer(temp_dir).organize()
    destination = temp_dir / "txt" / "a.txt"
    destination.write_text("edited afterwards")
    restored, errors, _ = UndoManager(temp_dir).undo_last()
    assert restored == 0 and errors == 1
    assert destination.read_text() == "edited afterwards"


def test_legacy_manifest_and_outside_path_are_safe(temp_dir, tmp_path):
    outside = tmp_path / "external.txt"
    outside.write_text("external")
    manager = UndoManager(temp_dir)
    manager.record_manifest(
        [{"source": str(temp_dir / "bad.txt"), "destination": str(outside)}]
    )
    assert manager.undo_last()[1] == 1
    assert outside.read_text() == "external"


def test_custom_category_cannot_escape(temp_dir):
    (temp_dir / "a.txt").write_text("data")
    cfg = ConfigManager()
    cfg.custom_categories = {"../escaped": ["txt"]}
    result = FileOrganizer(temp_dir, mode=OrganizeMode.CATEGORY, config=cfg).organize()
    assert result["errors"] == 1 and (temp_dir / "a.txt").exists()


def test_permission_failure_preserves_file(temp_dir, monkeypatch):
    (temp_dir / "a.txt").write_text("data")

    def denied(*a):
        raise PermissionError("locked file")

    monkeypatch.setattr("file_organizer.core.undo.move_no_replace", denied)
    stats = FileOrganizer(temp_dir).organize()
    assert stats["errors"] == 1 and (temp_dir / "a.txt").exists()
    assert UndoManager(temp_dir).undo_last()[0] == 0


def test_hidden_tree_and_links_are_not_followed(temp_dir, tmp_path):
    hidden = temp_dir / ".private" / "child"
    hidden.mkdir(parents=True)
    (hidden / "secret.txt").write_text("secret")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.txt").write_text("data")
    try:
        (temp_dir / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Windows symlink creation is not permitted")
    FileOrganizer(temp_dir, recursive=True, clean_empty=True).organize()
    assert (hidden / "secret.txt").exists() and (outside / "external.txt").exists()


def test_duplicate_scan_rechecks_content_with_unchanged_metadata(temp_dir, monkeypatch):
    a = temp_dir / "a.txt"
    b = temp_dir / "b.txt"
    a.write_text("same")
    b.write_text("same")
    import file_organizer.core.duplicates as module

    # Deterministically emulate filesystems whose timestamps do not distinguish
    # two same-size writes. No sleeps or reliance on the runner's clock speed.
    original_stat = Path.stat
    snapshots = {a: a.stat(), b: b.stat()}

    def unchanged_stat(path, *args, **kwargs):
        if path in snapshots:
            return snapshots[path]
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", unchanged_stat)

    original = module.get_file_hash
    calls = []

    def counted(*args):
        calls.append(args[0])
        return original(*args)

    monkeypatch.setattr(module, "get_file_hash", counted)
    cache = {}
    assert find_duplicates(temp_dir, cache=cache)
    assert find_duplicates(temp_dir, cache=cache)
    assert len(calls) == 4
    b.write_text("else")
    assert not find_duplicates(temp_dir, cache=cache)
    assert len(calls) == 6


def test_duplicate_snapshot_and_quarantine_pruning(temp_dir):
    a = temp_dir / "a.txt"
    b = temp_dir / "b.txt"
    a.write_text("same")
    b.write_text("same")
    nested = temp_dir / "_duplicates" / "nested"
    nested.mkdir(parents=True)
    (nested / "old.txt").write_text("same")
    signatures = {}
    groups = find_duplicates(temp_dir, recursive=True, signatures=signatures)
    assert sum(len(paths) for paths in groups.values()) == 2
    b.write_text("edited")
    with pytest.raises(ValueError):
        move_duplicates(temp_dir, groups, signatures=signatures)
    assert a.exists() and b.exists()


def test_duplicate_cancel_and_visual_detection(temp_dir):
    from PIL import Image

    Image.new("RGB", (30, 30), "red").save(temp_dir / "a.png")
    Image.new("RGB", (30, 30), "red").save(temp_dir / "b.png")
    assert find_duplicates(temp_dir, DuplicateMethod.VISUAL)
    stop = threading.Event()
    stop.set()
    with pytest.raises(OperationCancelled):
        find_duplicates(temp_dir, cancel_event=stop)


def test_watcher_does_not_claim_stopped_while_working():
    entered = threading.Event()
    release = threading.Event()

    class Slow:
        def organize(self, **kwargs):
            entered.set()
            release.wait(2)
            return {"moved": 0}

    watcher = FolderWatcher(Slow())
    watcher.start()
    assert entered.wait(1)
    assert watcher.stop(timeout=0.01) is False
    assert watcher.is_running()
    release.set()
    assert watcher.stop(timeout=1) is True


def test_autostart_uses_frozen_exe_and_preserves_rules(tmp_path, monkeypatch):
    import file_organizer.core.autostart as module

    folder = tmp_path / "files & photos"
    folder.mkdir()
    startup = tmp_path / "Startup"
    startup.mkdir()
    monkeypatch.setattr(
        module,
        "get_windows_startup_bat",
        lambda: startup / "FileOrganizerAutoWatch.bat",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setattr(module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        module.sys,
        "executable",
        str(tmp_path / "App Folder" / "File Organizer Pro.exe"),
    )
    assert module.enable_autostart(
        folder, mode="date", recursive=True, sub_extension=False
    )
    text = (startup / "FileOrganizerAutoWatch.vbs").read_text(encoding="utf-16")
    assert "--background-watch" in text and "File Organizer Pro.exe" in text
    saved = json.loads(
        (tmp_path / "local" / "FileOrganizer" / "startup.json").read_text()
    )
    assert saved["recursive"] is True and saved["sub_extension"] is False
    assert module.is_autostart_enabled()
    assert module.disable_autostart()
    assert not module.is_autostart_enabled()


def test_excluded_subtrees_are_pruned_without_link_privileges(temp_dir, monkeypatch):
    import file_organizer.core.safety as safety

    hidden = temp_dir / ".private" / "nested"
    linked = temp_dir / "linked-directory"
    hidden.mkdir(parents=True)
    linked.mkdir()
    (hidden / "secret.txt").write_text("private")
    (linked / "remote.txt").write_text("linked contents")
    original = safety.is_link
    monkeypatch.setattr(
        safety,
        "is_link",
        lambda path: Path(path).resolve() == linked.resolve() or original(path),
    )
    result = FileOrganizer(temp_dir, recursive=True, clean_empty=True).organize()
    assert result["moved"] == 0
    assert (hidden / "secret.txt").exists()
    assert (linked / "remote.txt").exists()


def test_posix_move_preserves_identity_for_undo(tmp_path, monkeypatch):
    from file_organizer.core.safety import _move_posix_no_replace
    from file_organizer.core.undo import MoveJournal

    source, destination = tmp_path / "one.txt", tmp_path / "two.txt"
    source.write_text("preserve identity")
    before = fingerprint(source)
    manager = UndoManager(tmp_path)
    monkeypatch.setattr(
        "file_organizer.core.undo.move_no_replace", _move_posix_no_replace
    )
    MoveJournal(manager).move(source, destination)
    assert fingerprint(destination) == before
    assert not source.exists()
    assert manager.undo_last()[:2] == (1, 0)
    assert source.read_text() == "preserve identity"


def test_posix_move_refuses_existing_destination(tmp_path):
    from file_organizer.core.safety import _move_posix_no_replace

    source, destination = tmp_path / "source", tmp_path / "destination"
    source.write_text("source")
    destination.write_text("keep")
    with pytest.raises(FileExistsError):
        _move_posix_no_replace(source, destination)
    assert source.read_text() == "source" and destination.read_text() == "keep"
