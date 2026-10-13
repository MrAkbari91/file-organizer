import sys
from unittest.mock import patch
import pytest
from file_organizer.cli.app import main


def test_cli_help(capsys):
    with patch.object(sys, "argv", ["file-organizer", "--help"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "Organize files in a directory" in captured.out
    assert "--by-category" in captured.out
    assert "--find-duplicates" in captured.out
    assert "--watch" in captured.out


def test_cli_dry_run(tmp_path):
    test_file = tmp_path / "sample.jpg"
    test_file.write_text("dummy")

    with patch.object(sys, "argv", ["file-organizer", str(tmp_path), "--dry-run"]):
        main()

    # Dry run should leave file in original place
    assert test_file.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["sample.jpg"]


def test_cli_respects_duplicate_ignore(tmp_path, capsys):
    for name in ("first.txt", "second.txt"):
        (tmp_path / name).write_text("same")
    with patch.object(
        sys,
        "argv",
        [
            "file-organizer",
            str(tmp_path),
            "--move-duplicates",
            "--ignore",
            "second.txt",
        ],
    ):
        main()
    assert (tmp_path / "second.txt").exists()
    assert not (tmp_path / "_duplicates").exists()


def test_cli_reports_operation_failure(tmp_path):
    with patch.object(sys, "argv", ["file-organizer", str(tmp_path)]), patch(
        "file_organizer.cli.app.FileOrganizer.organize", return_value={"errors": 1}
    ):
        with pytest.raises(SystemExit) as error:
            main()
        assert error.value.code == 1


def test_cli_frozen_startup_route(tmp_path):
    settings = tmp_path / "startup.json"
    with patch.object(
        sys, "argv", ["file-organizer-cli", "--background-watch", str(settings)]
    ), patch("file_organizer.gui.startup.run_background") as start:
        main()
    start.assert_called_once_with(settings)


def test_cli_dry_run_cannot_undo(tmp_path):
    with patch.object(
        sys, "argv", ["file-organizer", str(tmp_path), "--undo", "--dry-run"]
    ):
        with pytest.raises(SystemExit) as error:
            main()
        assert error.value.code == 2
