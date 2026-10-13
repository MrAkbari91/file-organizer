"""Build selection, failure reporting and complete release-bundle archives."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tarfile
import zipfile
import pytest

spec = importlib.util.spec_from_file_location(
    "build_script", Path(__file__).parents[1] / "scripts/build.py"
)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_build_failure_is_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(build, "preflight", lambda gui: None)

    def failed():
        raise subprocess.CalledProcessError(1, ["PyInstaller"])

    monkeypatch.setattr(build, "build_cli", failed)
    assert build.main(["--cli"]) == 1
    assert "Build failed" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["cli", "gui"])
def test_archive_contains_executable_and_runtime(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(build, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(build, "DIST_DIR", tmp_path / "dist/premium")
    bundle = build.bundle_path(kind)
    executable = build.executable_path(kind)
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"sample executable")
    executable.chmod(0o755)
    runtime = bundle / "_internal/library.dat"
    runtime.parent.mkdir(parents=True)
    runtime.write_bytes(b"sample runtime")
    if os.name != "nt":
        (runtime.parent / "library-link").symlink_to("library.dat")
    path = build.archive_bundle(kind)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            assert (
                archive.read(executable.relative_to(build.DIST_DIR).as_posix())
                == b"sample executable"
            )
            assert (
                archive.read(runtime.relative_to(build.DIST_DIR).as_posix())
                == b"sample runtime"
            )
    else:
        with tarfile.open(path) as archive:
            member = archive.getmember(
                executable.relative_to(build.DIST_DIR).as_posix()
            )
            assert member.mode & 0o111
            assert archive.getmember(
                (runtime.parent / "library-link").relative_to(build.DIST_DIR).as_posix()
            ).issym()
