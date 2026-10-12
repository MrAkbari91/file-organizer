"""Main entry point for `python -m file_organizer`."""

import sys


def main() -> None:
    """Detect whether to launch CLI or GUI based on arguments."""
    # If no arguments provided or explicitly requested --gui
    if len(sys.argv) == 1 or "--gui" in sys.argv:
        try:
            from file_organizer.gui.app import main as gui_main

            if "--gui" in sys.argv:
                sys.argv.remove("--gui")
            gui_main()
            return
        except ImportError as exc:
            print(f"Warning: GUI module could not be loaded ({exc}). Falling back to CLI mode.")

    from file_organizer.cli.app import main as cli_main

    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
    cli_main()


if __name__ == "__main__":
    main()
