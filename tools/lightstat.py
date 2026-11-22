#!/usr/bin/env python3
"""How bright each compiled level is, from its lightmaps.

Reads the world's faces from build/maps/<map>.bsp and their coloured light
from the .lit, and prints the mean light (0..255, where 128 shows a texture
at full brightness) on floors and on walls, and how much of the floor is
near black (below DARK). Floors are what a player reads a room by: when
they are black the room looks empty.

    tools/lightstat.py [map ...]      # default: every built level
"""
import glob
import math
import os
import struct
import sys

DARK = 24
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "maps")


def lumps(data):
    return [struct.unpack_from("<ii", data, 4 + 8 * i) for i in range(15)]


def stat(name):
    bsp = open(os.path.join(ROOT, name + ".bsp"), "rb").read()
    lit = open(os.path.join(ROOT, name + ".lit"), "rb").read()[8:]
    L = lumps(bsp)

    def rows(i, fmt):
        off, size = L[i]
        n = struct.calcsize(fmt)
        return [struct.unpack_from(fmt, bsp, off + k * n) for k in range(size // n)]

    planes = rows(1, "<4fi")
    verts = rows(3, "<3f")
    texinfo = rows(6, "<8f2i")
    faces = rows(7, "<hhihh4Bi")
    edges = rows(12, "<2H")
    surfedges = [s[0] for s in rows(13, "<i")]
    world = rows(14, "<9f7i")[0]
    first, count = world[-2], world[-1]

    floor, wall = [], []
    for f in faces[first:first + count]:
        plane, side, fe, ne, ti, s0, s1, s2, s3, ofs = f
        if ofs < 0 or s0 == 255:
            continue
        nz = planes[plane][2] * (-1 if side else 1)
        t = texinfo[ti]
        pts = []
        for k in range(ne):
            e = surfedges[fe + k]
            pts.append(verts[edges[e][0]] if e >= 0 else verts[edges[-e][1]])
        ext = []
        for a in (0, 4):
            vals = [p[0] * t[a] + p[1] * t[a + 1] + p[2] * t[a + 2] + t[a + 3] for p in pts]
            ext.append(math.ceil(max(vals) / 16) - math.floor(min(vals) / 16) + 1)
        n = ext[0] * ext[1]
        samples = [(lit[3 * (ofs + k)] * 3 + lit[3 * (ofs + k) + 1] * 6 + lit[3 * (ofs + k) + 2]) / 10
                   for k in range(n) if 3 * (ofs + k) + 2 < len(lit)]
        (floor if nz > 0.7 else wall if abs(nz) <= 0.7 else []).extend(samples)

    def mean(v):
        return sum(v) / len(v) if v else 0

    return mean(floor), mean(wall), (sum(1 for v in floor if v < DARK) / len(floor) if floor else 0)


def main():
    names = sys.argv[1:] or sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(ROOT, "*.lit")))
    print(f"{'level':12s} {'floor':>6s} {'walls':>6s} {'dark floor':>10s}")
    for n in names:
        fl, wa, dark = stat(n)
        print(f"{n:12s} {fl:6.1f} {wa:6.1f} {dark:10.0%}")


if __name__ == "__main__":
    main()
