#!/usr/bin/env python3
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Finds creatures, items and starts whose origin is inside a solid brush
(world or a door, button or wall), which the engine leaves stuck or drops:

    tools/stuck.py [MAP ...]      every maps_src/*.py when none are given

A censer-bearer inside a brake's rod once jammed the button so the finale
couldn't end. Exits 1 if anything is stuck.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKED = ("monster_", "item_", "weapon_", "info_player")
SOLID = ("func_door", "func_button", "func_wall", "func_plat", "func_train", "func_door_secret")


def load(name):
    path = os.path.join(ROOT, "maps_src", name + ".py")
    spec = importlib.util.spec_from_file_location("map_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build()


def inside(p, b):
    x, y, z = p
    return b.x0 < x < b.x1 and b.y0 < y < b.y1 and b.z0 < z < b.z1


def stuck(level):
    boxes = [b for b in level.world_brushes() if not b.tex.startswith("*")]
    for e in level.entities:
        if e.classname in SOLID:
            boxes += e.brushes
    found = []
    for e in level.entities:
        o = e.keys.get("origin")
        if o is None or not e.classname.startswith(CHECKED):
            continue
        p = tuple(float(v) for v in (o.split() if isinstance(o, str) else o))
        p = (p[0], p[1], p[2] + 1)     # an item stands on the floor: just above its origin is free
        hit = next((b for b in boxes if inside(p, b)), None)
        if hit:
            found.append((e.classname, p, hit.tex))
    return found


def main():
    names = sys.argv[1:] or sorted(f[:-3] for f in os.listdir(os.path.join(ROOT, "maps_src")) if f.endswith(".py"))
    bad = 0
    for name in names:
        for cls, p, tex in stuck(load(name)):
            bad += 1
            print(f"{name}: {cls} at ({p[0]:g}, {p[1]:g}, {p[2]:g}) is inside a {tex} brush")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
