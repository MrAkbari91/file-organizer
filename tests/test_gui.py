"""Behavior tests for the premium UI using isolated generated folders."""

import json
import time
import tkinter as tk
from pathlib import Path
import pytest
import customtkinter as ctk
from file_organizer.gui.app import OrganizerGUI
from file_organizer.gui.views import PAGES
from file_organizer.gui.windows import MainWindow, AppToplevel


def pump_events(window, milliseconds=30):
    """Run Tk's native event loop for a bounded interval.

    Tcl's update command drains the event queue before returning. On macOS,
    window initialization can keep that queue active indefinitely. A scheduled
    quit returns control to the test without requiring an empty event queue.
    Use the interpreter root so closing a child cannot delete the quit timer.
    """
    root = window._root()
    timer = root.after(milliseconds, root.quit)
    try:
        root.mainloop()
    finally:
        root.after_cancel(timer)


@pytest.fixture(scope="module")
def gui_root():
    root = MainWindow()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def gui_app(tmp_path, gui_root, monkeypatch):
    root = AppToplevel(gui_root)
    root.withdraw()
    app = OrganizerGUI(root, tmp_path / "settings" / "appearance.json")
    monkeypatch.setattr(app, "_notify", lambda *a, **k: True)
    yield app
    app._close()
    deadline = time.monotonic() + 5
    while not app._closed and time.monotonic() < deadline:
        pump_events(gui_root)
        time.sleep(0.01)
    assert app._closed


def wait(app):
    deadline = time.monotonic() + 8
    while (app._busy or app._render_timers) and time.monotonic() < deadline:
        pump_events(app.root)
        time.sleep(0.01)
    assert not app._busy
    pump_events(app.root)


def dataset(app, tmp_path):
    folder = tmp_path / "files"
    folder.mkdir()
    (folder / "notes.txt").write_text("hello")
    app.selected_folder.set(str(folder))
    app.organize_mode.set("extension")
    return folder


def test_launch_empty_state_and_navigation(gui_app):
    assert gui_app.active_tab == "dashboard"
    assert gui_app.stat_labels["scanned"].cget("text") == "—"
    assert gui_app.organize_btn.instate(["disabled"])
    for page in PAGES:
        gui_app._set_tab(page)
        assert gui_app.active_tab == page
    assert "Ready" in gui_app.status_text_var.get()


def test_themes_persist_without_losing_input(gui_app, tmp_path):
    folder = dataset(gui_app, tmp_path)
    gui_app._set_tab("organize")
    gui_app.toggle_theme()
    assert gui_app.selected_folder.get() == str(folder)
    assert gui_app.active_tab == "organize"
    saved = json.loads(gui_app.preferences_path.read_text())
    assert saved["theme"] == gui_app.current_theme
    assert saved["mode"] == "extension"
    assert gui_app.palette["accent_primary"] in ("#22D3EE", "#087EA4")


def test_preference_restored(gui_root, tmp_path):
    path = tmp_path / "appearance.json"
    path.write_text('{"theme":"light","mode":"date","recursive":true}')
    root = AppToplevel(gui_root)
    root.withdraw()
    app = OrganizerGUI(root, path)
    try:
        assert app.current_theme == "light"
        assert app.organize_mode.get() == "date"
        assert app.recursive_var.get()
    finally:
        app._close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_minimum_size_actions_visible(gui_app, theme):
    if gui_app.current_theme != theme:
        gui_app.toggle_theme()
    # Map before processing native window events, as on ordinary startup.
    gui_app.root.deiconify()
    pump_events(gui_app.root, 100)
    gui_app.root.geometry("1080x720")
    for page in PAGES:
        gui_app._set_tab(page)
        # Give each page's scrollable layout time to settle.
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            pump_events(gui_app.root)
            if gui_app.root.winfo_ismapped() and time.monotonic() > deadline - 0.8:
                break
            time.sleep(0.01)
        assert gui_app.page_host.winfo_height() > 80
        if page in gui_app.action_frames:
            actions = gui_app.action_frames[page]
            assert actions.winfo_ismapped()
            assert (
                actions.winfo_rooty() + actions.winfo_height()
                <= gui_app.console_card.winfo_rooty()
            )
        assert (
            gui_app.cancel_btn.winfo_rooty() + gui_app.cancel_btn.winfo_height()
            <= gui_app.root.winfo_rooty() + gui_app.root.winfo_height()
        )


def test_preview_is_read_only_then_organize_and_undo(gui_app, tmp_path):
    folder = dataset(gui_app, tmp_path)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    gui_app.dry_run_var.set(True)
    gui_app._start_preview()
    wait(gui_app)
    assert before == {p.name: p.read_bytes() for p in folder.iterdir()}
    assert len(gui_app.plan_table.tree.get_children()) == 1
    assert gui_app.organize_btn.instate(["disabled"])
    gui_app.dry_run_var.set(False)
    gui_app._start_organize()
    wait(gui_app)
    assert (folder / "txt" / "notes.txt").exists()
    assert gui_app._organized == 1
    gui_app._refresh_history()
    wait(gui_app)
    assert gui_app._undo_available
    gui_app._start_undo()
    wait(gui_app)
    assert (folder / "notes.txt").exists()
    assert "Restored 1" in gui_app.status_text_var.get()


def test_preview_invalidates_when_rules_change(gui_app, tmp_path):
    dataset(gui_app, tmp_path)
    gui_app._start_preview()
    wait(gui_app)
    assert gui_app._plan
    gui_app.recursive_var.set(True)
    assert gui_app._plan is None
    assert gui_app.organize_btn.instate(["disabled"])


def test_duplicate_selection_preview_and_move(gui_app, tmp_path):
    folder = dataset(gui_app, tmp_path)
    (folder / "copy.txt").write_text("hello")
    gui_app._start_find_duplicates()
    wait(gui_app)
    assert gui_app._duplicate_count == 1
    assert gui_app.move_dup_btn.instate(["disabled"])
    gui_app._select_extras()
    assert len(gui_app._selected_duplicate_paths()) == 1
    gui_app.dry_run_var.set(True)
    gui_app._start_move_duplicates()
    wait(gui_app)
    assert not (folder / "_duplicates").exists()
    gui_app.dry_run_var.set(False)
    gui_app._start_move_duplicates()
    wait(gui_app)
    assert len(list((folder / "_duplicates").iterdir())) == 1
    assert gui_app._undo_available


def test_background_failure_unlocks(gui_app, tmp_path, monkeypatch):
    dataset(gui_app, tmp_path)

    def fail(*a, **k):
        raise PermissionError("Test access denied")

    monkeypatch.setattr("file_organizer.gui.app.FileOrganizer.plan", fail)
    gui_app._start_preview()
    wait(gui_app)
    assert "Test access denied" in gui_app.status_text_var.get()
    assert not gui_app.preview_btn.instate(["disabled"])


def test_cancel_keeps_ui_responsive(gui_app, tmp_path, monkeypatch):
    dataset(gui_app, tmp_path)

    def slow(self, cancel, progress):
        while not cancel.wait(0.01):
            pass
        from file_organizer.core.safety import OperationCancelled

        raise OperationCancelled()

    monkeypatch.setattr("file_organizer.gui.app.FileOrganizer.plan", slow)
    gui_app._start_preview()
    gui_app._set_tab("dashboard")
    gui_app.toggle_theme()
    assert gui_app._busy
    gui_app._cancel()
    wait(gui_app)
    assert "cancelled" in gui_app.status_text_var.get()


def test_watcher_start_stop(gui_app, tmp_path):
    folder = dataset(gui_app, tmp_path)
    gui_app._toggle_watch()
    deadline = time.monotonic() + 4
    while not (folder / "txt" / "notes.txt").exists() and time.monotonic() < deadline:
        pump_events(gui_app.root)
        time.sleep(0.02)
    assert gui_app.active_watcher.is_running()
    assert gui_app.folder_entry.cget("state") == "disabled"
    gui_app.toggle_theme()
    assert "Watching" in gui_app.watcher_badge.cget("text")
    gui_app._toggle_watch()
    while gui_app._watch_stopping and time.monotonic() < deadline:
        pump_events(gui_app.root)
        time.sleep(0.02)
    assert gui_app.active_watcher is None
    assert (folder / "txt" / "notes.txt").exists()


def test_logs_copy_clear_and_invalid_folder(gui_app, tmp_path):
    gui_app._log("Test event", "WARNING")
    assert "WARNING" in gui_app.log_text.get("1.0", "end")
    gui_app._copy_log()
    assert "Test event" in gui_app.root.clipboard_get()
    gui_app._clear_log()
    assert not gui_app.log_text.get("1.0", "end").strip()
    gui_app.selected_folder.set(str(tmp_path / "missing"))
    assert gui_app.preview_btn.instate(["disabled"])
    assert "unavailable" in gui_app.folder_hint.cget("text")


def test_theme_switch_preserves_visible_window_and_review(gui_app, tmp_path):
    dataset(gui_app, tmp_path)
    gui_app._set_tab("organize")
    gui_app._start_preview()
    wait(gui_app)
    root = gui_app.root
    root.deiconify()
    pump_events(root, 100)
    tree = gui_app.plan_table.tree
    row = tree.get_children()[0]
    tree.selection_set(row)
    identity, geometry, plan = root.winfo_id(), root.geometry(), gui_app._plan
    unmapped = []
    root.bind(
        "<Unmap>",
        lambda event: unmapped.append(event.widget) if event.widget is root else None,
        add="+",
    )
    for _ in range(4):
        gui_app.toggle_theme()
        pump_events(root, 100)
        assert root.winfo_id() == identity and root.winfo_ismapped()
        assert root.geometry() == geometry
        assert gui_app._plan is plan
        assert tree.selection() == (row,)
        assert gui_app.active_tab == "organize"
    assert unmapped == []


def test_focus_events_do_not_restack_windows(gui_app, monkeypatch):
    from types import SimpleNamespace

    raised = []
    monkeypatch.setattr(gui_app.root, "lift", lambda: raised.append(True))
    for widget in (gui_app.root, gui_app.folder_entry):
        gui_app.root._focus_in_event(SimpleNamespace(widget=widget))
    assert raised == []
