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
import sys
import threading
import time

from . import config
from .input_sdl3 import SDL3Input, ControllerNotFound, list_gamepads


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
    """Continuously print live input so you can confirm the mapping."""
    inp = SDL3Input(cfg)
    print(f"Probing: {inp.name()}")
    print("\nMove sticks/triggers and press buttons. Watch the values change.")
    print("Ctrl+C to stop.\n")
    try:
        while True:
            s = inp.poll()
            pressed = [b for b, v in s.buttons.items() if v]
            line = (f"L({s.lx:+.2f},{s.ly:+.2f}) R({s.rx:+.2f},{s.ry:+.2f}) "
                    f"LT={s.lt:.2f} RT={s.rt:.2f} btns={pressed}")
            sys.stdout.write("\r" + line.ljust(110))
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
        extras = " + mouse" if self.mouse else ""
        print(f"Bridge active: {self.inp.name()}  ->  virtual {mode.upper()} pad{extras}")

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

    def icon_image():
        # A Steam logo (mechanical piston) rendered in Xbox green -- the running
        # joke of "Steam Controller, but for Xbox". Drawn at 4x then downscaled
        # so the curves come out smooth in the tray.
        S = 4
        sz = 64 * S
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        green = (16, 124, 16, 255)   # Xbox green (#107C10)
        white = (255, 255, 255, 255)

        def box(x0, y0, x1, y1):
            return [x0 * S, y0 * S, x1 * S, y1 * S]

        # Green coin background.
        d.ellipse(box(1, 1, 63, 63), fill=green)
        # Connecting rod from the big wheel to the small piston.
        d.line([(24 * S, 24 * S), (47 * S, 47 * S)], fill=white, width=6 * S)
        # Big wheel (ring) upper-left: white disc with a green hole.
        d.ellipse(box(8, 8, 36, 36), fill=white)
        d.ellipse(box(15, 15, 29, 29), fill=green)
        # Small piston lower-right: white disc with a small green hole.
        d.ellipse(box(40, 40, 56, 56), fill=white)
        d.ellipse(box(45, 45, 51, 51), fill=green)

        return img.resize((64, 64), Image.LANCZOS)

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

    menu = pystray.Menu(
        pystray.MenuItem(lambda item: f"SC2Xbox — emulating {bridge.mode.upper()}",
                         None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Emulate: Xbox 360", set_xbox, checked=is_xbox, radio=True),
        pystray.MenuItem("Emulate: DualShock 4", set_ds4, checked=is_ds4, radio=True),
        pystray.Menu.SEPARATOR,
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
    args = p.parse_args(argv)

    if args.list:
        cmd_list()
        return 0

    cfg = config.load()

    if args.probe:
        cmd_probe(cfg)
        return 0

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
