"""CLI routing must work without a display and GUI failure must never move files."""

import sys
import tkinter as tk
from unittest.mock import patch
import pytest
from file_organizer.__main__ import main


def test_cli_routes_without_starting_gui():
    with patch.object(sys, "argv", ["file-organizer", "--cli", "--help"]), patch(
        "file_organizer.cli.app.main"
    ) as cli, patch("file_organizer.gui.app.main") as gui:
        main()
    cli.assert_called_once()
    gui.assert_not_called()


def test_headless_gui_failure_never_runs_organizer(capsys):
    with patch.object(sys, "argv", ["file-organizer"]), patch(
        "file_organizer.gui.app.main", side_effect=tk.TclError("no display")
    ), patch("file_organizer.cli.app.main") as cli:
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 1
    cli.assert_not_called()
    assert "--cli" in capsys.readouterr().err


def test_conflicting_modes_rejected():
    with patch.object(sys, "argv", ["file-organizer", "--gui", "--cli"]):
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 2
