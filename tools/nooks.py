#!/usr/bin/env python3
"""Where a level has room for a secret closet (mapkit's Level.nook).

For each room (an air box at least 192 across) and each of its walls, it
tries a closet behind the middle stretch of the wall and keeps those whose
closet, with a wall's thickness round it, stays clear of every other air
box, whose wall there is whole, and with nothing built in front. Prints
the candidates, farthest from the player start first.

    tools/nooks.py foundry4 [more maps]
"""
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import Box  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "maps_src")
W = D = H = 96
T = 32


def load(name):
    spec = importlib.util.spec_from_file_location("map_" + name, os.path.join(ROOT, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build()


def closet(x, y, z, side):
    """The crack, the closet with its walls, and the stretch in front of it."""
    sg = 1 if side in "ne" else -1
    if side in "ns":
        crack = Box(x - W / 2, min(y, y + sg * T), z, x + W / 2, max(y, y + sg * T), z + H)
        a, b = sorted((y + sg * T, y + sg * (T + D)))
        shell = Box(x - W / 2 - T, a - T, z - T, x + W / 2 + T, b + T, z + H + T)
        front = Box(x - W / 2, min(y, y - sg * 80), z, x + W / 2, max(y, y - sg * 80), z + H)
    else:
        crack = Box(min(x, x + sg * T), y - W / 2, z, max(x, x + sg * T), y + W / 2, z + H)
        a, b = sorted((x + sg * T, x + sg * (T + D)))
        shell = Box(a - T, y - W / 2 - T, z - T, b + T, y + W / 2 + T, z + H + T)
        front = Box(min(x, x - sg * 80), y - W / 2, z, max(x, x - sg * 80), y + W / 2, z + H)
    return crack, shell, front


def candidates(L):
    start = next((e.keys["origin"] for e in L.entities if e.classname == "info_player_start"), (0, 0, 0))
    solid = [d for d in L.details if not d.tex.startswith("*")]
    liquid = [d for d in L.details if d.tex.startswith("*")]
    brushes = [b for e in L.entities for b in e.brushes]
    out = []
    for room in L.air:
        if room.x1 - room.x0 < 192 or room.y1 - room.y0 < 192 or room.z1 - room.z0 < H:
            continue
        for side in "nsew":
            axis, at = {"n": ("y", room.y1), "s": ("y", room.y0), "e": ("x", room.x1), "w": ("x", room.x0)}[side]
            levels = {room.z0}
            for d in solid:
                lo, hi = (d.y0, d.y1) if axis == "y" else (d.x0, d.x1)
                if lo - 1 <= at <= hi + 1 and room.z0 < d.z1 <= room.z1 - H:
                    levels.add(d.z1)
            if axis == "y":
                spots = [(x, at) for x in range(int(room.x0 + 64 + W / 2), int(room.x1 - 64 - W / 2) + 1, 32)]
            else:
                spots = [(at, y) for y in range(int(room.y0 + 64 + W / 2), int(room.y1 - 64 - W / 2) + 1, 32)]
            for z in sorted(levels):
                for x, y in spots:
                    crack, shell, front = closet(x, y, z, side)
                    if any(o is not room and (o.overlaps(shell) or o.overlaps(crack)) for o in L.air):
                        continue
                    if any(d.overlaps(front) or d.overlaps(crack) for d in L.details):
                        continue
                    if any(b.overlaps(front) or b.overlaps(shell) for b in brushes):
                        continue
                    # Something to stand on in front: the room's floor with no liquid on it, or a ledge.
                    if z != room.z0 and not any(d.z1 == z and d.x0 <= front.x0 and d.x1 >= front.x1
                                                and d.y0 <= front.y0 and d.y1 >= front.y1 for d in solid):
                        continue
                    if any(d.overlaps(Box(front.x0, front.y0, z - 64, front.x1, front.y1, z + 1)) for d in liquid):
                        continue
                    dist = ((x - start[0]) ** 2 + (y - start[1]) ** 2) ** 0.5
                    out.append((dist, x, y, z, side))
    out.sort(reverse=True)
    return out


def main():
    for name in sys.argv[1:]:
        c = candidates(load(name))
        print(name, len(c))
        for dist, x, y, z, side in c[:6]:
            print(f'   L.nook({x:g}, {y:g}, {z:g}, "{side}")   # {dist:.0f} from the start')


if __name__ == "__main__":
    main()
