"""Read the 2026 Steam Controller via SDL 3 and fill a GamepadState.

Why SDL 3 (not pygame/SDL 2): the 2026 Steam Controller (USB PID 0x1304) ships
in "lizard mode" -- it presents as a mouse + keyboard and never announces itself
as a joystick. SDL 2 has no driver for it, so pygame sees nothing. SDL 3's
HIDAPI Steam driver knows this device: enabling it disables lizard mode and
exposes a proper gamepad with a standard button/axis mapping (and gyro).

We use SDL 3's high-level *gamepad* API, so the standard buttons/sticks/triggers
map themselves -- no per-unit index guessing. The trackpad surfaces as the right
stick via SDL's mapping; gyro comes from the sensor API.
"""

import ctypes
import time

import sdl3

from .state import GamepadState
from .remap import apply_remap


class ControllerNotFound(Exception):
    pass


# Physical button name -> SDL gamepad button constant name. Includes the Steam
# Controller's extras (grip/back paddles, misc) as remap sources.
_PHYS_SDL = (
    ("A", "SOUTH"), ("B", "EAST"), ("X", "WEST"), ("Y", "NORTH"),
    ("LB", "LEFT_SHOULDER"), ("RB", "RIGHT_SHOULDER"),
    ("BACK", "BACK"), ("START", "START"), ("GUIDE", "GUIDE"),
    ("LS", "LEFT_STICK"), ("RS", "RIGHT_STICK"),
    ("DUP", "DPAD_UP"), ("DDOWN", "DPAD_DOWN"),
    ("DLEFT", "DPAD_LEFT"), ("DRIGHT", "DPAD_RIGHT"),
    ("MISC1", "MISC1"), ("MISC2", "MISC2"),
    ("LPADDLE1", "LEFT_PADDLE1"), ("RPADDLE1", "RIGHT_PADDLE1"),
    ("LPADDLE2", "LEFT_PADDLE2"), ("RPADDLE2", "RIGHT_PADDLE2"),
)


def _phys_button_map():
    """name -> SDL constant, for buttons this SDL build knows about."""
    m = {}
    for name, sdlname in _PHYS_SDL:
        c = getattr(sdl3, "SDL_GAMEPAD_BUTTON_" + sdlname, None)
        if c is not None:
            m[name] = c
    return m


def _deadzone(v, dz):
    if abs(v) < dz:
        return 0.0
    sign = 1.0 if v > 0 else -1.0
    return sign * (abs(v) - dz) / (1.0 - dz)


def init_sdl():
    """Init SDL with the Steam Controller HIDAPI driver enabled. Idempotent."""
    sdl3.SDL_SetHint(b"SDL_JOYSTICK_HIDAPI_STEAM", b"1")
    # Also let the gamepad expose gyro/accel where supported.
    sdl3.SDL_SetHint(b"SDL_JOYSTICK_HIDAPI_STEAM_HOME_LED", b"0")
    if not sdl3.SDL_Init(sdl3.SDL_INIT_GAMEPAD):
        raise ControllerNotFound(
            f"SDL_Init failed: {sdl3.SDL_GetError().decode(errors='ignore')}"
        )


def list_gamepads():
    """Return [(instance_id, name, is_gamepad)] of all detected devices."""
    init_sdl()
    time.sleep(0.4)
    sdl3.SDL_UpdateGamepads()
    count = ctypes.c_int(0)
    pads = sdl3.SDL_GetGamepads(ctypes.byref(count))
    out = []
    for i in range(count.value):
        jid = pads[i]
        name = sdl3.SDL_GetGamepadNameForID(jid)
        out.append((jid, name.decode(errors="ignore") if name else "?", True))
    return out


class SDL3Input:
    def __init__(self, cfg):
        self.cfg = cfg
        init_sdl()
        time.sleep(0.4)  # give SDL a moment to enumerate the HIDAPI device
        sdl3.SDL_UpdateGamepads()
        self.gp = self._open()
        self.phys_map = _phys_button_map()
        # Strip comment/meta keys from the remap config up front.
        self.remap = {k: v for k, v in (cfg.get("remap") or {}).items()
                      if not (k.startswith("comment") or k.startswith("_"))}
        # Physical buttons this specific controller actually reports (for probe).
        self.available = [n for n, c in self.phys_map.items()
                          if sdl3.SDL_GamepadHasButton(self.gp, c)]
        self.physical = {n: False for n in self.phys_map}
        self.state = GamepadState()
        self._last_poll = time.perf_counter()
        self._gyro_ready = self._enable_gyro_if_wanted()

    # --- device selection -------------------------------------------------
    def _open(self):
        count = ctypes.c_int(0)
        pads = sdl3.SDL_GetGamepads(ctypes.byref(count))
        if count.value == 0:
            raise ControllerNotFound(
                "SDL 3 detected no gamepad. Make sure the Steam Controller is "
                "connected (its dongle/USB) and that Steam is NOT running -- "
                "Steam grabs the controller exclusively."
            )
        wanted = (self.cfg.get("device", {}).get("name_contains") or "").lower()
        chosen = pads[0]
        for i in range(count.value):
            jid = pads[i]
            name = sdl3.SDL_GetGamepadNameForID(jid)
            nm = name.decode(errors="ignore").lower() if name else ""
            if not wanted or wanted in nm:
                chosen = jid
                break
        gp = sdl3.SDL_OpenGamepad(chosen)
        if not gp:
            raise ControllerNotFound(
                f"SDL_OpenGamepad failed: "
                f"{sdl3.SDL_GetError().decode(errors='ignore')}"
            )
        return gp

    def name(self):
        n = sdl3.SDL_GetGamepadName(self.gp)
        return n.decode(errors="ignore") if n else "Steam Controller"

    # --- gyro -------------------------------------------------------------
    def _enable_gyro_if_wanted(self):
        gcfg = self.cfg.get("gyro", {})
        if not gcfg.get("enabled"):
            return False
        if not sdl3.SDL_GamepadHasSensor(self.gp, sdl3.SDL_SENSOR_GYRO):
            print("[warn] gyro requested but this controller reports no gyro.")
            return False
        sdl3.SDL_SetGamepadSensorEnabled(self.gp, sdl3.SDL_SENSOR_GYRO, True)
        return True

    def _read_gyro(self):
        """Return (x, y, z) angular velocity in rad/s, or None."""
        if not self._gyro_ready:
            return None
        buf = (ctypes.c_float * 3)()
        ok = sdl3.SDL_GetGamepadSensorData(
            self.gp, sdl3.SDL_SENSOR_GYRO, buf, 3
        )
        if not ok:
            return None
        return (buf[0], buf[1], buf[2])

    def _apply_gyro(self, s):
        gcfg = self.cfg.get("gyro", {})
        if not self._gyro_ready:
            return
        mode = gcfg.get("activation", "hold")
        if mode == "off":
            return
        if mode == "hold":
            hold = gcfg.get("activation_button", "")
            # Gyro ratchet binds to a PHYSICAL button (e.g. a grip paddle), so it
            # works even when that button isn't mapped to any output.
            if hold and not self.physical.get(hold):
                return
        data = self._read_gyro()
        if data is None:
            return
        # SDL gyro: x = pitch rate, y = yaw rate, z = roll rate (rad/s).
        pitch_rate = data[0]
        yaw_rate = data[1]
        if gcfg.get("invert_pitch"):
            pitch_rate = -pitch_rate
        dz = gcfg.get("deadzone", 0.0)
        if abs(yaw_rate) < dz:
            yaw_rate = 0.0
        if abs(pitch_rate) < dz:
            pitch_rate = 0.0

        now = time.perf_counter()
        dt = now - self._last_poll
        if gcfg.get("destination", "right_stick") == "mouse":
            sens = gcfg.get("mouse_sensitivity", 800.0)
            s.mdx += yaw_rate * sens * dt
            s.mdy += pitch_rate * sens * dt
        else:
            sens = gcfg.get("sensitivity", 1.0)
            s.rx = max(-1.0, min(1.0, s.rx + yaw_rate * sens))
            s.ry = max(-1.0, min(1.0, s.ry + pitch_rate * sens))

    # --- per-frame read ---------------------------------------------------
    def poll(self):
        sdl3.SDL_UpdateGamepads()
        s = self.state
        dz = self.cfg.get("tuning", {}).get("stick_deadzone", 0.08)

        s.mdx = s.mdy = 0.0
        s.mouse_left = s.mouse_right = False

        def axis(a):
            return sdl3.SDL_GetGamepadAxis(self.gp, a) / 32767.0

        # Sticks: SDL Y grows downward; flip so +y = up (our convention).
        s.lx = _deadzone(axis(sdl3.SDL_GAMEPAD_AXIS_LEFTX), dz)
        s.ly = _deadzone(-axis(sdl3.SDL_GAMEPAD_AXIS_LEFTY), dz)
        s.rx = _deadzone(axis(sdl3.SDL_GAMEPAD_AXIS_RIGHTX), dz)
        s.ry = _deadzone(-axis(sdl3.SDL_GAMEPAD_AXIS_RIGHTY), dz)

        # Triggers already 0..1.
        s.lt = max(0.0, axis(sdl3.SDL_GAMEPAD_AXIS_LEFT_TRIGGER))
        s.rt = max(0.0, axis(sdl3.SDL_GAMEPAD_AXIS_RIGHT_TRIGGER))

        # Read every physical button (incl. grip/paddles), then let the remap
        # layer decide which physical button drives each output button.
        for name, sdl_btn in self.phys_map.items():
            self.physical[name] = bool(
                sdl3.SDL_GetGamepadButton(self.gp, sdl_btn)
            )
        s.buttons = apply_remap(self.physical, self.remap)

        self._apply_gyro(s)
        self._last_poll = time.perf_counter()
        return s

    def close(self):
        try:
            sdl3.SDL_CloseGamepad(self.gp)
        except Exception:
            pass
        try:
            sdl3.SDL_Quit()
        except Exception:
            pass
