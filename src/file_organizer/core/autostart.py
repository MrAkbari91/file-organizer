"""System startup auto-run management (Windows/macOS/Linux) with explicit user consent."""

import os
import sys
from pathlib import Path
from typing import Optional

APP_NAME = "FileOrganizerAutoWatch"


def get_windows_startup_bat() -> Optional[Path]:
    """Get path to the user's Windows Startup batch file."""
    if sys.platform != "win32":
        return None
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if startup_dir.exists():
        return startup_dir / f"{APP_NAME}.bat"
    return None


def is_autostart_enabled() -> bool:
    """Check if startup auto-watch is currently registered."""
    if sys.platform == "win32":
        bat_file = get_windows_startup_bat()
        return bat_file.exists() if bat_file else False
    return False


def enable_autostart(target_folder: Path, mode: str = "category") -> bool:
    """
    Enable background auto-watch on system startup with explicit user action.
    Creates a non-intrusive batch launcher in Windows Startup.
    """
    target = Path(target_folder).resolve()

    if sys.platform == "win32":
        bat_file = get_windows_startup_bat()
        if not bat_file:
            return False

        python_exe = sys.executable
        # pythonw.exe launches without showing a black console window
        pythonw_exe = Path(python_exe).parent / "pythonw.exe"
        runner = str(pythonw_exe) if pythonw_exe.exists() else python_exe

        # Command to run silent background watcher
        content = (
            "@echo off\n"
            f'start "" "{runner}" -m file_organizer "{target}" --by-{mode} -w --watch-interval 5\n'
        )

        try:
            bat_file.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    return False


def disable_autostart() -> bool:
    """Disable and completely remove startup auto-watch."""
    if sys.platform == "win32":
        bat_file = get_windows_startup_bat()
        if bat_file and bat_file.exists():
            try:
                bat_file.unlink()
                return True
            except Exception:
                return False
    return True
