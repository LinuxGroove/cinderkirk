#!/usr/bin/env python3
"""The Cinderkirk icon: the foundry mark, glowing, on a bronze-rimmed coal.

    tools/make_icon.py        writes snap/gui/cinderkirk.png and icon.png (512 px)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import menu_art  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
S = 512


def main():
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    disc = Image.new("L", (S, S))
    ImageDraw.Draw(disc).ellipse((8, 8, S - 8, S - 8), fill=255)
    ys, xs = np.mgrid[0:S, 0:S] / S
    r = np.hypot(xs - 0.5, ys - 0.62)
    base = np.stack([60 + 120 * np.clip(1 - r * 1.8, 0, 1),
                     22 + 40 * np.clip(1 - r * 2, 0, 1),
                     14 + 10 * np.clip(1 - r * 2, 0, 1)], axis=2)
    coal = Image.fromarray(base.astype(np.uint8), "RGB")
    out.paste(coal, (0, 0), disc)
    ring = Image.new("L", (S, S))
    ImageDraw.Draw(ring).ellipse((8, 8, S - 8, S - 8), outline=255, width=18)
    out.paste((196, 132, 60, 255), (0, 0), ring)
    mask = Image.open(os.path.join(ROOT, "assets_src/materials/glyph_mask.png")).convert("L")
    # The mark sits in a square frame on the glyph stone; keep the round part.
    w = mask.size[0]
    mask = mask.crop((int(w * 0.14), int(w * 0.14), int(w * 0.86), int(w * 0.86))).resize((S - 120, S - 120), Image.LANCZOS)
    keep = Image.new("L", mask.size)
    ImageDraw.Draw(keep).ellipse((0, 0, mask.size[0], mask.size[1]), fill=255)
    mask = Image.fromarray(np.minimum(np.asarray(mask), np.asarray(keep)))
    menu_art.SCALE = 4
    hot = menu_art.colour_letters(mask)
    out.alpha_composite(hot, (60, 60))
    for path in ("snap/gui/cinderkirk.png", "icon.png"):
        out.save(os.path.join(ROOT, path))
        print(path)


if __name__ == "__main__":
    main()
