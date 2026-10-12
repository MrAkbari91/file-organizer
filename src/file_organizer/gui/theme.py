"""Modern dark theme color palettes and ttk styling definitions."""

import tkinter as tk
from tkinter import ttk

# Curated Modern Dark Palette (Catppuccin Mocha inspired)
COLORS = {
    "bg_dark": "#181825",          # Deep base background
    "bg_surface": "#1e1e2e",       # Surface / Cards
    "bg_surface_alt": "#313244",   # Hover / Secondary surface
    "fg_text": "#cdd6f4",          # Main high-contrast text
    "fg_subtext": "#a6adc8",       # Subtle muted text
    "accent_primary": "#89b4fa",   # Vibrant blue accent
    "accent_success": "#a6e3a1",   # Pastel green
    "accent_warning": "#f9e2af",   # Pastel yellow
    "accent_danger": "#f38ba8",    # Pastel red / coral
    "accent_purple": "#cba6f7",   # Modern violet
    "border": "#45475a",           # Subtle border
}

FONTS = {
    "title": ("Segoe UI", 13, "bold"),
    "heading": ("Segoe UI", 10, "bold"),
    "body": ("Segoe UI", 9),
    "code": ("Consolas", 9),
    "badge": ("Segoe UI", 8, "bold"),
}


def apply_dark_theme(root: tk.Tk) -> ttk.Style:
    """Apply consistent, elegant dark theme styling across all ttk widgets."""
    root.configure(bg=COLORS["bg_dark"])

    style = ttk.Style(root)
    # Use 'clam' as base engine for full cross-platform color customization
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Global Frame & Label
    style.configure("TFrame", background=COLORS["bg_dark"])
    style.configure("Surface.TFrame", background=COLORS["bg_surface"])
    style.configure("TLabel", background=COLORS["bg_dark"], foreground=COLORS["fg_text"], font=FONTS["body"])
    style.configure("Subtext.TLabel", background=COLORS["bg_dark"], foreground=COLORS["fg_subtext"], font=FONTS["body"])

    # LabelFrames (Cards)
    style.configure(
        "TLabelframe",
        background=COLORS["bg_surface"],
        foreground=COLORS["accent_primary"],
        bordercolor=COLORS["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=COLORS["bg_surface"],
        foreground=COLORS["accent_primary"],
        font=FONTS["heading"],
    )

    # Buttons
    style.configure(
        "TButton",
        background=COLORS["bg_surface_alt"],
        foreground=COLORS["fg_text"],
        font=FONTS["heading"],
        borderwidth=0,
        focuscolor="none",
        padding=(10, 6),
    )
    style.map(
        "TButton",
        background=[("active", COLORS["border"]), ("disabled", COLORS["bg_dark"])],
        foreground=[("disabled", COLORS["fg_subtext"])],
    )

    # Primary Accent Button
    style.configure(
        "Primary.TButton",
        background=COLORS["accent_primary"],
        foreground="#11111b",
        font=FONTS["heading"],
        padding=(12, 6),
    )
    style.map(
        "Primary.TButton",
        background=[("active", "#b4befe"), ("disabled", COLORS["border"])],
    )

    # Danger/Secondary Buttons
    style.configure(
        "Warning.TButton",
        background=COLORS["accent_warning"],
        foreground="#11111b",
        font=FONTS["heading"],
        padding=(10, 6),
    )

    # Radiobuttons & Checkbuttons
    style.configure(
        "TRadiobutton",
        background=COLORS["bg_surface"],
        foreground=COLORS["fg_text"],
        font=FONTS["body"],
        focuscolor="none",
    )
    style.map("TRadiobutton", background=[("active", COLORS["bg_surface"])])

    style.configure(
        "TCheckbutton",
        background=COLORS["bg_surface"],
        foreground=COLORS["fg_text"],
        font=FONTS["body"],
        focuscolor="none",
    )
    style.map("TCheckbutton", background=[("active", COLORS["bg_surface"])])

    # Entry fields
    style.configure(
        "TEntry",
        fieldbackground=COLORS["bg_surface_alt"],
        foreground=COLORS["fg_text"],
        bordercolor=COLORS["border"],
        insertcolor=COLORS["fg_text"],
        padding=6,
    )

    # Progressbar
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=COLORS["bg_surface_alt"],
        background=COLORS["accent_success"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["accent_success"],
        darkcolor=COLORS["accent_success"],
    )

    return style
