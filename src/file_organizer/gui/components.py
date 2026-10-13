"""Reusable rounded controls, keyboard focus, dialogs and data tables."""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import customtkinter as ctk
from PIL import Image
from file_organizer.gui.theme import color, font
from file_organizer.gui.windows import AppToplevel

ASSETS = Path(__file__).with_name("assets")


def icon(name, size=20):
    return ctk.CTkImage(
        light_image=Image.open(ASSETS / f"{name}-light.png"),
        dark_image=Image.open(ASSETS / f"{name}-dark.png"),
        size=(size, size),
    )


def label(parent, text="", size=14, bold=False, tone="fg_text", **kwargs):
    return ctk.CTkLabel(
        parent,
        text=text,
        font=font(size, bold),
        text_color=color(tone),
        anchor="w",
        **kwargs,
    )


def frame(parent, token="bg_surface", **kwargs):
    return ctk.CTkFrame(parent, fg_color=color(token), **kwargs)


class Button(ctk.CTkButton):
    def __init__(self, parent, text, command, primary=False, icon_name=None, **kwargs):
        self.primary = primary
        self.base_color = color("accent_primary" if primary else "bg_surface_alt")
        super().__init__(
            parent,
            text=text,
            command=command,
            height=40,
            corner_radius=8,
            fg_color=self.base_color,
            hover_color=color("accent_primary_hover" if primary else "accent_soft"),
            text_color=color("accent_primary_fg" if primary else "fg_text"),
            text_color_disabled=color("fg_muted"),
            border_color=color("border"),
            border_width=0 if primary else 1,
            font=font(13, True),
            image=icon(icon_name) if icon_name else None,
            **kwargs,
        )
        tk.Frame.configure(self, takefocus=1)
        tk.Misc.bind(
            self,
            "<FocusIn>",
            lambda e: self.configure(
                border_width=2, border_color=color("accent_primary")
            ),
        )
        tk.Misc.bind(
            self,
            "<FocusOut>",
            lambda e: self.configure(
                border_width=0 if primary else 1, border_color=color("border")
            ),
        )
        tk.Misc.bind(self, "<Return>", lambda e: self.invoke())
        tk.Misc.bind(self, "<space>", lambda e: self.invoke())
        self.bind("<ButtonPress-1>", self._pressed)
        self.bind(
            "<ButtonRelease-1>",
            lambda e: (
                self.configure(fg_color=self.base_color)
                if self.cget("state") != "disabled"
                else None
            ),
        )

    def configure(self, require_redraw=False, **kwargs):
        if "state" in kwargs:
            disabled = kwargs["state"] == "disabled"
            tk.Frame.configure(self, takefocus=0 if disabled else 1)
            if self.primary:
                kwargs["fg_color"] = (
                    color("bg_surface_alt") if disabled else self.base_color
                )
                kwargs["border_width"] = 1 if disabled else 0
        super().configure(require_redraw=require_redraw, **kwargs)

    def _pressed(self, event):
        if self.cget("state") != "disabled":
            self.configure(
                fg_color=color("accent_pressed" if self.primary else "accent_soft")
            )

    def instate(self, states):
        return (
            self.cget("state") == "disabled"
            if "disabled" in states
            else self.cget("state") != "disabled"
        )


class Card(ctk.CTkFrame):
    def __init__(self, parent, title=None, subtitle=None, **kwargs):
        super().__init__(
            parent,
            fg_color=color("bg_surface"),
            border_color=color("border"),
            border_width=1,
            corner_radius=12,
            **kwargs,
        )
        self.body = frame(self, corner_radius=0)
        self.body.pack(fill="both", expand=True, padx=20, pady=16)
        if title:
            label(self.body, title, 17, True).pack(anchor="w")
        if subtitle:
            text = label(self.body, subtitle, 13, tone="fg_subtext", justify="left")
            text.pack(fill="x", pady=(4, 12))
            text.bind(
                "<Configure>",
                lambda e: text.configure(wraplength=max(160, text.winfo_width())),
            )


class Choice(ctk.CTkFrame):
    def __init__(self, parent, variable, value, title, detail, icon_name):
        super().__init__(
            parent,
            fg_color=color("bg_surface_alt"),
            corner_radius=10,
            border_width=1,
            border_color=color("border"),
        )
        self.variable, self.value = variable, value
        self.radio = ctk.CTkRadioButton(
            self,
            text=title,
            variable=variable,
            value=value,
            font=font(14, True),
            text_color=color("fg_text"),
            fg_color=color("accent_primary"),
            hover_color=color("accent_primary_hover"),
            border_color=color("fg_muted"),
            radiobutton_width=16,
            radiobutton_height=16,
            border_width_checked=5,
            border_width_unchecked=2,
        )
        self.radio.pack(anchor="w", padx=16, pady=(16, 8))
        tk.Frame.configure(self.radio, takefocus=1)
        tk.Misc.bind(self.radio, "<space>", lambda e: self.select())
        tk.Misc.bind(self.radio, "<Return>", lambda e: self.select())
        tk.Misc.bind(
            self.radio,
            "<FocusIn>",
            lambda e: self.configure(
                border_color=color("accent_primary"), border_width=2
            ),
        )
        tk.Misc.bind(self.radio, "<FocusOut>", lambda e: self.refresh())
        self.detail = label(
            self,
            detail,
            12,
            tone="fg_subtext",
            justify="left",
            image=icon(icon_name, 24),
            compound="left",
            padx=8,
        )
        self.detail.pack(fill="x", padx=12, pady=(0, 16))
        self.detail.bind(
            "<Configure>",
            lambda e: self.detail.configure(
                wraplength=max(100, self.winfo_width() - 66)
            ),
        )
        self.bind("<Button-1>", lambda e: self.select())
        self.detail.bind("<Button-1>", lambda e: self.select())
        self._trace = variable.trace_add("write", lambda *a: self.refresh())
        self.refresh()

    def select(self):
        if self.radio.cget("state") != "disabled":
            self.variable.set(self.value)

    def refresh(self):
        selected = self.variable.get() == self.value
        self.configure(
            fg_color=color("accent_soft" if selected else "bg_surface_alt"),
            border_color=color("accent_primary" if selected else "border"),
            border_width=2 if selected else 1,
        )

    def destroy(self):
        self.variable.trace_remove("write", self._trace)
        super().destroy()


class DataTable(ctk.CTkFrame):
    def __init__(self, parent, columns, height=7):
        super().__init__(parent, fg_color=color("bg_surface"), corner_radius=0)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        keys = [key for key, title, width in columns]
        self.tree = ttk.Treeview(
            self,
            columns=keys,
            show="headings",
            height=height,
            style="Premium.Treeview",
            selectmode="extended",
        )
        for key, title, width in columns:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=80, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical = ctk.CTkScrollbar(
            self, command=self.tree.yview, button_color=color("border")
        )
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ctk.CTkScrollbar(
            self,
            command=self.tree.xview,
            orientation="horizontal",
            button_color=color("border"),
        )
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

    def clear(self):
        self.tree.delete(*self.tree.get_children())


class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.window, self.timer = widget, text, None, None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<FocusOut>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def schedule(self, event=None):
        self.timer = self.widget.after(600, self.show)

    def show(self):
        self.timer = None
        self.window = ctk.CTkToplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.geometry(
            f"+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty() + self.widget.winfo_height() + 6}"
        )
        label(
            self.window, self.text, 12, wraplength=300, justify="left", padx=12, pady=8
        ).pack()

    def hide(self, event=None):
        if self.timer:
            self.widget.after_cancel(self.timer)
            self.timer = None
        if self.window:
            self.window.destroy()
            self.window = None


def dialog(root, title, message, confirm=False):
    window = AppToplevel(root)
    window.withdraw()
    window.title(title)
    window.geometry("560x360")
    window.resizable(False, False)
    window.transient(root)
    window.configure(fg_color=color("bg_surface"))
    label(window, title, 20, True).pack(anchor="w", padx=24, pady=(24, 12))
    message_box = ctk.CTkTextbox(
        window,
        height=180,
        fg_color=color("bg_surface"),
        text_color=color("fg_subtext"),
        font=font(14),
        wrap="word",
    )
    message_box.pack(fill="both", expand=True, padx=20)
    message_box.insert("1.0", message)
    message_box.configure(state="disabled")
    answer = [False]
    actions = frame(window)
    actions.pack(side="bottom", fill="x", padx=24, pady=20)

    def finish(value):
        answer[0] = value
        window.destroy()

    yes = Button(
        actions,
        "Confirm" if confirm else "OK",
        lambda: finish(True),
        primary=True,
        width=110,
    )
    yes.pack(side="right")
    if confirm:
        no = Button(actions, "Cancel", lambda: finish(False), width=100)
        no.pack(side="right", padx=8)
        no.focus_set()
    else:
        yes.focus_set()
    window.bind("<Escape>", lambda e: finish(False))
    window.update_idletasks()
    window.geometry(
        f"+{root.winfo_rootx() + max(0, (root.winfo_width()-560)//2)}+{root.winfo_rooty() + max(0, (root.winfo_height()-360)//2)}"
    )
    window.deiconify()
    window.wait_visibility()
    window.grab_set()
    root.wait_window(window)
    return answer[0]
