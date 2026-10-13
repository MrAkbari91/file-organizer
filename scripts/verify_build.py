"""Exercise real bundled executables using only isolated generated files."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def verify(kind, executable):
    executable = Path(executable).resolve()
    reports = ROOT / "build/verification"
    reports.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    with tempfile.TemporaryDirectory(prefix=f"{kind}-", dir=reports) as temporary:
        sandbox = Path(temporary)
        env["LOCALAPPDATA"] = str(sandbox / "settings")
        env["XDG_CONFIG_HOME"] = str(sandbox / "settings")
        if kind == "gui":
            report = reports / "gui-smoke.json"
            report.unlink(missing_ok=True)
            subprocess.run(
                [str(executable), "--smoke-test", str(report)],
                cwd=sandbox,
                env=env,
                check=True,
                timeout=90,
            )
            result = json.loads(report.read_text(encoding="utf-8"))
            if result.get("passed") is not True:
                raise RuntimeError(f"GUI smoke test failed: {result}")
        else:
            folder = sandbox / "files"
            folder.mkdir()
            (folder / "one.txt").write_text("generated data")
            (folder / "two.txt").write_text("generated data")

            def run(*args):
                return subprocess.run(
                    [str(executable), *map(str, args)],
                    cwd=sandbox,
                    env=env,
                    check=True,
                    timeout=45,
                    capture_output=True,
                )

            run("--help")
            run("--version")
            run(folder, "--by-extension", "--dry-run")
            assert sorted(p.name for p in folder.iterdir()) == ["one.txt", "two.txt"]
            run(folder, "--by-extension")
            assert (folder / "txt/one.txt").read_text() == "generated data"
            run(folder, "--undo")
            assert (folder / "one.txt").exists() and (folder / "two.txt").exists()
            run(folder, "--move-duplicates")
            assert len(list((folder / "_duplicates").iterdir())) == 1
            run(folder, "--undo")
            assert (folder / "one.txt").exists() and (folder / "two.txt").exists()
            result = {
                "passed": True,
                "checks": [
                    "help/version",
                    "read-only dry run",
                    "organize/undo",
                    "duplicates/undo",
                ],
            }
            (reports / "cli-smoke.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
    print(f"Verified {kind}: {result['checks']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["cli", "gui"])
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    verify(args.kind, args.executable)
