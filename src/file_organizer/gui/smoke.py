"""Explicit, isolated packaged-app smoke test; never runs on normal startup."""

import json
import tempfile
import time
from pathlib import Path
import customtkinter as ctk
from PIL import Image
from file_organizer.gui.app import OrganizerGUI
from file_organizer.gui.windows import MainWindow, AppToplevel


def run_smoke(report_path):
    report_path = Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"passed": False, "status": "running"}), encoding="utf-8"
    )
    scratch = tempfile.TemporaryDirectory(
        prefix="packaged-smoke-", dir=report_path.parent
    )
    base = Path(scratch.name)
    folder = base / "files"
    folder.mkdir()
    (folder / "one.txt").write_text("identical sample")
    (folder / "two.txt").write_text("identical sample")
    Image.new("RGB", (24, 24), "#22D3EE").save(folder / "photo.png")
    root = MainWindow()
    root.withdraw()
    app = OrganizerGUI(root, base / "settings" / "appearance.json")
    app._notify = lambda *args, **kwargs: True
    checks = []
    outcome = {"passed": False, "error": "The window closed before all checks finished"}
    deadline = time.monotonic() + 45
    phase = [0]
    app.selected_folder.set(str(folder))
    app.organize_mode.set("extension")
    for page in app.pages:
        app._set_tab(page)
    app._set_tab("organize")

    # History navigation may have initiated a read-only job.
    def fail(error):
        outcome["error"] = str(error)
        app._close()

    def tick():
        try:
            if time.monotonic() > deadline:
                raise TimeoutError("Packaged workflow exceeded 45 seconds")
            if app._busy or app._render_timers or app._watch_stopping:
                root.after(20, tick)
                return
            if "failed:" in app.status_text_var.get().lower():
                raise RuntimeError(app.status_text_var.get())
            step = phase[0]
            if step == 0:
                checks.append("launch, assets and five navigation pages")
                app.dry_run_var.set(True)
                app._start_preview()
            elif step == 1:
                assert app._plan and len(app._plan) == 3
                assert (folder / "one.txt").exists() and not (folder / "txt").exists()
                checks.append("read-only preview and planned paths")
                app.dry_run_var.set(False)
                app._start_organize()
            elif step == 2:
                assert (folder / "txt" / "one.txt").exists() and (
                    folder / "png" / "photo.png"
                ).exists()
                checks.append("confirmed organization and journal")
                app._start_undo()
            elif step == 3:
                assert (folder / "one.txt").exists() and (folder / "photo.png").exists()
                checks.append("undo restores generated files")
                app._start_find_duplicates()
            elif step == 4:
                assert app._duplicate_count == 1
                app._select_extras()
                app._start_move_duplicates()
            elif step == 5:
                assert len(list((folder / "_duplicates").iterdir())) == 1
                checks.append("duplicate groups, selection and quarantine move")
                app._start_undo()
            elif step == 6:
                assert (folder / "one.txt").exists() and (folder / "two.txt").exists()
                app.toggle_theme()
                app.toggle_theme()
                prefs = json.loads(app.preferences_path.read_text())
                assert prefs["theme"] == app.current_theme
                second = AppToplevel(root)
                second.withdraw()
                restored = OrganizerGUI(second, app.preferences_path)
                assert restored.current_theme == app.current_theme
                restored._close()
                checks.append("light/dark themes and restart persistence")
                app._toggle_watch()
            elif step == 7:
                if not (folder / "txt" / "one.txt").exists():
                    root.after(20, tick)
                    return
                app._toggle_watch()
            elif step == 8:
                assert app.active_watcher is None
                checks.append("watcher start, stop and clean shutdown")
                outcome["passed"] = True
                app._close()
                return
            phase[0] += 1
            root.after(20, tick)
        except Exception as error:
            fail(error)

    # Finish initialization before scheduling workflows that can close the app.
    root.update()
    root.report_callback_exception = lambda kind, error, trace: fail(error)
    root.after(100, tick)
    root.mainloop()
    scratch.cleanup()
    if not outcome["passed"]:
        raise RuntimeError(outcome["error"])
    report_path.write_text(
        json.dumps({"passed": True, "checks": checks}, indent=2), encoding="utf-8"
    )
