"""GUI entry point module with functional folder picker, sorting modes, sub-extension nesting, recursive option, and undo support."""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from file_organizer import __version__
from file_organizer.core.organizer import FileOrganizer, OrganizeMode
from file_organizer.core.undo import UndoManager


class OrganizerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"File Organizer Pro v{__version__}")
        self.root.geometry("690x550")
        self.root.minsize(590, 460)

        self.selected_folder = tk.StringVar(value="")
        self.organize_mode = tk.StringVar(value=OrganizeMode.CATEGORY.value)
        self.sub_ext_var = tk.BooleanVar(value=True)
        self.recursive_var = tk.BooleanVar(value=False)
        self.clean_empty_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self):
        # Folder selection frame
        folder_frame = ttk.LabelFrame(self.root, text="Select Target Folder", padding=10)
        folder_frame.pack(fill="x", padx=15, pady=8)

        entry = ttk.Entry(folder_frame, textvariable=self.selected_folder)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ttk.Button(folder_frame, text="Browse...", command=self._browse_folder)
        browse_btn.pack(side="right")

        # Sorting Mode frame
        mode_frame = ttk.LabelFrame(self.root, text="Sorting Mode", padding=8)
        mode_frame.pack(fill="x", padx=15, pady=5)

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

        # Options frame
        opts_frame = ttk.LabelFrame(self.root, text="Options", padding=8)
        opts_frame.pack(fill="x", padx=15, pady=5)

        ttk.Checkbutton(
            opts_frame,
            text="Separate extensions inside Category & Date (e.g. Images/jpg/, 2026/October/pdf/)",
            variable=self.sub_ext_var,
        ).pack(anchor="w", pady=(0, 4))

        row2 = ttk.Frame(opts_frame)
        row2.pack(fill="x")

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

        # Action Buttons frame
        btn_frame = ttk.Frame(self.root, padding=(15, 6))
        btn_frame.pack(fill="x")

        self.organize_btn = ttk.Button(
            btn_frame, text="⚡ Organize Files Now", command=self._start_organize
        )
        self.organize_btn.pack(side="left", padx=(0, 10))

        self.undo_btn = ttk.Button(
            btn_frame, text="↩ Undo Last Operation", command=self._start_undo
        )
        self.undo_btn.pack(side="left")

        # Log & status area
        log_frame = ttk.LabelFrame(self.root, text="Activity Log", padding=8)
        log_frame.pack(fill="both", expand=True, padx=15, pady=(0, 12))

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

    def _start_organize(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path:
            messagebox.showwarning("No Folder Selected", "Please select a folder to organize first!")
            return

        target = Path(folder_path)
        if not target.is_dir():
            messagebox.showerror("Invalid Directory", "The specified path is not a valid folder.")
            return

        self.organize_btn.configure(state="disabled")
        self.undo_btn.configure(state="disabled")
        selected_mode = OrganizeMode(self.organize_mode.get())
        self._log(
            f"\n--- Starting organization on: {target} (Mode: {selected_mode.value}, "
            f"Sub-extensions: {self.sub_ext_var.get()}, Recursive: {self.recursive_var.get()}) ---"
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
                )
                stats = organizer.organize()
                summary = (
                    f"Completed! Moved: {stats['moved']} | Skipped: {stats['skipped']} | "
                    f"Errors: {stats['errors']} | Cleaned Folders: {stats.get('cleaned_dirs', 0)}"
                )
                self.root.after(0, lambda: self._log(summary))
                self.root.after(0, lambda: messagebox.showinfo("Finished", summary))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Error: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self.organize_btn.configure(state="normal"))
                self.root.after(0, lambda: self.undo_btn.configure(state="normal"))

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
            f"Are you sure you want to revert the last organize operation in:\n{target}?",
        )
        if not confirm:
            return

        self.organize_btn.configure(state="disabled")
        self.undo_btn.configure(state="disabled")
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
                self.root.after(0, lambda: self.organize_btn.configure(state="normal"))
                self.root.after(0, lambda: self.undo_btn.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    app = OrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
