"""Steam Controller Bridge -- main entry point.

Usage (via run.bat or `python -m src.bridge`):
    --probe        Live-print every axis/button/hat the controller reports.
                   Use this to fill in config.json for your unit.
    --list         List all detected joysticks and exit.
    --mode xbox    Start emulating an Xbox 360 pad (default).
    --mode ds4     Start emulating a DualShock 4 pad.
    --no-tray      Run headless (no system-tray icon).

The bridge reads the Steam Controller, normalizes its input, and feeds a virtual
Xbox/DS4 pad that Windows -- and clients like Game Pass -- accept.
"""

import argparse
import os
import sys
import threading
import time

from . import config
from .input_sdl3 import SDL3Input, ControllerNotFound, list_gamepads


def _resource(name):
    """Path to a bundled data file, both as a PyInstaller exe and from source."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, name)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), name)


def cmd_list():
    pads = list_gamepads()
    if not pads:
        print("No controllers detected by SDL 3.")
        print("Tip: connect the Steam Controller (dongle/USB) and CLOSE Steam "
              "(it grabs the device exclusively).")
        return
    print(f"{len(pads)} controller(s) detected:\n")
    for jid, name, _ in pads:
        print(f"  id={jid}  {name}")


def cmd_probe(cfg):
    """Continuously print live PHYSICAL input so you can build a remap."""
    inp = SDL3Input(cfg)
    print(f"Probing: {inp.name()}")
    print(f"Physical buttons on this controller: {', '.join(inp.available)}")
    print("\nPress each button to learn its name (esp. the grip/paddle buttons),")
    print("then use those names in the \"remap\" section of config.json.")
    print("Ctrl+C to stop.\n")
    try:
        while True:
            inp.poll()
            pressed = [b for b, v in inp.physical.items() if v]
            s = inp.state
            line = (f"L({s.lx:+.2f},{s.ly:+.2f}) R({s.rx:+.2f},{s.ry:+.2f}) "
                    f"LT={s.lt:.2f} RT={s.rt:.2f} pressed={pressed}")
            sys.stdout.write("\r" + line.ljust(115))
            sys.stdout.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nDone.")
    finally:
        inp.close()


class Bridge:
    """Owns the input reader and the (swappable) output backend."""

    def __init__(self, cfg, mode):
        from .output_vgamepad import make_output
        from .output_mouse import MouseOutput
        self.cfg = cfg
        self.inp = SDL3Input(cfg)
        self.mode = mode
        self._make_output = make_output
        self.out = make_output(mode)
        # Mouse output is only meaningful if a processor routes to it.
        self.mouse = MouseOutput() if self._mouse_enabled(cfg) else None
        self._lock = threading.Lock()
        self._pending_mode = None
        self.running = True
        self._cfg_mtime = self._cfg_stamp()
        self._cfg_check_at = 0.0
        extras = " + mouse" if self.mouse else ""
        print(f"Bridge active: {self.inp.name()}  ->  virtual {mode.upper()} pad{extras}")

    @staticmethod
    def _cfg_stamp():
        try:
            return os.path.getmtime(config.USER_PATH)
        except OSError:
            return 0.0

    def _maybe_reload_config(self):
        """Hot-reload config.json when the GUI saves it (checked ~1/sec)."""
        now = time.monotonic()
        if now < self._cfg_check_at:
            return
        self._cfg_check_at = now + 1.0
        m = self._cfg_stamp()
        if m == self._cfg_mtime:
            return
        self._cfg_mtime = m
        try:
            newcfg = config.load()
            self.cfg = newcfg
            self.inp.update_config(newcfg)
            newmode = newcfg.get("output", {}).get("mode", self.mode)
            if newmode != self.mode:
                self.request_mode(newmode)
            print("[config] reloaded from config.json (live)")
        except Exception as e:
            print(f"[config] reload failed: {e}")

    @staticmethod
    def _mouse_enabled(cfg):
        tp = cfg.get("trackpad", {})
        gy = cfg.get("gyro", {})
        return (
            (tp.get("enabled") and tp.get("destination") == "mouse")
            or (gy.get("enabled") and gy.get("destination") == "mouse")
            or (tp.get("enabled") and tp.get("click_on_press_button", -1) >= 0)
        )

    def request_mode(self, mode):
        """Thread-safe request (from tray) to switch output type."""
        with self._lock:
            self._pending_mode = mode

    def _maybe_switch(self):
        with self._lock:
            pending = self._pending_mode
            self._pending_mode = None
        if pending and pending != self.mode:
            try:
                self.out.close()
            except Exception:
                pass
            self.out = self._make_output(pending)
            self.mode = pending
            print(f"\n[switched] now emulating virtual {pending.upper()} pad")

    def run(self):
        period = 1.0 / max(30, self.cfg["tuning"].get("poll_hz", 250))
        try:
            while self.running:
                self._maybe_switch()
                self._maybe_reload_config()
                state = self.inp.poll()
                self.out.apply(state)
                if self.mouse:
                    self.mouse.move(state.mdx, state.mdy)
                    self.mouse.set_left(state.mouse_left)
                    self.mouse.set_right(state.mouse_right)
                time.sleep(period)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        self.running = False
        self.out.close()
        if self.mouse:
            self.mouse.close()
        self.inp.close()


def _start_tray(bridge):
    """Optional system-tray icon to switch Xbox<->DS4 and quit."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception as e:
        print(f"[info] tray unavailable ({e}); running headless. "
              f"Use --mode to choose output, Ctrl+C to quit.")
        return None

    def _drawn_icon():
        # Fallback Steam-piston logo in Xbox green, if logo.png isn't found.
        S = 4
        sz = 64 * S
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        green = (16, 124, 16, 255)
        white = (255, 255, 255, 255)

        def box(x0, y0, x1, y1):
            return [x0 * S, y0 * S, x1 * S, y1 * S]

        d.ellipse(box(1, 1, 63, 63), fill=green)
        d.line([(24 * S, 24 * S), (47 * S, 47 * S)], fill=white, width=6 * S)
        d.ellipse(box(8, 8, 36, 36), fill=white)
        d.ellipse(box(15, 15, 29, 29), fill=green)
        d.ellipse(box(40, 40, 56, 56), fill=white)
        d.ellipse(box(45, 45, 51, 51), fill=green)
        return img.resize((64, 64), Image.LANCZOS)

    def icon_image():
        # Use the real green Steam logo (bundled logo.png); fall back to the
        # drawn version if it can't be loaded.
        try:
            return Image.open(_resource("logo.png")).convert("RGBA")
        except Exception:
            return _drawn_icon()

    def set_xbox(icon, item):
        bridge.request_mode("xbox")

    def set_ds4(icon, item):
        bridge.request_mode("ds4")

    def is_xbox(item):
        return bridge.mode == "xbox"

    def is_ds4(item):
        return bridge.mode == "ds4"

    def on_quit(icon, item):
        bridge.running = False
        icon.stop()

    def open_settings(icon, item):
        # Launch the GUI as a SEPARATE process so it's independent of the bridge.
        import subprocess
        try:
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--gui"]
            else:
                cmd = [sys.executable, "-m", "src.bridge", "--gui"]
            subprocess.Popen(cmd, close_fds=True)
        except Exception as e:
            print(f"[warn] couldn't open settings window: {e}")

    def toggle_startup(icon, item):
        from . import startup
        startup.set_enabled(not startup.is_enabled())

    def startup_checked(item):
        from . import startup
        return startup.is_enabled()

    menu = pystray.Menu(
        pystray.MenuItem(lambda item: f"SC2Xbox — emulating {bridge.mode.upper()}",
                         None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Remap buttons / Settings…", open_settings,
                         default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Emulate: Xbox 360", set_xbox, checked=is_xbox, radio=True),
        pystray.MenuItem("Emulate: DualShock 4", set_ds4, checked=is_ds4, radio=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start with Windows", toggle_startup,
                         checked=startup_checked),
        pystray.MenuItem("Quit", on_quit),
    )
    icon = pystray.Icon("SteamCtrlBridge", icon_image(),
                        "SC2Xbox — Steam Controller Bridge", menu)

    def on_ready(icon):
        # Runs once the tray icon is actually visible.
        icon.visible = True
        try:
            icon.notify(
                "Running in the system tray. There's no window to keep open — "
                "right-click the green Steam icon to switch Xbox/DS4 or quit.",
                "SC2Xbox is running",
            )
        except Exception:
            pass

    t = threading.Thread(target=lambda: icon.run(setup=on_ready), daemon=True)
    t.start()
    print("Tray icon active (system tray / hidden-icons '^' area). "
          "No window needed - quit from the tray icon.")
    return icon


def main(argv=None):
    p = argparse.ArgumentParser(description="Steam Controller Bridge")
    p.add_argument("--probe", action="store_true",
                   help="live-print controller input to build a mapping")
    p.add_argument("--list", action="store_true",
                   help="list detected joysticks and exit")
    p.add_argument("--mode", choices=["xbox", "ds4"], default=None,
                   help="output pad type (overrides config)")
    p.add_argument("--no-tray", action="store_true", help="run without tray icon")
    p.add_argument("--gui", action="store_true",
                   help="open the settings/remapping window (separate process)")
    args = p.parse_args(argv)

    if args.gui:
        from .gui import run_gui
        run_gui()
        return 0

    if args.list:
        cmd_list()
        return 0

    cfg = config.load()

    if args.probe:
        cmd_probe(cfg)
        return 0

    # Warn (don't fail) on a typo'd remap so the user can fix config.json.
    from .remap import validate
    for problem in validate(cfg.get("remap")):
        print(f"[warn] remap: {problem}")

    mode = args.mode or cfg["output"].get("mode", "xbox")

    try:
        bridge = Bridge(cfg, mode)
    except ControllerNotFound as e:
        print(f"[error] {e}")
        return 1
    except Exception as e:
        print(f"[error] failed to start: {e}")
        print("If this is a ViGEmBus error, install the driver -- see README.")
        return 1

    icon = None
    if not args.no_tray:
        icon = _start_tray(bridge)

    bridge.run()
    if icon:
        try:
            icon.stop()
        except Exception:
            pass
    print("Stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
