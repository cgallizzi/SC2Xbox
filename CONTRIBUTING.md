# Contributing to SC2Xbox

Thanks for helping make the 2026 Steam Controller work everywhere!

## Dev setup

```
git clone https://github.com/cgallizzi/SC2Xbox.git
cd SC2Xbox
install.bat          # creates .venv, installs deps
run.bat --list       # confirm SDL 3 sees your controller (close Steam first!)
run.bat              # run from source
```

Requires Python 3.10+ and the [ViGEmBus driver](https://github.com/nefarius/ViGEmBus/releases).

## How it fits together

```
input_sdl3.py   reads the controller via SDL 3 (disables "lizard mode"),
                produces a normalized GamepadState
state.py        the GamepadState shared across the whole bridge
output_*.py     turn a GamepadState into a virtual Xbox/DS4 pad or mouse motion
bridge.py       main loop + CLI + tray + runtime Xbox/DS4 switching
```

To add a feature, you almost always touch exactly one of those files. Keep the
normalized `GamepadState` as the only thing the two sides share.

## Pull requests

- Keep changes focused; one feature/fix per PR.
- Match the existing style (small, commented, no heavy frameworks).
- Test against real hardware when you can, and say what you tested in the PR.
- CI builds the exe on every PR — make sure it stays green.

## Good first issues

- Trackpad → mouse (the pad currently maps to the right stick via SDL).
- Optional [HidHide](https://github.com/nefarius/HidHide) integration to hide the
  physical device from games that double-enumerate.
- Per-game profiles / a small settings GUI.
- Support for the original 2015 Steam Controller.

## Reporting bugs

Open an issue with: Windows version, whether Steam was running, the output of
`run.bat --list`, and what the game did. Controller probe output (`run.bat
--probe`) helps a lot for input bugs.
