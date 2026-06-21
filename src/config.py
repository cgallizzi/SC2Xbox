"""Load/save the JSON config that drives the input->logical mapping.

Keeping the mapping in a data file (not code) is what lets us tune the bridge to
your specific controller from the live probe without touching Python.
"""

import json
import os

# Project root = parent of this src/ folder.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(ROOT, "config.default.json")
USER_PATH = os.path.join(ROOT, "config.json")


def load():
    """Load config.json if present, otherwise fall back to the defaults."""
    path = USER_PATH if os.path.exists(USER_PATH) else DEFAULT_PATH
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_path"] = path
    return cfg


def save(cfg):
    """Write the user's config (always to config.json, never the defaults)."""
    out = {k: v for k, v in cfg.items() if not k.startswith("_")}
    with open(USER_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    return USER_PATH
