"""GUI entry point module placeholder for phase 1."""


def main() -> None:
    """Launch the GUI window."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.title("File Organizer Pro")
        root.geometry("400x200")
        label = tk.Label(root, text="File Organizer Pro - Ready", font=("Segoe UI", 12))
        label.pack(expand=True)
        root.mainloop()
    except ImportError:
        print("Error: tkinter is not installed or available on this system.")


if __name__ == "__main__":
    main()
