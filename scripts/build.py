"""Build native CLI/GUI bundles, optionally verify and archive them for release."""

import argparse
import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
DIST_DIR = ROOT_DIR / "dist" / "premium"


def preflight(gui):
    for dependency in ("pyinstaller", "Pillow", "customtkinter"):
        importlib.metadata.version(dependency)
    if gui:
        import tkinter
        import customtkinter
    if sys.platform not in ("win32", "darwin", "linux"):
        raise RuntimeError(f"Unsupported build host: {sys.platform}")


def build_gui():
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(ROOT_DIR / "dist" / "premium"),
        "--workpath",
        str(ROOT_DIR / "build" / "premium"),
        str(ROOT_DIR / "packaging" / "file-organizer-premium.spec"),
    ]
    subprocess.run(command, cwd=ROOT_DIR, check=True)


def build_cli():
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--paths",
        str(SRC_DIR),
        "--name",
        "file-organizer-cli",
        "--distpath",
        str(ROOT_DIR / "dist" / "premium"),
        "--workpath",
        str(ROOT_DIR / "build" / "premium-cli"),
        "--specpath",
        str(ROOT_DIR / "build"),
        str(SRC_DIR / "file_organizer" / "cli" / "app.py"),
    ]
    subprocess.run(command, cwd=ROOT_DIR, check=True)


def bundle_path(kind):
    if kind == "gui" and sys.platform == "darwin":
        return DIST_DIR / "File Organizer Pro.app"
    return DIST_DIR / ("File Organizer Pro" if kind == "gui" else "file-organizer-cli")


def executable_path(kind):
    name = "File Organizer Pro" if kind == "gui" else "file-organizer-cli"
    bundle = bundle_path(kind)
    if kind == "gui" and sys.platform == "darwin":
        return bundle / "Contents/MacOS" / name
    return bundle / (name + (".exe" if os.name == "nt" else ""))


def archive_bundle(kind):
    machine = platform.machine().lower()
    architecture = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64"}.get(
        machine, machine
    )
    system = {"win32": "windows", "darwin": "macos", "linux": "linux"}[sys.platform]
    release = ROOT_DIR / "dist/releases"
    release.mkdir(parents=True, exist_ok=True)
    name = release / f"file-organizer-{kind}-{system}-{architecture}"
    # tar preserves POSIX symlinks and executable modes required by PyInstaller.
    archive = shutil.make_archive(
        str(name),
        "zip" if os.name == "nt" else "gztar",
        root_dir=DIST_DIR,
        base_dir=bundle_path(kind).name,
    )
    print(f"Release archive: {archive}")
    return Path(archive)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build for the current OS. Run on each OS to produce its native bundle."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--cli", action="store_true", help="Build only the command-line bundle"
    )
    selection.add_argument(
        "--gui", action="store_true", help="Build only the desktop bundle"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run generated-data checks on built executables",
    )
    parser.add_argument(
        "--archive", action="store_true", help="Archive whole bundles for distribution"
    )
    args = parser.parse_args(argv)
    kinds = ["cli"] if args.cli else ["gui"] if args.gui else ["cli", "gui"]
    try:
        preflight("gui" in kinds)
        for kind in kinds:
            (build_gui if kind == "gui" else build_cli)()
            executable = executable_path(kind)
            if not executable.is_file():
                raise RuntimeError(
                    f"Expected executable was not produced: {executable}"
                )
            if args.verify:
                from verify_build import verify

                verify(kind, executable)
            if args.archive:
                archive_bundle(kind)
            print(f"Built {kind}: {executable}")
    except (OSError, RuntimeError, ImportError, subprocess.SubprocessError) as error:
        print(
            f"Build failed: {error}\nUse build.bat (Windows) or sh build.sh (macOS/Linux) to install build dependencies first. Close running bundles before rebuilding.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
