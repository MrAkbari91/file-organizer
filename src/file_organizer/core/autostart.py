"""Explicit Windows sign-in automation, including frozen executable support."""

import json
import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "FileOrganizerAutoWatch"


def get_windows_startup_bat():
    if sys.platform != "win32":
        return None
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    folder = Path(appdata) / "Microsoft/Windows/Start Menu/Programs/Startup"
    return folder / f"{APP_NAME}.bat" if folder.is_dir() else None


def is_autostart_enabled():
    path = get_windows_startup_bat()
    return bool(path and (path.exists() or path.with_suffix(".vbs").exists()))


def enable_autostart(
    target_folder,
    mode="category",
    *,
    recursive=False,
    sub_extension=True,
    clean_empty=False,
    ignore_patterns=None,
    config=None,
):
    legacy = get_windows_startup_bat()
    if legacy is None:
        return False
    target = Path(target_folder).resolve()
    if not target.is_dir():
        return False
    storage = (
        Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".config")
        / "FileOrganizer"
    )
    settings = storage / "startup.json"
    values = dict(
        folder=str(target),
        mode=mode,
        recursive=recursive,
        sub_extension=sub_extension,
        clean_empty=clean_empty,
        ignore_patterns=ignore_patterns or [],
        categories=config.custom_categories if config else {},
    )
    try:
        storage.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(values, indent=2), encoding="utf-8")
        if getattr(sys, "frozen", False):
            args = [sys.executable, "--background-watch", str(settings)]
        else:
            runner = storage / "startup_runner.py"
            source_root = Path(__file__).resolve().parents[2]
            runner.write_text(
                "import sys\nfrom pathlib import Path\nsys.path.insert(0, "
                + repr(str(source_root))
                + ")\nfrom file_organizer.gui.startup import run_background\nrun_background(Path(sys.argv[1]))\n",
                encoding="utf-8",
            )
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            args = [
                str(pythonw if pythonw.exists() else sys.executable),
                str(runner),
                str(settings),
            ]
        command = subprocess.list2cmdline(args)
        # VBScript quotes escape by doubling. No cmd.exe interpolation of paths.
        script = (
            'Set shell = CreateObject("WScript.Shell")\nshell.Run "'
            + command.replace('"', '""')
            + '", 0, False\n'
        )
        path = legacy.with_suffix(".vbs")
        path.write_text(script, encoding="utf-16")
        legacy.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def disable_autostart():
    legacy = get_windows_startup_bat()
    if legacy is None:
        return True
    try:
        legacy.unlink(missing_ok=True)
        legacy.with_suffix(".vbs").unlink(missing_ok=True)
        return True
    except OSError:
        return False
