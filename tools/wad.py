#!/usr/bin/env python3
"""Make the texture WAD the map compiler reads.

qbsp needs every texture a map names in a WAD2 file, at the size the map is
textured to. Cinderkirk's real textures are 1024 px PNGs the engine loads from
cinder/textures/ at run time; the WAD only holds small stand-ins of them, cut
down to Quake's palette, which fix each texture's size on the walls (128 px
in the WAD is 128 units in the world, so 1024 px is 8 pixels a unit) and give
the light tool a colour for bounced light.

    tools/wad.py PALETTE OUT.wad TEXTURE_DIR [--size 128]

Every PNG in TEXTURE_DIR without a _norm, _gloss, _luma or _rough suffix
becomes a texture. Names starting with # are liquids and go in as *name.
A few tool textures (clip, skip, trigger, sky) are always added.
"""

import argparse
import os
import struct
import sys

import numpy as np
from PIL import Image

SUFFIXES = ("_norm", "_gloss", "_luma", "_rough", "_glow")
FULLBRIGHT_START = 224  # palette entries from here on ignore light


def load_palette(path):
    data = open(path, "rb").read()
    if len(data) != 768:
        sys.exit(f"{path}: a palette is 768 bytes, this is {len(data)}")
    return np.frombuffer(data, dtype=np.uint8).reshape(256, 3).astype(np.int32)


def quantize(rgb, palette, fullbright=False):
    """Nearest palette entry for each pixel, leaving out fullbrights."""
    usable = palette if fullbright else palette[:FULLBRIGHT_START]
    px = rgb.reshape(-1, 1, 3).astype(np.int32)
    # Weighted distance, closer to how the eye judges colour.
    w = np.array([3, 4, 2])
    d = (((px - usable[None, :, :]) ** 2) * w).sum(axis=2)
    return d.argmin(axis=1).astype(np.uint8).reshape(rgb.shape[:2])


def miptex(name, img, palette, fullbright=False):
    """A miptex lump: header, then four mip levels."""
    w, h = img.size
    if w % 16 or h % 16:
        sys.exit(f"{name}: {w}x{h} is not a multiple of 16")
    levels = []
    for i in range(4):
        lw, lh = w >> i, h >> i
        small = img.resize((lw, lh), Image.LANCZOS)
        levels.append(quantize(np.asarray(small)[:, :, :3], palette, fullbright).tobytes())
    head = struct.pack("<16sII", name.encode()[:15], w, h)
    offsets, at = [], 40
    for data in levels:
        offsets.append(at)
        at += len(data)
    return head + struct.pack("<4I", *offsets) + b"".join(levels)


def tool_texture(name, colour, size=64):
    img = Image.new("RGB", (size, size), colour)
    if name == "sky":
        # Quake skies are two halves side by side.
        img = Image.new("RGB", (size * 2, size), colour)
    return img


def write_wad(path, lumps):
    """lumps: list of (name, bytes). WAD2, type 0x44 (miptex)."""
    out = bytearray(b"WAD2" + struct.pack("<II", len(lumps), 0))
    entries = []
    for name, data in lumps:
        entries.append((len(out), len(data), name))
        out += data
        while len(out) % 4:
            out += b"\0"
    dir_at = len(out)
    for at, size, name in entries:
        out += struct.pack("<IIIbbH16s", at, size, size, 0x44, 0, 0, name.encode()[:15])
    struct.pack_into("<I", out, 8, dir_at)
    with open(path, "wb") as f:
        f.write(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("palette")
    ap.add_argument("out")
    ap.add_argument("texture_dir")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--sizes", default="",
                    help="other sizes for some textures: name=px,name=px")
    ap.add_argument("--native", action="store_true",
                    help="keep each image's own size (for WADs of ready-made textures)")
    ap.add_argument("--qpakman-names", action="store_true",
                    help="read plus_, star_ and _fbr in file names as qpakman does")
    ap.add_argument("--no-tools", action="store_true", help="leave out clip, skip, trigger and sky")
    args = ap.parse_args()

    palette = load_palette(args.palette)
    sizes = dict((k, int(v)) for k, v in (p.split("=") for p in args.sizes.split(",") if p))
    lumps = []
    for fn in sorted(os.listdir(args.texture_dir)):
        base, ext = os.path.splitext(fn)
        if ext.lower() != ".png" or base.endswith(SUFFIXES):
            continue
        name = "*" + base[1:] if base.startswith("#") else base
        fullbright = name.startswith("*")
        if args.qpakman_names:
            # LibreQuake's texture folders name files as qpakman reads them.
            if name.endswith("_fbr"):
                name, fullbright = name[:-4], True
            for word, char in (("plus_", "+"), ("star_", "*"), ("minus_", "-")):
                if name.startswith(word):
                    name = char + name[len(word):]
        if len(name) > 15:
            sys.exit(f"{fn}: texture names are 15 characters at most")
        img = Image.open(os.path.join(args.texture_dir, fn)).convert("RGB")
        if not args.native:
            size = sizes.get(name, args.size)
            img = img.resize((size, size), Image.LANCZOS)
        lumps.append((name, miptex(name, img, palette, fullbright)))
    for name, colour in () if args.no_tools else (("clip", (128, 0, 128)), ("skip", (0, 128, 128)),
                         ("trigger", (128, 64, 0)), ("sky", (40, 30, 30))):
        lumps.append((name, miptex(name, tool_texture(name, colour), palette)))
    write_wad(args.out, lumps)
    print(f"{args.out}: {len(lumps)} textures")


if __name__ == "__main__":
    main()
