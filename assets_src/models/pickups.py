"""Cinderkirk's pickups: health, ammunition, armour, keys and the backpack,
built from primitives in headless Blender and baked to MD3 the way the
creatures are (creatures.py). The weapons' pickups come from weapons.py
with WORLD=1.

    python pickups.py -- <out dir> [resolution] [only=health,key_gold]   (with the bpy wheel)

Built in metres, standing on the floor at z = 0. Health and ammunition stand
in a 1 m square from the origin (the box the game code gives them); armour,
keys and the backpack are centred on it and turn.

Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy first: it makes bmesh importable)
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import creatures as C  # noqa: E402
import weapons as W  # noqa: E402  (the metals and the pieces)

P = Vector
_shade = C.shade


def shade(name):
    g = C.Nodes(bpy.data.materials[name]) if name in ("salve", "glass", "port") else None
    if name == "salve":
        # A red salve that glows a little through the glass.
        n = g.noise(12.0, 3.0, 0.5, seed=21.0)
        return g, g.ramp(n, [(0.3, (0.45, 0.03, 0.02)), (0.7, (0.75, 0.08, 0.04))]), g.ramp(n, [(0.3, (0.25, 0.02, 0.01)), (0.7, (0.5, 0.06, 0.02))])
    if name == "glass":
        return g, (0.32, 0.36, 0.34), None
    if name == "port":
        return g, (0.32, 0.36, 0.34), (0.08, 0.2, 0.16)      # a faint light inside, so it shows in the dark
    return _shade(name)


C.shade = shade


class Pickup(C.Creature):
    def __init__(self, name, spin=False, corner=False):
        super().__init__(name, [("root", None, (0, 0, 0), (0, 0, 0.1))], hull_bottom=0.0)
        self.flags = 8 if spin else 0  # EF_ROTATE
        self.offset = P((0.5, 0.5, 0)) if corner else P((0, 0, 0))

    def put(self, o, material, bevel=0.0, smooth=True):
        bpy.context.view_layer.update()
        o.matrix_world = Matrix.Translation(self.offset) @ o.matrix_world
        if bevel:
            m = o.modifiers.new("bevel", "BEVEL")
            m.width = bevel
            m.segments = 2
            m.limit_method = "ANGLE"
        return self.add(o, material, bone="root", smooth=smooth)

    def done(self):
        C.build(self, [("idle", 1, [(0.0, {})], False, None)])


def crate(p, w, d, h, at=(0, 0)):
    """An iron-bound wooden crate, open at the top, with its floor at h * 0.15."""
    x, y = at
    t = 0.025
    for sx in (-1, 1):
        p.put(W.box(t, h, d, P((x + sx * (w - t) / 2, y, h / 2))), "oak", bevel=0.006)
    for sy in (-1, 1):
        p.put(W.box(w - 2 * t, h, t, P((x, y + sy * (d - t) / 2, h / 2))), "oak", bevel=0.006)
    p.put(W.box(w - 2 * t, 0.02, d - 2 * t, P((x, y, h * 0.15))), "oak")
    for z in (0.06, h - 0.05):  # iron bands
        for sx in (-1, 1):
            p.put(W.box(0.008, 0.04, d + 0.01, P((x + sx * (w / 2 + 0.002), y, z))), "iron")
        for sy in (-1, 1):
            p.put(W.box(w + 0.01, 0.04, 0.008, P((x, y + sy * (d / 2 + 0.002), z))), "iron")


def flask(p, at, r, h):
    """A round-bottomed flask of salve with a cork."""
    x, y = at
    neck = r * 0.38
    prof = [(0.0, 0.0), (r * 0.55, 0.02 * r), (r * 0.95, r * 0.5), (r, r), (r * 0.8, r * 1.6), (neck, r * 2.0),
            (neck, h), (0.0, h)]
    p.put(C.lathe("flask", prof, segs=24, at=(x, y, 0)), "glass")
    liquid = [(0.0, 0.02 * r), (r * 0.5, 0.04 * r), (r * 0.9, r * 0.5), (r * 0.93, r), (r * 0.8, r * 1.35), (0.0, r * 1.35)]
    p.put(C.lathe("salve", [(a * 1.01, b) for a, b in liquid], segs=24, at=(x, y, 0)), "salve")
    p.put(W.rod(P((x, y, h - 0.01)), P((x, y, h + r * 0.5)), neck * 1.15, segs=12), "oak")


def health_small():
    p = Pickup("health_small", corner=True)
    p.put(W.box(0.36, 0.03, 0.3, P((0, 0, 0.015))), "oak", bevel=0.005)
    flask(p, (0.0, 0.0), 0.09, 0.26)
    p.done()


def health():
    p = Pickup("health", corner=True)
    crate(p, 0.5, 0.36, 0.18)
    for x in (-0.12, 0.0, 0.12):
        flask(p, (x, 0.0), 0.06 if x else 0.075, 0.3 if x else 0.36)
    p.done()


def health_mega():
    p = Pickup("health_mega", corner=True, spin=False)
    p.put(W.rod(P((0, 0, 0)), P((0, 0, 0.05)), 0.24, segs=32), "oak", bevel=0.005)
    flask(p, (0.0, 0.0), 0.17, 0.52)
    for i in range(6):  # a brass cage
        a = math.tau * i / 6
        bot, top = P((0.2 * math.cos(a), 0.2 * math.sin(a), 0.05)), P((0.07 * math.cos(a), 0.07 * math.sin(a), 0.5))
        p.put(W.rod(bot, P((0.2 * math.cos(a), 0.2 * math.sin(a), 0.3)), 0.008, segs=8), "brass")
        p.put(W.rod(P((0.2 * math.cos(a), 0.2 * math.sin(a), 0.3)), top, 0.008, segs=8), "brass")
    for z, r in ((0.06, 0.2), (0.3, 0.2), (0.5, 0.07)):
        p.put(W.ring(P((0, 0, z)), P((0, 0, 1)), r, 0.01), "brass")
    p.done()


def shells(big=False):
    p = Pickup("shells_big" if big else "shells", corner=True)
    w, d, h = (0.62, 0.44, 0.24) if big else (0.44, 0.32, 0.18)
    crate(p, w, d, h)
    n, m = (7, 5) if big else (5, 3)
    for i in range(n):
        for j in range(m):
            x, y = (i - (n - 1) / 2) * (w - 0.08) / n, (j - (m - 1) / 2) * (d - 0.08) / m
            p.put(W.rod(P((x, y, h * 0.15)), P((x, y, h + 0.02)), 0.026, segs=12), "copper")
            p.put(W.rod(P((x, y, h + 0.02)), P((x, y, h + 0.03)), 0.03, segs=12), "brass")
    p.done()


def slag(big=False):
    p = Pickup("slag_big" if big else "slag", corner=True)
    pots = [(-0.16, 0.0, 0.17), (0.16, 0.02, 0.15)] if big else [(0.0, 0.0, 0.17)]
    for x, y, r in pots:
        prof = [(0.0, 0.0), (r * 0.7, 0.0), (r * 0.9, 0.05), (r, r * 1.3), (r * 1.08, r * 1.5), (r * 0.95, r * 1.5),
                (r * 0.88, r * 1.35), (0.0, r * 1.35)]
        p.put(C.lathe("pot", prof, segs=28, at=(x, y, 0)), "iron")
        top = C.prim("uv_sphere", radius=r * 0.86, segments=24, ring_count=10, location=(x, y, r * 1.3))
        top.scale = (1, 1, 0.18)
        p.put(top, "slag")
        for s in (-1, 1):
            p.put(W.ring(P((x + s * r * 1.05, y, r * 1.2)), P((0, 1, 0)), r * 0.22, 0.012), "iron")
    p.done()


def iron(big=False):
    p = Pickup("iron_big" if big else "iron", corner=True)
    w, d, h = (0.6, 0.46, 0.22) if big else (0.44, 0.34, 0.18)
    crate(p, w, d, h)
    r = 0.055
    n, m = (5, 4) if big else (4, 3)
    for layer in range(2 if big else 1):
        for i in range(n - layer):
            for j in range(m - layer):
                x = (i - (n - layer - 1) / 2) * 2.05 * r
                y = (j - (m - layer - 1) / 2) * 2.05 * r
                p.put(C.prim("uv_sphere", radius=r, segments=14, ring_count=8, location=(x, y, h - 0.03 + layer * 1.5 * r)), "iron")
    p.done()


def clappers(big=False):
    p = Pickup("clappers_big" if big else "clappers", corner=True)
    w, d, h = (0.62, 0.42, 0.2) if big else (0.46, 0.32, 0.16)
    crate(p, w, d, h)
    n = 6 if big else 4
    for i in range(n):
        x = (i - (n - 1) / 2) * (w - 0.1) / n
        prof = [(0.0, 0.0), (0.045, 0.02), (0.05, 0.06), (0.03, 0.11), (0.012, 0.15), (0.012, 0.34), (0.0, 0.36)]
        o = C.lathe("clapper", prof, segs=16)
        o.rotation_euler = (math.radians(90 - 8), 0, math.radians(6 * (i % 2 * 2 - 1)))
        o.location = (x, d / 2 - 0.06, h * 0.4 + 0.05)
        p.put(o, "bronze")
    p.put(W.box(w - 0.06, 0.03, 0.04, P((0, 0, h + 0.02))), "leather")  # a strap across
    p.done()


def armour(name, metal, plates):
    """A cuirass on its own: a breastplate narrow at the waist and broad at
    the chest, with pauldrons, a gorget and bands."""
    p = Pickup(name, spin=True)

    def shape(a, z, x, y):
        k = 1.0 + 0.3 * max(0.0, -math.sin(a)) * max(0.0, 1 - abs(z - 0.62) / 0.25)  # the chest swells forward
        return x * 1.25, y * 0.62 * k, z

    prof = [(0.15, 0.28), (0.15, 0.36), (0.17, 0.46), (0.21, 0.6), (0.22, 0.7), (0.17, 0.8), (0.09, 0.84)]
    p.put(C.thicken(C.lathe(name, prof, segs=40, shape=shape), 0.012), metal)
    for i in range(plates):  # the tassets' bands at the waist
        z = 0.30 + 0.045 * i
        o = C.lathe("band", [(0.158 + 0.004 * i, z - 0.018), (0.162 + 0.004 * i, z + 0.018)], segs=40, shape=shape)
        p.put(C.thicken(o, 0.01), "brass" if metal != "brass" else "iron")
    for s in (-1, 1):
        pad = C.prim("uv_sphere", radius=0.11, segments=20, ring_count=10, location=(s * 0.25, 0.0, 0.76))
        pad.scale = (1.0, 0.9, 0.55)
        pad.rotation_euler = (0, math.radians(s * 25), 0)
        p.put(pad, metal)
        p.put(W.ring(P((s * 0.25, 0.0, 0.73)), P((s * 0.4, 0, 1)), 0.1, 0.008), "brass" if metal != "brass" else "iron")
    p.put(W.ring(P((0, 0, 0.84)), P((0, 0, 1)), 0.1, 0.018), "brass" if metal != "brass" else "iron")
    for z in (0.5, 0.62):
        p.put(C.prim("uv_sphere", radius=0.014, segments=8, ring_count=5, location=(0, -0.172 if z < 0.55 else -0.19, z)), "brass")
    p.done()


def key(name, metal):
    """A big key with a little bell for its bow."""
    p = Pickup(name, spin=True)
    z = 0.55
    bell = C.lathe("bell", [(0.0, 0.16), (0.03, 0.155), (0.05, 0.12), (0.06, 0.06), (0.08, 0.01), (0.085, 0.0)], segs=24)
    bell.rotation_euler = (0, math.radians(-90), 0)
    bell.location = (0.2, 0.0, z)  # the crown joins the shaft, the mouth faces out
    p.put(C.thicken(bell, 0.012), metal)
    p.put(W.rod(P((0.06, 0.0, z)), P((-0.34, 0.0, z)), 0.02, segs=12), metal)
    for x in (0.03, -0.06):
        p.put(W.ring(P((x, 0.0, z)), P((1, 0, 0)), 0.026, 0.009), metal)
    for i, hgt in enumerate((0.08, 0.055, 0.09)):
        p.put(W.box(0.028, hgt, 0.018, P((-0.27 - 0.03 * i, 0.0, z - hgt / 2))), metal)
    p.done()


def backpack():
    p = Pickup("backpack", spin=True)
    p.put(W.box(0.36, 0.4, 0.2, P((0, 0, 0.22))), "leather", bevel=0.04)
    p.put(W.box(0.37, 0.18, 0.22, P((0, -0.01, 0.36)), rot=(10, 0, 0)), "leather", bevel=0.02)  # the flap
    for x in (-0.1, 0.1):
        p.put(W.box(0.03, 0.2, 0.01, P((x, -0.112, 0.28))), "leather")
        p.put(W.box(0.04, 0.035, 0.012, P((x, -0.115, 0.2))), "brass")
    p.put(W.tube([(0.0, 0.1, 0.42), (0.0, 0.14, 0.5), (0.0, 0.18, 0.42)], 0.012), "leather")
    p.done()


# The powerups hang in the air over where they lie (the game gives them a box
# from 24 under the origin), turning, each with something hot in it.

def forge_heart():
    """The Forge Heart: a lump of live iron the size of a fist, beating in an iron cage."""
    p = Pickup("forge_heart", spin=True)
    core = C.prim("uv_sphere", radius=0.13, segments=20, ring_count=12, location=(0, 0, 0.12))
    core.scale = (1.0, 0.85, 1.15)
    p.put(core, "slag")
    for sx in (-1, 1):  # the heart's two lobes and its point
        lobe = C.prim("uv_sphere", radius=0.08, segments=14, ring_count=8, location=(sx * 0.07, 0, 0.22))
        p.put(lobe, "slag")
    p.put(C.between("cone", P((0, 0, 0.04)), P((0, 0, -0.07)), radius1=0.1, radius2=0.01, vertices=14), "slag")
    crust = C.prim("ico_sphere", subdivisions=2, radius=0.15, location=(0.03, -0.02, 0.1))
    crust.scale = (0.9, 0.7, 1.1)
    p.put(crust, "crust")
    for i in range(6):  # the cage: six bars from a ring at the foot to a ring at the crown
        a = math.tau * i / 6
        mid = P((0.21 * math.cos(a), 0.21 * math.sin(a), 0.12))
        p.put(W.rod(P((0.1 * math.cos(a), 0.1 * math.sin(a), -0.14)), mid, 0.01, segs=8), "iron")
        p.put(W.rod(mid, P((0.08 * math.cos(a), 0.08 * math.sin(a), 0.38)), 0.01, segs=8), "iron")
    for z, r in ((-0.14, 0.1), (0.12, 0.21), (0.38, 0.08)):
        p.put(W.ring(P((0, 0, z)), P((0, 0, 1)), r, 0.014), "iron")
    p.put(W.ring(P((0, 0, 0.44)), P((1, 0, 0)), 0.05, 0.012), "iron")       # the hook it hung from
    p.done()


def mantle():
    """The Founder's Mantle: a little bronze cope, cast for nothing to stand in, glowing at its seams."""
    p = Pickup("mantle", spin=True)
    prof = [(0.24, -0.16), (0.25, -0.13), (0.2, 0.0), (0.16, 0.16), (0.13, 0.28), (0.07, 0.34), (0.0, 0.35)]
    cope = C.lathe("cope", prof, segs=40)
    p.put(C.thicken(cope, 0.015), "cope")
    p.put(W.ring(P((0, 0, -0.13)), P((0, 0, 1)), 0.245, 0.016), "bronze")
    p.put(W.ring(P((0, 0, 0.16)), P((0, 0, 1)), 0.162, 0.012), "bronze")
    p.put(W.ring(P((0, 0, 0.4)), P((1, 0, 0)), 0.05, 0.014), "iron")
    p.put(C.prim("uv_sphere", radius=0.07, segments=12, ring_count=8, location=(0, 0, -0.04)), "ember")  # hot inside
    p.done()


def veil():
    """The Soot Veil: a shroud of charred cloth hanging on nothing, its hem going to ash."""
    p = Pickup("veil", spin=True)
    prof = [(0.0, 0.36), (0.07, 0.34), (0.12, 0.27), (0.15, 0.12), (0.19, -0.05), (0.24, -0.2), (0.27, -0.3)]
    sh = C.lathe("veil", prof, segs=40,
                 shape=lambda a, z, x, y: (x * (1 + 0.18 * math.sin(a * 5 + z * 7)) , y * (1 + 0.18 * math.sin(a * 5 + z * 7)),
                                           z - (0.06 * (1 + math.sin(a * 7)) if z < -0.25 else 0.0)))
    p.put(C.thicken(sh, 0.012), "hood")
    for a, z in ((0.6, 0.2), (2.3, 0.02), (3.6, -0.12), (5.1, 0.1), (4.3, -0.24)):  # embers caught in the cloth
        r = 0.152 + 0.04 * max(0.0, -z) / 0.3
        p.put(C.prim("uv_sphere", radius=0.016, segments=8, ring_count=5, location=(math.cos(a) * r, math.sin(a) * r, z)), "ember")
    p.done()


def quench_suit():
    """The Quench Suit's helmet: a brass diving bell for a head, with a glass port and a hose."""
    p = Pickup("quench_suit", spin=True)
    dome = C.prim("uv_sphere", radius=0.19, segments=28, ring_count=16, location=(0, 0, 0.14))
    p.put(dome, "brass")
    p.put(W.rod(P((0, 0, -0.1)), P((0, 0, -0.02)), 0.21, segs=32), "brass", bevel=0.01)   # the collar
    for i in range(8):
        a = math.tau * i / 8
        p.put(C.prim("uv_sphere", radius=0.016, segments=8, ring_count=5, location=(0.21 * math.cos(a), 0.21 * math.sin(a), -0.06)), "iron")
    p.put(W.rod(P((0, -0.17, 0.15)), P((0, -0.21, 0.15)), 0.1, segs=24), "brass")              # the port's frame
    p.put(W.rod(P((0, -0.205, 0.15)), P((0, -0.212, 0.15)), 0.08, segs=24), "port")
    for ang in (0, 60, 120):
        a = math.radians(ang)
        d = P((math.cos(a), 0, math.sin(a))) * 0.08
        p.put(W.rod(P((0, -0.215, 0.15)) - d, P((0, -0.215, 0.15)) + d, 0.006, segs=6), "brass")  # its grille
    p.put(W.tube([(0.1, 0.12, 0.22), (0.2, 0.2, 0.18), (0.27, 0.22, 0.06), (0.26, 0.16, -0.06), (0.18, 0.1, -0.14),
                  (0.08, 0.14, -0.2)], 0.025), "leather")    # the air hose, looping down
    p.done()


PICKUPS = {
    "health_small": health_small, "health": health, "health_mega": health_mega,
    "shells": shells, "shells_big": lambda: shells(True), "slag": slag, "slag_big": lambda: slag(True),
    "iron": iron, "iron_big": lambda: iron(True), "clappers": clappers, "clappers_big": lambda: clappers(True),
    "armour_leather": lambda: armour("armour_leather", "leather", 2), "armour_iron": lambda: armour("armour_iron", "iron", 3),
    "armour_bronze": lambda: armour("armour_bronze", "bronze", 4),
    "key_silver": lambda: key("key_silver", "steel"), "key_gold": lambda: key("key_gold", "brass"),
    "backpack": backpack,
    "forge_heart": forge_heart, "mantle": mantle, "veil": veil, "quench_suit": quench_suit,
}

if __name__ == "__main__":
    for name, make in PICKUPS.items():
        if not C.ONLY or name in C.ONLY:
            make()
