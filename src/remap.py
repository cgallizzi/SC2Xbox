"""Button remapping: physical buttons -> output (logical) buttons.

The input layer reads every *physical* button the controller exposes -- the
standard face/shoulder/d-pad buttons PLUS the Steam Controller's extra grip /
back buttons (paddles, misc). This layer then decides, per output button, which
physical button drives it. Identity by default; a config overrides it.

    state.buttons[OUT] = physical[ remap.get(OUT, OUT) ]

Kept pure (no SDL, no I/O) so it's easy to unit-test.
"""

from .state import BUTTONS

# Every physical source a remap can point at. The first 15 mirror the output
# buttons; the rest are the Steam Controller's extras (grip/back buttons).
PHYSICAL_NAMES = (
    "A", "B", "X", "Y",
    "LB", "RB",
    "BACK", "START", "GUIDE",
    "LS", "RS",
    "DUP", "DDOWN", "DLEFT", "DRIGHT",
    "MISC1", "MISC2",
    "LPADDLE1", "RPADDLE1", "LPADDLE2", "RPADDLE2",
)


def apply_remap(physical, remap_cfg):
    """Return an output-button dict from physical state + a remap config.

    remap_cfg maps OUTPUT button name -> physical source name. Missing entries
    default to identity. A source of "" or "NONE" leaves that output unbound.
    Two outputs may share one physical source.
    """
    out = {}
    for b in BUTTONS:
        src = remap_cfg.get(b, b) if remap_cfg else b
        if not src or str(src).strip().upper() == "NONE":
            out[b] = False
        else:
            out[b] = bool(physical.get(src, False))
    return out


def validate(remap_cfg):
    """Return a list of human-readable problems in a remap config (or [])."""
    problems = []
    valid_sources = set(PHYSICAL_NAMES) | {"", "NONE"}
    for out_btn, src in (remap_cfg or {}).items():
        if out_btn.startswith("comment") or out_btn.startswith("_"):
            continue
        if out_btn not in BUTTONS:
            problems.append(f"unknown output button '{out_btn}'")
        if str(src).strip().upper() not in {s.upper() for s in valid_sources}:
            problems.append(
                f"'{out_btn}' points at unknown source '{src}'"
            )
    return problems
