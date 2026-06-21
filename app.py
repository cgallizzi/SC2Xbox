"""PyInstaller / standalone entry point.

Runs as a module in dev (`python -m src.bridge`) and as a frozen single-file exe
for distribution. When double-clicked from Explorer, the console closes the
instant the process exits -- so on any error we print it and wait for a keypress,
otherwise a startup failure would just "flash and disappear".
"""

import sys
import traceback

# Frozen console apps block-buffer stdout; make status lines appear immediately.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass


def _run():
    from src.bridge import main
    return main()


if __name__ == "__main__":
    try:
        code = _run()
    except Exception:
        traceback.print_exc()
        code = 1

    # If launched by double-click and something went wrong, keep the window open
    # so the user can actually read the error.
    if code != 0:
        try:
            input("\nSomething went wrong (see above). Press Enter to close...")
        except EOFError:
            pass
    sys.exit(code)
