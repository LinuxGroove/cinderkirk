#!/usr/bin/env python3
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Cinderkirk's sprites, drawn from fixed seeds into the game's palette:

    tools/sprites.py PALETTE OUT_DIR    writes OUT_DIR/s_explod.spr and s_bubble.spr

The explosion is a burst of slag and steam that cools as it grows: six
64 px frames. The bubble is two 16 px frames of a ring of grey-green water.
Quake sprites are 8-bit: each pixel takes the nearest of the palette's
colours (the fullbright end for the hottest, so the fire glows in the dark)
and 255 is see-through.
"""

import os
import struct
import sys

import numpy as np

SIZE = 64


def palette(path):
    return np.frombuffer(open(path, "rb").read(), np.uint8).reshape(256, 3).astype(float)


def quantise(rgb, alpha, pal, glow):
    """Nearest palette index for each pixel: the fullbright colours (224 up)
    only where `glow` is set, the rest from the ordinary ones."""
    flat = rgb.reshape(-1, 3)
    d = ((flat[:, None, :] - pal[None, :255, :]) ** 2).sum(axis=2)
    lit = d.copy()
    lit[:, :224] = 1e12
    dark = d.copy()
    dark[:, 224:] = 1e12
    idx = np.where(glow.reshape(-1), lit.argmin(axis=1), dark.argmin(axis=1))
    idx[alpha.reshape(-1) < 0.5] = 255
    return idx.astype(np.uint8).reshape(rgb.shape[:2])


def value_noise(n, cells, seed):
    """Smooth noise over an n x n square: a random grid, eased between."""
    rng = np.random.default_rng(seed)
    g = rng.random((cells + 1, cells + 1))
    x = np.linspace(0, cells, n, endpoint=False)
    i = x.astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    a = g[i][:, i] * (1 - f)[None, :] + g[i][:, i + 1] * f[None, :]
    b = g[i + 1][:, i] * (1 - f)[None, :] + g[i + 1][:, i + 1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]


def explosion(pal):
    n = SIZE
    y, x = np.mgrid[0:n, 0:n] + 0.5 - n / 2
    r = np.hypot(x, y) / (n / 2)
    turb = 0.6 * value_noise(n, 4, 1) + 0.3 * value_noise(n, 9, 2) + 0.1 * value_noise(n, 17, 3)
    frames = []
    for k in range(6):
        t = k / 5
        size = 0.45 + 0.5 * t
        edge = size * (0.75 + 0.5 * turb)
        body = np.clip((edge - r) / 0.18, 0, 1)
        # Heat: hottest at the middle and early; a hollow of smoke opens late.
        heat = np.clip((1 - r / max(edge.max(), 1e-3)) * (1.4 - 1.1 * t) + 0.35 * (turb - 0.5), 0, 1)
        holes = value_noise(n, 6, 10 + k) > 1.05 - 0.45 * t
        alpha = body * (~holes)
        ramp = np.array([(40, 34, 30), (90, 40, 20), (190, 70, 20), (240, 140, 40), (255, 220, 120)], float)
        pos = heat * (len(ramp) - 1)
        lo = np.floor(pos).astype(int).clip(0, len(ramp) - 2)
        f = (pos - lo)[..., None]
        rgb = ramp[lo] * (1 - f) + ramp[lo + 1] * f
        glow = heat > 0.35
        frames.append(quantise(rgb, alpha, pal, glow))
    return frames


def bubble(pal):
    n = 16
    y, x = np.mgrid[0:n, 0:n] + 0.5 - n / 2
    r = np.hypot(x, y)
    frames = []
    for k, rad in enumerate((5.0, 5.8)):
        ring = np.clip(1.4 - abs(r - rad), 0, 1)
        shine = ((x + 2.5) ** 2 + (y + 2.5) ** 2 < 2.2).astype(float)
        alpha = np.maximum(ring, shine)
        rgb = np.zeros((n, n, 3)) + (110, 140, 120)
        rgb[shine > 0] = (200, 215, 200)
        frames.append(quantise(rgb, alpha, pal, np.zeros((n, n), bool)))
    return frames


def write_spr(path, frames):
    h, w = frames[0].shape
    out = struct.pack("<4siifiiifi", b"IDSP", 1, 2, float(np.hypot(w, h) / 2), w, h, len(frames), 0.0, 0)
    for f in frames:
        out += struct.pack("<i4i", 0, -w // 2, h // 2, w, h) + f.tobytes()
    with open(path, "wb") as fh:
        fh.write(out)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    pal = palette(sys.argv[1])
    os.makedirs(sys.argv[2], exist_ok=True)
    write_spr(os.path.join(sys.argv[2], "s_explod.spr"), explosion(pal))
    write_spr(os.path.join(sys.argv[2], "s_bubble.spr"), bubble(pal))
    print("sprites in", sys.argv[2])


if __name__ == "__main__":
    main()
