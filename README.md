<p align="center">
  <img src="logo.png" alt="SC2Xbox" width="160">
</p>

<h1 align="center">SC2Xbox — Steam Controller Bridge</h1>

Use the **2026 Steam Controller** in apps that only accept standard gamepads —
**Xbox PC app / PC Game Pass** (Forza, etc.), Epic, GOG, EA, Ubisoft, emulators,
anything that speaks XInput or DualShock 4.

> Turns the new Steam Controller into a virtual Xbox 360 or DualShock 4 pad that
> every PC gaming client recognizes — no Steam required.

## Download (easiest)

Grab **`SC2Xbox.exe`** from the [Releases page](https://github.com/cgallizzi/SC2Xbox/releases),
then:

1. Install the [ViGEmBus driver](https://github.com/nefarius/ViGEmBus/releases) once.
2. **Close Steam** (it grabs the controller exclusively).
3. Run `SC2Xbox.exe`. It runs **in the system tray — no window**. A notification
   confirms it's running; the green Steam icon (check the hidden-icons **^** area)
   lets you switch Xbox ⇄ DS4 or quit. There's nothing to keep open.
4. Launch your game from Game Pass / wherever.

No Python needed — the exe bundles everything. If it ever fails to start, it
shows a popup and writes `SC2Xbox.log` next to the exe. To run from source
instead, see **Build from source** below.

## Why this is needed

The new Steam Controller has **no native XInput support**, and out of the box it
sits in **"lizard mode"** — presenting to Windows as a *mouse + keyboard*, never
as a gamepad. So non-Steam clients (especially the Xbox app / PC Game Pass) see
no controller at all. Steam Input can route it to non-Steam games launched
*through* Steam, but that path **can't reach Game Pass / Microsoft Store apps**.

This bridge fixes that:

```
Steam Controller   →  SDL 3   →  bridge  →  ViGEmBus       →  Windows sees
 (lizard mode)        disables    normalize   virtual Xbox360    a standard Xbox
                      lizard,                  OR DS4 pad         (or DS4) pad
                      exposes a                                       ↓
                      real gamepad                       Game Pass / any client
```

**SDL 3 is the key piece.** Its HIDAPI Steam driver recognizes the 2025
controller, disables lizard mode, and exposes a proper gamepad with a standard
button/stick/trigger mapping plus gyro. (SDL 2 / pygame can't see this device at
all — that's a dead end for the new controller.) The bridge then mirrors that
into a virtual **Xbox 360** or **DualShock 4** pad via ViGEmBus, switchable from
the tray.

## Important: close Steam while using this

When Steam is running it grabs the controller **exclusively** and hides it from
everything else, including this bridge. So **close Steam** (or disable Steam
Input for this controller) before running. If `run.bat --list` shows nothing,
Steam is almost certainly holding it.

## Build from source

1. Install **Python 3.10+** ([python.org](https://www.python.org/downloads/),
   tick *Add python.exe to PATH*).
2. Double-click **`install.bat`** (creates a `.venv`, installs deps). SDL 3 and
   the ViGEmBus driver download/install automatically on first run.
3. If you get a ViGEmBus error, install it from
   [ViGEmBus releases](https://github.com/nefarius/ViGEmBus/releases).
4. Run from source with `run.bat`, or build your own exe with **`build_exe.bat`**
   (output: `dist\SC2Xbox.exe`).

## Usage

| Command | What it does |
| --- | --- |
| `run.bat --list` | List controllers SDL 3 sees (should show **Steam Controller**) |
| `run.bat` | Start the bridge (Xbox mode + tray icon) |
| `run.bat --mode ds4` | Start in DualShock 4 mode |
| `run.bat --probe` | Live-print sticks/triggers/buttons to confirm the mapping |
| `run.bat --no-tray` | Run headless |

The window now **stays open** and prints `Bridge active: Steam Controller -> virtual XBOX pad`.
Leave it running while you play. The tray icon switches **Xbox 360 ⇄ DualShock 4**
and quits.

### Typical flow for Game Pass / Forza

1. Close Steam.
2. `run.bat` — confirm it prints `Bridge active`.
3. Launch the game from the Xbox / Game Pass app. It now sees a standard Xbox
   controller.

If a game still fights between two controllers (sees both the virtual pad *and*
the physical device), the fix is **HidHide** to cloak the physical controller —
ask and I'll wire it in.

## Gyro aiming

Off by default. Enable it in `config.json` (copy `config.default.json` first):

```json
"gyro": {
  "enabled": true,
  "destination": "right_stick",   // or "mouse"
  "activation": "hold",            // "always", "hold", or "off"
  "activation_button": "LB",       // logical button to hold for "gyro ratchet"
  "sensitivity": 0.5,
  "invert_pitch": false
}
```

`"hold"` is the classic **gyro ratchet** — aim only steers while you hold the
chosen button, so the controller can rest without drifting. Button names:
`A B X Y LB RB BACK START GUIDE LS RS DUP DDOWN DLEFT DRIGHT`.

## Config

With SDL 3, standard buttons/sticks/triggers/d-pad **and the trackpad (mapped to
the right stick)** are handled automatically — no per-unit index tuning. The only
things you'd normally touch in `config.json`:

- `output.mode` — `xbox` or `ds4` startup default
- `gyro` — as above
- `tuning.stick_deadzone` — raise if you get stick drift

## Project layout

```
steam-controller-bridge/
  install.bat / run.bat        setup + launcher
  requirements.txt
  config.default.json          settings (copy to config.json to customize)
  src/
    bridge.py                  main loop, CLI, tray, runtime Xbox/DS4 switch
    input_sdl3.py              SDL 3 read (disables lizard mode) -> normalized state
    output_vgamepad.py         normalized state -> virtual Xbox360 / DS4 (ViGEm)
    output_mouse.py            normalized state -> real mouse cursor (gyro->mouse)
    state.py                   the normalized GamepadState shared across the bridge
    config.py                  load/save config
```

## Status / roadmap

- [x] SDL 3 input — detects the 2025 controller, disables lizard mode
- [x] Emulate Xbox 360 & DS4, runtime switching, tray UI
- [x] Verified end-to-end on real hardware: controller → virtual Xbox pad in Windows
- [x] Gyro aiming → right stick / mouse, hold-to-aim ratchet
- [ ] Trackpad → mouse (currently the pad maps to the right stick via SDL)
- [ ] Optional HidHide integration to cloak the physical device from games
- [ ] Per-game profiles

## Prior art

[SteamlessController](https://github.com/ddeverill/SteamlessController) (Xbox 360
only) and [Steam-Controller-Remapper](https://github.com/CommonMugger/Steam-Controller-Remapper)
solve the same problem; this project adds switchable Xbox/DS4 output and gyro.

## Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Good first issues: trackpad
→ mouse, HidHide integration, per-game profiles, original 2015 SC support.

## License

[MIT](LICENSE). Not affiliated with or endorsed by Valve. "Steam", "Xbox", and
"DualShock" are trademarks of their respective owners, used here only to describe
compatibility.
