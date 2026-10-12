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
