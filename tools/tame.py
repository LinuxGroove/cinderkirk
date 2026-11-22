#!/usr/bin/env python3
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Tones down the pale stone textures as they go into the pak:

    tools/tame.py DIR      rewrites DIR/<name>.png for each name in PALE

The engine doubles a texture's brightness under a bright lightmap, so pale
flowstone, limestone, plaster and bone went to flat white beside every
lamp (the second review's worst problem). Each of these is scaled to a mean
of at most MEAN and its highlights are rolled off above KNEE, so the grain
stays visible right up to the lamp. Metals, lamps and glowing things are
left alone: they're meant to shine. The baked textures in assets/textures
are untouched, so a new bake needs nothing redone.
"""

import os
import sys

from PIL import Image, ImageStat

PALE = ("cist_lime1", "cist_stone1", "cist_tile1", "kirk_stone1", "kirk_glyph1", "kirk_column1",
        "kirk_trim1", "kirk_crack1", "plaster1", "ossuary1", "crypt_stone1", "sand_mould1")
MEAN = 98
KNEE = 150


def curve(scale):
    def f(v):
        v = v * scale
        if v > KNEE:
            v = KNEE + (v - KNEE) * 0.45
        return int(round(min(v, 255)))
    return f


def tame(path):
    im = Image.open(path)
    mode = im.mode
    rgb = im.convert("RGB")
    mean = sum(ImageStat.Stat(rgb.convert("L").resize((128, 128))).mean)
    lut = curve(min(1.0, MEAN / mean)) if mean else curve(1.0)
    out = rgb.point([lut(v) for v in range(256)] * 3)
    if mode == "RGBA":
        out.putalpha(im.getchannel("A"))
    out.save(path)


def main():
    d = sys.argv[1]
    for name in PALE:
        p = os.path.join(d, name + ".png")
        if os.path.exists(p):
            tame(p)


if __name__ == "__main__":
    main()
