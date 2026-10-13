"""Prepare an isolated build environment, then build, verify and archive."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.", file=sys.stderr)
        return 1
    environment = ROOT / ".venv-build"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    try:
        if not python.exists():
            subprocess.run(
                [sys.executable, "-m", "venv", str(environment)],
                check=True,
                cwd=ROOT,
                env=env,
            )
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "-r",
                "requirements-build.txt",
                "-e",
                ".",
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        subprocess.run(
            [str(python), "scripts/build.py", "--verify", "--archive", *sys.argv[1:]],
            check=True,
            cwd=ROOT,
            env=env,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        print(
            f"Build stopped: {error}\nCheck Python/Tk installation, network access for pip, and close any previous build that is running.",
            file=sys.stderr,
        )
        return 1
    print("Build, executable checks and release archives completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
