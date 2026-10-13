"""Desktop page composition. Operations and mutable state live in app.py."""

import tkinter as tk
import customtkinter as ctk
from file_organizer import __version__
from file_organizer.gui.theme import color, font
from file_organizer.gui.components import (
    Button,
    Card,
    Choice,
    DataTable,
    Tooltip,
    frame,
    label,
    icon,
)

PAGES = {
    "dashboard": (
        "Dashboard",
        "A calmer workspace starts here.",
        "Your activity at a glance. Real results, one folder at a time.",
        "home",
    ),
    "organize": (
        "Organize Studio",
        "Everything, in its right place.",
        "Choose a strategy, review the plan, then organize with confidence.",
        "folder",
    ),
    "duplicates": (
        "Duplicate Hunter",
        "Find the extra. Keep the essential.",
        "Compare files and review each group before moving selected copies.",
        "copies",
    ),
    "settings": (
        "Automation & Settings",
        "Less effort. Lasting order.",
        "Choose how your workspace stays organized.",
        "settings",
    ),
    "history": (
        "Activity & History",
        "Every action, accounted for.",
        "Review recent jobs and safely restore your last file operation.",
        "history",
    ),
}


def check(parent, text, variable):
    widget = ctk.CTkCheckBox(
        parent,
        text=text,
        variable=variable,
        font=font(13),
        text_color=color("fg_text"),
        fg_color=color("accent_primary"),
        hover_color=color("accent_primary_hover"),
        checkmark_color=color("accent_primary_fg"),
        border_color=color("fg_muted"),
        checkbox_width=18,
        checkbox_height=18,
        corner_radius=4,
    )
    tk.Frame.configure(widget, takefocus=1)
    tk.Misc.bind(widget, "<space>", lambda e: widget.toggle())
    return widget


def entry(parent, variable, placeholder=None):
    return ctk.CTkEntry(
        parent,
        textvariable=variable,
        placeholder_text=placeholder,
        height=40,
        corner_radius=8,
        fg_color=color("bg_card_inner"),
        border_color=color("border"),
        text_color=color("fg_text"),
        placeholder_text_color=color("fg_muted"),
        font=font(14),
    )


def build(app):
    root = app.root
    root.columnconfigure(1, weight=1)
    root.rowconfigure(1, weight=1)
    top = frame(root, "bg_header", corner_radius=0, height=72)
    top.grid(row=0, column=0, columnspan=2, sticky="ew")
    top.columnconfigure(1, weight=1)
    brand = frame(top, "bg_header", corner_radius=0)
    brand.grid(row=0, column=0, padx=24, pady=16, sticky="w")
    from PIL import Image
    from file_organizer.gui.components import ASSETS

    app.brand_image = ctk.CTkImage(Image.open(ASSETS / "app.png"), size=(36, 36))
    label(
        brand,
        "File Organizer Pro",
        17,
        True,
        image=app.brand_image,
        compound="left",
        padx=10,
    ).pack(side="left")
    label(brand, f"v{__version__}", 11, tone="fg_muted").pack(side="left", padx=8)
    app.context_label = label(top, "Dashboard", 13, tone="fg_subtext")
    app.context_label.grid(row=0, column=1, sticky="w", padx=20)
    app.watcher_badge = label(top, "●  Watcher off", 12, tone="fg_subtext")
    app.watcher_badge.grid(row=0, column=2, padx=16)
    app.theme_btn = Button(
        top, "Light theme", app.toggle_theme, icon_name="sun", width=140
    )
    app.theme_btn.grid(row=0, column=3, padx=(0, 24))

    sidebar = frame(root, "bg_header", corner_radius=0, width=228)
    sidebar.grid(row=1, column=0, sticky="nsew")
    sidebar.grid_propagate(False)
    sidebar.columnconfigure(0, weight=1)
    sidebar.rowconfigure(7, weight=1)
    label(sidebar, "WORKSPACE", 11, True, tone="fg_muted").grid(
        row=0, column=0, sticky="w", padx=28, pady=(28, 16)
    )
    app.tab_buttons = {}
    for i, (key, (title, _, __, image)) in enumerate(PAGES.items(), 1):
        btn = Button(
            sidebar,
            title,
            lambda k=key: app._set_tab(k),
            icon_name=image,
            anchor="w",
            width=190,
        )
        btn.grid(row=i, column=0, sticky="ew", padx=16, pady=4)
        app.tab_buttons[key] = btn
    note = Card(sidebar)
    note.grid(row=8, column=0, sticky="ew", padx=16, pady=20)
    label(note.body, "Your files stay yours.", 13, True).pack(anchor="w")
    label(
        note.body,
        "Local processing.\nPreview before you move.",
        12,
        tone="fg_subtext",
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    label(
        sidebar,
        "Ctrl+O  Browse folder\nCtrl+L  Edit folder path",
        11,
        tone="fg_muted",
        justify="left",
    ).grid(row=9, column=0, sticky="w", padx=28, pady=(0, 24))

    main = frame(root, "bg_root", corner_radius=0)
    main.grid(row=1, column=1, sticky="nsew", padx=24, pady=20)
    main.columnconfigure(0, weight=1)
    main.rowconfigure(2, weight=1)
    heading = frame(main, "bg_root", corner_radius=0)
    heading.grid(row=0, column=0, sticky="ew", pady=(0, 16))
    app.page_title = label(heading, "", 28, True)
    app.page_title.pack(anchor="w")
    app.page_subtitle = label(heading, "", 13, tone="fg_subtext")
    app.page_subtitle.pack(anchor="w", pady=(4, 0))

    app.folder_card = Card(main)
    app.folder_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))
    body = app.folder_card.body
    row = frame(body)
    row.pack(fill="x")
    label(row, "TARGET DIRECTORY", 11, True, tone="fg_subtext").pack(side="left")
    app.folder_hint = label(row, "Choose a folder to get started.", 12, tone="fg_muted")
    app.folder_hint.pack(side="right")
    row = frame(body)
    row.pack(fill="x", pady=8)
    app.folder_entry = entry(row, app.selected_folder)
    app.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
    app.browse_btn = Button(
        row, "Browse", app._browse_folder, width=96, icon_name="folder"
    )
    app.browse_btn.pack(side="left")
    app.explorer_btn = Button(row, "Open", app._open_in_explorer, width=76)
    app.explorer_btn.pack(side="left", padx=(8, 0))
    app.inputs += [app.folder_entry, app.browse_btn]
    row = frame(body)
    row.pack(fill="x")
    app.preset_buttons = []
    for name in ("Downloads", "Documents", "Desktop", "Pictures"):
        button = Button(row, name, lambda n=name: app._set_preset_folder(n), width=100)
        button.configure(height=28, font=font(12))
        button.pack(side="left", padx=(0, 8))
        app.inputs.append(button)
        app.preset_buttons.append(button)
    Tooltip(
        app.folder_entry,
        "Paste a folder path. Selecting a folder never changes its files.",
    )

    app.page_host = frame(main, "bg_root", corner_radius=0)
    app.page_host.grid(row=2, column=0, sticky="nsew")
    app.page_host.rowconfigure(0, weight=1)
    app.page_host.columnconfigure(0, weight=1)
    app.pages = {}
    for key in PAGES:
        page = ctk.CTkScrollableFrame(
            app.page_host,
            fg_color=color("bg_root"),
            corner_radius=0,
            scrollbar_button_color=color("border"),
            scrollbar_button_hover_color=color("fg_muted"),
        )
        page.columnconfigure(0, weight=1)
        app.pages[key] = page
    dashboard(app, app.pages["dashboard"])
    organize(app, app.pages["organize"])
    duplicates(app, app.pages["duplicates"])
    settings(app, app.pages["settings"])
    history(app, app.pages["history"])

    app.action_area = frame(main, "bg_root", corner_radius=0)
    app.action_area.grid(row=3, column=0, sticky="ew", pady=(12, 0))
    app.action_frames = {}
    for key in ("organize", "duplicates", "history"):
        app.action_frames[key] = frame(app.action_area, "bg_root", corner_radius=0)
    row = app.action_frames["organize"]
    app.preview_btn = Button(
        row, "Scan & preview", app._start_preview, icon_name="scan", width=156
    )
    app.preview_btn.pack(side="left")
    app.organize_btn = Button(
        row, "Organize reviewed files", app._start_organize, primary=True, width=210
    )
    app.organize_btn.pack(side="right")
    row = app.action_frames["duplicates"]
    app.find_dup_btn = Button(
        row,
        "Scan for duplicates",
        app._start_find_duplicates,
        icon_name="scan",
        width=180,
    )
    app.find_dup_btn.pack(side="left")
    app.move_dup_btn = Button(
        row, "Move selected copies", app._start_move_duplicates, primary=True, width=200
    )
    app.move_dup_btn.pack(side="right")
    row = app.action_frames["history"]
    app.undo_btn = Button(
        row, "Undo last file operation", app._start_undo, icon_name="undo", width=215
    )
    app.undo_btn.pack(side="left")
    app.refresh_history_btn = Button(
        row, "Refresh folder history", app._refresh_history, width=180
    )
    app.refresh_history_btn.pack(side="right")
    Tooltip(
        app.organize_btn,
        "Requires a fresh preview. Files changed since the scan are left untouched.",
    )

    app.console_card = Card(main)
    app.console_card.grid(row=4, column=0, sticky="ew", pady=(16, 0))
    row = frame(app.console_card.body)
    row.pack(fill="x")
    label(row, "Live activity", 13, True).pack(side="left")
    app.autoscroll_cb = check(row, "Auto-scroll", app.autoscroll_var)
    app.autoscroll_cb.pack(side="left", padx=16)
    for title, callback in (("Clear", app._clear_log), ("Copy", app._copy_log)):
        btn = Button(row, title, callback, width=64)
        btn.configure(height=28)
        btn.pack(side="right", padx=(6, 0))
    app.log_text = ctk.CTkTextbox(
        app.console_card.body,
        height=76,
        fg_color=color("log_bg"),
        text_color=color("fg_text"),
        font=font(12, mono=True),
        corner_radius=8,
        wrap="word",
        state="disabled",
        border_width=0,
    )
    app.log_text.pack(fill="x", pady=(8, 0))
    app.status_bar = frame(main, "bg_root", corner_radius=0)
    app.status_bar.grid(row=5, column=0, sticky="ew", pady=(12, 0))
    app.status_bar.columnconfigure(0, weight=1)
    app.status_lbl = label(
        app.status_bar, textvariable=app.status_text_var, size=12, tone="fg_subtext"
    )
    app.status_lbl.grid(row=0, column=0, sticky="ew")
    app.status_lbl.bind(
        "<Configure>",
        lambda e: app.status_lbl.configure(
            wraplength=max(200, app.status_lbl.winfo_width())
        ),
    )
    app.cancel_btn = Button(app.status_bar, "Cancel", app._cancel, width=88)
    app.cancel_btn.configure(height=28)
    app.cancel_btn.grid(row=0, column=1, padx=(12, 0))
    app.progress_bar = ctk.CTkProgressBar(
        app.status_bar,
        height=4,
        fg_color=color("border"),
        progress_color=color("accent_primary"),
    )
    app.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
    app.progress_bar.set(0)


def dashboard(app, page):
    stats = frame(page, "bg_root", corner_radius=0)
    stats.pack(fill="x", pady=(0, 16))
    app.stat_labels = {}
    for i, (key, title, detail, image) in enumerate(
        (
            ("scanned", "Files scanned", "Latest organization scan", "scan"),
            ("organized", "Files organized", "This session", "folder"),
            ("duplicates", "Extra copies", "Latest duplicate scan", "copies"),
            ("bytes", "Duplicate size", "Potential · not disk space saved", "file"),
        )
    ):
        stats.columnconfigure(i, weight=1, uniform="stats")
        card = Card(stats)
        card.grid(
            row=0,
            column=i,
            sticky="nsew",
            padx=(0 if i == 0 else 6, 0 if i == 3 else 6),
        )
        label(
            card.body,
            title,
            12,
            tone="fg_subtext",
            image=icon(image),
            compound="left",
            padx=6,
        ).pack(anchor="w")
        app.stat_labels[key] = label(card.body, "—", 30, True)
        app.stat_labels[key].pack(anchor="w", pady=12)
        label(
            card.body, detail, 11, tone="fg_muted", wraplength=145, justify="left"
        ).pack(anchor="w")
    hero = Card(
        page,
        "A fresh start for your files.",
        "Sort a folder, review every change and keep an undo record for the files you move.",
    )
    hero.pack(fill="x", pady=(0, 16))
    Button(
        hero.body,
        "Open Organize Studio",
        lambda: app._set_tab("organize"),
        primary=True,
        width=220,
    ).pack(anchor="w")
    recent = Card(
        page,
        "Recent jobs",
        "Your completed jobs appear here. No scans have run automatically.",
    )
    recent.pack(fill="x", pady=(0, 16))
    app.recent_table = DataTable(
        recent.body,
        [("time", "TIME", 140), ("action", "ACTION", 160), ("result", "RESULT", 400)],
        height=4,
    )
    app.recent_table.pack(fill="x")
    app.dashboard_watcher = label(
        page,
        "Watcher is off. Start it from Automation & Settings.",
        13,
        tone="fg_subtext",
    )
    app.dashboard_watcher.pack(anchor="w", pady=8)


def organize(app, page):
    card = Card(
        page,
        "01  Choose a sorting strategy",
        "The preview shows the real source and destination for each file.",
    )
    card.pack(fill="x", pady=(0, 16))
    row = frame(card.body)
    row.pack(fill="x")
    for i, (value, title, desc, image) in enumerate(
        (
            (
                "category",
                "By category",
                "Images, documents, code\nand more.",
                "category",
            ),
            ("extension", "By extension", "A folder for each\nfile extension.", "file"),
            (
                "date",
                "By timeline",
                "Year and month of\nlast modification.",
                "calendar",
            ),
        )
    ):
        row.columnconfigure(i, weight=1, uniform="modes")
        choice = Choice(row, app.organize_mode, value, title, desc, image)
        choice.grid(
            row=0,
            column=i,
            sticky="nsew",
            padx=(0 if i == 0 else 6, 0 if i == 2 else 6),
        )
        app.inputs.append(choice.radio)
    app.route_var = ctk.StringVar()
    label(card.body, textvariable=app.route_var, size=12, tone="accent_info").pack(
        anchor="w", pady=(12, 0)
    )
    rules = Card(page, "02  Organization rules")
    rules.pack(fill="x", pady=(0, 16))
    rules.body.columnconfigure((0, 1), weight=1)
    # Card header is packed; put grid controls in a separate frame.
    row = frame(rules.body)
    row.pack(fill="x", pady=(12, 0))
    row.columnconfigure((0, 1), weight=1)
    for i, (title, var) in enumerate(
        (
            ("Group extensions inside categories", app.sub_ext_var),
            ("Include subfolders", app.recursive_var),
            ("Remove empty folders after moving", app.clean_empty_var),
            ("Dry run · preview only", app.dry_run_var),
        )
    ):
        control = check(row, title, var)
        control.grid(row=i // 2, column=i % 2, sticky="w", pady=6)
        app.inputs.append(control)
    preview = Card(
        page,
        "03  Review planned changes",
        "Scan first. Nothing moves until you confirm. Double-click a row to inspect full paths.",
    )
    preview.pack(fill="x", pady=(0, 8))
    app.plan_summary = label(
        preview.body,
        "No preview yet. Select a folder and choose Scan & preview.",
        13,
        tone="fg_subtext",
    )
    app.plan_summary.pack(anchor="w", pady=(0, 12))
    app.plan_table = DataTable(
        preview.body,
        [
            ("source", "SOURCE", 270),
            ("destination", "DESTINATION", 290),
            ("status", "STATUS", 190),
        ],
        height=7,
    )
    app.plan_table.pack(fill="x")
    app.plan_table.tree.bind("<Double-1>", app._inspect_plan)
    app.plan_table.tree.bind("<Return>", app._inspect_plan)


def duplicates(app, page):
    card = Card(
        page,
        "Choose how to compare",
        "Exact copies share identical contents. Name and visual matches can contain different information.",
    )
    card.pack(fill="x", pady=(0, 16))
    row = frame(card.body)
    row.pack(fill="x")
    for i, (value, title, desc, image) in enumerate(
        (
            (
                "exact",
                "Exact content",
                "Size filtering and\nSHA-256 comparison.",
                "file",
            ),
            (
                "converted",
                "Same filename",
                "Same name across\ndifferent formats.",
                "copies",
            ),
            (
                "visual",
                "Similar images",
                "Compare image\nappearance with dHash.",
                "watch",
            ),
        )
    ):
        row.columnconfigure(i, weight=1, uniform="dups")
        choice = Choice(row, app.dup_method_var, value, title, desc, image)
        choice.grid(
            row=0,
            column=i,
            sticky="nsew",
            padx=(0 if i == 0 else 6, 0 if i == 2 else 6),
        )
        app.inputs.append(choice.radio)
    row = frame(card.body)
    row.pack(fill="x", pady=(12, 0))
    for title, var in (
        ("Include subfolders", app.recursive_var),
        ("Dry run · preview only", app.dry_run_var),
    ):
        control = check(row, title, var)
        control.pack(side="left", padx=(0, 24))
        app.inputs.append(control)
    results = Card(
        page,
        "Review duplicate groups",
        "The first file in each group is kept. Select extra rows with Ctrl/Shift; double-click for full metadata.",
    )
    results.pack(fill="x")
    app.stats_summary_var = ctk.StringVar(
        value="No scan yet. Your files remain untouched."
    )
    label(
        results.body,
        textvariable=app.stats_summary_var,
        size=13,
        tone="accent_info",
        wraplength=700,
    ).pack(anchor="w", pady=(0, 12))
    row = frame(results.body)
    row.pack(fill="x", pady=(0, 8))
    app.select_extras_btn = Button(
        row, "Select extra copies", app._select_extras, width=170
    )
    app.select_extras_btn.configure(height=30)
    app.select_extras_btn.pack(side="left")
    app.selected_count = label(row, "0 copies selected", 12, tone="fg_subtext")
    app.selected_count.pack(side="left", padx=12)
    app.dup_table = DataTable(
        results.body,
        [
            ("group", "GROUP", 80),
            ("role", "ACTION", 90),
            ("path", "FILE PATH", 340),
            ("size", "SIZE", 100),
            ("modified", "MODIFIED", 160),
        ],
        height=9,
    )
    app.dup_table.pack(fill="x")
    app.dup_table.tree.bind("<<TreeviewSelect>>", app._duplicate_selection)
    app.dup_table.tree.bind("<Double-1>", app._inspect_duplicate)
    app.dup_table.tree.bind("<Return>", app._inspect_duplicate)
    label(
        results.body,
        "Moving copies into _duplicates/ does not free disk space. Nothing is deleted.",
        12,
        tone="fg_subtext",
    ).pack(anchor="w", pady=(12, 0))


def settings(app, page):
    card = Card(
        page,
        "Folder watcher",
        "Continuously organize new files using the selected folder, strategy and rules.",
    )
    card.pack(fill="x", pady=(0, 16))
    app.watch_details = label(
        card.body,
        "Watcher is off.",
        13,
        tone="fg_subtext",
        wraplength=700,
        justify="left",
    )
    app.watch_details.pack(anchor="w", pady=(0, 12))
    app.watch_btn = Button(
        card.body,
        "Start monitoring",
        app._toggle_watch,
        primary=True,
        width=190,
        icon_name="watch",
    )
    app.watch_btn.pack(anchor="w")
    label(
        card.body,
        "Stop monitoring to edit the folder or rules. Monitoring stops when this app closes.",
        12,
        tone="fg_subtext",
        wraplength=700,
    ).pack(anchor="w", pady=(12, 0))
    startup = Card(
        page,
        "Windows sign-in",
        "Launch a separate silent watcher when you sign in. Disabling this removes future automatic starts.",
    )
    startup.pack(fill="x", pady=(0, 16))
    app.boot_cb = check(
        startup.body, "Start auto-watch when I sign in to Windows", app.autostart_var
    )
    app.boot_cb.configure(command=app._on_toggle_autostart)
    app.boot_cb.pack(anchor="w")
    app.inputs.append(app.boot_cb)
    label(
        startup.body,
        "Already-running sign-in watchers keep running until Windows signs out or their process is stopped.",
        12,
        tone="fg_subtext",
        wraplength=700,
    ).pack(anchor="w", pady=(8, 0))
    ignores = Card(
        page,
        "Exclusions",
        "Comma-separated patterns apply to organizing and duplicate scans. Hidden and system files are excluded by default.",
    )
    ignores.pack(fill="x", pady=(0, 16))
    app.ignore_entry = entry(ignores.body, app.custom_ignore_var)
    app.ignore_entry.pack(fill="x")
    app.inputs.append(app.ignore_entry)
    label(
        ignores.body,
        "Examples: *.tmp, draft_*, private\nDirectory links and junctions are never followed.",
        12,
        tone="fg_subtext",
        justify="left",
    ).pack(anchor="w", pady=(8, 0))
    Tooltip(
        app.ignore_entry,
        "Existing config.json categories and ignore rules are preserved and merged with these patterns.",
    )


def history(app, page):
    jobs = Card(
        page,
        "Recent jobs",
        "A local record of completed work. Clearing the activity display does not remove file undo history.",
    )
    jobs.pack(fill="x", pady=(0, 16))
    app.history_table = DataTable(
        jobs.body,
        [
            ("time", "TIME", 150),
            ("action", "ACTION", 150),
            ("folder", "FOLDER", 250),
            ("result", "RESULT", 330),
        ],
        height=7,
    )
    app.history_table.pack(fill="x")
    undo = Card(
        page,
        "Restore a file operation",
        "Undo uses the latest manifest in the selected folder. Occupied or changed files are left untouched.",
    )
    undo.pack(fill="x")
    app.undo_summary = label(
        undo.body,
        "Choose a folder to inspect its undo history.",
        13,
        tone="fg_subtext",
        wraplength=700,
    )
    app.undo_summary.pack(anchor="w")
