"""GUI entry point module with sleek modern dark theme, animated progress bar, live watcher, duplicate manager, and undo support."""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from file_organizer import __version__
from file_organizer.core.autostart import disable_autostart, enable_autostart, is_autostart_enabled
from file_organizer.core.config import ConfigManager
from file_organizer.core.duplicates import (
    DuplicateMethod,
    calculate_duplicate_space,
    find_duplicates,
    move_duplicates,
)
from file_organizer.core.logger import setup_logger
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.undo import UndoManager
from file_organizer.core.watcher import FolderWatcher
from file_organizer.gui.theme import COLORS, FONTS, apply_dark_theme


def format_bytes(num_bytes: int) -> str:
    """Format bytes into readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


class OrganizerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"🗂️ File Organizer Pro — v{__version__}")
        self.root.geometry("820x730")
        self.root.minsize(700, 580)

        # Apply Modern Dark Theme
        self.style = apply_dark_theme(self.root)

        # State Variables
        self.selected_folder = tk.StringVar(value="")
        self.organize_mode = tk.StringVar(value=OrganizeMode.CATEGORY.value)
        self.dup_method_var = tk.StringVar(value=DuplicateMethod.EXACT.value)
        self.sub_ext_var = tk.BooleanVar(value=True)
        self.recursive_var = tk.BooleanVar(value=False)
        self.clean_empty_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=False)
        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        self.custom_ignore_var = tk.StringVar(value="")
        self.status_text_var = tk.StringVar(value="Ready. Select a folder to begin.")

        self.active_watcher: FolderWatcher = None
        self.config = ConfigManager()
        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        # Header Title
        header_frame = ttk.Frame(container)
        header_frame.pack(fill="x", pady=(0, 10))
        title_lbl = tk.Label(
            header_frame,
            text="🗂️ File Organizer Pro",
            bg=COLORS["bg_dark"],
            fg=COLORS["accent_primary"],
            font=FONTS["title"],
        )
        title_lbl.pack(side="left")

        version_badge = tk.Label(
            header_frame,
            text=f"v{__version__}",
            bg=COLORS["bg_surface_alt"],
            fg=COLORS["accent_purple"],
            font=FONTS["badge"],
            padx=8,
            pady=2,
        )
        version_badge.pack(side="left", padx=10)

        # 1. Folder Selection Card
        folder_frame = ttk.LabelFrame(container, text="  Target Folder  ", padding=12)
        folder_frame.pack(fill="x", pady=6)

        entry = ttk.Entry(folder_frame, textvariable=self.selected_folder, font=FONTS["body"])
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_btn = ttk.Button(folder_frame, text="📂 Browse Folder", command=self._browse_folder)
        browse_btn.pack(side="right")

        # 2. Sorting Mode Card
        mode_frame = ttk.LabelFrame(container, text="  Sorting Mode  ", padding=10)
        mode_frame.pack(fill="x", pady=6)

        ttk.Radiobutton(
            mode_frame,
            text="By Category (Images/, Code/, Videos/)",
            variable=self.organize_mode,
            value=OrganizeMode.CATEGORY.value,
        ).pack(side="left", padx=(0, 20))

        ttk.Radiobutton(
            mode_frame,
            text="By Extension (jpg/, pdf/)",
            variable=self.organize_mode,
            value=OrganizeMode.EXTENSION.value,
        ).pack(side="left", padx=(0, 20))

        ttk.Radiobutton(
            mode_frame,
            text="By Date (2026/October/)",
            variable=self.organize_mode,
            value=OrganizeMode.DATE.value,
        ).pack(side="left")

        # 3. Duplicate Detection Mode Card
        dup_frame = ttk.LabelFrame(container, text="  Duplicate Detection Engine  ", padding=10)
        dup_frame.pack(fill="x", pady=6)

        ttk.Radiobutton(
            dup_frame,
            text="Exact Binary (SHA-256)",
            variable=self.dup_method_var,
            value=DuplicateMethod.EXACT.value,
        ).pack(side="left", padx=(0, 16))

        ttk.Radiobutton(
            dup_frame,
            text="Converted Formats (Same name across formats)",
            variable=self.dup_method_var,
            value=DuplicateMethod.CONVERTED.value,
        ).pack(side="left", padx=(0, 16))

        ttk.Radiobutton(
            dup_frame,
            text="Visual Similarity (Pixel hash)",
            variable=self.dup_method_var,
            value=DuplicateMethod.VISUAL.value,
        ).pack(side="left")

        # 4. Options & Settings Card
        opts_frame = ttk.LabelFrame(container, text="  Preferences & Automation  ", padding=10)
        opts_frame.pack(fill="x", pady=6)

        ttk.Checkbutton(
            opts_frame,
            text="Separate extensions inside Category & Date (e.g. Images/jpg/, 2026/October/pdf/)",
            variable=self.sub_ext_var,
        ).pack(anchor="w", pady=(0, 4))

        row2 = ttk.Frame(opts_frame, style="Surface.TFrame")
        row2.pack(fill="x", pady=(0, 4))

        ttk.Checkbutton(
            row2,
            text="Recursive (subfolders)",
            variable=self.recursive_var,
        ).pack(side="left", padx=(0, 20))

        ttk.Checkbutton(
            row2,
            text="Clean empty folders",
            variable=self.clean_empty_var,
        ).pack(side="left", padx=(0, 20))

        ttk.Checkbutton(
            row2,
            text="Dry Run (preview only)",
            variable=self.dry_run_var,
        ).pack(side="left")

        # Autostart checkbox
        boot_row = ttk.Frame(opts_frame, style="Surface.TFrame")
        boot_row.pack(fill="x", pady=(2, 4))
        self.boot_cb = ttk.Checkbutton(
            boot_row,
            text="Start silent auto-watch on Windows Boot (Set & Forget)",
            variable=self.autostart_var,
            command=self._on_toggle_autostart,
        )
        self.boot_cb.pack(side="left")

        # Ignore input row
        ignore_row = ttk.Frame(opts_frame, style="Surface.TFrame")
        ignore_row.pack(fill="x", pady=(2, 0))
        ttk.Label(ignore_row, text="Ignore patterns:").pack(side="left", padx=(0, 8))
        ignore_entry = ttk.Entry(ignore_row, textvariable=self.custom_ignore_var)
        ignore_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(ignore_row, text="(e.g. *.tmp, draft_*, private)").pack(side="left")

        # 5. Action Buttons Toolbar
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x", pady=10)

        self.organize_btn = ttk.Button(
            btn_frame,
            text="⚡ Organize Now",
            style="Primary.TButton",
            command=self._start_organize,
        )
        self.organize_btn.pack(side="left", padx=(0, 8))

        self.watch_btn = ttk.Button(
            btn_frame,
            text="👀 Start Auto-Watch",
            command=self._toggle_watch,
        )
        self.watch_btn.pack(side="left", padx=(0, 8))

        self.find_dup_btn = ttk.Button(
            btn_frame,
            text="🔍 Find Duplicates",
            command=self._start_find_duplicates,
        )
        self.find_dup_btn.pack(side="left", padx=(0, 8))

        self.move_dup_btn = ttk.Button(
            btn_frame,
            text="📦 Move Duplicates",
            command=self._start_move_duplicates,
        )
        self.move_dup_btn.pack(side="left", padx=(0, 8))

        self.undo_btn = ttk.Button(
            btn_frame,
            text="↩ Undo Last",
            style="Warning.TButton",
            command=self._start_undo,
        )
        self.undo_btn.pack(side="left")

        # 6. Progress Bar
        self.progress_bar = ttk.Progressbar(container, mode="indeterminate", style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=(0, 6))

        # Status label
        status_lbl = tk.Label(
            container,
            textvariable=self.status_text_var,
            bg=COLORS["bg_dark"],
            fg=COLORS["fg_subtext"],
            font=FONTS["body"],
            anchor="w",
        )
        status_lbl.pack(fill="x", pady=(0, 4))

        # 7. Activity Log Card
        log_frame = ttk.LabelFrame(container, text="  Live Console & Activity Log  ", padding=6)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            state="disabled",
            bg=COLORS["bg_dark"],
            fg=COLORS["fg_text"],
            insertbackground=COLORS["fg_text"],
            selectbackground=COLORS["bg_surface_alt"],
            font=FONTS["code"],
            borderwidth=0,
            padx=8,
            pady=8,
        )
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

    def _log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Target Folder")
        if folder:
            self.selected_folder.set(folder)
            self._log(f"📂 Selected: {folder}")
            self.status_text_var.set(f"Selected: {folder}")

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.organize_btn.configure(state=state)
        self.find_dup_btn.configure(state=state)
        self.move_dup_btn.configure(state=state)
        self.undo_btn.configure(state=state)
        if busy:
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()

    def _on_toggle_autostart(self):
        if self.autostart_var.get():
            folder_path = self.selected_folder.get().strip()
            if not folder_path or not Path(folder_path).is_dir():
                messagebox.showwarning("Folder Required", "Please select a valid folder before enabling startup auto-watch!")
                self.autostart_var.set(False)
                return

            confirm = messagebox.askyesno(
                "Confirm System Startup Permission",
                f"Are you sure you want File Organizer to automatically run in the background "
                f"every time your computer starts up for:\n\n{folder_path}?\n\n"
                f"You can turn this off at any time by unchecking this box.",
            )
            if confirm:
                mode = self.organize_mode.get()
                if enable_autostart(Path(folder_path), mode=mode):
                    self._log("✅ Startup background auto-watch enabled with your permission.")
                    messagebox.showinfo("Enabled", "Background auto-watch will now run silently on PC boot.")
                else:
                    self.autostart_var.set(False)
                    messagebox.showerror("Error", "Could not register startup task on this system.")
            else:
                self.autostart_var.set(False)
        else:
            if disable_autostart():
                self._log("Removed from system startup.")
                messagebox.showinfo("Disabled", "Auto-watch has been removed from system startup.")

    def _get_active_config(self) -> ConfigManager:
        cfg = ConfigManager()
        raw_ignores = self.custom_ignore_var.get().strip()
        if raw_ignores:
            for item in raw_ignores.split(","):
                pattern = item.strip()
                if pattern and pattern not in cfg.ignore_patterns:
                    cfg.ignore_patterns.append(pattern)
        return cfg

    def _create_organizer(self, target: Path) -> FileOrganizer:
        selected_mode = OrganizeMode(self.organize_mode.get())
        cfg = self._get_active_config()
        logger = setup_logger(
            target_folder=target,
            gui_callback=lambda msg: self.root.after(0, lambda m=msg: self._log(m)),
        )
        return FileOrganizer(
            target,
            mode=selected_mode,
            sub_extension=self.sub_ext_var.get(),
            recursive=self.recursive_var.get(),
            clean_empty=self.clean_empty_var.get(),
            dry_run=self.dry_run_var.get(),
            config=cfg,
            logger=logger,
        )

    def _start_organize(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path or not Path(folder_path).is_dir():
            messagebox.showwarning("No Folder Selected", "Please select a valid folder first!")
            return

        target = Path(folder_path)
        organizer = self._create_organizer(target)
        self._set_busy(True)
        self.status_text_var.set(f"Organizing {target.name}...")

        def run():
            try:
                stats = organizer.organize()
                summary = (
                    f"Done! Moved: {stats['moved']} | Skipped: {stats['skipped']} | "
                    f"Errors: {stats['errors']} | Cleaned: {stats.get('cleaned_dirs', 0)}"
                )
                self.root.after(0, lambda: self.status_text_var.set(summary))
                self.root.after(0, lambda: messagebox.showinfo("Organization Complete", summary))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.status_text_var.set(f"Error: {e}"))
            finally:
                self.root.after(0, lambda: self._set_busy(False))

        threading.Thread(target=run, daemon=True).start()

    def _toggle_watch(self):
        if self.active_watcher and self.active_watcher.is_running():
            self.active_watcher.stop()
            self.active_watcher = None
            self.watch_btn.configure(text="👀 Start Auto-Watch")
            self._log("⏹ Live Auto-Watch stopped.")
            self.status_text_var.set("Auto-Watch stopped.")
            return

        folder_path = self.selected_folder.get().strip()
        if not folder_path or not Path(folder_path).is_dir():
            messagebox.showwarning("No Folder Selected", "Please select a valid folder first!")
            return

        target = Path(folder_path)
        organizer = self._create_organizer(target)
        self.active_watcher = FolderWatcher(organizer, interval=3.0)
        self.active_watcher.start()

        self.watch_btn.configure(text="⏹ Stop Auto-Watch")
        self._log(f"👀 Live Auto-Watch ACTIVE on {target}. Monitoring for new files...")
        self.status_text_var.set("Watching for new files...")

    def _start_find_duplicates(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path or not Path(folder_path).is_dir():
            messagebox.showwarning("No Folder Selected", "Please select a valid folder first!")
            return

        target = Path(folder_path)
        method = DuplicateMethod(self.dup_method_var.get())
        self._set_busy(True)
        self.status_text_var.set(f"Scanning duplicates ({method.value})...")
        self._log(f"\n--- Scanning duplicates in: {target} (Method: {method.value}) ---")

        def run():
            try:
                dups = find_duplicates(target, method=method, recursive=self.recursive_var.get())
                if not dups:
                    self.root.after(0, lambda: self._log(f"🎉 No duplicates found using {method.value} check!"))
                    self.root.after(0, lambda: self.status_text_var.set("No duplicates found."))
                    self.root.after(0, lambda: messagebox.showinfo("No Duplicates", f"No duplicates were found using {method.value} check."))
                else:
                    wasted = calculate_duplicate_space(dups)
                    total_dup_files = sum(len(files) - 1 for files in dups.values())
                    summary = f"Found {len(dups)} group(s) with {total_dup_files} redundant files (~{format_bytes(wasted)} waste)."
                    self.root.after(0, lambda: self._log(f"\n⚠️  {summary}"))

                    for idx, (key, files) in enumerate(dups.items(), 1):
                        label = key if len(key) < 30 else f"{key[:20]}..."
                        self.root.after(0, lambda i=idx, l=label, f0=files[0]: self._log(f"\nGroup #{i} [{l}]:\n  [Original] -> {f0.name} ({format_bytes(f0.stat().st_size)})"))
                        for extra in files[1:]:
                            self.root.after(0, lambda ex=extra: self._log(f"  [Duplicate] -> {ex.name} ({format_bytes(ex.stat().st_size)})"))

                    self.root.after(0, lambda: self.status_text_var.set(summary))
                    self.root.after(0, lambda: messagebox.showwarning("Duplicates Detected", summary))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self._set_busy(False))

        threading.Thread(target=run, daemon=True).start()

    def _start_move_duplicates(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path or not Path(folder_path).is_dir():
            messagebox.showwarning("No Folder Selected", "Please select a valid folder first!")
            return

        target = Path(folder_path)
        method = DuplicateMethod(self.dup_method_var.get())
        confirm = messagebox.askyesno(
            "Confirm Move Duplicates",
            f"Are you sure you want to isolate extra duplicate files ({method.value} method) into '_duplicates/' in:\n{target}?",
        )
        if not confirm:
            return

        self._set_busy(True)
        self._log(f"\n--- Moving duplicate files to _duplicates/ (Method: {method.value}) ---")

        def run():
            try:
                dups = find_duplicates(target, method=method, recursive=self.recursive_var.get())
                if not dups:
                    self.root.after(0, lambda: self._log("No duplicates to move."))
                    self.root.after(0, lambda: messagebox.showinfo("No Duplicates", "No duplicates were found to move."))
                else:
                    undo_mgr = UndoManager(target)
                    moved_count, _ = move_duplicates(target, dups, undo_manager=undo_mgr, dry_run=self.dry_run_var.get())
                    msg = f"Done! Moved {moved_count} extra duplicate file(s) to '_duplicates/'."
                    self.root.after(0, lambda: self._log(msg))
                    self.root.after(0, lambda: messagebox.showinfo("Duplicates Isolated", msg))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self._set_busy(False))

        threading.Thread(target=run, daemon=True).start()

    def _start_undo(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path or not Path(folder_path).is_dir():
            messagebox.showwarning("No Folder Selected", "Please select a target folder first!")
            return

        target = Path(folder_path)
        confirm = messagebox.askyesno(
            "Confirm Undo",
            f"Are you sure you want to revert the last operation in:\n{target}?",
        )
        if not confirm:
            return

        self._set_busy(True)
        self._log(f"\n--- Reverting last operation on: {target} ---")

        def run():
            try:
                undo_mgr = UndoManager(target)
                reverted, error_count, errors = undo_mgr.undo_last()
                if error_count > 0 and reverted == 0:
                    msg = f"Undo failed: {errors[0]}"
                    self.root.after(0, lambda: self._log(msg))
                    self.root.after(0, lambda: messagebox.showwarning("Undo Failed", msg))
                else:
                    msg = f"Undo Finished! Successfully reverted {reverted} file(s)."
                    self.root.after(0, lambda: self._log(msg))
                    self.root.after(0, lambda: messagebox.showinfo("Undo Successful", msg))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self._set_busy(False))

        threading.Thread(target=run, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    app = OrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
