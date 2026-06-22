"""SC2Xbox settings GUI (separate process).

Launched from the tray's "Settings..." item as its own process, so it's fully
independent of the bridge -- closing this window never stops the bridge. It only
edits config.json (the running bridge watches that file and hot-reloads the
remap) and the 'Start with Windows' registry key.

Deliberately imports no SDL / ViGEm, so it's light and never opens the
controller the bridge already holds.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

from . import config, startup
from .state import BUTTONS
from .remap import PHYSICAL_NAMES

SOURCE_OPTIONS = ["NONE"] + list(PHYSICAL_NAMES)

# Friendly labels for the output buttons.
LABELS = {
    "A": "A", "B": "B", "X": "X", "Y": "Y",
    "LB": "LB (left bumper)", "RB": "RB (right bumper)",
    "BACK": "Back / View", "START": "Start / Menu", "GUIDE": "Guide",
    "LS": "LS (left stick click)", "RS": "RS (right stick click)",
    "DUP": "D-pad Up", "DDOWN": "D-pad Down",
    "DLEFT": "D-pad Left", "DRIGHT": "D-pad Right",
}


def _resource(name):
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, name)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), name)


def run_gui():
    cfg = config.load()
    remap = dict(cfg.get("remap", {}))

    root = tk.Tk()
    root.title("SC2Xbox — Remapping & Settings")
    try:
        root.iconbitmap(_resource("icon.ico"))
    except Exception:
        pass
    root.resizable(False, False)

    pad = {"padx": 8, "pady": 4}
    ttk.Label(root, text="Button remapping",
              font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=4,
                                                   sticky="w", **pad)
    ttk.Label(root,
              text="Each output button (left) is driven by a physical button "
                   "(right). Paddle/grip sources: MISC1, LPADDLE1/2, RPADDLE1/2. "
                   "Pick NONE to disable.",
              wraplength=520, foreground="#555").grid(
        row=1, column=0, columnspan=4, sticky="w", padx=8)

    combos = {}
    # Two columns of rows.
    half = (len(BUTTONS) + 1) // 2
    for i, btn in enumerate(BUTTONS):
        col = 0 if i < half else 2
        r = 2 + (i if i < half else i - half)
        ttk.Label(root, text=LABELS.get(btn, btn)).grid(
            row=r, column=col, sticky="e", padx=(12, 4), pady=2)
        var = tk.StringVar(value=remap.get(btn, btn))
        cb = ttk.Combobox(root, textvariable=var, values=SOURCE_OPTIONS,
                          width=12, state="readonly")
        cb.grid(row=r, column=col + 1, sticky="w", padx=(0, 12), pady=2)
        combos[btn] = var

    optrow = 2 + half
    ttk.Separator(root, orient="horizontal").grid(
        row=optrow, column=0, columnspan=4, sticky="ew", pady=8)

    ttk.Label(root, text="Options",
              font=("Segoe UI", 11, "bold")).grid(
        row=optrow + 1, column=0, columnspan=4, sticky="w", padx=8)

    # Output mode.
    ttk.Label(root, text="Emulate:").grid(row=optrow + 2, column=0, sticky="e",
                                          padx=(12, 4))
    mode_var = tk.StringVar(value=cfg.get("output", {}).get("mode", "xbox"))
    mode_frame = ttk.Frame(root)
    mode_frame.grid(row=optrow + 2, column=1, columnspan=3, sticky="w")
    ttk.Radiobutton(mode_frame, text="Xbox 360", variable=mode_var,
                    value="xbox").pack(side="left")
    ttk.Radiobutton(mode_frame, text="DualShock 4", variable=mode_var,
                    value="ds4").pack(side="left", padx=12)

    # Start with Windows.
    start_var = tk.BooleanVar(value=startup.is_enabled())
    ttk.Checkbutton(root, text="Start SC2Xbox with Windows",
                    variable=start_var).grid(
        row=optrow + 3, column=0, columnspan=4, sticky="w", padx=12, pady=4)

    status = ttk.Label(root, text="", foreground="#0a7d0a")
    status.grid(row=optrow + 4, column=0, columnspan=4, sticky="w", padx=8)

    def do_save():
        new_remap = dict(remap)  # keep "comment"
        for btn, var in combos.items():
            new_remap[btn] = var.get()
        cfg["remap"] = new_remap
        cfg.setdefault("output", {})["mode"] = mode_var.get()
        try:
            config.save(cfg)
            startup.set_enabled(start_var.get())
            status.config(text="Saved ✓  changes apply live; the bridge "
                               "keeps running.")
        except Exception as e:
            status.config(text=f"Save failed: {e}", foreground="#b00")

    def do_reset():
        for btn, var in combos.items():
            var.set(btn)
        status.config(text="Reset to defaults (not saved yet).",
                      foreground="#555")

    btnrow = ttk.Frame(root)
    btnrow.grid(row=optrow + 5, column=0, columnspan=4, sticky="ew", padx=8,
                pady=8)
    ttk.Button(btnrow, text="Save & Apply", command=do_save).pack(side="left")
    ttk.Button(btnrow, text="Reset to defaults", command=do_reset).pack(
        side="left", padx=8)
    ttk.Button(btnrow, text="Close", command=root.destroy).pack(side="right")

    ttk.Label(root,
              text="Closing this window does NOT stop the bridge — it keeps "
                   "running in the tray.",
              foreground="#888").grid(row=optrow + 6, column=0, columnspan=4,
                                      sticky="w", padx=8, pady=(0, 8))

    root.update_idletasks()
    # Bring the settings window to the front when opened from the tray.
    root.lift()
    root.attributes("-topmost", True)
    root.after(400, lambda: root.attributes("-topmost", False))
    root.focus_force()
    root.mainloop()


if __name__ == "__main__":
    run_gui()
