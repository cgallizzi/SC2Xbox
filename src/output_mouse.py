"""Real Windows mouse-cursor output via SendInput (ctypes, no dependency).

The gamepad output (ViGEm) can't move the OS cursor, so trackpad-as-mouse and
gyro-as-mouse need their own path. This emits relative mouse motion the same way
a physical mouse does, so it works everywhere -- desktop, Game Pass menus, games.
"""

import ctypes
from ctypes import wintypes

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
INPUT_MOUSE = 0


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


class MouseOutput:
    def __init__(self):
        self._send = ctypes.windll.user32.SendInput
        # Sub-pixel accumulator: SendInput takes integer pixels, but trackpad /
        # gyro deltas are often fractional. Carry the remainder so slow motion
        # isn't lost to truncation.
        self._acc_x = 0.0
        self._acc_y = 0.0
        self._left_down = False
        self._right_down = False

    def move(self, dx, dy):
        self._acc_x += dx
        self._acc_y += dy
        ix = int(self._acc_x)
        iy = int(self._acc_y)
        self._acc_x -= ix
        self._acc_y -= iy
        if ix == 0 and iy == 0:
            return
        self._emit(ix, iy, MOUSEEVENTF_MOVE)

    def set_left(self, down):
        if down == self._left_down:
            return
        self._left_down = down
        self._emit(0, 0, MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP)

    def set_right(self, down):
        if down == self._right_down:
            return
        self._right_down = down
        self._emit(0, 0, MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP)

    def _emit(self, dx, dy, flags):
        mi = _MOUSEINPUT(dx, dy, 0, flags, 0, None)
        inp = _INPUT(INPUT_MOUSE)
        inp.mi = mi
        self._send(1, ctypes.byref(inp), ctypes.sizeof(inp))

    def close(self):
        # Release any held buttons so we don't leave the mouse stuck.
        self.set_left(False)
        self.set_right(False)
