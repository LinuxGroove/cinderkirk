"""Cinderkirk mockup models, built in code in headless Blender and exported as
glTF for the mockup page: the Deacon (a creature), the Spitter (a first person
weapon with the stoker's gloved hand) and the cracked bell.

    python models.py -- <out dir>          (with the bpy wheel)

Materials carry names the page maps to the baked textures from materials.py
(robe -> cloth_char1, iron -> iron_plate1, bronze -> bronze1 and so on). Every
mesh gets a cube projection at a real-world scale, so the tiling textures keep
their size. In the game these would be exported as MD5 (or MD3) with their
animations; the mockup only needs one pose.
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy first: it makes bmesh importable)
import bmesh
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "models")

COLORS = {
    "robe": ((0.05, 0.045, 0.04), 0.9, 0.0),
    "iron": ((0.08, 0.08, 0.085), 0.5, 0.9),
    "blued": ((0.05, 0.055, 0.07), 0.35, 0.95),
    "brass": ((0.62, 0.43, 0.18), 0.3, 1.0),
    "bronze": ((0.5, 0.33, 0.15), 0.35, 1.0),
    "wood": ((0.16, 0.08, 0.04), 0.6, 0.0),
    "leather": ((0.12, 0.06, 0.03), 0.6, 0.0),
    "coal": ((1.0, 0.4, 0.05), 0.5, 0.0),
    "glow": ((1.0, 0.45, 0.08), 0.5, 0.0),
    "crack_glow": ((1.0, 0.6, 0.2), 0.5, 0.0),
    "glass": ((0.6, 0.5, 0.4), 0.1, 0.0),
    "gauge_face": ((0.8, 0.75, 0.6), 0.5, 0.0),
    "hood_inner": ((0.0, 0.0, 0.0), 1.0, 0.0),
    "sleeve": ((0.05, 0.045, 0.04), 0.9, 0.0),
}


def mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    col, rough, metal = COLORS[name]
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*col, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if name in ("coal", "glow", "crack_glow"):
        b.inputs["Emission Color"].default_value = (*col, 1.0)
        b.inputs["Emission Strength"].default_value = 4.0
    return m


def finish_obj(o, material, uv=1.0, smooth=True, bevel=0.0):
    o.data.materials.clear()
    o.data.materials.append(mat(material))
    bpy.context.view_layer.objects.active = o
    for other in bpy.context.selected_objects:
        other.select_set(False)
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if bevel:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = 2
        m.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier="bevel")
    for p in o.data.polygons:
        p.use_smooth = smooth
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=uv, correct_aspect=False, scale_to_bounds=False, clip_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return o


def new_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return o


def lathe(name, profile, segs=48, shape=None, skip=None):
    """A surface of revolution about Z from (r, z) points. shape(a, z, x, y)
    may move each vertex (folds, ragged hems, a hunch); skip(a, z) leaves a
    face out (the hood's opening)."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(segs):
            a = math.tau * i / segs
            x, y = r * math.cos(a), r * math.sin(a)
            if shape:
                x, y, z2 = shape(a, z, x, y)
            else:
                z2 = z
            ring.append(bm.verts.new((x, y, z2)))
        rings.append(ring)
    for j in range(len(rings) - 1):
        for i in range(segs):
            a = math.tau * (i + 0.5) / segs
            zm = (profile[j][1] + profile[j + 1][1]) / 2
            if skip and skip(a, zm):
                continue
            v = [rings[j][i], rings[j][(i + 1) % segs], rings[j + 1][(i + 1) % segs], rings[j + 1][i]]
            try:
                bm.faces.new(v)
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(name, bm)


def prim(kind, **kw):
    getattr(bpy.ops.mesh, "primitive_%s_add" % kind)(**kw)
    return bpy.context.active_object


def between(kind, a, b, **kw):
    """A cylinder or cone from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    o = prim(kind, depth=d.length, **kw)
    o.location = (a + b) / 2
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return o


def tube(name, pts, radius, material, uv=1.0, closed=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1.0)
    sp.order_u = min(4, len(pts))
    sp.use_endpoint_u = True
    sp.resolution_u = 8
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    for other in bpy.context.selected_objects:
        other.select_set(False)
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return finish_obj(bpy.context.active_object, material, uv)


def chain(name, a, b, link=0.06, thick=0.008, uv=1.0):
    """Iron links from a to b, alternating a quarter turn."""
    a, b = Vector(a), Vector(b)
    d = b - a
    n = max(2, int(d.length / (link * 0.78)))
    q = d.to_track_quat("Z", "Y")
    for i in range(n):
        o = prim("torus", major_radius=link * 0.38, minor_radius=thick, major_segments=14, minor_segments=6)
        o.scale = (0.75, 1.0, 1.0)
        o.rotation_euler = (q @ Matrix.Rotation(math.pi / 2 * (i % 2), 4, "Z").to_quaternion()
                            @ Matrix.Rotation(math.pi / 2, 4, "X").to_quaternion()).to_euler()
        o.location = a + d * ((i + 0.5) / n)
        o.name = "%s_%d" % (name, i)
        finish_obj(o, "iron", uv)


def export(path, scale=1.0):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True,
                              use_selection=False, export_materials="EXPORT", export_image_format="NONE")
    print("saved", path, flush=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


# ---------------------------------------------------------------- the Deacon

def deacon():
    """A Deacon of the Throat: a hunched, hooded foundry priest with a coal
    for a face behind an iron grille, a censer of live coals on a chain and a
    bell-hook staff. About 2.6 m tall: the large hull. Faces -Y."""
    reset()
    H = 1.75

    def robe_shape(a, z, x, y):
        t = z / H
        fold = 1 + 0.07 * math.sin(9 * a + 0.6) * (1 - t) + 0.03 * math.sin(17 * a + 2 * t)
        x, y = x * fold, y * fold
        y -= 0.20 * t ** 2
        if z < 0.01:
            z = -0.02 + 0.06 * math.sin(7 * a) + 0.035 * math.sin(13 * a + 1.3)
        return x, y, z

    lathe("robe", [(0.70, 0.0), (0.67, 0.12), (0.58, 0.45), (0.47, 0.85), (0.40, 1.2), (0.37, 1.5), (0.33, H)],
          segs=64, shape=robe_shape)
    finish_obj(bpy.data.objects["robe"], "robe", 2.0)

    def mantle_shape(a, z, x, y):
        fold = 1 + 0.06 * math.sin(7 * a + 1.0)
        return x * fold * 1.12, y * fold - 0.30 - 0.10 * (z - 1.6), z
    lathe("mantle", [(0.30, 1.58), (0.52, 1.74), (0.50, 1.92), (0.36, 2.06), (0.16, 2.12)], segs=48, shape=mantle_shape)
    finish_obj(bpy.data.objects["mantle"], "robe", 2.0)

    # Hood: open at the front (-Y is a = 270 degrees).
    def hood_shape(a, z, x, y):
        t = (z - 2.0) / 0.6
        y = y - 0.40 - 0.10 * t
        if z > 2.5:
            y -= 0.12 * (z - 2.5) / 0.1
        return x, y, z

    def hood_skip(a, z):
        return abs(a - 1.5 * math.pi) < 0.75 and 2.06 < z < 2.40

    lathe("hood", [(0.20, 1.98), (0.26, 2.08), (0.28, 2.22), (0.27, 2.36), (0.21, 2.48), (0.11, 2.56), (0.02, 2.6)],
          segs=40, shape=hood_shape, skip=hood_skip)
    hood = finish_obj(bpy.data.objects["hood"], "robe", 2.0)
    sol = hood.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.025
    bpy.context.view_layer.objects.active = hood
    bpy.ops.object.modifier_apply(modifier="thick")
    inner = prim("uv_sphere", radius=0.22, segments=24, ring_count=12, location=(0, -0.40, 2.26))
    finish_obj(inner, "hood_inner")
    # The face: a coal behind an iron grille.
    coal = prim("uv_sphere", radius=0.13, segments=24, ring_count=12, location=(0, -0.50, 2.24))
    coal.scale = (1.0, 0.6, 1.15)
    finish_obj(coal, "coal", 0.5)
    for i in range(5):
        x = -0.10 + i * 0.05
        bar = between("cylinder", (x, -0.64, 2.10), (x * 0.85, -0.66, 2.38), radius=0.011, vertices=8)
        finish_obj(bar, "iron", 1.0)
    for z in (2.14, 2.30):
        band = between("cylinder", (-0.13, -0.645, z), (0.13, -0.645, z), radius=0.012, vertices=8)
        finish_obj(band, "iron", 1.0)

    # Right arm raised, holding the censer's chain.
    sh, el, wr = (0.44, -0.30, 1.92), (0.66, -0.58, 1.70), (0.72, -0.92, 1.92)
    finish_obj(between("cone", sh, el, radius1=0.12, radius2=0.15, vertices=20), "robe", 2.0)
    finish_obj(between("cone", el, (0.71, -0.83, 1.86), radius1=0.12, radius2=0.18, vertices=20), "robe", 2.0)
    finish_obj(between("cone", (0.70, -0.78, 1.84), wr, radius1=0.06, radius2=0.055, vertices=16), "iron", 1.0, bevel=0.004)
    hand = prim("uv_sphere", radius=0.06, segments=16, ring_count=8, location=(0.73, -0.96, 1.95))
    hand.scale = (1.0, 1.2, 0.8)
    finish_obj(hand, "iron", 1.0)
    for k in range(3):
        finish_obj(between("cone", (0.71 + 0.02 * k, -1.0, 1.96), (0.70 + 0.025 * k, -1.06, 1.88), radius1=0.012, radius2=0.004, vertices=8), "iron", 1.0)
    # Censer: an iron cage of live coals, swung out to the side.
    cen = Vector((0.98, -1.08, 1.12))
    chain("cchain", (0.73, -1.0, 1.9), cen + Vector((0, 0, 0.17)), link=0.07, thick=0.008)
    lathe("censer_bowl", [(0.0, -0.15), (0.09, -0.13), (0.14, -0.06), (0.15, 0.0)], segs=24)
    bowl = bpy.data.objects["censer_bowl"]
    bowl.location = cen
    finish_obj(bowl, "iron", 1.0)
    lathe("censer_cap", [(0.15, 0.06), (0.12, 0.11), (0.06, 0.15), (0.0, 0.17)], segs=24)
    cap = bpy.data.objects["censer_cap"]
    cap.location = cen
    finish_obj(cap, "iron", 1.0)
    for i in range(8):
        a = math.tau * i / 8
        p0 = cen + Vector((0.15 * math.cos(a), 0.15 * math.sin(a), 0.0))
        p1 = cen + Vector((0.15 * math.cos(a), 0.15 * math.sin(a), 0.07))
        finish_obj(between("cylinder", p0, p1, radius=0.008, vertices=6), "iron", 1.0)
    c = prim("uv_sphere", radius=0.115, segments=20, ring_count=10, location=cen + Vector((0, 0, 0.02)))
    finish_obj(c, "coal", 0.3)

    # Left arm down to the bell-hook staff.
    sh, el, wr = (-0.44, -0.30, 1.92), (-0.60, -0.48, 1.55), (-0.58, -0.70, 1.40)
    finish_obj(between("cone", sh, el, radius1=0.12, radius2=0.15, vertices=20), "robe", 2.0)
    finish_obj(between("cone", el, (-0.585, -0.64, 1.43), radius1=0.12, radius2=0.18, vertices=20), "robe", 2.0)
    finish_obj(between("cone", (-0.585, -0.60, 1.44), wr, radius1=0.06, radius2=0.055, vertices=16), "iron", 1.0, bevel=0.004)
    lh = prim("uv_sphere", radius=0.065, segments=16, ring_count=8, location=(-0.57, -0.74, 1.40))
    finish_obj(lh, "iron", 1.0)
    top = Vector((-0.60, -0.80, 2.85))
    finish_obj(between("cylinder", (-0.55, -0.72, 0.0), top, radius=0.022, vertices=10), "iron", 1.0)
    hook = [top, top + Vector((0.0, -0.06, 0.16)), top + Vector((0.0, -0.22, 0.22)), top + Vector((0.0, -0.32, 0.12)), top + Vector((0.0, -0.30, 0.02))]
    tube("hook", [tuple(p) for p in hook], 0.02, "iron")
    chain("hchain", top + Vector((0, -0.30, 0.02)), top + Vector((0, -0.30, -0.22)), link=0.05, thick=0.006)
    lathe("hbell", [(0.10, 0.0), (0.095, 0.02), (0.07, 0.08), (0.06, 0.15), (0.03, 0.18), (0.0, 0.185)], segs=24)
    hb = bpy.data.objects["hbell"]
    hb.location = top + Vector((0, -0.30, -0.43))
    finish_obj(hb, "bronze", 0.5)

    # A chain belt, links round the robe at the waist.
    n = 26
    for i in range(n):
        a = math.tau * i / n
        r = 0.46
        o = prim("torus", major_radius=0.035, minor_radius=0.009, major_segments=12, minor_segments=6)
        o.scale = (1.4, 1.0, 1.0)
        o.rotation_euler = (math.pi / 2 * (i % 2), 0, a + math.pi / 2)
        o.location = (r * math.cos(a), r * math.sin(a) - 0.09, 1.08 + 0.05 * math.sin(a))
        finish_obj(o, "iron", 1.0)
    export(os.path.join(OUT, "deacon.glb"))


# --------------------------------------------------------------- the Spitter

def spitter():
    """The Spitter: a slag thrower held in the stoker's right hand. Forward is
    +Y (glTF -Z, the camera's forward). Origin at the grip."""
    reset()
    rx = Matrix.Rotation(-math.pi / 2, 4, "X")

    def along_y(o, y0=0.0, z0=0.0, x0=0.0):
        o.matrix_world = Matrix.Translation((x0, y0, z0)) @ rx
        return o

    barrel = lathe("barrel", [(0.0, 0.0), (0.046, 0.0), (0.046, 0.02), (0.038, 0.03), (0.036, 0.40), (0.040, 0.41),
                              (0.040, 0.44), (0.036, 0.45), (0.036, 0.52), (0.045, 0.54), (0.053, 0.58), (0.055, 0.60),
                              (0.05, 0.606), (0.03, 0.604), (0.027, 0.58), (0.0, 0.58)], segs=40)
    finish_obj(along_y(barrel, 0.04), "blued", 0.6, smooth=True)
    for y in (0.24, 0.33, 0.46):
        ring = prim("torus", major_radius=0.039, minor_radius=0.007, major_segments=32, minor_segments=8)
        along_y(ring, 0.04 + y)
        finish_obj(ring, "brass", 0.5)
    glow = prim("cylinder", radius=0.031, depth=0.004, vertices=24)
    along_y(glow, 0.04 + 0.578)
    finish_obj(glow, "glow")
    drip = prim("uv_sphere", radius=0.011, segments=12, ring_count=8, location=(0.0, 0.64, -0.052))
    drip.scale = (1.0, 1.0, 1.9)
    finish_obj(drip, "coal", 0.2)

    rec = prim("cube", size=1.0, location=(0.0, -0.08, 0.0))
    rec.scale = (0.10, 0.26, 0.13)
    finish_obj(rec, "iron", 0.6, smooth=False, bevel=0.012)
    for x in (-0.05, 0.05):
        for y in (-0.18, -0.10, -0.02):
            for z in (-0.045, 0.045):
                rv = prim("uv_sphere", radius=0.006, segments=10, ring_count=6, location=(x * 1.04, y, z))
                finish_obj(rv, "brass", 0.5)

    # The crucible: molten slag behind glass in an iron cage, a valve on top.
    cz, cy = 0.03, 0.12
    base = lathe("cr_base", [(0.0, 0.0), (0.066, 0.0), (0.066, 0.016), (0.058, 0.02)], segs=40)
    base.location = (0, cy, cz)
    finish_obj(base, "iron", 0.6)
    core = prim("cylinder", radius=0.043, depth=0.08, vertices=32, location=(0, cy, cz + 0.058))
    finish_obj(core, "coal", 0.25)
    glass = prim("cylinder", radius=0.05, depth=0.085, vertices=32, location=(0, cy, cz + 0.058))
    finish_obj(glass, "glass", 0.5)
    for i in range(8):
        a = math.tau * i / 8 + 0.2
        p = Vector((0.057 * math.cos(a), cy + 0.057 * math.sin(a), 0))
        finish_obj(between("cylinder", p + Vector((0, 0, cz + 0.015)), p + Vector((0, 0, cz + 0.10)), radius=0.0045, vertices=8), "iron", 0.6)
    capm = lathe("cr_cap", [(0.066, 0.0), (0.066, 0.014), (0.05, 0.03), (0.02, 0.045), (0.0, 0.048)], segs=40)
    capm.location = (0, cy, cz + 0.095)
    finish_obj(capm, "iron", 0.6)
    wheel = prim("torus", major_radius=0.026, minor_radius=0.004, major_segments=24, minor_segments=6, location=(0, cy, cz + 0.16))
    finish_obj(wheel, "brass", 0.5)
    finish_obj(between("cylinder", (0, cy, cz + 0.14), (0, cy, cz + 0.16), radius=0.005, vertices=8), "brass", 0.5)
    for i in range(3):
        a = math.tau * i / 3
        finish_obj(between("cylinder", (0, cy, cz + 0.16), (0.026 * math.cos(a), cy + 0.026 * math.sin(a), cz + 0.16), radius=0.0025, vertices=6), "brass", 0.5)

    # A pressure gauge on the left, facing up and out, where the player sees it.
    g = prim("cylinder", radius=0.03, depth=0.014, vertices=32)
    g.matrix_world = Matrix.Translation((-0.072, -0.16, 0.05)) @ Matrix.Rotation(math.radians(-55), 4, "Y")
    finish_obj(g, "brass", 0.5)
    face = prim("cylinder", radius=0.025, depth=0.002, vertices=32)
    face.matrix_world = Matrix.Translation((-0.0798, -0.16, 0.0555)) @ Matrix.Rotation(math.radians(-55), 4, "Y")
    face.data.materials.append(mat("gauge_face"))
    face.data.materials.clear()
    face.data.materials.append(mat("gauge_face"))
    bpy.context.view_layer.objects.active = face
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    face.name = "gauge_face"

    # Pipes from the crucible down to the barrel.
    for s in (-1, 1):
        tube("pipe", [(s * 0.045, cy - 0.01, cz + 0.07), (s * 0.075, cy + 0.05, cz + 0.05), (s * 0.062, cy + 0.13, 0.03), (s * 0.038, cy + 0.19, 0.012)], 0.0075, "brass", 0.5)
        tube("feed", [(s * 0.03, -0.02, 0.066), (s * 0.05, 0.03, 0.08), (s * 0.05, cy - 0.04, cz + 0.06), (s * 0.04, cy - 0.03, cz + 0.05)], 0.006, "brass", 0.5)

    # Grip and the stoker's gloved hand round it.
    grip = prim("cube", size=1.0)
    grip.scale = (0.044, 0.066, 0.17)
    tilt = Matrix.Rotation(math.radians(-18), 4, "X")
    grip.matrix_world = Matrix.Translation((0, -0.15, -0.13)) @ tilt @ Matrix.Diagonal((0.044, 0.066, 0.17, 1))
    finish_obj(grip, "wood", 0.3, smooth=False, bevel=0.01)
    axis_top, axis_dir = Vector((0, -0.15, -0.06)), (tilt @ Vector((0, 0, -1, 0))).to_3d()
    side = Vector((1, 0, 0))
    fwd = side.cross(axis_dir).normalized()  # towards the muzzle
    palm = prim("uv_sphere", radius=0.05, segments=20, ring_count=12)
    palm.matrix_world = Matrix.Translation(axis_top + axis_dir * 0.06 + side * 0.03 + fwd * -0.012) @ tilt @ Matrix.Diagonal((0.55, 0.85, 1.15, 1))
    finish_obj(palm, "leather", 0.3)
    for k in range(4):
        c = axis_top + axis_dir * (0.025 + k * 0.026)
        pts = []
        for j in range(6):
            a = math.radians(-15 + j * 36)
            r = 0.04 + 0.004 * (j in (0, 1))
            pts.append(tuple(c + side * (r * math.cos(a)) + fwd * (r * math.sin(a) + 0.006)))
        tube("finger", pts, 0.0115 - k * 0.0007, "leather", 0.3)
    thumb = [tuple(axis_top + side * 0.03 + axis_dir * 0.02), tuple(axis_top + side * -0.01 + fwd * -0.01 + Vector((0, 0, 0.03))),
             tuple(Vector((-0.045, -0.12, 0.05))), tuple(Vector((-0.055, -0.08, 0.055)))]
    tube("thumb", thumb, 0.013, "leather", 0.3)
    wrist = axis_top + axis_dir * 0.15 + fwd * -0.04 + side * 0.02
    elbow = Vector((0.16, -0.62, -0.42))
    finish_obj(between("cone", wrist, wrist + (elbow - wrist) * 0.22, radius1=0.042, radius2=0.05, vertices=24), "leather", 0.3)
    cuff = prim("torus", major_radius=0.052, minor_radius=0.008, major_segments=28, minor_segments=8)
    q = (elbow - wrist).to_track_quat("Z", "Y")
    cuff.matrix_world = Matrix.Translation(wrist + (elbow - wrist) * 0.22) @ q.to_matrix().to_4x4()
    finish_obj(cuff, "brass", 0.5)
    finish_obj(between("cone", wrist + (elbow - wrist) * 0.2, elbow, radius1=0.056, radius2=0.075, vertices=24), "sleeve", 1.0)
    export(os.path.join(OUT, "spitter.glb"))


# --------------------------------------------------------------- the bell

def bell():
    """The shaft's bell, cracked: a lathe-turned bronze bell on a timber yoke,
    with an iron clapper and a crack that glows. Lip at z = 0, about 1.4 m."""
    reset()
    outer = [(0.74, 0.0), (0.80, 0.0), (0.80, 0.05), (0.75, 0.15), (0.63, 0.32), (0.55, 0.55), (0.51, 0.80),
             (0.495, 1.0), (0.47, 1.15), (0.40, 1.25), (0.25, 1.31), (0.0, 1.33)]
    inner = [(0.0, 1.2), (0.22, 1.18), (0.40, 1.10), (0.43, 0.95), (0.44, 0.75), (0.48, 0.5), (0.58, 0.28), (0.68, 0.12), (0.735, 0.02)]
    lathe("bell", outer + inner, segs=72)
    finish_obj(bpy.data.objects["bell"], "bronze", 1.0)
    for z, r in ((1.02, 0.50), (0.22, 0.70), (0.30, 0.66)):
        t = prim("torus", major_radius=r, minor_radius=0.014, major_segments=72, minor_segments=8, location=(0, 0, z))
        finish_obj(t, "bronze", 1.0)

    def surface_r(z):
        for (r0, z0), (r1, z1) in zip(outer[1:], outer[2:]):
            if z0 <= z <= z1:
                return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return 0.5

    # The crack, facing -Y.
    bm = bmesh.new()
    pts = [(0.00, 0.0), (0.05, 0.12), (-0.03, 0.24), (0.06, 0.38), (0.0, 0.52), (0.08, 0.66), (0.03, 0.82), (0.07, 0.94)]
    prev = None
    for (da, z) in pts:
        a = -math.pi / 2 + da
        r = surface_r(z) + 0.004
        w = 0.045 * (1.0 - z)
        p = Vector((r * math.cos(a), r * math.sin(a), z))
        t = Vector((-math.sin(a), math.cos(a), 0)) * max(w, 0.004)
        v = (bm.verts.new(p - t), bm.verts.new(p + t))
        if prev:
            bm.faces.new((prev[0], prev[1], v[1], v[0]))
        prev = v
    o = new_obj("crack", bm)
    finish_obj(o, "crack_glow", 1.0, smooth=False)

    loop = prim("torus", major_radius=0.1, minor_radius=0.03, major_segments=24, minor_segments=8, location=(0, 0, 1.40), rotation=(math.pi / 2, 0, 0))
    finish_obj(loop, "bronze", 1.0)
    yoke = prim("cube", size=1.0, location=(0, 0, 1.58))
    yoke.scale = (2.0, 0.34, 0.30)
    finish_obj(yoke, "wood", 1.0, smooth=False, bevel=0.03)
    for x in (-0.18, 0.18):
        strap = prim("cube", size=1.0, location=(x, 0, 1.50))
        strap.scale = (0.06, 0.38, 0.36)
        finish_obj(strap, "iron", 1.0, smooth=False, bevel=0.008)
    finish_obj(between("cylinder", (0, 0, 1.22), (0, 0, 0.30), radius=0.03, vertices=12), "iron", 1.0)
    ball = prim("uv_sphere", radius=0.11, segments=20, ring_count=10, location=(0, 0, 0.24))
    ball.scale = (1, 1, 1.3)
    finish_obj(ball, "iron", 1.0)
    for x in (-0.9, 0.9):
        finish_obj(between("cylinder", (x, 0, 1.70), (x, 0, 2.20), radius=0.04, vertices=12), "iron", 1.0)
    export(os.path.join(OUT, "bell.glb"))


deacon()
spitter()
bell()
