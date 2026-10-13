"""Centralized product tokens. CTk owns appearance; ttk is used only for tables."""

import tkinter.font as tkfont
from tkinter import ttk
import customtkinter as ctk

DARK_THEME = dict(
    name="dark",
    bg_root="#0B1220",
    bg_header="#0F192B",
    bg_surface="#131F33",
    bg_surface_alt="#192941",
    bg_card_inner="#0E192B",
    accent_primary="#22D3EE",
    accent_primary_hover="#06B6D4",
    accent_pressed="#0891B2",
    accent_primary_fg="#0B1220",
    fg_text="#F1F5F9",
    fg_subtext="#A5B4CF",
    fg_muted="#71829F",
    border="#293B56",
    accent_success="#22C55E",
    accent_warning="#F59E0B",
    accent_danger="#EF4444",
    accent_info="#38BDF8",
    accent_soft="#123B55",
    log_bg="#080E19",
    # Brighter error text on dark surfaces maintains readable small-label contrast.
    error_text="#FF8A94",
    success_text="#67E8A0",
)
LIGHT_THEME = dict(
    name="light",
    bg_root="#F3F6FB",
    bg_header="#FFFFFF",
    bg_surface="#FFFFFF",
    bg_surface_alt="#F8FAFD",
    bg_card_inner="#FFFFFF",
    accent_primary="#087EA4",
    accent_primary_hover="#066786",
    accent_pressed="#07566F",
    accent_primary_fg="#FFFFFF",
    fg_text="#17243B",
    fg_subtext="#52627A",
    fg_muted="#718096",
    border="#D9E2EF",
    accent_success="#15803D",
    accent_warning="#B45309",
    accent_danger="#B91C1C",
    accent_info="#0369A1",
    accent_soft="#E0F2FE",
    log_bg="#F8FAFC",
    error_text="#B91C1C",
    success_text="#15803D",
)
THEMES = {"dark": DARK_THEME, "light": LIGHT_THEME}
COLORS = DARK_THEME
FONT_FAMILY = "Segoe UI"


def color(token):
    return (LIGHT_THEME[token], DARK_THEME[token])


def font(size=14, bold=False, mono=False):
    return ("Consolas" if mono else FONT_FAMILY, size, "bold" if bold else "normal")


def apply_theme(root, name="dark"):
    global FONT_FAMILY
    families = tkfont.families(root)
    FONT_FAMILY = (
        "Segoe UI"
        if "Segoe UI" in families
        else "Arial" if "Arial" in families else "TkDefaultFont"
    )
    palette = THEMES.get(name, DARK_THEME)
    ctk.set_appearance_mode(palette["name"])
    if isinstance(root, (ctk.CTk, ctk.CTkToplevel)):
        root.configure(fg_color=color("bg_root"))
    else:
        root.configure(bg=palette["bg_root"])
    style = ttk.Style(root)
    if style.theme_use() != "clam":
        style.theme_use("clam")
    style.configure(
        "Premium.Treeview",
        background=palette["bg_surface"],
        fieldbackground=palette["bg_surface"],
        foreground=palette["fg_text"],
        bordercolor=palette["border"],
        lightcolor=palette["border"],
        darkcolor=palette["border"],
        rowheight=34,
        font=(FONT_FAMILY, -13),
        borderwidth=0,
    )
    style.configure(
        "Premium.Treeview.Heading",
        background=palette["bg_surface_alt"],
        foreground=palette["fg_subtext"],
        font=(FONT_FAMILY, -12, "bold"),
        bordercolor=palette["border"],
        lightcolor=palette["border"],
        darkcolor=palette["border"],
        relief="flat",
        padding=(8, 10),
    )
    style.map(
        "Premium.Treeview",
        background=[("selected", palette["accent_soft"])],
        foreground=[("selected", palette["fg_text"])],
    )
    style.map(
        "Premium.Treeview.Heading", background=[("active", palette["accent_soft"])]
    )
    return style, palette
