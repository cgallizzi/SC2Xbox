"""'Start with Windows' via the per-user Run registry key (no admin needed).

Adds/removes HKCU\\...\\Run\\SC2Xbox pointing at the exe (or the dev command),
so SC2Xbox launches on login. The registry is the single source of truth, so
the GUI checkbox and any tray toggle stay consistent.
"""

import os
import sys

try:
    import winreg
except ImportError:  # non-Windows / import-time safety
    winreg = None

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE = "SC2Xbox"


def _command():
    """The command Windows should run at login."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    # Dev: launch the module with the same interpreter, from the project root.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return f'"{sys.executable}" -m src.bridge'  # cwd handled by user in dev


def is_enabled():
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            val, _ = winreg.QueryValueEx(k, _VALUE)
            return bool(val)
    except OSError:
        return False


def enable():
    if not winreg:
        return False
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
        winreg.SetValueEx(k, _VALUE, 0, winreg.REG_SZ, _command())
    return True


def disable():
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, _VALUE)
    except FileNotFoundError:
        pass
    except OSError:
        return False
    return True


def set_enabled(on):
    return enable() if on else disable()
