"""Generate icon.ico -- the Steam piston logo in Xbox green.

Run `python make_icon.py` to regenerate icon.ico (used as the exe's file icon).
The tray icon is drawn from the same shapes in src/bridge.py.
"""

from PIL import Image, ImageDraw


def render(px):
    """Render the logo at `px` size with anti-aliasing."""
    S = 4
    sz = px * S
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    green = (16, 124, 16, 255)   # Xbox green (#107C10)
    white = (255, 255, 255, 255)
    k = sz / 64.0

    def box(a, b, c, e):
        return [a * k, b * k, c * k, e * k]

    d.ellipse(box(1, 1, 63, 63), fill=green)
    d.line([(24 * k, 24 * k), (47 * k, 47 * k)], fill=white, width=int(6 * k))
    d.ellipse(box(8, 8, 36, 36), fill=white)
    d.ellipse(box(15, 15, 29, 29), fill=green)
    d.ellipse(box(40, 40, 56, 56), fill=white)
    d.ellipse(box(45, 45, 51, 51), fill=green)
    return img.resize((px, px), Image.LANCZOS)


if __name__ == "__main__":
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base = render(256)
    base.save("icon.ico", sizes=[(s, s) for s in sizes])
    print("wrote icon.ico", sizes)
