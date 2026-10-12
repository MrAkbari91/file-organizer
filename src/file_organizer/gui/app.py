"""GUI entry point module with functional folder picker, sorting modes, custom ignore rules, duplicate detection, and undo support."""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from file_organizer import __version__
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
        self.root.title(f"File Organizer Pro v{__version__}")
        self.root.geometry("760x650")
        self.root.minsize(640, 530)

        self.selected_folder = tk.StringVar(value="")
        self.organize_mode = tk.StringVar(value=OrganizeMode.CATEGORY.value)
        self.dup_method_var = tk.StringVar(value=DuplicateMethod.EXACT.value)
        self.sub_ext_var = tk.BooleanVar(value=True)
        self.recursive_var = tk.BooleanVar(value=False)
        self.clean_empty_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=False)
        self.custom_ignore_var = tk.StringVar(value="")

        self.config = ConfigManager()
        self._build_ui()

    def _build_ui(self):
        # Folder selection frame
        folder_frame = ttk.LabelFrame(self.root, text="Select Target Folder", padding=10)
        folder_frame.pack(fill="x", padx=15, pady=6)

        entry = ttk.Entry(folder_frame, textvariable=self.selected_folder)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ttk.Button(folder_frame, text="Browse...", command=self._browse_folder)
        browse_btn.pack(side="right")

        # Sorting Mode frame
        mode_frame = ttk.LabelFrame(self.root, text="Sorting Mode", padding=8)
        mode_frame.pack(fill="x", padx=15, pady=4)

        ttk.Radiobutton(
            mode_frame,
            text="By Category (Images/, Code/, Videos/)",
            variable=self.organize_mode,
            value=OrganizeMode.CATEGORY.value,
        ).pack(side="left", padx=(0, 15))

        ttk.Radiobutton(
            mode_frame,
            text="By Extension (jpg/, pdf/)",
            variable=self.organize_mode,
            value=OrganizeMode.EXTENSION.value,
        ).pack(side="left", padx=(0, 15))

        ttk.Radiobutton(
            mode_frame,
            text="By Date (2026/October/)",
            variable=self.organize_mode,
            value=OrganizeMode.DATE.value,
        ).pack(side="left")

        # Duplicate Method Selection frame
        dup_frame = ttk.LabelFrame(self.root, text="Duplicate Detection Method", padding=8)
        dup_frame.pack(fill="x", padx=15, pady=4)

        ttk.Radiobutton(
            dup_frame,
            text="Exact Binary (SHA-256)",
            variable=self.dup_method_var,
            value=DuplicateMethod.EXACT.value,
        ).pack(side="left", padx=(0, 12))

        ttk.Radiobutton(
            dup_frame,
            text="Converted Formats (Same name across formats)",
            variable=self.dup_method_var,
            value=DuplicateMethod.CONVERTED.value,
        ).pack(side="left", padx=(0, 12))

        ttk.Radiobutton(
            dup_frame,
            text="Visual Similarity (Pixel hash)",
            variable=self.dup_method_var,
            value=DuplicateMethod.VISUAL.value,
        ).pack(side="left")

        # Options & Custom Ignore frame
        opts_frame = ttk.LabelFrame(self.root, text="Options & Ignore Rules", padding=8)
        opts_frame.pack(fill="x", padx=15, pady=4)

        ttk.Checkbutton(
            opts_frame,
            text="Separate extensions inside Category & Date (e.g. Images/jpg/, 2026/October/pdf/)",
            variable=self.sub_ext_var,
        ).pack(anchor="w", pady=(0, 4))

        row2 = ttk.Frame(opts_frame)
        row2.pack(fill="x", pady=(0, 4))

        ttk.Checkbutton(
            row2,
            text="Recursive (include subdirectories)",
            variable=self.recursive_var,
        ).pack(side="left", padx=(0, 15))

        ttk.Checkbutton(
            row2,
            text="Clean empty directories",
            variable=self.clean_empty_var,
        ).pack(side="left", padx=(0, 15))

        ttk.Checkbutton(
            row2,
            text="Dry Run (preview only)",
            variable=self.dry_run_var,
        ).pack(side="left")

        # Ignore input row
        ignore_row = ttk.Frame(opts_frame)
        ignore_row.pack(fill="x", pady=(2, 0))
        ttk.Label(ignore_row, text="Ignore pattern(s):").pack(side="left", padx=(0, 6))
        ignore_entry = ttk.Entry(ignore_row, textvariable=self.custom_ignore_var)
        ignore_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Label(ignore_row, text="(comma separated, e.g. *.tmp, draft_*, private)").pack(side="left")

        # Action Buttons frame
        btn_frame = ttk.Frame(self.root, padding=(15, 6))
        btn_frame.pack(fill="x")

        self.organize_btn = ttk.Button(
            btn_frame, text="⚡ Organize Files", command=self._start_organize
        )
        self.organize_btn.pack(side="left", padx=(0, 8))

        self.find_dup_btn = ttk.Button(
            btn_frame, text="🔍 Find Duplicates", command=self._start_find_duplicates
        )
        self.find_dup_btn.pack(side="left", padx=(0, 8))

        self.move_dup_btn = ttk.Button(
            btn_frame, text="📦 Move Duplicates", command=self._start_move_duplicates
        )
        self.move_dup_btn.pack(side="left", padx=(0, 8))

        self.undo_btn = ttk.Button(
            btn_frame, text="↩ Undo Last", command=self._start_undo
        )
        self.undo_btn.pack(side="left")

        # Log & status area
        log_frame = ttk.LabelFrame(self.root, text="Activity Log (also saved to file_organizer.log)", padding=8)
        log_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.log_text = tk.Text(log_frame, wrap="word", state="disabled", font=("Consolas", 9))
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
        folder = filedialog.askdirectory(title="Select Folder to Organize")
        if folder:
            self.selected_folder.set(folder)
            self._log(f"Selected: {folder}")

    def _set_buttons_state(self, state: str):
        self.organize_btn.configure(state=state)
        self.find_dup_btn.configure(state=state)
        self.move_dup_btn.configure(state=state)
        self.undo_btn.configure(state=state)

    def _get_active_config(self) -> ConfigManager:
        cfg = ConfigManager()
        # Parse extra custom ignore patterns from GUI
        raw_ignores = self.custom_ignore_var.get().strip()
        if raw_ignores:
            for item in raw_ignores.split(","):
                pattern = item.strip()
                if pattern and pattern not in cfg.ignore_patterns:
                    cfg.ignore_patterns.append(pattern)
        return cfg

    def _start_organize(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path:
            messagebox.showwarning("No Folder Selected", "Please select a folder to organize first!")
            return

        target = Path(folder_path)
        if not target.is_dir():
            messagebox.showerror("Invalid Directory", "The specified path is not a valid folder.")
            return

        self._set_buttons_state("disabled")
        selected_mode = OrganizeMode(self.organize_mode.get())
        cfg = self._get_active_config()

        logger = setup_logger(
            target_folder=target,
            gui_callback=lambda msg: self.root.after(0, lambda m=msg: self._log(m)),
        )

        def run():
            try:
                organizer = FileOrganizer(
                    target,
                    mode=selected_mode,
                    sub_extension=self.sub_ext_var.get(),
                    recursive=self.recursive_var.get(),
                    clean_empty=self.clean_empty_var.get(),
                    dry_run=self.dry_run_var.get(),
                    config=cfg,
                    logger=logger,
                )
                stats = organizer.organize()
                summary = (
                    f"Completed! Moved: {stats['moved']} | Skipped: {stats['skipped']} | "
                    f"Errors: {stats['errors']} | Cleaned Folders: {stats.get('cleaned_dirs', 0)}"
                )
                self.root.after(0, lambda: messagebox.showinfo("Finished", summary))
            except Exception as e:
                logger.error(f"Error during organize: {e}")
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=run, daemon=True).start()

    def _start_find_duplicates(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path:
            messagebox.showwarning("No Folder Selected", "Please select a folder first!")
            return

        target = Path(folder_path)
        if not target.is_dir():
            messagebox.showerror("Invalid Directory", "The specified path is not a valid folder.")
            return

        method = DuplicateMethod(self.dup_method_var.get())
        self._set_buttons_state("disabled")
        self._log(f"\n--- Scanning duplicates in: {target} (Method: {method.value}) ---")

        def run():
            try:
                dups = find_duplicates(target, method=method, recursive=self.recursive_var.get())
                if not dups:
                    self.root.after(0, lambda: self._log(f"🎉 No duplicates found using {method.value} check!"))
                    self.root.after(0, lambda: messagebox.showinfo("No Duplicates", f"No duplicates were found using {method.value} check."))
                else:
                    wasted = calculate_duplicate_space(dups)
                    total_dup_files = sum(len(files) - 1 for files in dups.values())
                    summary = f"Found {len(dups)} group(s) with {total_dup_files} extra files (~{format_bytes(wasted)} can be saved)."
                    self.root.after(0, lambda: self._log(f"\n⚠️  {summary}"))

                    for idx, (key, files) in enumerate(dups.items(), 1):
                        label = key if len(key) < 30 else f"{key[:20]}..."
                        self.root.after(0, lambda i=idx, l=label, f0=files[0]: self._log(f"\nGroup #{i} [{l}]:\n  [Keep/Original] -> {f0.name} ({format_bytes(f0.stat().st_size)})"))
                        for extra in files[1:]:
                            self.root.after(0, lambda ex=extra: self._log(f"  [Duplicate/Copy] -> {ex.name} ({format_bytes(ex.stat().st_size)})"))

                    self.root.after(0, lambda: messagebox.showwarning("Duplicates Detected", summary))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Error finding duplicates: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=run, daemon=True).start()

    def _start_move_duplicates(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path:
            messagebox.showwarning("No Folder Selected", "Please select a folder first!")
            return

        target = Path(folder_path)
        if not target.is_dir():
            messagebox.showerror("Invalid Directory", "The specified path is not a valid folder.")
            return

        method = DuplicateMethod(self.dup_method_var.get())
        confirm = messagebox.askyesno(
            "Confirm Move Duplicates",
            f"Are you sure you want to isolate extra duplicate files ({method.value} method) into '_duplicates/' in:\n{target}?",
        )
        if not confirm:
            return

        self._set_buttons_state("disabled")
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
                self.root.after(0, lambda: self._log(f"Error moving duplicates: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=run, daemon=True).start()

    def _start_undo(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path:
            messagebox.showwarning("No Folder Selected", "Please select a target folder first!")
            return

        target = Path(folder_path)
        if not target.is_dir():
            messagebox.showerror("Invalid Directory", "The specified path is not a valid folder.")
            return

        confirm = messagebox.askyesno(
            "Confirm Undo",
            f"Are you sure you want to revert the last operation in:\n{target}?",
        )
        if not confirm:
            return

        self._set_buttons_state("disabled")
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
                self.root.after(0, lambda: self._log(f"Error during undo: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Undo Error", str(e)))
            finally:
                self.root.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=run, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    app = OrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
