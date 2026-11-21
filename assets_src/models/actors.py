"""Cinderkirk's stoker as other players see him, what's left of him, and the
things the guns throw: built from primitives in headless Blender and baked
to MD3 the way the creatures are (creatures.py).

    python actors.py -- <out dir> [resolution] [only=player,gib1]   (with the bpy wheel)

Each writes <out>/<name>.md3 (with its .png and _luma.png) under the name of
the stand-in it replaces: the engine loads progs/player.md3 in place of
progs/player.mdl, so the game code doesn't change. The stoker's frames are
player.qc's, in its order; the rest have one frame each.

The stoker is built like a creature (facing -Y, feet at z 0, in metres) and
the small things centred on the origin, flying along -Y, which the export
turns to Quake's +X. The Toll's beam pieces run from the origin to 30 units
ahead, as the engine strings them.

Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy first: it makes bmesh importable)
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import creatures as C  # noqa: E402
import weapons as W  # noqa: E402  (the metals and the pieces)

P = Vector
pose_of = C.pose_of

# The stoker's jacket and hood take a player's shirt colour in Pit fights and
# co-op, and his long coat the trousers' (creatures.build bakes the mask).
C.TILES.update({
    "jacket": ("cloth_char1", 0.45, (1.15, 1.1, 1.0)),
    "cowl": ("leather1", 0.4, (1.1, 1.05, 1.0)),
    "coat": ("leather1", 0.6, (1.2, 1.15, 1.05)),
})
TEAM = {"jacket": (1.0, 0.0, 0.0), "cowl": (1.0, 0.0, 0.0), "coat": (0.0, 1.0, 0.0)}

# Model flags (the MD3 header's): trails and the gib's blood.
ROCKET, GRENADE, GIB, ZOMGIB = 1, 2, 4, 32


# ------------------------------------------------------------------ the stoker

def stoker_joints():
    """A stoker holding a gun low across the body: right hand at the grip,
    left hand under the barrel."""
    J = dict(C.HUMAN)
    J.update({"elb_r": (-0.25, 0.05, 1.17), "wri_r": (-0.16, -0.16, 1.06), "fin_r": (-0.14, -0.25, 1.06),
              "elb_l": (0.23, -0.08, 1.16), "wri_l": (0.03, -0.40, 1.11), "fin_l": (0.0, -0.49, 1.12)})
    return J


def stoker():
    J = stoker_joints()
    butt, muzzle = P((-0.15, 0.16, 1.10)), P((-0.02, -0.78, 1.15))
    haft0, haft1 = P(J["wri_r"]) + P((0, 0.04, -0.12)), P(J["wri_r"]) + P((0, -0.10, 0.55))
    bones = C.humanoid(J, [("gun", "hand_r", J["wri_r"], tuple(muzzle)), ("pick", "hand_r", J["wri_r"], tuple(haft1))])
    c = C.Creature("player", bones, hull_bottom=-24.0)
    c.team = TEAM

    # Body in a long leather coat over work clothes.
    body = {n: J[n] for n in ("pelvis", "spine", "chest", "neck", "hip_l", "knee_l", "ankle_l", "hip_r", "knee_r", "ankle_r",
                              "sho_l", "elb_l", "wri_l", "sho_r", "elb_r", "wri_r")}
    e = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck")]
    rad = {"pelvis": (0.15, 0.11), "spine": (0.15, 0.115), "chest": (0.18, 0.125), "neck": 0.06}
    for s in "lr":
        e += [("pelvis", "hip_" + s), ("hip_" + s, "knee_" + s), ("knee_" + s, "ankle_" + s),
              ("chest", "sho_" + s), ("sho_" + s, "elb_" + s), ("elb_" + s, "wri_" + s)]
        rad.update({"hip_" + s: 0.08, "knee_" + s: 0.058, "ankle_" + s: 0.05,
                    "sho_" + s: 0.07, "elb_" + s: 0.055, "wri_" + s: 0.045})
    body_bones = [b[0] for b in bones if b[0] not in ("gun", "pick", "head", "hand_l", "hand_r", "foot_l", "foot_r")]
    c.add(C.skin_body("body", body, e, rad, "pelvis", seed=7.0, lumps=0.004), "jacket", power=4.0, among=body_bones)
    # The coat's skirt, split at the front, to just below the knee.
    skirt = C.lathe("skirt", [(0.17, 1.02), (0.19, 0.9), (0.22, 0.7), (0.25, 0.5)], segs=36,
                    shape=lambda a, z, x, y: (x * (1 + 0.04 * math.sin(7 * a)), y * 0.85, z + 0.015 * math.sin(5 * a)),
                    skip=lambda a, z: abs(math.sin(a) + 1) < 0.08 and z < 0.95)
    c.add(C.thicken(skirt, 0.012), "coat", among=["pelvis", "thigh_l", "thigh_r"], power=3.0, anchor=("pelvis", 0.5))
    collar = C.prim("torus", major_radius=0.085, minor_radius=0.03, major_segments=24, minor_segments=8,
                    location=(0, -0.01, 1.52))
    c.add(collar, "leather", among=["chest", "neck"])
    belt = C.prim("torus", major_radius=0.165, minor_radius=0.018, major_segments=32, minor_segments=6, location=(0, 0.0, 1.02))
    belt.scale = (1.05, 0.8, 1.0)
    c.add(belt, "leather", among=["pelvis", "spine"])
    c.add(W.box(0.05, 0.05, 0.02, P((0, -0.135, 1.02))), "bronze", "pelvis")   # the buckle
    # Shoulder pads of riveted iron, and a bronze pressure flask on the back.
    for sx in (-1, 1):
        pad = C.prim("uv_sphere", radius=0.095, segments=14, ring_count=8, location=(sx * 0.22, 0.0, 1.47))
        pad.scale = (1.0, 1.05, 0.55)
        c.add(pad, "iron", among=["chest", "upper_l" if sx > 0 else "upper_r"], power=6.0)
    flask = C.lathe("flask", [(0.0, 1.08), (0.07, 1.09), (0.08, 1.14), (0.08, 1.38), (0.06, 1.43), (0.0, 1.45)],
                    segs=18, at=(0.0, 0.17, 0.0))
    c.add(flask, "bronze", "chest")
    for s in "lr":
        ax, ay, az = J["ankle_" + s]
        boot = C.prim("uv_sphere", radius=0.065, segments=14, ring_count=8, location=(ax, ay - 0.06, 0.055))
        boot.scale = (0.85, 1.8, 0.85)
        c.add(boot, "leather", "foot_" + s)
        cuff = C.prim("cylinder", radius=0.06, depth=0.1, vertices=12, location=(ax, ay, 0.15))
        c.add(cuff, "leather", "shin_" + s)
        w, f = P(J["wri_" + s]), P(J["fin_" + s])
        glove = C.skin_body("glove_" + s, {"w": tuple(w - (f - w) * 0.5), "f": tuple(f)}, [("w", "f")],
                            {"w": 0.05, "f": (0.047, 0.032)}, "w", subdiv=1)
        c.add(glove, "leather", "hand_" + s)
    # The head: a leather hood, a scarf over the mouth and goggles that glow.
    hx, hy, hz = J["head"]
    head = C.prim("uv_sphere", radius=0.105, segments=18, ring_count=10, location=(hx, hy, hz + 0.07))
    head.scale = (0.92, 1.0, 1.1)
    c.add(head, "cowl", "head")
    scarf = C.prim("uv_sphere", radius=0.085, segments=16, ring_count=8, location=(hx, hy - 0.035, hz + 0.0))
    scarf.scale = (1.0, 0.95, 0.75)
    c.add(scarf, "robe", among=["head", "neck"], power=6.0)
    for sx in (-1, 1):
        at = P((hx + sx * 0.042, hy - 0.092, hz + 0.09))
        c.add(W.rod(at + P((0, 0.02, 0)), at - P((0, 0.012, 0)), 0.03, segs=14), "bronze", "head")
        c.add(W.rod(at - P((0, 0.010, 0)), at - P((0, 0.014, 0)), 0.024, segs=14), "ember", "head")
    c.add(W.ring(P((hx, hy, hz + 0.09)), (0, 0, 1), 0.1, 0.008), "leather", "head")   # the goggles' strap

    # The gun: an iron barrel on an oak stock, banded in bronze.
    d = (muzzle - butt).normalized()
    c.add(W.rod(butt, butt + d * 0.32, 0.034, segs=10), "oak", "gun")
    c.add(W.rod(butt + d * 0.28, muzzle, 0.024, segs=14), "iron", "gun")
    c.add(W.rod(butt + d * 0.45, butt + d * 0.75, 0.032, segs=14), "iron", "gun")
    for t in (0.3, 0.55, 0.8, 0.98):
        c.add(W.ring(butt + d * t * (muzzle - butt).length, d, 0.033, 0.008, segs=16), "bronze", "gun")
    c.add(W.rod(muzzle - d * 0.01, muzzle + d * 0.005, 0.018, segs=12), "coal", "gun")

    # The pick, for when he swings it: an oak haft and an iron head.
    c.add(W.rod(haft0, haft1, 0.022, segs=10), "oak", "pick")
    top = haft1 - (haft1 - haft0).normalized() * 0.04
    c.add(W.rod(top + P((0, 0.10, 0)), top + P((0, -0.24, -0.06)), 0.03, segs=10, cap=0.006), "iron", "pick")
    c.add(W.rod(top + P((0, 0.10, 0)), top + P((0, 0.16, -0.02)), 0.028, segs=10, cap=0.012), "iron", "pick")

    def axe(pose):   # the left hand leaves the gun when he swings the pick
        return pose_of(pose, upper_l=(44, 0, -10), fore_l=(-10, 0, 0))

    base = {"spine": (4, 0, 0), "neck": (-4, 0, 0), "thigh_l": (-3, 0, 0), "thigh_r": (3, 0, 0)}
    breathe = pose_of(base, chest=(3, 0, 0), head=(-3, 0, 3), move=(0, 0, -0.006))
    stand = [(0.0, base), (0.5, breathe), (1.0, base)]
    look = pose_of(base, neck=(-4, 0, 16), head=(0, 0, 12))
    axstand = [(0.0, axe(base)), (0.3, axe(breathe)), (0.6, axe(look)), (1.0, axe(base))]
    rbase = pose_of(base, spine=(12, 0, 0), chest=(3, 0, 0))
    rstep = pose_of(rbase, thigh_l=(-38, 0, 0), shin_l=(18, 0, 0), thigh_r=(28, 0, 0), shin_r=(50, 0, 0), foot_r=(-10, 0, 0),
                    move=(0, 0, -0.04))
    rmid = pose_of(rbase, thigh_l=(-8, 0, 0), shin_l=(10, 0, 0), thigh_r=(-14, 0, 0), shin_r=(70, 0, 0), move=(0, 0, 0.03))
    run = [(0.0, rstep), (0.25, rmid), (0.5, C.mirror(rstep)), (0.75, C.mirror(rmid)), (1.0, rstep)]
    axrun = [(t, axe(p)) for t, p in run]
    reel = pose_of(base, spine=(-12, 0, 8), chest=(-10, 0, 0), neck=(10, 0, 0), head=(12, 0, -10), move=(0, 0.05, 0))
    pain = [(0.0, base), (0.3, reel), (1.0, base)]
    axpain = [(t, axe(p)) for t, p in pain]
    # Firing: the gun kicks a little and comes back.
    kick = pose_of(base, chest=(-6, 0, 0), upper_r=(6, 0, 0), upper_l=(4, 0, 0), move=(0, 0.04, 0))
    shot = [(0.0, kick), (0.35, pose_of(base, chest=(-2, 0, 0))), (1.0, base)]
    rattle = [(0.0, kick), (1.0, pose_of(base, chest=(-3, 0, 0)))]
    # The pick: four swings, overhead, from the right, from the left, and low.
    up = axe(pose_of(base, upper_r=(-150, 0, 10), fore_r=(-30, 0, 0), spine=(-6, 0, 0), chest=(-6, 0, 0)))
    down = axe(pose_of(base, upper_r=(-35, 0, 0), fore_r=(-10, 0, 0), spine=(18, 0, 0), chest=(8, 0, 0), move=(0, -0.05, -0.03)))
    side = axe(pose_of(base, upper_r=(-80, -60, 0), chest=(0, 0, -25), spine=(0, 0, -10)))
    across = axe(pose_of(base, upper_r=(-80, 40, 0), fore_r=(-20, 0, 0), chest=(0, 0, 25), spine=(0, 0, 10)))
    low = axe(pose_of(base, upper_r=(-20, 0, 0), fore_r=(-60, 0, 0), spine=(22, 0, 0), thigh_l=(-25, 0, 0), shin_l=(20, 0, 0)))
    swing_a = [(0.0, axe(base)), (0.4, up), (0.7, down), (1.0, axe(base))]
    swing_b = [(0.0, axe(base)), (0.35, side), (0.7, across), (1.0, axe(base))]
    swing_c = [(0.0, axe(base)), (0.35, across), (0.7, side), (1.0, axe(base))]
    swing_d = [(0.0, axe(base)), (0.4, axe(pose_of(base, upper_r=(-60, 0, 0), fore_r=(-80, 0, 0)))), (0.7, low), (1.0, axe(base))]
    # Deaths: back, forward, a turn and down, knees, and a heap.
    back = pose_of(base, pelvis=(-88, 0, 0), spine=(-4, 0, 0), neck=(12, 0, 0), thigh_l=(-8, 0, 6), thigh_r=(-4, 0, -6),
                   upper_l=(-40, 0, 50), upper_r=(-30, 0, -50), move=(0, 0, -0.85))
    fwd = pose_of(base, pelvis=(88, 0, 0), spine=(0, 0, 0), neck=(-25, 0, 0), thigh_l=(6, 0, 4), thigh_r=(0, 0, -4),
                  upper_r=(-150, 0, -15), upper_l=(-160, 0, 20), move=(0, 0, -0.85))
    kneel = pose_of(base, spine=(25, 0, 0), thigh_l=(-70, 0, 0), shin_l=(120, 0, 0), thigh_r=(-60, 0, 0), shin_r=(115, 0, 0),
                    foot_l=(-40, 0, 0), foot_r=(-40, 0, 0), upper_r=(30, 0, 0), move=(0, 0.08, -0.38))
    turn = pose_of(reel, pelvis=(0, 0, 60), spine=(0, 0, 30), move=(0, 0, -0.05))
    death_a = [(0.0, base), (0.3, reel), (0.85, back), (1.0, back)]
    death_b = [(0.0, base), (0.45, kneel), (0.85, fwd), (1.0, fwd)]
    death_c = [(0.0, base), (0.25, reel), (0.5, turn), (0.85, pose_of(fwd, pelvis=(88, 0, 70))), (1.0, pose_of(fwd, pelvis=(88, 0, 70)))]
    death_d = [(0.0, base), (0.5, kneel), (0.9, pose_of(fwd, pelvis=(88, 0, -30))), (1.0, pose_of(fwd, pelvis=(88, 0, -30)))]
    death_e = [(0.0, base), (0.3, pose_of(reel, spine=(-20, 0, -15))), (0.85, pose_of(back, pelvis=(-88, 0, -40))),
               (1.0, pose_of(back, pelvis=(-88, 0, -40)))]
    axdeath = [(t, axe(p)) for t, p in death_b]

    G, A = "hide:pick", "hide:gun"   # gun frames hide the pick, pick frames the gun
    anims = [
        ("axrun", 6, axrun, True, A), ("rockrun", 6, run, True, G),
        ("stand", 5, stand, True, G), ("axstnd", 12, axstand, True, A),
        ("axpain", 6, axpain, False, A), ("pain", 6, pain, False, G),
        ("axdeth", 9, axdeath, False, A), ("deatha", 11, death_a, False, G), ("deathb", 9, death_b, False, G),
        ("deathc", 15, death_c, False, G), ("deathd", 9, death_d, False, G), ("deathe", 9, death_e, False, G),
        ("nailatt", 2, rattle, True, G), ("light", 2, rattle, True, G),
        ("rockatt", 6, shot, False, G), ("shotatt", 6, shot, False, G),
        ("axatt", 6, swing_a, False, A), ("axattb", 6, swing_b, False, A),
        ("axattc", 6, swing_c, False, A), ("axattd", 6, swing_d, False, A),
    ]
    C.build(c, anims)


# ------------------------------------------------------------------ small things

class Thing(C.Creature):
    """A one-frame model on a single bone, centred on the origin."""

    def __init__(self, name, flags=0):
        super().__init__(name, [("root", None, (0, 0, 0), (0, 0, 0.1))], hull_bottom=0.0)
        self.flags = flags

    def put(self, o, material, smooth=True):
        return self.add(o, material, bone="root", smooth=smooth)

    def done(self):
        C.build(self, [("idle", 1, [(0.0, {})], False, None)])


def lump(name, r, seed, squash=(1.0, 1.0, 1.0), rough=0.3, segs=12):
    """A rough rock or clot: a sphere pushed about by noise."""
    o = C.prim("uv_sphere", radius=r, segments=segs, ring_count=max(6, segs // 2))
    o.scale = squash
    C.apply_all(o)
    for v in o.data.vertices:
        q = v.co * (3.0 / r) + P((seed, seed * 1.7, seed * 0.3))
        v.co += v.normal * r * rough * noise.noise(q)
    return o


def h_player():
    """The stoker's hooded head, goggles and all, for when nothing else is left."""
    t = Thing("h_player", GIB)
    head = C.prim("uv_sphere", radius=0.105, segments=18, ring_count=10, location=(0, 0, 0))
    head.scale = (0.92, 1.0, 1.1)
    t.put(head, "hood")
    scarf = C.prim("uv_sphere", radius=0.085, segments=16, ring_count=8, location=(0, -0.035, -0.07))
    scarf.scale = (1.0, 0.95, 0.75)
    t.put(scarf, "robe")
    for sx in (-1, 1):
        at = P((sx * 0.042, -0.092, 0.02))
        t.put(W.rod(at + P((0, 0.02, 0)), at - P((0, 0.012, 0)), 0.03, segs=14), "bronze")
        t.put(W.rod(at - P((0, 0.010, 0)), at - P((0, 0.014, 0)), 0.024, segs=14), "ember")
    t.put(W.ring(P((0, 0, 0.02)), (0, 0, 1), 0.1, 0.008), "leather")
    t.done()


def eyes():
    """All anyone sees of a stoker under the Soot Veil: his goggles' glow."""
    t = Thing("eyes")
    for sx in (-1, 1):
        at = P((sx * 0.042, -0.092, 0.0))
        t.put(W.rod(at - P((0, 0.010, 0)), at - P((0, 0.014, 0)), 0.024, segs=14), "ember")
    t.done()


def gib(name, r, seed, squash, parts):
    """Charred remains: a lump of scorched cloth and leather, still smouldering."""
    t = Thing(name, GIB)
    t.put(lump(name, r, seed, squash), "coal")
    for i, (mat, k, off) in enumerate(parts):
        bit = lump(name, r * k, seed + 10 + i, (1.2, 0.8, 0.5), 0.4, 10)
        bit.location = off
        t.put(bit, mat)
    t.done()


def zom_gib():
    """A clot of hot slag, thrown."""
    t = Thing("zom_gib", ZOMGIB)
    t.put(lump("clot", 0.09, 3.0, (1.0, 1.0, 0.85)), "crust")
    t.done()


def spike():
    """The Spitter's shot: a red-hot rivet, head first."""
    t = Thing("spike")
    t.put(W.rod(P((0, 0.10, 0)), P((0, -0.08, 0)), 0.018, segs=10), "slag")
    t.put(W.rod(P((0, -0.08, 0)), P((0, -0.12, 0)), 0.032, segs=12, cap=0.02), "ember")
    t.done()


def s_spike():
    """The Bolt Caster's bolt: a longer iron bolt, its point still glowing."""
    t = Thing("s_spike")
    t.put(W.rod(P((0, 0.22, 0)), P((0, -0.14, 0)), 0.022, segs=10), "iron")
    t.put(W.rod(P((0, -0.14, 0)), P((0, -0.24, 0)), 0.03, segs=12, cap=0.0), "ember")
    for y in (0.14, 0.2):
        t.put(W.ring(P((0, y, 0)), (0, 1, 0), 0.024, 0.008, segs=12), "bronze")
    t.done()


def grenade():
    """The Crucible's shot: a little clay crucible, its mouth full of slag."""
    t = Thing("grenade", GRENADE)
    body = C.lathe("crucible", [(0.0, -0.09), (0.06, -0.085), (0.085, -0.03), (0.09, 0.05), (0.08, 0.09), (0.07, 0.095)], segs=18)
    t.put(body, "firebrick")
    t.put(C.prim("cylinder", radius=0.07, depth=0.01, vertices=18, location=(0, 0, 0.09)), "slag")
    t.done()


def missile():
    """The Shot Mortar's round: a cast-iron shell with a bronze driving band and
    a burning fuse at the back."""
    t = Thing("missile", ROCKET)
    shell = W.along([(0.0, 0.0), (0.05, 0.02), (0.07, 0.1), (0.075, 0.3), (0.06, 0.4), (0.0, 0.62)],
                    P((0, 0.3, 0)), P((0, -0.35, 0)), segs=18)
    t.put(shell, "iron")
    t.put(W.ring(P((0, 0.12, 0)), (0, 1, 0), 0.077, 0.012, segs=18), "bronze")
    t.put(W.rod(P((0, 0.30, 0)), P((0, 0.36, 0)), 0.02, segs=8), "ember")
    t.done()


def lavaball():
    """A gob of slag in flight, crusting over."""
    t = Thing("lavaball", ROCKET)
    t.put(lump("gob", 0.17, 5.0, (1.0, 1.15, 0.95), 0.25, 16), "crust")
    t.done()


def bolt(name, r, twist):
    """A piece of the Toll's beam: a ringing band of heat 30 units long,
    twisted so the pieces don't line up."""
    t = Thing(name)
    n, length = 12, 30.0 / C.UNITS
    pts = []
    for i in range(n + 1):
        y = -length * i / n
        a = twist * i / n
        pts.append((r * math.cos(a), y, r * math.sin(a)))
    pts2 = [(-x, y, -z) for x, y, z in pts]
    for a, b in zip(pts, pts[1:]):
        t.put(W.rod(P(a), P(b), r * 0.45, segs=6), "ember")
    for a, b in zip(pts2, pts2[1:]):
        t.put(W.rod(P(a), P(b), r * 0.3, segs=5), "slag")
    t.done()


ACTORS = {
    "player": stoker, "h_player": h_player, "eyes": eyes,
    "gib1": lambda: gib("gib1", 0.08, 1.0, (1.0, 1.3, 0.7), [("leather", 0.6, (0.04, 0.0, 0.03))]),
    "gib2": lambda: gib("gib2", 0.16, 2.0, (1.2, 1.0, 0.7), [("robe", 0.6, (0.06, -0.04, 0.05)), ("leather", 0.4, (-0.08, 0.05, 0.0))]),
    "gib3": lambda: gib("gib3", 0.2, 3.0, (1.4, 1.0, 0.5), [("robe", 0.5, (0.1, 0.0, 0.06)), ("iron", 0.35, (-0.1, 0.04, 0.05))]),
    "zom_gib": zom_gib, "spike": spike, "s_spike": s_spike, "grenade": grenade, "missile": missile,
    "lavaball": lavaball, "bolt": lambda: bolt("bolt", 0.06, 2.5), "bolt2": lambda: bolt("bolt2", 0.05, 3.5),
    "bolt3": lambda: bolt("bolt3", 0.12, 2.0),
}

if __name__ == "__main__":
    for name, make in ACTORS.items():
        if not C.ONLY or name in C.ONLY:
            make()
