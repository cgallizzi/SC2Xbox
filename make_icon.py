"""Generate icon.ico (and a square logo.png) from logo_src.png.

logo_src.png is the green Steam logo with a transparent background. This crops
the transparent margins, centers it on a square canvas, and emits:
  - logo.png  : 512x512 master used for the tray icon + README
  - icon.ico  : multi-size icon used as the exe's file icon

Run `python make_icon.py` after replacing logo_src.png to refresh both.
"""

from PIL import Image

SRC = "logo_src.png"
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def square_logo():
    im = Image.open(SRC).convert("RGBA")
    bbox = im.getchannel("A").getbbox()  # tight crop to visible pixels
    if bbox:
        im = im.crop(bbox)
    w, h = im.size
    s = max(w, h)
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    canvas.paste(im, ((s - w) // 2, (s - h) // 2), im)
    return canvas


if __name__ == "__main__":
    logo = square_logo()
    logo.resize((512, 512), Image.LANCZOS).save("logo.png")
    logo.resize((256, 256), Image.LANCZOS).save(
        "icon.ico", sizes=[(x, x) for x in ICO_SIZES]
    )
    print("wrote logo.png (512) and icon.ico", ICO_SIZES)
