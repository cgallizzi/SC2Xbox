"""SC2Xbox entry point.

Runs as a module in dev (`python -m src.bridge`, with a console) and as a frozen
**windowed** exe for distribution (no console window -- it lives in the system
tray). In windowed mode there's no console, so:
  - stdout/stderr are redirected to a logfile next to the exe (prints would
    otherwise crash, since PyInstaller sets them to None), and
  - a startup failure shows a popup with the error instead of silently vanishing.
"""

import os
import sys
import tempfile
import traceback


def _wants_console():
    """Diagnostic flags need a visible console even in the windowed exe."""
    return any(a in ("--probe", "--list") for a in sys.argv[1:])


def _setup_output():
    """Make output safe in windowed mode. Returns the log path, or None."""
    has_console = sys.stdout is not None

    # Windowed exe + a diagnostic flag: allocate a real console so the live
    # readout is visible (used to discover button names for remapping).
    if getattr(sys, "frozen", False) and not has_console and _wants_console():
        try:
            import ctypes
            ctypes.windll.kernel32.AllocConsole()
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
            sys.stderr = sys.stdout
            sys.stdin = open("CONIN$", "r")
            return None
        except Exception:
            pass

    if getattr(sys, "frozen", False) and not has_console:
        # No console: route all output to a logfile so print() works and the
        # user has something to send us if anything goes wrong.
        for directory in (os.path.dirname(sys.executable), tempfile.gettempdir()):
            try:
                path = os.path.join(directory, "SC2Xbox.log")
                f = open(path, "w", encoding="utf-8", buffering=1)
                sys.stdout = f
                sys.stderr = f
                return path
            except Exception:
                continue
        # Couldn't open a log; swallow output so prints don't crash.
        import io
        sys.stdout = sys.stderr = io.StringIO()
        return None
    # Console present (dev / run.bat): just make status appear immediately.
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    return None


def _popup(title, text):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)  # MB_ICONERROR
    except Exception:
        pass


def _log_tail(path, limit=1500):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[-limit:].strip()
    except Exception:
        return ""


if __name__ == "__main__":
    log_path = _setup_output()
    try:
        from src.bridge import main
        code = main()
    except Exception:
        traceback.print_exc()
        code = 1

    if code != 0:
        # Windowed build: no console to read, so surface the error in a popup.
        if getattr(sys, "frozen", False) and log_path:
            detail = _log_tail(log_path)
            msg = "SC2Xbox couldn't start.\n\n"
            msg += (detail or "Unknown error.")
            msg += f"\n\nFull log: {log_path}"
            _popup("SC2Xbox", msg)
        else:
            try:
                input("\nSomething went wrong (see above). Press Enter to close...")
            except EOFError:
                pass
    sys.exit(code)
