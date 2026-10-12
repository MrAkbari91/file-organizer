"""Build script to generate standalone CLI and GUI executables using PyInstaller."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"


def build_cli() -> None:
    """Build standalone CLI binary."""
    print("Building CLI executable...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "file-organizer-cli",
        str(SRC_DIR / "file_organizer" / "cli" / "app.py"),
    ]
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
    print("CLI build finished! Output located in dist/file-organizer-cli.exe")


def build_gui() -> None:
    """Build standalone GUI binary."""
    print("Building GUI executable...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "file-organizer-gui",
        str(SRC_DIR / "file_organizer" / "gui" / "app.py"),
    ]
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
    print("GUI build finished! Output located in dist/file-organizer-gui.exe")


def main() -> None:
    parser = argparse.ArgumentParser(description="One-click build script for File Organizer Pro.")
    parser.add_argument("--cli", action="store_true", help="Build only CLI binary")
    parser.add_argument("--gui", action="store_true", help="Build only GUI binary")
    args = parser.parse_args()

    if args.cli:
        build_cli()
    elif args.gui:
        build_gui()
    else:
        # Build both by default
        build_cli()
        build_gui()


if __name__ == "__main__":
    main()
