"""Load/save the JSON config that drives the bridge.

Keeping settings in a data file (not code) lets users tweak gyro/output without
touching Python. Works both when run from source and as a PyInstaller exe.
"""

import json
import os
import sys


def _paths():
    """Return (default_config_path, user_config_path).

    Frozen exe: the bundled default lives in PyInstaller's extraction dir
    (sys._MEIPASS); the user's editable override sits next to the .exe so they
    can actually find and edit it. From source: both live in the project root.
    """
    if getattr(sys, "frozen", False):
        default = os.path.join(getattr(sys, "_MEIPASS", ""), "config.default.json")
        user = os.path.join(os.path.dirname(sys.executable), "config.json")
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default = os.path.join(root, "config.default.json")
        user = os.path.join(root, "config.json")
    return default, user


DEFAULT_PATH, USER_PATH = _paths()


def load():
    """Load the user's config.json if present, else the bundled defaults."""
    path = USER_PATH if os.path.exists(USER_PATH) else DEFAULT_PATH
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_path"] = path
    return cfg


def save(cfg):
    """Write the user's config (always to config.json next to the exe/project)."""
    out = {k: v for k, v in cfg.items() if not k.startswith("_")}
    with open(USER_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    return USER_PATH
