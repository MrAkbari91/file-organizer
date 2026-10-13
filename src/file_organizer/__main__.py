"""Main entry point for `python -m file_organizer`."""

import sys


def main() -> None:
    """Detect whether to launch CLI or GUI based on arguments."""
    if "--gui" in sys.argv and "--cli" in sys.argv:
        print("Choose either --gui or --cli.", file=sys.stderr)
        raise SystemExit(2)
    # A missing GUI/display must never fall through into organizing the cwd.
    if len(sys.argv) == 1 or "--gui" in sys.argv:
        try:
            import tkinter as tk
            from file_organizer.gui.app import main as gui_main
        except ImportError as exc:
            print(
                f"GUI dependencies are unavailable: {exc}. Install Python with Tk and the project requirements. Use --cli for command-line mode.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        try:
            if "--gui" in sys.argv:
                sys.argv.remove("--gui")
            gui_main()
            return
        except tk.TclError as exc:
            print(
                f"GUI could not start: {exc}. A desktop display is required; use --cli on headless systems.",
                file=sys.stderr,
            )
            raise SystemExit(1)

    from file_organizer.cli.app import main as cli_main

    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
    cli_main()


if __name__ == "__main__":
    main()
