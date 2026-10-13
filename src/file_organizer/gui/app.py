"""Desktop coordinator. Workers communicate with Tk only through a queue."""

import os
import queue
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from file_organizer import __version__
from file_organizer.core.autostart import (
    enable_autostart,
    disable_autostart,
    is_autostart_enabled,
)
from file_organizer.core.config import ConfigManager
from file_organizer.core.duplicates import (
    DuplicateMethod,
    find_duplicates,
    move_duplicates,
    calculate_duplicate_space,
)
from file_organizer.core.logger import setup_logger, close_logger
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.safety import fingerprint
from file_organizer.core.undo import UndoManager
from file_organizer.core.watcher import FolderWatcher
from file_organizer.gui.preferences import Preferences
from file_organizer.gui.jobs import JobRunner
from file_organizer.gui.windows import MainWindow
from file_organizer.gui.theme import color, apply_theme
from file_organizer.gui.components import dialog, ASSETS
from file_organizer.gui import views


def format_bytes(value):
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"


class OrganizerGUI:
    def __init__(self, root, preferences_path=None):
        self.root = root
        root.title(f"File Organizer Pro — v{__version__}")
        root.geometry(f"1280x{min(960, root.winfo_screenheight()-80)}")
        root.minsize(1080, 720)
        if os.name == "nt":
            root.iconbitmap(str(ASSETS / "app.ico"))
        else:
            self._window_icon = tk.PhotoImage(master=root, file=str(ASSETS / "app.png"))
            root.iconphoto(True, self._window_icon)
        self.config = ConfigManager()
        self.preferences = Preferences(preferences_path)
        self.preferences_path = self.preferences.path
        saved = self.preferences.data
        self.current_theme = saved.get("theme", getattr(self.config, "theme", "dark"))
        if self.current_theme not in ("light", "dark"):
            self.current_theme = "dark"
        self.style, self.palette = apply_theme(root, self.current_theme)
        self.selected_folder = tk.StringVar(root, value=saved.get("folder", ""))
        mode = saved.get("mode", self.config.default_mode)
        self.organize_mode = tk.StringVar(
            root,
            value=mode if mode in ("category", "date", "extension") else "category",
        )
        self.dup_method_var = tk.StringVar(root, value="exact")
        self.sub_ext_var = tk.BooleanVar(
            root, value=saved.get("sub_extension", self.config.sub_extension)
        )
        self.recursive_var = tk.BooleanVar(root, value=saved.get("recursive", False))
        self.clean_empty_var = tk.BooleanVar(
            root, value=saved.get("clean_empty", False)
        )
        self.dry_run_var = tk.BooleanVar(root, value=saved.get("dry_run", False))
        self.autoscroll_var = tk.BooleanVar(root, value=saved.get("autoscroll", True))
        self.autostart_var = tk.BooleanVar(root, value=is_autostart_enabled())
        self.custom_ignore_var = tk.StringVar(root, value=saved.get("ignore", ""))
        self.status_text_var = tk.StringVar(
            root, value="Ready. Select a folder to begin."
        )
        self.runner = JobRunner()
        self.inputs = []
        self.active_tab = "dashboard"
        self.active_watcher = None
        self._watch_stopping = False
        self._closed = False
        self._closing = False
        self._folder_valid = False
        self._undo_available = False
        self._plan = None
        self._organizer = None
        self._duplicate_groups = {}
        self._duplicate_rows = {}
        self._signatures = {}
        self._hash_cache = {}
        self._save_timer = None
        self._render_timers = {}
        self._trace_ids = []
        self._log_count = 0
        self._organized = 0
        self._last_scanned = None
        self._duplicate_count = None
        self._duplicate_bytes = None
        self.jobs = saved.get("jobs", [])
        if not isinstance(self.jobs, list):
            self.jobs = []
        self.jobs = [
            j
            for j in self.jobs
            if isinstance(j, dict)
            and all(k in j for k in ("time", "action", "folder", "result"))
        ][-50:]
        views.build(self)
        try:
            self.preferences.path.parent.mkdir(parents=True, exist_ok=True)
            log_path = self.preferences.path.parent / "activity.log"
        except OSError:
            log_path = None
        self.logger = setup_logger(
            log_file=log_path,
            gui_callback=lambda text: self.runner.events.put(("log", text)),
        )
        for variable in (
            self.selected_folder,
            self.organize_mode,
            self.sub_ext_var,
            self.recursive_var,
            self.clean_empty_var,
            self.custom_ignore_var,
        ):
            self._trace_ids.append(
                (variable, variable.trace_add("write", self._options_changed))
            )
        self._trace_ids.append(
            (
                self.dup_method_var,
                self.dup_method_var.trace_add("write", self._duplicate_options_changed),
            )
        )
        for variable in (self.dry_run_var, self.autoscroll_var):
            self._trace_ids.append(
                (variable, variable.trace_add("write", self._preferences_changed))
            )
        self._configure_log_tags()
        self._update_route()
        self._folder_changed()
        self._update_dashboard()
        self._render_jobs()
        self._set_tab("dashboard")
        self.theme_btn.configure(
            text="Light theme" if self.current_theme == "dark" else "Dark theme"
        )
        self._log(
            "Ready. Select a folder; no files have been scanned or changed.", "INFO"
        )
        root.bind("<Control-o>", lambda e: self._browse_folder())
        root.bind("<Control-l>", lambda e: self._focus_folder())
        root.bind(
            "<Control-Return>",
            lambda e: self._start_preview() if self.active_tab == "organize" else None,
        )
        root.bind("<Escape>", lambda e: self._cancel() if self.runner.busy else None)
        root.bind("<FocusIn>", self._reveal_focus, add="+")
        root.protocol("WM_DELETE_WINDOW", self._close)
        self._event_timer = root.after(60, self._drain_events)
        root.bind("<Destroy>", self._on_destroy, add="+")

    @property
    def _busy(self):
        return self.runner.busy

    def _locked(self):
        return (
            self.runner.busy
            or self._watch_stopping
            or bool(self.active_watcher and self.active_watcher.is_running())
        )

    def _set_tab(self, key):
        if key not in views.PAGES:
            return
        for page in self.pages.values():
            page.grid_remove()
        self.pages[key].grid(row=0, column=0, sticky="nsew")
        self.active_tab = key
        title, heading, subtitle, _ = views.PAGES[key]
        self.page_title.configure(text=heading)
        self.page_subtitle.configure(text=subtitle)
        self.context_label.configure(text=title)
        for tab, button in self.tab_buttons.items():
            button.base_color = color("accent_soft" if tab == key else "bg_header")
            button.configure(
                fg_color=button.base_color,
                border_width=0,
                text_color=color("accent_primary" if tab == key else "fg_subtext"),
            )
        if key == "dashboard":
            self.folder_card.grid_remove()
        else:
            self.folder_card.grid()
        for frame in self.action_frames.values():
            frame.pack_forget()
        if key in self.action_frames:
            self.action_area.grid()
            self.action_frames[key].pack(fill="x")
        else:
            self.action_area.grid_remove()
        if key == "history" and self._folder_valid and not self._locked():
            self._refresh_history()

    def _focus_folder(self):
        if self.active_tab == "dashboard":
            self._set_tab("organize")
        self.folder_entry.focus_set()

    def _reveal_focus(self, event):
        page = self.pages.get(self.active_tab)
        widget = event.widget
        if page is None or not str(widget).startswith(str(page) + "."):
            return
        canvas = page._parent_canvas
        top = widget.winfo_rooty() - page.winfo_rooty()
        visible = canvas.canvasy(0)
        if (
            top < visible
            or top + widget.winfo_height() > visible + canvas.winfo_height()
        ):
            canvas.yview_moveto(max(0, top - 16) / max(1, page.winfo_height()))

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.style, self.palette = apply_theme(self.root, self.current_theme)
        self.theme_btn.configure(
            text="Light theme" if self.current_theme == "dark" else "Dark theme"
        )
        self._configure_log_tags()
        self._save_preferences()

    def _configure_log_tags(self):
        for tag, token in (
            ("INFO", "accent_info"),
            ("SUCCESS", "success_text"),
            ("WARNING", "accent_warning"),
            ("ERROR", "error_text"),
        ):
            self.log_text.tag_config(tag, foreground=self.palette[token])

    def _save_preferences(self):
        self._save_timer = None
        try:
            self.preferences.save(
                theme=self.current_theme,
                folder=self.selected_folder.get(),
                mode=self.organize_mode.get(),
                sub_extension=self.sub_ext_var.get(),
                recursive=self.recursive_var.get(),
                clean_empty=self.clean_empty_var.get(),
                dry_run=self.dry_run_var.get(),
                autoscroll=self.autoscroll_var.get(),
                ignore=self.custom_ignore_var.get(),
                jobs=self.jobs[-50:],
            )
        except OSError as error:
            self._log(f"Preferences could not be saved: {error}", "WARNING")

    def _preferences_changed(self, *_):
        if self._save_timer:
            self.root.after_cancel(self._save_timer)
        self._save_timer = self.root.after(400, self._save_preferences)
        self._update_actions()

    def _options_changed(self, *_):
        self._invalidate_plan()
        self._invalidate_duplicates()
        self._undo_available = False
        self.undo_summary.configure(
            text="Refresh folder history to check available undo records."
        )
        self._update_route()
        self._folder_changed()
        self._preferences_changed()

    def _duplicate_options_changed(self, *_):
        self._invalidate_duplicates()
        self._update_actions()

    def _cancel_render(self, table):
        timer = self._render_timers.pop(table, None)
        if timer:
            self.root.after_cancel(timer)

    def _invalidate_plan(self):
        self._plan = None
        self._organizer = None
        self._cancel_render(self.plan_table)
        self.plan_table.clear()
        self.plan_summary.configure(
            text="Scan to review planned changes for the current folder and rules."
        )

    def _invalidate_duplicates(self):
        self._duplicate_groups = {}
        self._duplicate_rows = {}
        self._signatures = {}
        self._cancel_render(self.dup_table)
        self.dup_table.clear()
        self.selected_count.configure(text="0 copies selected")
        self.stats_summary_var.set(
            "Scan to review matches for the current folder and method."
        )

    def _folder_changed(self):
        text = self.selected_folder.get().strip()
        try:
            self._folder_valid = (
                bool(text) and Path(text).is_dir() and os.access(Path(text), os.R_OK)
            )
        except (OSError, ValueError):
            self._folder_valid = False
        self.folder_hint.configure(
            text=(
                "Folder ready"
                if self._folder_valid
                else "Folder unavailable" if text else "Choose a folder to get started."
            ),
            text_color=color(
                "success_text"
                if self._folder_valid
                else "error_text" if text else "fg_muted"
            ),
        )
        self._update_actions()

    def _update_route(self):
        sub = "png / " if self.sub_ext_var.get() else ""
        route = {
            "category": f"Images / {sub}photo.png",
            "extension": "png / photo.png",
            "date": f"2026 / October / {sub}photo.png",
        }
        self.route_var.set(
            "Example destination   →   " + route[self.organize_mode.get()]
        )

    def _update_actions(self):
        locked = self._locked()
        valid = self._folder_valid and not locked
        for widget in self.inputs:
            widget.configure(state="disabled" if locked else "normal")
        self.preview_btn.configure(state="normal" if valid else "disabled")
        ready = (
            valid
            and bool(self._plan)
            and any(row.status == "Ready" for row in self._plan)
            and not self.dry_run_var.get()
        )
        self.organize_btn.configure(
            state="normal" if ready else "disabled",
            text=(
                "Dry run · no files moved"
                if self.dry_run_var.get()
                else "Organize reviewed files"
            ),
        )
        self.find_dup_btn.configure(state="normal" if valid else "disabled")
        self.move_dup_btn.configure(
            state=(
                "normal" if valid and self._selected_duplicate_paths() else "disabled"
            ),
            text=(
                "Preview selected copies"
                if self.dry_run_var.get()
                else "Move selected copies"
            ),
        )
        self.select_extras_btn.configure(
            state=(
                "normal"
                if valid
                and self._duplicate_rows
                and self.dup_table not in self._render_timers
                else "disabled"
            )
        )
        self.undo_btn.configure(
            state="normal" if valid and self._undo_available else "disabled"
        )
        self.refresh_history_btn.configure(state="normal" if valid else "disabled")
        self.explorer_btn.configure(
            state="normal" if self._folder_valid else "disabled"
        )
        self.cancel_btn.configure(state="normal" if self.runner.busy else "disabled")
        watching = bool(self.active_watcher and self.active_watcher.is_running())
        self.watch_btn.configure(
            state=(
                "disabled"
                if self.runner.busy or self._watch_stopping or not self._folder_valid
                else "normal"
            ),
            text=(
                "Stopping…"
                if self._watch_stopping
                else "Stop monitoring" if watching else "Start monitoring"
            ),
        )
        if sys.platform != "win32":
            self.boot_cb.configure(state="disabled")
        self._update_watcher_badge()

    def _update_watcher_badge(self):
        watching = bool(self.active_watcher and self.active_watcher.is_running())
        error = self.active_watcher.last_error if watching else None
        text = (
            "Stopping watcher…"
            if self._watch_stopping
            else (
                "●  Watcher error"
                if error
                else "●  Watching" if watching else "●  Watcher off"
            )
        )
        self.watcher_badge.configure(
            text=text,
            text_color=color(
                "error_text" if error else "success_text" if watching else "fg_subtext"
            ),
        )
        detail = f'{self.selected_folder.get()}\nStrategy: {self.organize_mode.get()} · Subfolders: {"included" if self.recursive_var.get() else "excluded"}'
        self.watch_details.configure(
            text=(
                (f"Monitoring: {detail}" if watching else f"Ready to monitor: {detail}")
                if self._folder_valid
                else "Select a folder before starting monitoring."
            )
        )
        if error:
            self.watch_details.configure(
                text=f"Watcher error: {error}\nMonitoring will retry; stop to change the folder or rules."
            )
        self.dashboard_watcher.configure(
            text=(
                "Watcher active · " + self.selected_folder.get()
                if watching
                else "Watcher is off. Start it from Automation & Settings."
            )
        )

    def _browse_folder(self):
        if self._locked():
            return
        folder = filedialog.askdirectory(
            parent=self.root, title="Choose a target folder", mustexist=True
        )
        if folder:
            self.selected_folder.set(folder)
            if self.active_tab == "dashboard":
                self._set_tab("organize")

    def _set_preset_folder(self, name):
        if self._locked():
            return
        path = Path.home() / name
        if path.is_dir():
            self.selected_folder.set(str(path))
        else:
            self._notify(
                "Folder not found",
                f"{name} was not found in your profile. Use Browse to locate it.",
            )

    def _open_in_explorer(self):
        if not self._folder_valid:
            return
        path = self.selected_folder.get().strip()
        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen(
                    ["open" if sys.platform == "darwin" else "xdg-open", path]
                )
        except OSError as error:
            self._notify("Could not open folder", str(error))

    def _notify(self, title, message, confirm=False):
        return dialog(self.root, title, message, confirm)

    def _get_active_config(self):
        cfg = ConfigManager()
        for pattern in self.custom_ignore_var.get().split(","):
            pattern = pattern.strip()
            if pattern and pattern not in cfg.ignore_patterns:
                cfg.ignore_patterns.append(pattern)
        return cfg

    def _create_organizer(self):
        return FileOrganizer(
            Path(self.selected_folder.get().strip()),
            mode=OrganizeMode(self.organize_mode.get()),
            sub_extension=self.sub_ext_var.get(),
            recursive=self.recursive_var.get(),
            clean_empty=self.clean_empty_var.get(),
            dry_run=self.dry_run_var.get(),
            config=self._get_active_config(),
            logger=self.logger,
        )

    def _launch(self, name, work):
        if self._locked() or not self._folder_valid:
            return False
        self._job_folder = self.selected_folder.get().strip()
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.status_text_var.set(name + "…")
        started = self.runner.start(name, work)
        self._update_actions()
        return started

    def _start_preview(self):
        if self._locked() or not self._folder_valid:
            return
        organizer = self._create_organizer()
        self._invalidate_plan()

        def scan(cancel, progress):
            return {"plan": organizer.plan(cancel, progress), "organizer": organizer}

        self._launch("Preview", scan)

    def _start_organize(self):
        if self._locked() or not self._folder_valid:
            return
        if self._plan is None:
            self._start_preview()
            return
        if self.dry_run_var.get():
            self.status_text_var.set("Dry run is enabled. No files were moved.")
            return
        count = sum(row.status == "Ready" for row in self._plan)
        if not count:
            return
        cleanup = " Empty folders may be removed." if self.clean_empty_var.get() else ""
        if not self._notify(
            "Organize reviewed files?",
            f"Move {count} file(s) in the selected folder? Existing destinations will be skipped. A file undo record will be saved.{cleanup}",
            True,
        ):
            return
        organizer = self._organizer
        organizer.dry_run = False
        plan = self._plan
        self._launch(
            "Organize",
            lambda cancel, progress: organizer.organize(plan, cancel, progress),
        )

    def _start_find_duplicates(self):
        if self._locked() or not self._folder_valid:
            return
        target = Path(self.selected_folder.get().strip())
        method = DuplicateMethod(self.dup_method_var.get())
        recursive = self.recursive_var.get()
        config = self._get_active_config()
        self._invalidate_duplicates()

        def scan(cancel, progress):
            signatures = {}
            groups = find_duplicates(
                target,
                method,
                recursive,
                cancel,
                progress,
                self._hash_cache,
                signatures,
                config,
            )
            return {
                "groups": groups,
                "signatures": signatures,
                "bytes": calculate_duplicate_space(groups),
            }

        self._launch("Duplicate scan", scan)

    def _selected_duplicate_paths(self):
        return {
            self._duplicate_rows[i][1]
            for i in self.dup_table.tree.selection()
            if i in self._duplicate_rows and self._duplicate_rows[i][2] == "Extra"
        }

    def _duplicate_selection(self, event=None):
        self.selected_count.configure(
            text=f"{len(self._selected_duplicate_paths())} copies selected"
        )
        self._update_actions()

    def _select_extras(self):
        self.dup_table.tree.selection_set(
            [
                i
                for i, (_, __, role) in self._duplicate_rows.items()
                if role == "Extra" and self.dup_table.tree.exists(i)
            ]
        )
        self._duplicate_selection()

    def _start_move_duplicates(self):
        if self._locked():
            return
        selected = self._selected_duplicate_paths()
        if not selected:
            return
        dry = self.dry_run_var.get()
        if not dry and not self._notify(
            "Move selected copies?",
            f"Move {len(selected)} selected extra file(s) into _duplicates/? Originals stay in place. No files will be deleted and disk space will not be freed.",
            True,
        ):
            return
        groups = {
            key: [paths[0]] + [p for p in paths[1:] if p in selected]
            for key, paths in self._duplicate_groups.items()
        }
        groups = {key: paths for key, paths in groups.items() if len(paths) > 1}
        target = Path(self.selected_folder.get().strip())
        signatures = dict(self._signatures)

        def move(cancel, progress):
            count, records = move_duplicates(
                target, groups, UndoManager(target), dry, cancel, progress, signatures
            )
            return {"moved": count, "dry": dry, "cancelled": cancel.is_set()}

        self._launch("Duplicate move", move)

    def _refresh_history(self):
        if self._locked() or not self._folder_valid:
            return
        manager = UndoManager(Path(self.selected_folder.get().strip()))

        def read(cancel, progress):
            latest = manager.get_latest_manifest()
            moves = manager.read_manifest(latest) if latest else []
            return {"latest": str(latest) if latest else None, "count": len(moves)}

        self._launch("History", read)

    def _start_undo(self):
        if self._locked() or not self._undo_available:
            return
        if not self._notify(
            "Undo the latest file operation?",
            "Restore files using the latest manifest in this folder? Occupied original locations and files changed since moving will be left untouched. Empty-folder cleanup itself cannot be undone.",
            True,
        ):
            return
        manager = UndoManager(Path(self.selected_folder.get().strip()))
        self._launch(
            "Undo", lambda cancel, progress: manager.undo_last(cancel, progress)
        )

    def _inspect_plan(self, event=None):
        selected = self.plan_table.tree.selection()
        if selected:
            values = self.plan_table.tree.item(selected[0], "values")
            self._notify(
                "Planned file change",
                f"Source: {values[0]}\n\nDestination: {values[1]}\n\n{values[2]}",
            )

    def _inspect_duplicate(self, event=None):
        selected = self.dup_table.tree.selection()
        if selected and selected[0] in self._duplicate_rows:
            values = self.dup_table.tree.item(selected[0], "values")
            self._notify(
                "Duplicate details",
                f"Group {values[0]} · {values[1]}\n\n{values[2]}\n\nSize: {values[3]}\nModified: {values[4]}",
            )

    def _toggle_watch(self):
        if self.runner.busy or self._watch_stopping:
            return
        if self.active_watcher and self.active_watcher.is_running():
            self._watch_stopping = True
            self.active_watcher.request_stop()
            self.status_text_var.set("Stopping watcher after the current file…")
            self._update_actions()
            return
        if not self._folder_valid:
            return
        if self.dry_run_var.get():
            self._notify(
                "Dry run is enabled",
                "Turn off Dry run in Organize Studio before starting monitoring.",
            )
            return
        if not self._notify(
            "Start automatic organization?",
            "The watcher will immediately organize files in the selected folder using the current strategy and rules, then monitor for new files.",
            True,
        ):
            return
        self.active_watcher = FolderWatcher(
            self._create_organizer(),
            on_cycle=lambda count: self.runner.events.put(("watch_cycle", count)),
        )
        self.active_watcher.start()
        self._invalidate_plan()
        self._invalidate_duplicates()
        self.status_text_var.set("Watching for files…")
        self._log("Folder watcher started.", "INFO")
        self._update_actions()

    def _on_toggle_autostart(self):
        if self._locked():
            return
        if self.autostart_var.get():
            if not self._folder_valid:
                self.autostart_var.set(False)
                self._notify(
                    "Choose a folder",
                    "Select a valid folder before enabling sign-in automation.",
                )
                return
            if not self._notify(
                "Enable Windows sign-in automation?",
                "Start a separate silent watcher for this folder whenever you sign in? It uses the current strategy and rules. It does not start until your next sign-in.",
                True,
            ):
                self.autostart_var.set(False)
                return
            result = enable_autostart(
                Path(self.selected_folder.get()),
                mode=self.organize_mode.get(),
                recursive=self.recursive_var.get(),
                sub_extension=self.sub_ext_var.get(),
                clean_empty=self.clean_empty_var.get(),
                ignore_patterns=self._get_active_config().ignore_patterns,
                config=self._get_active_config(),
            )
        else:
            result = disable_autostart()
        if not result:
            self.autostart_var.set(is_autostart_enabled())
            self._notify(
                "Startup setting was not changed",
                "Windows could not update the startup launcher. Check your permissions.",
            )
        else:
            self._log("Windows sign-in automation setting updated.", "SUCCESS")

    def _cancel(self):
        if not self.runner.busy:
            return
        self.runner.cancel()
        self.status_text_var.set("Cancelling safely after the current file…")
        self.cancel_btn.configure(state="disabled")

    def _drain_events(self):
        for _ in range(120):
            try:
                kind, payload = self.runner.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._log(payload)
            elif kind == "progress":
                done, total, text = payload
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(done / total if total else 0)
                self.status_text_var.set(f"{text} · {done:,} / {total:,} files")
            elif kind == "result":
                self._handle_result(*payload)
            elif kind == "error":
                name, error = payload
                self.status_text_var.set(f"{name} failed: {error}")
                self._log(error, "ERROR")
                self._record_job(name, f"Failed: {error}")
            elif kind == "cancelled":
                self.status_text_var.set(
                    payload + " cancelled. No further files will be processed."
                )
                self._log(payload + " cancelled.", "WARNING")
            elif kind == "finished":
                self.runner.busy = False
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(0)
                self._update_actions()
            elif kind == "watch_cycle":
                self._organized += payload
                self._undo_available = True
                self._update_dashboard()
                self._record_job("Watcher", f"Organized {payload} files")
        if (
            self._watch_stopping
            and self.active_watcher
            and not self.active_watcher.is_running()
        ):
            self.active_watcher = None
            self._watch_stopping = False
            self.status_text_var.set("Watcher stopped.")
            self._log("Folder watcher stopped.", "INFO")
            self._update_actions()
        if self.active_watcher:
            self._update_watcher_badge()
        if self._closing and not self.runner.busy and not self._watch_stopping:
            self._finish_close()
            return
        if not self._closed:
            self._event_timer = self.root.after(60, self._drain_events)

    def _handle_result(self, name, result):
        if name == "Preview":
            self._plan = result["plan"]
            self._organizer = result["organizer"]
            self._last_scanned = len(self._plan)
            count = sum(row.status == "Ready" for row in self._plan)
            summary = f"{len(self._plan):,} scanned · {count:,} ready to move · {len(self._plan)-count:,} skipped or blocked"
            self.plan_summary.configure(text=summary)
            self._render_table(
                self.plan_table,
                [
                    (str(row.source), str(row.destination or "—"), row.status)
                    for row in self._plan
                ],
            )
        elif name == "Organize":
            self._organized += result["moved"]
            self._undo_available = result["moved"] > 0
            summary = f'{"Cancelled · " if result["cancelled"] else ""}Organized {result["moved"]} · Skipped {result["skipped"]} · Errors {result["errors"]}'
            self._invalidate_plan()
            self._invalidate_duplicates()
        elif name == "Duplicate scan":
            self._duplicate_groups = result["groups"]
            self._signatures = result["signatures"]
            self._duplicate_count = sum(
                len(paths) - 1 for paths in self._duplicate_groups.values()
            )
            self._duplicate_bytes = result["bytes"]
            summary = f'{len(self._duplicate_groups)} groups · {self._duplicate_count} extra copies · {format_bytes(result["bytes"])} potential'
            self.stats_summary_var.set(summary)
            rows = []
            for group, paths in enumerate(self._duplicate_groups.values(), 1):
                for index, path in enumerate(paths):
                    role = "Keep" if index == 0 else "Extra"
                    signature = self._signatures[str(path)]
                    self._duplicate_rows[str(len(rows))] = (group, path, role)
                    rows.append(
                        (
                            str(group),
                            role,
                            str(path),
                            format_bytes(signature[0]),
                            datetime.fromtimestamp(signature[1] / 1e9).strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                        )
                    )
            self._render_table(self.dup_table, rows)
        elif name == "Duplicate move":
            summary = f'{"Cancelled · " if result["cancelled"] else ""}{"Would move" if result["dry"] else "Moved"} {result["moved"]} extra copies'
            if not result["dry"]:
                self._undo_available = result["moved"] > 0
                self._invalidate_duplicates()
                self._invalidate_plan()
            self.stats_summary_var.set(summary)
        elif name == "Undo":
            restored, errors, messages = result
            summary = f"Restored {restored} files · {errors} errors"
            if self.runner.cancel_event.is_set():
                summary = "Cancelled · " + summary
            for message in messages:
                self._log(message, "WARNING")
            self._undo_available = False
            self.undo_summary.configure(
                text="Refresh folder history to inspect remaining operations."
            )
            self._invalidate_plan()
            self._invalidate_duplicates()
        elif name == "History":
            self._undo_available = bool(result["latest"] and result["count"])
            summary = (
                f'Latest undo record: {result["count"]} file entries'
                if self._undo_available
                else "No file operation is available to undo in this folder."
            )
            self.undo_summary.configure(text=summary)
        else:
            return
        self.status_text_var.set(summary)
        self._log(summary, "INFO" if name == "History" else "SUCCESS")
        self._update_dashboard()
        if name != "History":
            self._record_job(name, summary)

    def _render_table(self, table, rows):
        self._cancel_render(table)
        table.clear()

        def batch(start=0):
            if self._closed:
                return
            for index in range(start, min(start + 150, len(rows))):
                table.tree.insert("", "end", iid=str(index), values=rows[index])
            if start + 150 < len(rows):
                self._render_timers[table] = self.root.after(
                    1, lambda: batch(start + 150)
                )
            else:
                self._render_timers.pop(table, None)
                self._update_actions()

        batch()

    def _record_job(self, action, result):
        self.jobs.append(
            dict(
                time=datetime.now().strftime("%Y-%m-%d %H:%M"),
                action=action,
                folder=self.selected_folder.get(),
                result=result,
            )
        )
        self.jobs = self.jobs[-50:]
        self._render_jobs()
        self._save_preferences()

    def _render_jobs(self):
        self.recent_table.clear()
        self.history_table.clear()
        for job in reversed(self.jobs):
            self.history_table.tree.insert(
                "",
                "end",
                values=(job["time"], job["action"], job["folder"], job["result"]),
            )
        for job in reversed(self.jobs[-5:]):
            self.recent_table.tree.insert(
                "", "end", values=(job["time"], job["action"], job["result"])
            )

    def _update_dashboard(self):
        for key, value in (
            ("scanned", self._last_scanned),
            ("organized", self._organized),
            ("duplicates", self._duplicate_count),
            ("bytes", self._duplicate_bytes),
        ):
            self.stat_labels[key].configure(
                text=(
                    "—"
                    if value is None
                    else format_bytes(value) if key == "bytes" else f"{value:,}"
                )
            )

    def _log(self, message, severity=None):
        if severity is None:
            lower = message.lower()
            severity = (
                "ERROR"
                if "error" in lower or "failed" in lower
                else "WARNING" if "warning" in lower or "skipped" in lower else "INFO"
            )
        text = (
            f"{datetime.now():%H:%M:%S}  {severity:<7}  {message}\n"
            if not message.startswith("[")
            else message + "\n"
        )
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text, severity)
        self._log_count += 1
        if self._log_count > 5000:
            self.log_text.delete("1.0", "501.0")
            self._log_count -= 500
        if self.autoscroll_var.get():
            self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._log_count = 0
        self.status_text_var.set("Activity display cleared. File history is unchanged.")

    def _copy_log(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_text.get("1.0", "end").strip())
        self.status_text_var.set("Activity copied to clipboard.")

    def _close(self):
        if self._closing:
            return
        self._closing = True
        self.runner.cancel()
        if self.active_watcher and self.active_watcher.is_running():
            self._watch_stopping = True
            self.active_watcher.request_stop()
        if self.runner.busy or self._watch_stopping:
            self.status_text_var.set(
                "Finishing the current file and saving history before closing…"
            )
            self._update_actions()
        else:
            self._finish_close()

    def _finish_close(self):
        self._save_preferences()
        close_logger(self.logger)
        self.root.destroy()

    def _on_destroy(self, event):
        if event.widget is not self.root:
            return
        self._closed = True
        for timer in (
            getattr(self, "_event_timer", None),
            self._save_timer,
            *self._render_timers.values(),
        ):
            if timer:
                try:
                    self.root.after_cancel(timer)
                except tk.TclError:
                    pass
        for variable, trace in self._trace_ids:
            variable.trace_remove("write", trace)


def main():
    if "--smoke-test" in sys.argv:
        from file_organizer.gui.smoke import run_smoke

        report = Path(sys.argv[sys.argv.index("--smoke-test") + 1])
        try:
            run_smoke(report)
        except Exception:
            import json
            import traceback

            report.write_text(
                json.dumps(
                    {"passed": False, "error": traceback.format_exc()}, indent=2
                ),
                encoding="utf-8",
            )
            raise SystemExit(1)
        return
    if "--background-watch" in sys.argv:
        from file_organizer.gui.startup import run_background

        run_background(Path(sys.argv[sys.argv.index("--background-watch") + 1]))
        return
    root = MainWindow()
    app = OrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
