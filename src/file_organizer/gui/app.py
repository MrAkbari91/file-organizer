"""GUI entry point module with functional folder picker and organizer."""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from file_organizer import __version__
from file_organizer.core.organizer import FileOrganizer


class OrganizerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"File Organizer Pro v{__version__}")
        self.root.geometry("600x420")
        self.root.minsize(500, 350)

        self.selected_folder = tk.StringVar(value="")
        self.dry_run_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self):
        # Folder selection frame
        folder_frame = ttk.LabelFrame(self.root, text="Select Target Folder", padding=10)
        folder_frame.pack(fill="x", padx=15, pady=10)

        entry = ttk.Entry(folder_frame, textvariable=self.selected_folder)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ttk.Button(folder_frame, text="Browse...", command=self._browse_folder)
        browse_btn.pack(side="right")

        # Options frame
        opts_frame = ttk.Frame(self.root, padding=(15, 0))
        opts_frame.pack(fill="x")

        dry_run_cb = ttk.Checkbutton(
            opts_frame,
            text="Dry Run (Preview only, do not actually move files)",
            variable=self.dry_run_var,
        )
        dry_run_cb.pack(side="left")

        # Action Buttons frame
        btn_frame = ttk.Frame(self.root, padding=(15, 10))
        btn_frame.pack(fill="x")

        self.organize_btn = ttk.Button(
            btn_frame, text="⚡ Organize Files Now", command=self._start_organize
        )
        self.organize_btn.pack(side="left", padx=(0, 10))

        # Log & status area
        log_frame = ttk.LabelFrame(self.root, text="Activity Log", padding=8)
        log_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

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
        self._log(f"\n--- Starting organization on: {target} ---")

        # Run organize logic in background thread so GUI doesn't freeze
        def run():
            try:
                organizer = FileOrganizer(target, dry_run=self.dry_run_var.get())
                stats = organizer.organize()
                summary = f"Completed! Moved: {stats['moved']} | Skipped: {stats['skipped']} | Errors: {stats['errors']}"
                self.root.after(0, lambda: self._log(summary))
                self.root.after(0, lambda: messagebox.showinfo("Finished", summary))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Error: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self.organize_btn.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    app = OrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
