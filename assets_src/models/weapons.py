"""Cinderkirk's weapons as the player holds them: built from primitives in
headless Blender with the stoker's gloved right hand, animated on a small
skeleton, skinned by baking (creatures.py does the rigging, baking and MD3)
and written as MD3 view models.

    python weapons.py -- <out dir> [resolution] [only=pick,steam]   (with the bpy wheel)
    blender -b -P weapons.py -- <out dir> [resolution]

Each weapon writes <out>/v_<name>.md3, .png and _luma.png. Frame 0 is the
weapon at rest and frames 1 to 8 are what the game code's weaponframe steps
through: 1-4 and 5-8 are the Pick's two swings; the Scattergun, Crucible,
Steam Cannon and Shot Mortar fire on 1 and settle by 6; the Spitter and the
Bolt Caster loop 1-8 while the trigger is held, and the Tolling Iron 1-4.

Built in metres with the eye at the origin, forward -Y, right -X and up +Z;
creatures.build turns that to Quake's view model space (forward +X) at 32
units a metre. Recoil stays small: Cinderkirk keeps the view steady.

Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy first: it makes bmesh importable)
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import creatures as C  # noqa: E402

# Metal tiles for the guns, on top of the creatures' (iron, bronze, oak, leather).
C.TILES.update({
    "blued": ("iron_plate1", 0.35, (0.55, 0.6, 0.72)),
    "steel": ("iron_plate1", 0.35, (1.5, 1.45, 1.4)),
    "brass": ("bronze1", 0.25, (1.45, 1.2, 0.75)),
    "copper": ("bronze1", 0.3, (1.5, 0.8, 0.55)),
    "walnut": ("oak1", 0.25, (0.7, 0.55, 0.45)),
    "glove": ("leather1", 0.25, (0.9, 0.8, 0.7)),
    "sleeve": ("cloth_char1", 0.45, (1.0, 1.0, 1.0)),
})
_shade = C.shade


def shade(name):
    if name == "gauge":
        g = C.Nodes(bpy.data.materials[name])
        n = g.noise(40.0, 3.0, 0.5, seed=11.0)
        return g, g.ramp(n, [(0.3, (0.55, 0.5, 0.38)), (0.7, (0.7, 0.64, 0.5))]), None
    if name == "pilot":
        return C.Nodes(bpy.data.materials[name]), (0.6, 0.3, 0.1), (1.0, 0.5, 0.15)
    return _shade(name)


C.shade = shade
P = Vector


class Weapon(C.Creature):
    """A view model: the root bone is the hand at the grip, so recoil turns
    the weapon about the wrist; "part" bones move pieces on their own."""

    def __init__(self, name, grip, parts=()):
        bones = [("root", None, tuple(VIEW @ P(grip)), tuple(VIEW @ (P(grip) + P((0, -0.1, 0)))))]
        bones += [(n, "root", tuple(VIEW @ P(h)), tuple(VIEW @ P(t))) for n, h, t in parts]
        super().__init__("v_" + name, bones, hull_bottom=0.0)

    def put(self, o, material, bone="root", bevel=0.0, smooth=True):
        bpy.context.view_layer.update()  # matrix_world is stale after setting location or rotation
        o.matrix_world = VIEW @ o.matrix_world
        if bevel:
            m = o.modifiers.new("bevel", "BEVEL")
            m.width = bevel
            m.segments = 2
            m.limit_method = "ANGLE"
        return self.add(o, material, bone=bone, smooth=smooth)


# ------------------------------------------------------------------ pieces

def box(w, h, d, at, rot=(0, 0, 0)):
    """A box w wide (x), d long (y), h tall (z) centred at `at`."""
    o = C.prim("cube", size=1.0)
    o.scale = (w, d, h)
    o.rotation_euler = tuple(math.radians(a) for a in rot)
    o.location = at
    return o


def rod(a, b, r, segs=24, cap=None):
    """A cylinder from a to b; cap=r2 makes it a cone."""
    if cap is None:
        return C.between("cylinder", a, b, radius=r, vertices=segs)
    return C.between("cone", a, b, radius1=r, radius2=cap, vertices=segs)


def along(profile, a, b, segs=32):
    """A lathe (radius, distance from a) laid from a towards b."""
    a, b = P(a), P(b)
    o = C.lathe("lathe", profile, segs=segs)
    q = (b - a).to_track_quat("Z", "Y")
    o.matrix_world = Matrix.Translation(a) @ q.to_matrix().to_4x4()
    return o


def ring(at, axis, r, t, segs=28):
    o = C.prim("torus", major_radius=r, minor_radius=t, major_segments=segs, minor_segments=8)
    o.matrix_world = Matrix.Translation(P(at)) @ P(axis).to_track_quat("Z", "Y").to_matrix().to_4x4()
    return o


def tube(pts, r):
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1.0)
    sp.order_u = min(4, len(pts))
    sp.use_endpoint_u = True
    sp.resolution_u = 8
    o = bpy.data.objects.new("tube", cu)
    bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    for other in bpy.context.selected_objects:
        other.select_set(False)
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.active_object


def rivets(w, pts, r=0.0055, bone="root"):
    for p in pts:
        w.put(C.prim("uv_sphere", radius=r, segments=8, ring_count=5, location=p), "brass", bone)


def hand(w, top, down, fwd, elbow, fingers=4, grip_r=0.036):
    """The stoker's right glove closed round a grip: top is where the grip
    meets the gun, down runs along the grip, fwd towards the muzzle."""
    d = P(down).normalized()
    f = (P(fwd) - d * P(fwd).dot(d)).normalized()
    s = d.cross(f).normalized()  # the hand's outside (right)
    if s.x > 0:
        s = -s
    top = P(top)
    palm = C.prim("uv_sphere", radius=0.05, segments=20, ring_count=12)
    basis = Matrix((s, f, -d)).transposed().to_4x4()
    palm.matrix_world = Matrix.Translation(top + d * 0.065 + s * 0.028 - f * 0.018) @ basis @ Matrix.Diagonal((0.6, 0.9, 1.25, 1))
    w.put(palm, "glove")
    for k in range(fingers):
        c = top + d * (0.024 + k * 0.025)
        pts = []
        for j in range(7):
            a = math.radians(-35 + j * 37)
            r = grip_r + 0.004 * (j < 2)
            pts.append(tuple(c + s * (r * math.cos(a)) + f * (r * math.sin(a) + 0.004)))
        w.put(tube(pts, 0.0118 - k * 0.0008), "glove")
        w.put(C.prim("uv_sphere", radius=0.0085, segments=8, ring_count=5, location=pts[2]), "brass")  # knuckle plates
    thumb = [top + s * 0.03 + d * 0.03 - f * 0.01, top + s * 0.012 - f * 0.012 + P((0, 0, 0.02)),
             top - s * 0.03 + f * 0.01 + P((0, 0, 0.025)), top - s * 0.04 + f * 0.045 + P((0, 0, 0.018))]
    w.put(tube([tuple(p) for p in thumb], 0.0135), "glove")
    wrist = top + d * 0.15 - f * 0.045 + s * 0.02
    elbow = P(elbow)
    cuff_at = wrist + (elbow - wrist) * 0.2
    w.put(rod(wrist, cuff_at, 0.043, cap=0.052), "glove")
    w.put(ring(cuff_at, elbow - wrist, 0.054, 0.009), "brass")
    w.put(rod(cuff_at - (elbow - wrist) * 0.02, elbow, 0.06, cap=0.085), "sleeve")


def recoil(back, lift, part=None, part_rot=(0, 0, 0), settle=6, loop=False, period=8):
    """Poses for frames 0-8: a kick on frame 1 that settles by `settle`, or a
    loop of `period` frames from 1. part_rot is what the part bone does over
    the same time."""
    out = []
    for k in range(9):
        if k == 0:
            u, v = 0.0, 0.0
        elif loop:
            ph = ((k - 1) % period) / period
            u = 0.5 + 0.5 * math.cos(math.tau * ph)
            v = ph
        else:
            t = (k - 1) / max(settle - 1, 1)
            u = max(0.0, 1.0 - t) ** 2 if k <= settle else 0.0
            v = min(1.0, t) if k <= settle else 1.0
        pose = {"root": (-lift * u, 0, 0), "move": (0, back * u, lift * 0.01 * u)}
        if part:
            pose[part] = tuple(a * v for a in part_rot) if not loop else tuple(a * math.sin(math.tau * v) if i == 0 else a * v for i, a in enumerate(part_rot))
        out.append(pose)
    return out


def frames(poses):
    return [("f%d" % k, 1, [(0.0, p)], False, None) for k, p in enumerate(poses)]


ELBOW = (-0.34, 0.30, -0.72)
# Where the weapons sit in view: each is built about a grip near PIVOT and
# placed by this, so they all sit alike: on the right, a little low, turned
# in towards the crosshair and scaled up from life so they read on screen.
PIVOT = Vector((-0.1, -0.44, -0.4))
VIEW_AT = Vector([float(a) for a in os.environ.get("VIEW_AT", "-0.27,-0.62,-0.41").split(",")])
VIEW_YAW = float(os.environ.get("VIEW_YAW", "7"))
VIEW_PITCH = float(os.environ.get("VIEW_PITCH", "0"))
VIEW_SCALE = float(os.environ.get("VIEW_SCALE", "1.5"))
VIEW = (Matrix.Translation(VIEW_AT) @ Matrix.Rotation(math.radians(VIEW_YAW), 4, "Z") @ Matrix.Rotation(math.radians(VIEW_PITCH), 4, "X")
        @ Matrix.Scale(VIEW_SCALE, 4) @ Matrix.Translation(-PIVOT))


# ------------------------------------------------------------------ the arsenal

def pick():
    """1, the Pick: a stoker's pick on an ash haft, its head steam-driven by a
    brass cylinder, held high on the right."""
    g = P((-0.2, -0.42, -0.36))
    w = Weapon("pick", g)
    up = P((0.08, -0.5, 0.5)).normalized()
    top = g + up * 0.42
    w.put(rod(g - up * 0.12, top, 0.019, segs=16), "walnut")
    w.put(ring(g - up * 0.13, up, 0.021, 0.006), "brass")
    for t in (0.18, 0.3):
        w.put(ring(g + up * t, up, 0.021, 0.004), "iron")
    side = up.cross(P((1, 0, 0))).normalized()  # towards the front of the swing
    head_c = top + up * 0.03
    w.put(box(0.07, 0.07, 0.09, head_c, rot=(math.degrees(math.atan2(up.y, up.z)), 0, 0)), "iron", bevel=0.008)
    spike = along([(0.0, 0.0), (0.034, 0.0), (0.03, 0.1), (0.018, 0.22), (0.006, 0.3), (0.0, 0.32)], head_c, head_c + side * 0.3 - up * 0.1, segs=12)
    w.put(spike, "steel")
    hammer = along([(0.0, 0.0), (0.034, 0.0), (0.036, 0.06), (0.044, 0.08), (0.044, 0.13), (0.0, 0.13)], head_c, head_c - side * 0.2, segs=16)
    w.put(hammer, "iron")
    cyl_a, cyl_b = g + up * 0.24 + side * 0.035, g + up * 0.36 + side * 0.035
    w.put(rod(cyl_a, cyl_b, 0.018), "brass")
    w.put(rod(cyl_b, cyl_b + up * 0.012, 0.022), "iron")
    w.put(rod(cyl_a - up * 0.01, cyl_a, 0.022), "iron")
    w.put(tube([tuple(cyl_a), tuple(g + up * 0.2 + side * 0.03), tuple(g + up * 0.08 + side * 0.025)], 0.005), "copper")
    w.put(C.prim("uv_sphere", radius=0.009, segments=10, ring_count=6, location=head_c + side * 0.02 + P((0.028, 0, 0))), "pilot")
    hand(w, g, -up, side, ELBOW, grip_r=0.028)
    poses = []
    for k in range(9):
        if k == 0:
            poses.append({})
            continue
        j = (k - 1) % 4
        alt = k >= 5
        # back, strike, follow through, return: one swing down, one across
        a = [(-24, 0, 0), (38, 0, 0), (46, 0, 0), (12, 0, 0)][j]
        if alt:
            a = (a[0] * 0.7, 0, [-14, 30, 36, 8][j])
        mv = [(0, 0.03, 0.04), (0, -0.08, -0.06), (0, -0.06, -0.1), (0, -0.01, -0.02)][j]
        poses.append({"root": a, "move": mv})
    C.build(w, frames(poses))


def scattergun():
    """2, the Scattergun: a short brass-bound blunderbuss with a flared muzzle,
    a walnut stock under the arm and a cocking lever."""
    g = P((-0.1, -0.46, -0.34))
    lever_h = P((-0.1, -0.5, -0.33))
    w = Weapon("scattergun", g, [("lever", lever_h, lever_h + P((0, 0, -0.1)))])
    ax_a, ax_b = P((-0.1, -0.36, -0.25)), P((-0.1, -1.08, -0.2))
    w.put(along([(0.0, 0.0), (0.045, 0.0), (0.045, 0.2), (0.034, 0.24), (0.031, 0.56), (0.036, 0.6), (0.05, 0.68),
                 (0.066, 0.72), (0.062, 0.73), (0.04, 0.70), (0.0, 0.70)], ax_a, ax_b, segs=36), "blued")
    d = (ax_b - ax_a).normalized()
    for t in (0.26, 0.42, 0.56):
        w.put(ring(ax_a + d * t, d, 0.034, 0.006), "brass")
    w.put(box(0.07, 0.1, 0.24, P((-0.1, -0.44, -0.27))), "iron", bevel=0.01)
    rivets(w, [(-0.1 + x, y, -0.27 + z) for x in (-0.036, 0.036) for y in (-0.36, -0.44, -0.52) for z in (-0.03, 0.03)])
    w.put(box(0.06, 0.07, 0.42, P((-0.1, -0.68, -0.31)), rot=(4, 0, 0)), "walnut", bevel=0.012)
    w.put(box(0.05, 0.16, 0.06, g + P((0, 0.02, -0.07)), rot=(-18, 0, 0)), "walnut", bevel=0.01)
    w.put(box(0.06, 0.09, 0.2, P((-0.1, -0.24, -0.33)), rot=(-12, 0, 0)), "walnut", bevel=0.01)  # stock, under the arm
    w.put(tube([tuple(lever_h), tuple(lever_h + P((0, -0.06, -0.06))), tuple(lever_h + P((0, -0.01, -0.12))),
                tuple(lever_h + P((0, 0.05, -0.08)))], 0.007), "brass", bone="lever")
    w.put(C.prim("uv_sphere", radius=0.012, segments=10, ring_count=6, location=lever_h + P((0, 0.05, -0.08))), "brass", "lever")
    hand(w, g + P((0, 0.0, -0.03)), (0, 0.3, -1), (0, -1, 0), ELBOW)
    poses = recoil(0.05, 7, part="lever", part_rot=(55, 0, 0))
    for k in range(1, 9):  # the lever throws open and back as the kick settles
        t = (k - 1) / 5
        poses[k]["lever"] = (55 * math.sin(math.pi * min(t, 1.0)), 0, 0)
    C.build(w, frames(poses))


def spitter():
    """3, the Spitter: slag thrown through a blued barrel from a glass-sided
    crucible on top, with a pressure gauge and a valve wheel."""
    g = P((-0.09, -0.42, -0.36))
    cy = -0.6
    w = Weapon("spitter", g, [("wheel", (-0.09, cy, -0.06), (-0.09, cy, 0.0))])
    a, b = P((-0.09, -0.5, -0.27)), P((-0.09, -1.08, -0.27))
    w.put(along([(0.0, 0.0), (0.046, 0.0), (0.046, 0.02), (0.038, 0.03), (0.036, 0.4), (0.04, 0.41), (0.04, 0.44),
                 (0.036, 0.45), (0.036, 0.5), (0.045, 0.52), (0.053, 0.56), (0.055, 0.58), (0.05, 0.586), (0.03, 0.584),
                 (0.0, 0.56)], a, b, segs=36), "blued")
    d = (b - a).normalized()
    for t in (0.2, 0.3, 0.44):
        w.put(ring(a + d * t, d, 0.039, 0.007), "brass")
    w.put(rod(a + d * 0.575, a + d * 0.579, 0.03), "slag")
    w.put(box(0.1, 0.13, 0.26, P((-0.09, -0.42, -0.27))), "iron", bevel=0.012)
    rivets(w, [(-0.09 + x * 1.04, y, -0.27 + z) for x in (-0.05, 0.05) for y in (-0.34, -0.42, -0.5) for z in (-0.045, 0.045)])
    cz = -0.2
    w.put(C.lathe("base", [(0.0, 0.0), (0.066, 0.0), (0.066, 0.016), (0.058, 0.02)], segs=36, at=(-0.09, cy, cz)), "iron")
    w.put(rod((-0.09, cy, cz + 0.018), (-0.09, cy, cz + 0.1), 0.043), "slag")
    for i in range(8):
        an = math.tau * i / 8 + 0.2
        p = P((-0.09 + 0.057 * math.cos(an), cy + 0.057 * math.sin(an), 0))
        w.put(rod(p + P((0, 0, cz + 0.015)), p + P((0, 0, cz + 0.1)), 0.0045, segs=8), "iron")
    w.put(C.lathe("cap", [(0.066, 0.0), (0.066, 0.014), (0.05, 0.03), (0.02, 0.045), (0.0, 0.048)], segs=36, at=(-0.09, cy, cz + 0.095)), "iron")
    wh = P((-0.09, cy, cz + 0.16))
    w.put(rod(wh - P((0, 0, 0.02)), wh, 0.005, segs=8), "brass")
    w.put(ring(wh, (0, 0, 1), 0.026, 0.0045), "brass", "wheel")
    for i in range(3):
        an = math.tau * i / 3
        w.put(rod(wh, wh + P((0.026 * math.cos(an), 0.026 * math.sin(an), 0)), 0.0028, segs=6), "brass", "wheel")
    gp = P((0.0, -0.4, -0.2))
    gm = Matrix.Translation(gp) @ Matrix.Rotation(math.radians(55), 4, "Y")
    gg = C.prim("cylinder", radius=0.032, depth=0.016, vertices=28)
    gg.matrix_world = gm
    w.put(gg, "brass")
    face = C.prim("cylinder", radius=0.026, depth=0.002, vertices=28)
    face.matrix_world = gm @ Matrix.Translation((0, 0, 0.009))
    w.put(face, "gauge")
    for s in (-1, 1):
        x0 = -0.09 + s * 0.045
        w.put(tube([(x0, cy - 0.01, cz + 0.07), (-0.09 + s * 0.075, cy - 0.05, cz + 0.05), (-0.09 + s * 0.06, cy - 0.13, -0.24),
                    (-0.09 + s * 0.036, cy - 0.2, -0.26)], 0.0075), "brass")
    w.put(tube([(-0.05, -0.4, -0.22), (-0.03, -0.46, -0.2), (-0.04, cy + 0.04, cz + 0.06)], 0.006), "copper")
    w.put(box(0.044, 0.17, 0.066, g + P((0, 0.02, -0.08)), rot=(-18, 0, 0)), "walnut", bevel=0.01)
    hand(w, g + P((0, 0, -0.02)), (0, 0.3, -1), (0, -1, 0), ELBOW)
    poses = recoil(0.012, 1.2, part="wheel", part_rot=(0, 0, 360), loop=True, period=8)
    for k in range(1, 9):
        poses[k]["wheel"] = (0, 0, 45 * k)
    C.build(w, frames(poses))


def bolt_caster():
    """4, the Bolt Caster: a rivet thrower, two leaf-spring limbs across an
    iron rail and a drum of red-hot rivets under it."""
    g = P((-0.08, -0.44, -0.37))
    lh = P((-0.08, -0.86, -0.25))
    w = Weapon("bolt", g, [("limb_l", lh, lh + P((0.2, 0, 0))), ("limb_r", lh, lh + P((-0.2, 0, 0))),
                           ("drum", (-0.08, -0.6, -0.33), (-0.08, -0.7, -0.33))])
    w.put(box(0.06, 0.05, 0.66, P((-0.08, -0.72, -0.26))), "iron", bevel=0.008)
    w.put(box(0.03, 0.018, 0.6, P((-0.08, -0.74, -0.226))), "steel", bevel=0.004)
    w.put(box(0.1, 0.11, 0.2, P((-0.08, -0.46, -0.27))), "iron", bevel=0.012)
    rivets(w, [(-0.08 + x, y, -0.27 + z) for x in (-0.051, 0.051) for y in (-0.4, -0.52) for z in (-0.04, 0.04)])
    for s, bn in ((1, "limb_l"), (-1, "limb_r")):
        pts = [lh + P((s * 0.02, 0, 0)), lh + P((s * 0.12, 0.03, 0.01)), lh + P((s * 0.22, 0.09, 0.0)), lh + P((s * 0.26, 0.14, -0.01))]
        w.put(tube([tuple(p) for p in pts], 0.011), "steel", bn)
        w.put(rod(pts[-1], pts[-1] + P((0, 0, 0.03)), 0.012, segs=10), "brass", bn)
    w.put(tube([tuple(lh + P((0.26, 0.14, 0.0))), (-0.08, -0.5, -0.23), tuple(lh + P((-0.26, 0.14, 0.0)))], 0.003), "iron")
    w.put(box(0.06, 0.06, 0.1, lh + P((0, 0.02, 0))), "brass", bevel=0.008)
    dc = P((-0.08, -0.65, -0.33))
    w.put(along([(0.0, 0.0), (0.05, 0.0), (0.055, 0.01), (0.055, 0.07), (0.05, 0.08), (0.0, 0.08)], dc - P((0, 0.04, 0)), dc + P((0, -0.04, 0)) - P((0, 0.04, 0)) * -2, segs=20), "brass", "drum")
    for i in range(10):
        an = math.tau * i / 10
        p = dc + P((0.056 * math.cos(an), 0, 0.056 * math.sin(an)))
        w.put(rod(p + P((0, 0.03, 0)), p + P((0, -0.05, 0)), 0.006, segs=8), "ember", "drum")
    w.put(rod((-0.08, -0.85, -0.19), (-0.08, -1.0, -0.19), 0.01, segs=10), "ember")
    w.put(box(0.044, 0.17, 0.066, g + P((0, 0.02, -0.08)), rot=(-18, 0, 0)), "walnut", bevel=0.01)
    hand(w, g + P((0, 0, -0.02)), (0, 0.3, -1), (0, -1, 0), ELBOW)
    poses = recoil(0.02, 2.0, loop=True, period=4)
    for k in range(1, 9):
        snap = math.cos(math.tau * ((k - 1) % 4) / 4)  # the limbs spring forward and draw back twice a turn of the drum
        poses[k]["limb_l"] = (0, 0, -9 * snap)
        poses[k]["limb_r"] = (0, 0, 9 * snap)
        poses[k]["drum"] = (0, 18 * k, 0)
    C.build(w, frames(poses))


def crucible():
    """5, the Crucible: a stubby wide-bore launcher with a lidded pot of molten
    iron riding on top, ladling a load into the breech each shot."""
    g = P((-0.1, -0.44, -0.38))
    lid_h = P((-0.1, -0.52, -0.08))
    w = Weapon("crucible", g, [("lid", lid_h, lid_h + P((0, -0.1, 0)))])
    a, b = P((-0.1, -0.5, -0.27)), P((-0.1, -1.0, -0.25))
    w.put(along([(0.0, 0.0), (0.062, 0.0), (0.062, 0.04), (0.054, 0.06), (0.052, 0.4), (0.062, 0.44), (0.064, 0.5),
                 (0.046, 0.505), (0.0, 0.48)], a, b, segs=36), "iron")
    w.put(box(0.08, 0.1, 0.16, P((-0.1, -0.44, -0.28))), "iron", bevel=0.014)
    rivets(w, [(-0.1 + x, y, -0.28 + z) for x in (-0.041, 0.041) for y in (-0.39, -0.49) for z in (-0.03, 0.03)])
    d = (b - a).normalized()
    w.put(rod(a + d * 0.495, a + d * 0.5, 0.044), "dark")
    for t in (0.1, 0.26, 0.42):
        w.put(ring(a + d * t, d, 0.054, 0.008), "copper")
    pc = P((-0.1, -0.62, -0.2))
    w.put(C.lathe("pot", [(0.0, 0.0), (0.05, 0.0), (0.066, 0.03), (0.072, 0.08), (0.075, 0.1), (0.068, 0.105)], segs=32, at=tuple(pc)), "bronze")
    w.put(rod(pc + P((0, 0, 0.07)), pc + P((0, 0, 0.098)), 0.062), "slag")
    for s in (-1, 1):
        w.put(box(0.012, 0.09, 0.02, pc + P((s * 0.06, 0, -0.03))), "iron")
    lid = C.lathe("lid", [(0.0, 0.03), (0.04, 0.025), (0.072, 0.008), (0.076, 0.0)], segs=32, at=tuple(pc + P((0, 0, 0.1))))
    w.put(lid, "iron", "lid")
    w.put(rod(pc + P((0, 0, 0.13)), pc + P((0, 0, 0.15)), 0.012), "brass", "lid")
    w.put(tube([tuple(lid_h), tuple(lid_h + P((0, -0.04, 0.03))), tuple(pc + P((0, 0.04, 0.12)))], 0.006), "brass", "lid")
    w.put(tube([tuple(pc + P((0, -0.05, -0.02))), tuple(pc + P((0, -0.1, -0.06))), tuple(a + d * 0.38 + P((0, 0, 0.06)))], 0.012), "copper")
    w.put(box(0.05, 0.17, 0.07, g + P((0, 0.02, -0.07)), rot=(-18, 0, 0)), "walnut", bevel=0.01)
    hand(w, g + P((0, 0, -0.03)), (0, 0.3, -1), (0, -1, 0), ELBOW)
    poses = recoil(0.06, 8)
    for k in range(1, 9):
        t = (k - 1) / 5
        poses[k]["lid"] = (-40 * math.sin(math.pi * min(t, 1.0)), 0, 0)
    C.build(w, frames(poses))


def steam_cannon():
    """6, the Steam Cannon: a riveted boiler with a horn mouth, a gauge on top
    and a relief valve that blows on every shot."""
    g = P((-0.1, -0.44, -0.4))
    vh = P((-0.05, -0.56, -0.17))
    w = Weapon("steam", g, [("valve", vh, vh + P((0, 0, 0.06)))])
    a, b = P((-0.1, -0.36, -0.28)), P((-0.1, -0.82, -0.27))
    w.put(along([(0.0, 0.0), (0.05, 0.0), (0.068, 0.03), (0.072, 0.06), (0.072, 0.4), (0.064, 0.44), (0.0, 0.46)], a, b, segs=40), "copper")
    d = (b - a).normalized()
    for t in (0.08, 0.2, 0.32, 0.4):
        w.put(ring(a + d * t, d, 0.073, 0.006), "iron")
        rivets(w, [tuple(a + d * t + P((0.075 * math.cos(q), 0, 0.075 * math.sin(q)))) for q in (0.4, 1.2, 2.0, 2.8)], r=0.0045)
    h0 = a + d * 0.44
    w.put(along([(0.0, 0.0), (0.04, 0.0), (0.04, 0.05), (0.05, 0.16), (0.08, 0.24), (0.12, 0.28), (0.124, 0.29),
                 (0.11, 0.285), (0.07, 0.25), (0.03, 0.2), (0.0, 0.2)], h0, h0 + d, segs=40), "brass")
    w.put(rod(h0 + d * 0.198, h0 + d * 0.2, 0.03), "dark")
    gp = a + d * 0.22 + P((0, 0, 0.072))
    w.put(rod(gp, gp + P((0, 0, 0.03)), 0.012), "brass")
    gg = C.prim("cylinder", radius=0.04, depth=0.02, vertices=28)
    gg.matrix_world = Matrix.Translation(gp + P((0, 0.0, 0.05))) @ Matrix.Rotation(math.radians(-62), 4, "X")
    w.put(gg, "brass")
    face = C.prim("cylinder", radius=0.033, depth=0.002, vertices=28)
    face.matrix_world = Matrix.Translation(gp + P((0, 0.0, 0.05))) @ Matrix.Rotation(math.radians(-62), 4, "X") @ Matrix.Translation((0, 0, 0.011))
    w.put(face, "gauge")
    w.put(rod(vh - P((0, 0, 0.03)), vh, 0.01), "iron")
    w.put(rod(vh, vh + P((0, 0, 0.02)), 0.016), "brass", "valve")
    w.put(C.prim("uv_sphere", radius=0.012, segments=10, ring_count=6, location=vh + P((0, 0, 0.032))), "brass", "valve")
    w.put(box(0.1, 0.1, 0.12, P((-0.1, -0.34, -0.3))), "iron", bevel=0.014)
    w.put(rod((-0.1, -0.36, -0.355), (-0.1, -0.36, -0.37), 0.014), "pilot")
    w.put(box(0.05, 0.17, 0.07, g + P((0, 0.02, -0.07)), rot=(-18, 0, 0)), "walnut", bevel=0.01)
    hand(w, g + P((0, 0, -0.03)), (0, 0.3, -1), (0, -1, 0), ELBOW)
    poses = recoil(0.075, 10)
    for k in range(1, 9):
        t = (k - 1) / 5
        poses[k]["valve"] = (0, 0, 0)
        poses[k]["move"] = poses[k]["move"]
        poses[k]["valve"] = (-25 * max(0.0, 1 - t), 0, 0)
    C.build(w, frames(poses))


def shot_mortar():
    """7, the Shot Mortar: a short fat barrel fed from a six-shell drum that
    turns a chamber on with every shot."""
    g = P((-0.1, -0.44, -0.42))
    dc = P((-0.1, -0.5, -0.27))
    w = Weapon("mortar", g, [("drum", tuple(dc), tuple(dc + P((0, -0.1, 0))))])
    a, b = P((-0.1, -0.58, -0.25)), P((-0.1, -1.0, -0.24))
    w.put(along([(0.0, 0.0), (0.075, 0.0), (0.075, 0.03), (0.066, 0.05), (0.064, 0.34), (0.08, 0.38), (0.085, 0.42),
                 (0.06, 0.425), (0.0, 0.4)], a, b, segs=36), "blued")
    d = (b - a).normalized()
    w.put(rod(a + d * 0.41, a + d * 0.42, 0.058), "dark")
    for t in (0.12, 0.24):
        w.put(ring(a + d * t, d, 0.067, 0.008), "brass")
    w.put(along([(0.0, 0.0), (0.1, 0.0), (0.106, 0.01), (0.106, 0.14), (0.1, 0.15), (0.0, 0.15)], dc + P((0, 0.07, 0)), dc + P((0, -0.2, 0)), segs=36), "iron", bone="drum")
    for i in range(6):
        an = math.tau * i / 6
        p = dc + P((0.068 * math.cos(an), 0, 0.068 * math.sin(an)))
        w.put(rod(p + P((0, 0.0725, 0)), p + P((0, 0.0745, 0)), 0.026, segs=16), "brass", "drum")
        w.put(rod(p + P((0, 0.0745, 0)), p + P((0, 0.077, 0)), 0.01, segs=10), "ember", "drum")
        q = dc + P((0.107 * math.cos(an + 0.52), -0.075, 0.107 * math.sin(an + 0.52)))
        w.put(box(0.012, 0.012, 0.12, q), "steel", "drum")
    w.put(rod(dc + P((0, 0.09, 0)), dc + P((0, -0.1, 0)), 0.018), "steel")
    w.put(box(0.12, 0.06, 0.1, P((-0.1, -0.39, -0.33))), "iron", bevel=0.012)
    w.put(box(0.05, 0.17, 0.07, g + P((0, 0.02, -0.07)), rot=(-18, 0, 0)), "walnut", bevel=0.01)
    hand(w, g + P((0, 0, -0.03)), (0, 0.3, -1), (0, -1, 0), ELBOW)
    poses = recoil(0.07, 9)
    for k in range(1, 9):
        t = min((k - 1) / 4, 1.0)
        poses[k]["drum"] = (0, 60 * C.ease(t), 0)
    C.build(w, frames(poses))


def tolling_iron():
    """8, the Tolling Iron: a bronze bell carried mouth-forward on an iron yoke,
    rung by a hammer the trigger throws. Its toll is what it fires."""
    g = P((-0.1, -0.44, -0.42))
    hh = P((-0.1, -0.5, -0.17))
    bc = P((-0.1, -0.78, -0.24))
    w = Weapon("toll", g, [("hammer", tuple(hh), tuple(hh + P((0, -0.2, 0)))), ("bell", tuple(bc), tuple(bc + P((0, -0.1, 0))))])
    w.put(box(0.09, 0.1, 0.26, P((-0.1, -0.46, -0.28))), "iron", bevel=0.012)
    w.put(box(0.05, 0.03, 0.3, P((-0.1, -0.68, -0.22))), "iron", bevel=0.006)
    bell = along([(0.0, 0.0), (0.035, 0.0), (0.045, 0.02), (0.05, 0.06), (0.056, 0.11), (0.07, 0.16), (0.095, 0.2),
                  (0.11, 0.22), (0.105, 0.226), (0.09, 0.21), (0.065, 0.17), (0.05, 0.12), (0.042, 0.07), (0.03, 0.03), (0.0, 0.03)],
                 bc + P((0, 0.06, 0)), bc + P((0, -1, 0)), segs=40)
    w.put(bell, "bronze", "bell")
    w.put(ring(bc + P((0, -0.14, 0)), (0, 1, 0), 0.075, 0.005), "brass", "bell")
    w.put(C.prim("uv_sphere", radius=0.022, segments=12, ring_count=8, location=bc + P((0, -0.09, 0))), "ember", "bell")
    for s in (-1, 1):
        w.put(tube([(bc.x + s * 0.06, -0.56, -0.26), (bc.x + s * 0.09, -0.66, -0.25), (bc.x + s * 0.06, bc.y + 0.02, bc.z)], 0.008), "iron")
    w.put(rod(hh + P((-0.03, 0, 0)), hh + P((0.03, 0, 0)), 0.01, segs=10), "iron")
    w.put(tube([tuple(hh), tuple(hh + P((0, -0.12, 0.03))), tuple(hh + P((0, -0.22, 0.01)))], 0.008), "iron", "hammer")
    w.put(rod(hh + P((0, -0.22, -0.03)), hh + P((0, -0.22, 0.05)), 0.02, segs=14), "bronze", "hammer")
    w.put(C.prim("uv_sphere", radius=0.012, segments=10, ring_count=6, location=(-0.1, -0.58, -0.2)), "pilot")
    w.put(box(0.05, 0.17, 0.07, g + P((0, 0.02, -0.07)), rot=(-18, 0, 0)), "walnut", bevel=0.01)
    hand(w, g + P((0, 0, -0.03)), (0, 0.3, -1), (0, -1, 0), ELBOW)
    poses = recoil(0.015, 1.5, loop=True, period=4)
    for k in range(1, 9):
        ph = (k - 1) % 4
        poses[k]["hammer"] = ([-35, 6, -10, -24][ph], 0, 0)
        poses[k]["bell"] = (0, [0, 4, -3, 1.5][ph], [0, 2.5, -2, 1][ph])
    C.build(w, frames(poses))


def viewshot(name, names, positions, tris, st, albedo, out, size=None):
    """VIEWSHOT=dir: frames 0, 1 and 4 seen from the eye as the engine draws a
    view model (the gun's own 90 degree field of view, 16:9), with the status
    bar's band shaded, to place the weapons without starting the game."""
    sc = bpy.context.scene
    res = C.RES
    img = bpy.data.images.new("skin", res, res)
    import numpy as np
    px = np.ones((res, res, 4), dtype=np.float32)
    px[:, :, :3] = np.clip(albedo[::-1], 0, 1)
    img.pixels.foreach_set(px.ravel())
    m = bpy.data.materials.new("vs")
    m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 2.5
    nt.links.new(em.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])
    me = bpy.data.meshes.new("vs")
    me.from_pydata(positions[0].tolist(), [], [list(t) for t in tris])
    uvl = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            u, v = st[me.loops[li].vertex_index]
            uvl.data[li].uv = (u, 1 - v)
    me.materials.append(m)
    ob = bpy.data.objects.new("vs", me)
    sc.collection.objects.link(ob)
    for o in list(sc.objects):
        if o.type == "MESH" and o is not ob:
            o.hide_render = True
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.rotation_euler = (math.pi / 2, 0, -math.pi / 2)  # looking down +X, up +Z
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle = 2 * math.atan(0.75)
    cam.data.clip_start = 2.0
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.2, 0.17, 0.15)
    sc.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "CYCLES"
    sc.cycles.samples = 4
    sc.render.resolution_x, sc.render.resolution_y = 640, 360
    sheet = []
    path = os.path.join(out, "frame.png")
    for f in (0, 1, 4):
        me.vertices.foreach_set("co", positions[f].ravel())
        me.update()
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(path)
        a = C.pixels(im).reshape(360, 640, 4)[::-1, :, :3]
        bpy.data.images.remove(im)
        a[324:] *= 0.35  # where the status bar covers it
        sheet.append(a)
    a = np.concatenate(sheet, axis=1)
    o = bpy.data.images.new("sheet", a.shape[1], a.shape[0])
    q = np.ones((a.shape[0], a.shape[1], 4), dtype=np.float32)
    q[:, :, :3] = a[::-1]
    o.pixels.foreach_set(q.ravel())
    o.filepath_raw = os.path.join(out, name + "_view.png")
    o.file_format = "PNG"
    o.save()


if os.environ.get("VIEWSHOT"):
    os.environ["PREVIEW"] = os.environ["VIEWSHOT"]
    C.preview = viewshot


WEAPONS = {"pick": pick, "scattergun": scattergun, "spitter": spitter, "bolt": bolt_caster,
           "crucible": crucible, "steam": steam_cannon, "mortar": shot_mortar, "toll": tolling_iron}

if __name__ == "__main__":
    for name, make in WEAPONS.items():
        if not C.ONLY or name in C.ONLY:
            make()
