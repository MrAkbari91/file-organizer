import tkinter as tk
from file_organizer.gui.app import OrganizerGUI
from file_organizer.core.organizer import OrganizeMode
from file_organizer.core.duplicates import DuplicateMethod


def test_organizer_gui_initialization():
    root = tk.Tk()
    root.withdraw()  # Hide window during test
    try:
        app = OrganizerGUI(root)
        assert app.organize_mode.get() == OrganizeMode.CATEGORY.value
        assert app.dup_method_var.get() == DuplicateMethod.EXACT.value
        assert app.sub_ext_var.get() is True
        assert app.recursive_var.get() is False
        assert app.clean_empty_var.get() is False
        assert "Ready" in app.status_text_var.get()
        assert app.root.title().startswith("🗂️ File Organizer Pro")
    finally:
        root.destroy()
