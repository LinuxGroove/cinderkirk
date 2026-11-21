"""Cinderkirk's creatures: built from primitives in headless Blender, rigged
with a skeleton posed here in numpy, skinned by baking their materials and
ambient occlusion in Cycles, and written as MD3 for vkQuake.

    python creatures.py -- <out dir> [resolution] [only=ashen,deacon]   (with the bpy wheel)
    blender -b -P creatures.py -- <out dir> [resolution]

For each creature it writes <out>/<name>.md3, <name>.png (albedo with the
occlusion in it) and <name>_luma.png (what glows), which the pak puts in
progs/. Frames come in the order of ANIMS; the creature's QuakeC lists the
same names with $frame. CYCLES_DEVICE=OPTIX (or CUDA, HIP) bakes on a GPU, and
BAKE_SAMPLES sets the occlusion's samples.

Every creature is built facing -Y with its feet at z 0, in metres, and turned
to face +X in Quake units (32 a metre) with its feet at the hull's bottom.

Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy first: it makes bmesh importable)
import bmesh
import numpy as np
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import md3  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "creatures")
RES = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 1024
ONLY = next((a[5:].split(",") for a in argv if a.startswith("only=")), None)
HERE = os.path.dirname(os.path.abspath(__file__))
TEXTURES = os.path.join(HERE, "..", "..", "assets", "textures")
UNITS = 32.0

# ------------------------------------------------------------------ building

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


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


def new_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return o


def lathe(name, profile, segs=32, shape=None, skip=None, at=(0, 0, 0)):
    """A surface of revolution about Z from (r, z) points. shape(a, z, x, y)
    may move each vertex; skip(a, z) leaves a face out."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(segs):
            a = math.tau * i / segs
            x, y, z2 = r * math.cos(a), r * math.sin(a), z
            if shape:
                x, y, z2 = shape(a, z, x, y)
            ring.append(bm.verts.new((x + at[0], y + at[1], z2 + at[2])))
        rings.append(ring)
    for j in range(len(rings) - 1):
        for i in range(segs):
            a = math.tau * (i + 0.5) / segs
            if skip and skip(a, (profile[j][1] + profile[j + 1][1]) / 2):
                continue
            try:
                bm.faces.new([rings[j][i], rings[j][(i + 1) % segs], rings[j + 1][(i + 1) % segs], rings[j + 1][i]])
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(name, bm)


def apply_all(o):
    bpy.context.view_layer.objects.active = o
    for other in bpy.context.selected_objects:
        other.select_set(False)
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def thicken(o, t):
    m = o.modifiers.new("thick", "SOLIDIFY")
    m.thickness = t
    apply_all(o)
    return o


class Creature:
    """A skeleton and the parts hung on it. Bones are (name, parent, head,
    tail): head is the pivot, and the segment head..tail is what body skin
    near it follows."""

    def __init__(self, name, bones, hull_bottom=-24.0):
        reset()
        self.name = name
        self.bones = bones
        self.index = {b[0]: i for i, b in enumerate(bones)}
        self.hull_bottom = hull_bottom
        self.parts = []

    def add(self, o, material, bone=None, among=None, smooth=True, power=4.0, anchor=None):
        """Hangs a part on the skeleton: on one bone, or blended between the
        nearest of `among` (all bones when None) by distance."""
        apply_all(o)
        o.data.materials.clear()
        o.data.materials.append(material_slot(material))
        for p in o.data.polygons:
            p.use_smooth = smooth
        co = np.array([v.co[:] for v in o.data.vertices])
        if bone:
            w = np.zeros((len(co), len(self.bones)))
            w[:, self.index[bone]] = 1.0
        else:
            w = self.auto_weights(co, among, power)
        if anchor:
            # Part of every vertex stays with one bone: a robe's hem only half follows the legs.
            name, share = anchor
            w *= 1 - share
            w[:, self.index[name]] += share
        for i, b in enumerate(self.bones):
            col = w[:, i]
            idx = np.nonzero(col > 1e-4)[0]
            if not len(idx):
                continue
            g = o.vertex_groups.get(b[0]) or o.vertex_groups.new(name=b[0])
            for j in idx:
                g.add([int(j)], float(col[j]), "REPLACE")
        self.parts.append(o)
        return o

    def auto_weights(self, co, among=None, power=4.0, keep=3):
        names = among or [b[0] for b in self.bones]
        d = np.zeros((len(co), len(self.bones))) + 1e9
        for nm in names:
            i = self.index[nm]
            a, b = np.array(self.bones[i][2]), np.array(self.bones[i][3])
            ab = b - a
            t = np.clip(((co - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
            d[:, i] = np.linalg.norm(co - (a + t[:, None] * ab), axis=1)
        w = 1.0 / np.maximum(d, 1e-3) ** power
        order = np.argsort(-w, axis=1)
        mask = np.zeros_like(w, dtype=bool)
        np.put_along_axis(mask, order[:, :keep], True, axis=1)
        w = np.where(mask, w, 0.0)
        return w / w.sum(axis=1, keepdims=True)


def skin_body(name, joints, edges, radius, root, seed=0, lumps=0.0, subdiv=2, shape=None):
    """An organic body from a stick figure: Blender's skin modifier gives every
    joint a radius (x, y), then subdivision rounds it. lumps adds noise to the
    surface, and shape(co) may push each vertex afterwards."""
    me = bpy.data.meshes.new(name)
    names = list(joints)
    me.from_pydata([joints[n] for n in names], [(names.index(a), names.index(b)) for a, b in edges], [])
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.modifiers.new("skin", "SKIN")
    for i, n in enumerate(names):
        r = radius[n]
        o.data.skin_vertices[0].data[i].radius = r if isinstance(r, tuple) else (r, r)
        o.data.skin_vertices[0].data[i].use_root = n == root
    s = o.modifiers.new("sub", "SUBSURF")
    s.levels = subdiv
    s.render_levels = subdiv
    apply_all(o)
    if lumps or shape:
        for v in o.data.vertices:
            p = v.co.copy()
            if lumps:
                q = p + Vector((seed, seed * 2, 0))
                p += v.normal * lumps * (noise.noise(q * 9.0) + 0.5 * noise.noise(q * 23.0))
            if shape:
                p = Vector(shape(p, v.normal))
            v.co = p
    return o


# ------------------------------------------------------------------ materials

# Tiles from the world textures, mapped by box projection at metres a tile.
TILES = {
    "robe": ("cloth_char1", 1.2, (1.0, 1.0, 1.0)),
    "hood": ("cloth_char1", 0.9, (0.8, 0.8, 0.8)),
    "leather": ("leather1", 0.6, (1.0, 1.0, 1.0)),
    "iron": ("iron_plate1", 0.8, (1.3, 1.3, 1.3)),
    "bronze": ("bronze1", 0.5, (1.0, 1.0, 1.0)),
    "oak": ("oak1", 0.6, (1.0, 1.0, 1.0)),
}


def material_slot(name):
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    return m


class Nodes:
    def __init__(self, mat):
        self.t = mat.node_tree
        self.t.nodes.clear()
        self.co = self.node("ShaderNodeTexCoord").outputs["Object"]
        self.out = self.node("ShaderNodeOutputMaterial")

    def node(self, kind, **props):
        nd = self.t.nodes.new(kind)
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def feed(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.t.links.new(v, sock)
        elif isinstance(v, (tuple, list)) and len(v) == 3 and sock.type == "RGBA":
            sock.default_value = (*v, 1.0)
        else:
            sock.default_value = v

    def noise(self, scale, detail=4.0, rough=0.55, seed=0.0):
        nd = self.node("ShaderNodeTexNoise", noise_dimensions="4D")
        self.feed(nd.inputs["Vector"], self.co)
        nd.inputs["W"].default_value = seed
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough
        return nd.outputs["Fac"]

    def voronoi(self, scale, feature="DISTANCE_TO_EDGE", seed=0.0):
        nd = self.node("ShaderNodeTexVoronoi", voronoi_dimensions="4D", feature=feature)
        self.feed(nd.inputs["Vector"], self.co)
        nd.inputs["W"].default_value = seed
        nd.inputs["Scale"].default_value = scale
        return nd.outputs["Distance"]

    def ramp(self, fac, stops):
        nd = self.node("ShaderNodeValToRGB")
        self.feed(nd.inputs[0], fac)
        el = nd.color_ramp.elements
        while len(el) < len(stops):
            el.new(0.5)
        for e, (p, c) in zip(el, stops):
            e.position = p
            e.color = (*c, 1.0) if len(c) == 3 else c
        return nd.outputs["Color"]

    def mixc(self, fac, a, b, blend="MIX"):
        nd = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=True)
        self.feed(nd.inputs[0], fac)
        self.feed(nd.inputs[6], a)
        self.feed(nd.inputs[7], b)
        return nd.outputs[2]

    def tile(self, image, size, tint):
        img = bpy.data.images.load(os.path.join(TEXTURES, image + ".png"), check_existing=True)
        mp = self.node("ShaderNodeMapping")
        self.feed(mp.inputs["Vector"], self.co)
        mp.inputs["Scale"].default_value = (1 / size, 1 / size, 1 / size)
        tx = self.node("ShaderNodeTexImage", image=img, projection="BOX", projection_blend=0.25)
        self.t.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
        col = self.mixc(1.0, tx.outputs["Color"], tint, blend="MULTIPLY")
        luma = None
        lpath = os.path.join(TEXTURES, image + "_luma.png")
        if os.path.exists(lpath):
            limg = bpy.data.images.load(lpath, check_existing=True)
            lt = self.node("ShaderNodeTexImage", image=limg, projection="BOX", projection_blend=0.25)
            self.t.links.new(mp.outputs["Vector"], lt.inputs["Vector"])
            # The world tiles' embers are too busy on a body: keep a few, dimmer.
            luma = self.mixc(1.0, lt.outputs["Color"], (0.25, 0.25, 0.25), blend="MULTIPLY")
        return col, luma


def shade(name):
    """(albedo, glow) sockets for one of the creature materials."""
    g = Nodes(bpy.data.materials[name])
    if name in TILES:
        col, luma = g.tile(*TILES[name])
        return g, col, luma
    if name == "ash":
        # Ash crust: pale grey flakes over char, split by cracks that still glow.
        n = g.noise(14.0, 6.0, 0.6, seed=1.0)
        col = g.ramp(n, [(0.30, (0.035, 0.032, 0.030)), (0.55, (0.13, 0.12, 0.11)), (0.75, (0.30, 0.28, 0.26))])
        crack = g.voronoi(7.0, seed=2.0)
        c = g.ramp(crack, [(0.0, (1, 1, 1)), (0.04, (0, 0, 0))])
        col = g.mixc(c, col, (0.02, 0.012, 0.008))
        heat = g.ramp(g.noise(3.0, 2.0, 0.5, seed=3.0), [(0.52, (0, 0, 0)), (0.62, (1, 1, 1))])
        glow = g.mixc(g.mixc(heat, (0, 0, 0), c, blend="MULTIPLY"), (0, 0, 0), (1.0, 0.33, 0.06))
        return g, col, glow
    if name == "bone":
        n = g.noise(10.0, 5.0, 0.6, seed=5.0)
        col = g.ramp(n, [(0.3, (0.16, 0.14, 0.11)), (0.7, (0.42, 0.38, 0.31))])
        return g, col, None
    if name == "coal":
        n = g.noise(18.0, 4.0, 0.6, seed=7.0)
        col = g.ramp(n, [(0.35, (0.25, 0.06, 0.01)), (0.65, (0.6, 0.22, 0.04))])
        glow = g.ramp(n, [(0.3, (0.55, 0.12, 0.01)), (0.7, (1.0, 0.62, 0.22))])
        return g, col, glow
    if name == "ember":
        return g, (0.5, 0.2, 0.05), (1.0, 0.55, 0.15)
    if name == "dark":
        return g, (0.005, 0.004, 0.004), None
    raise KeyError(name)


# ------------------------------------------------------------------ skins

def setup_cycles():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    device = os.environ.get("CYCLES_DEVICE", "CPU").upper()
    sc.cycles.device = "CPU"
    if device != "CPU":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = device
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == device
        if any(d.use for d in prefs.devices):
            sc.cycles.device = "GPU"
    sc.cycles.samples = int(os.environ.get("BAKE_SAMPLES", 64 if sc.cycles.device == "GPU" else 16))
    sc.render.bake.margin = max(4, RES // 128)
    sc.render.bake.margin_type = "EXTEND"


def bake(obj, kind, sources):
    """Bakes every material's source socket (or ambient occlusion) into one image."""
    img = bpy.data.images.new(kind, RES, RES, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    for slot in obj.material_slots:
        g = sources[slot.material.name]
        nd = g.node("ShaderNodeTexImage", image=img)
        for n in g.t.nodes:
            n.select = False
        nd.select = True
        g.t.nodes.active = nd
        if kind != "AO":
            src = g.src[kind]
            em = g.node("ShaderNodeEmission")
            g.feed(em.inputs["Color"], src if src is not None else (0.0, 0.0, 0.0))
            g.t.links.new(em.outputs["Emission"], g.out.inputs["Surface"])
        else:
            bs = g.node("ShaderNodeBsdfDiffuse")
            g.t.links.new(bs.outputs["BSDF"], g.out.inputs["Surface"])
    bpy.ops.object.bake(type="EMIT" if kind != "AO" else "AO")
    a = np.array(img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)[::-1, :, :3]
    return a


def save_png(path, rgb):
    """Saves linear colour as an 8-bit sRGB PNG."""
    rgb = np.clip(rgb, 0, 1)
    s = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
    img = bpy.data.images.new(os.path.basename(path), RES, RES, alpha=False)
    px = np.ones((RES, RES, 4), dtype=np.float32)
    px[:, :, :3] = s[::-1]
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()


# ------------------------------------------------------------------ posing

def rot(rx, ry, rz):
    x, y, z = (math.radians(a) for a in (rx, ry, rz))
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return mz @ my @ mx


def bone_matrices(c, pose):
    """World matrices of every bone for a pose: {bone: (rx, ry, rz)} in degrees
    about the rest axes at the bone's pivot (+X tips a bone's top forward),
    and "move": a translation of the root."""
    mats = []
    for name, parent, head, _tail in c.bones:
        r = pose.get(name, (0, 0, 0))
        h = np.array(head)
        local = np.eye(4)
        local[:3, :3] = rot(*r)
        local[:3, 3] = h - local[:3, :3] @ h
        if parent is None:
            local[:3, 3] += np.array(pose.get("move", (0, 0, 0)))
            mats.append(local)
        else:
            mats.append(mats[c.index[parent]] @ local)
    return np.array(mats)


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)


def sample(keys, t):
    """A pose between keyframes [(time 0..1, pose)], eased."""
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = ease((t - t0) / max(t1 - t0, 1e-9))
            out = {}
            for k in set(p0) | set(p1):
                a = np.array(p0.get(k, (0, 0, 0)), dtype=float)
                b = np.array(p1.get(k, (0, 0, 0)), dtype=float)
                out[k] = tuple(a + (b - a) * u)
            return out
    return dict(keys[-1][1])


def frames_of(anims):
    """[(frame name, pose, effect)] for every animation: (name, count, keys,
    loop, effect). A looping one doesn't repeat its first pose at the end."""
    out = []
    for name, count, keys, loop, effect in anims:
        for i in range(count):
            t = i / count if loop else i / max(count - 1, 1)
            out.append(("%s%d" % (name, i + 1), sample(keys, t), effect and (effect, t)))
    return out


def mirror(pose):
    """The same pose with left and right swapped (a walk's second step)."""
    out = {}
    for k, v in pose.items():
        k2 = k[:-2] + ("_r" if k.endswith("_l") else "_l") if k.endswith(("_l", "_r")) else k
        if k == "move":
            out[k] = v
        else:
            out[k2] = (v[0], -v[1], -v[2])
    return out


# ------------------------------------------------------------------ export

def build(c, anims, effects=None):
    effects = effects or {}
    bpy.ops.object.select_all(action="DESELECT")
    for o in c.parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = c.parts[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = c.name
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")

    me = obj.data
    nv = len(me.vertices)
    rest = np.array([v.co[:] for v in me.vertices])
    w = np.zeros((nv, len(c.bones)))
    gi = {g.index: c.index[g.name] for g in obj.vertex_groups}
    for v in me.vertices:
        for ge in v.groups:
            w[v.index, gi[ge.group]] = ge.weight
    w /= np.maximum(w.sum(axis=1, keepdims=True), 1e-9)

    # One export vertex for each vertex and texture coordinate.
    uv = me.uv_layers.active.data
    keys, remap, src, st = {}, [], [], []
    tris = []
    for tri in me.loop_triangles:
        t = []
        for li in tri.loops:
            vi = me.loops[li].vertex_index
            u, v = uv[li].uv
            k = (vi, round(u, 6), round(v, 6))
            if k not in keys:
                keys[k] = len(src)
                src.append(vi)
                st.append((u, 1.0 - v))
            t.append(keys[k])
        tris.append((t[0], t[2], t[1]))  # Quake winds the other way
    src = np.array(src)
    faces = np.array([[me.loops[li].vertex_index for li in tri.loops] for tri in me.loop_triangles])

    # The skin.
    setup_cycles()
    sources = {}
    for slot in obj.material_slots:
        g, col, glow = shade(slot.material.name)
        g.src = {"albedo": col, "glow": glow}
        sources[slot.material.name] = g
    albedo = bake(obj, "albedo", sources)
    glow = bake(obj, "glow", sources)
    ao = bake(obj, "AO", sources)[:, :, :1]
    albedo = albedo * (0.25 + 0.75 * ao)
    os.makedirs(OUT, exist_ok=True)
    save_png(os.path.join(OUT, c.name + ".png"), albedo)
    save_png(os.path.join(OUT, c.name + "_luma.png"), glow)

    # Every frame, posed, turned to face +X and scaled to Quake units.
    turn = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)
    restp = np.c_[rest, np.ones(nv)]
    names, positions, normals = [], [], []
    for fname, pose, effect in frames_of(anims):
        m = bone_matrices(c, pose)
        p = np.einsum("vb,bij,vj->vi", w, m[:, :3, :], restp)
        if effect:
            p = effects[effect[0]](p, rest, effect[1])
        p = (p @ turn.T) * UNITS
        p[:, 2] += c.hull_bottom
        fn = np.cross(p[faces[:, 1]] - p[faces[:, 0]], p[faces[:, 2]] - p[faces[:, 0]])
        n = np.zeros_like(p)
        for k in range(3):
            np.add.at(n, faces[:, k], fn)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        names.append(fname)
        positions.append(p[src])
        normals.append(n[src])
    if os.environ.get("PREVIEW"):
        preview(c.name, names, positions, tris, st, albedo, os.environ["PREVIEW"])
    surf = {"name": c.name, "tris": tris, "st": st, "frames": positions, "normals": normals}
    size = md3.write(os.path.join(OUT, c.name + ".md3"), [surf], names)
    print("%s: %d triangles, %d vertices, %d frames, %d KiB" % (c.name, len(tris), len(st), len(names), size // 1024), flush=True)
    with open(os.path.join(OUT, c.name + ".frames"), "w") as fh:
        fh.write(" ".join(names) + "\n")


def preview(name, names, positions, tris, st, albedo, out, size=220):
    """A contact sheet of every other frame, rendered from the front-left
    three-quarter view, to check the animations without the engine."""
    sc = bpy.context.scene
    img = bpy.data.images.new("skin", RES, RES)
    px = np.ones((RES, RES, 4), dtype=np.float32)
    px[:, :, :3] = np.clip(albedo[::-1], 0, 1)
    img.pixels.foreach_set(px.ravel())
    m = bpy.data.materials.new("preview")
    m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    me = bpy.data.meshes.new("pv")
    me.from_pydata(positions[0].tolist(), [], [list(t) for t in tris])
    uvl = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            u, v = st[me.loops[li].vertex_index]
            uvl.data[li].uv = (u, 1 - v)
    me.materials.append(m)
    ob = bpy.data.objects.new("pv", me)
    sc.collection.objects.link(ob)
    for o in list(sc.objects):
        if o.type == "MESH" and o is not ob:
            o.hide_render = True
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    top = max(float(p[:, 2].max()) for p in positions)
    low = min(float(p[:, 2].min()) for p in positions)
    mid = (top + low) / 2
    cam.location = (150, 100, mid + 30)
    cam.rotation_euler = (Vector((0, 0, mid)) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50 * 180 / max(top - low + 30, 60) * 1.0
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 7
    sun.rotation_euler = (0.8, 0.2, 2.2)
    sc.collection.objects.link(sun)
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.5, 0.5, 0.55)
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.cycles.samples = 8
    sc.render.film_transparent = False
    want = os.environ.get("PREVIEW_FRAMES")
    picks = [names.index(n) for n in want.split(",")] if want else list(range(0, len(names), 2))
    size = int(os.environ.get("PREVIEW_SIZE", size))
    sc.render.resolution_x = sc.render.resolution_y = size
    cols = min(8, len(picks))
    rows = (len(picks) + cols - 1) // cols
    sheet = np.zeros((rows * size, cols * size, 3), dtype=np.float32)
    path = os.path.join(out, "frame.png")
    for k, f in enumerate(picks):
        me.vertices.foreach_set("co", positions[f].ravel())
        me.update()
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(path)
        a = np.array(im.pixels[:], dtype=np.float32).reshape(size, size, 4)[::-1, :, :3]
        bpy.data.images.remove(im)
        r, cidx = divmod(k, cols)
        sheet[r * size:(r + 1) * size, cidx * size:(cidx + 1) * size] = a
    out_img = bpy.data.images.new("sheet", cols * size, rows * size)
    px = np.ones((rows * size, cols * size, 4), dtype=np.float32)
    px[:, :, :3] = sheet[::-1]
    out_img.pixels.foreach_set(px.ravel())
    out_img.filepath_raw = os.path.join(out, name + "_sheet.png")
    out_img.file_format = "PNG"
    out_img.save()
    print("preview", out_img.filepath_raw, " ".join(names[f] for f in picks), flush=True)


# ------------------------------------------------------------------ crumbling

def crumble(p, rest, t):
    """Ash falling in on itself: each bit drops once the heat reaches it (from
    the top down), spreading as it lands, into a low pile."""
    z = rest[:, 2]
    top = max(z.max(), 1e-3)
    jitter = np.array([noise.noise(Vector(r) * 7.0) for r in rest]) * 0.12
    start = (1.0 - z / top) * 0.45 + jitter
    u = np.clip((t - start) / 0.5, 0.0, 1.0)
    u = u * u * (3 - 2 * u)
    base = p[:, :2]
    centre = np.array([0.0, 0.0])
    spread = (base - centre) * (1.0 + 0.9 * u[:, None]) + centre
    pile = 0.18 * np.clip(1.0 - np.linalg.norm(spread, axis=1) / 0.7, 0.0, 1.0) * (0.6 + 0.4 * np.abs(jitter / 0.12))
    out = p.copy()
    out[:, :2] = base + (spread - base) * u[:, None]
    out[:, 2] = p[:, 2] + (pile - p[:, 2]) * u
    return out


def rise(p, rest, t):
    return crumble(p, rest, 1.0 - t)


# ------------------------------------------------------------------ the Ashen

def ashen():
    """The dead risen from the ash: gaunt and hunched, crusted grey, with heat
    still in the cracks and in the eyes. About 1.8 m tall: the player's hull."""
    J = {
        "pelvis": (0, 0.02, 0.96), "spine": (0, 0.0, 1.16), "chest": (0, -0.08, 1.36), "neck": (0, -0.17, 1.52),
        "head": (0, -0.22, 1.60),
        "hip_l": (0.10, 0.02, 0.92), "knee_l": (0.12, -0.04, 0.52), "ankle_l": (0.13, 0.03, 0.09), "toe_l": (0.14, -0.13, 0.03),
        "hip_r": (-0.10, 0.02, 0.92), "knee_r": (-0.12, -0.04, 0.52), "ankle_r": (-0.13, 0.03, 0.09), "toe_r": (-0.14, -0.13, 0.03),
        "sho_l": (0.19, -0.10, 1.40), "elb_l": (0.27, -0.12, 1.10), "wri_l": (0.31, -0.22, 0.84), "fin_l": (0.32, -0.30, 0.72),
        "sho_r": (-0.19, -0.10, 1.40), "elb_r": (-0.28, -0.16, 1.12), "wri_r": (-0.33, -0.28, 0.88), "fin_r": (-0.34, -0.37, 0.77),
    }
    bones = [
        ("pelvis", None, J["pelvis"], J["spine"]),
        ("spine", "pelvis", J["spine"], J["chest"]),
        ("chest", "spine", J["chest"], J["neck"]),
        ("neck", "chest", J["neck"], J["head"]),
        ("head", "neck", J["head"], (0, -0.24, 1.78)),
    ]
    for s in "lr":
        bones += [
            ("thigh_" + s, "pelvis", J["hip_" + s], J["knee_" + s]),
            ("shin_" + s, "thigh_" + s, J["knee_" + s], J["ankle_" + s]),
            ("foot_" + s, "shin_" + s, J["ankle_" + s], J["toe_" + s]),
            ("upper_" + s, "chest", J["sho_" + s], J["elb_" + s]),
            ("fore_" + s, "upper_" + s, J["elb_" + s], J["wri_" + s]),
            ("hand_" + s, "fore_" + s, J["wri_" + s], J["fin_" + s]),
        ]
    c = Creature("ashen", bones, hull_bottom=-24.0)
    edges = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck"), ("neck", "head")]
    for s in "lr":
        edges += [("pelvis", "hip_" + s), ("hip_" + s, "knee_" + s), ("knee_" + s, "ankle_" + s), ("ankle_" + s, "toe_" + s),
                  ("chest", "sho_" + s), ("sho_" + s, "elb_" + s), ("elb_" + s, "wri_" + s), ("wri_" + s, "fin_" + s)]
    radius = {"pelvis": (0.14, 0.10), "spine": (0.11, 0.08), "chest": (0.19, 0.12), "neck": 0.05, "head": 0.05}
    for s in "lr":
        radius.update({"hip_" + s: 0.085, "knee_" + s: 0.055, "ankle_" + s: 0.04, "toe_" + s: (0.042, 0.028),
                       "sho_" + s: 0.062, "elb_" + s: 0.045, "wri_" + s: 0.034, "fin_" + s: (0.045, 0.016)})

    def ribs(p, n):
        # Ribs and a sunken belly under the crust.
        if 1.12 < p.z < 1.40 and abs(p.x) < 0.17:
            k = max(0.0, math.sin((p.z - 1.12) * math.tau / 0.05))
            p = p - n * 0.010 * k * (1.0 - abs(p.x) / 0.17)
        if 0.98 < p.z < 1.13 and p.y < 0:
            p = p - n * 0.02 * math.sin((p.z - 0.98) / 0.15 * math.pi)
        return p

    body = skin_body("body", J, edges, radius, "pelvis", seed=1, lumps=0.016, shape=ribs)
    c.add(body, "ash", power=5.0)
    # The skull: long, the jaw hanging open, eyes still burning.
    skull = prim("uv_sphere", radius=0.1, segments=20, ring_count=12, location=(0, -0.25, 1.68))
    skull.scale = (0.85, 1.05, 1.05)
    c.add(skull, "ash", "head")
    jaw = prim("uv_sphere", radius=0.07, segments=16, ring_count=8, location=(0, -0.29, 1.57))
    jaw.scale = (0.8, 0.9, 0.55)
    jaw.rotation_euler = (math.radians(-25), 0, 0)
    c.add(jaw, "bone", "head")
    maw = prim("uv_sphere", radius=0.05, segments=12, ring_count=6, location=(0, -0.33, 1.61))
    maw.scale = (0.7, 0.4, 0.7)
    c.add(maw, "dark", "head")
    for x in (-0.036, 0.036):
        eye = prim("uv_sphere", radius=0.018, segments=10, ring_count=6, location=(x, -0.335, 1.69))
        c.add(eye, "ember", "head")
    # Long claws of fused bone.
    for s, sx in (("l", 1), ("r", -1)):
        w, f = Vector(J["wri_" + s]), Vector(J["fin_" + s])
        d = (f - w).normalized()
        side = Vector((sx, 0, 0)).cross(d).normalized()
        for k in (-1, 0, 1):
            base = f + Vector((0.018 * k * sx, 0, 0)) - d * 0.01
            tip = base + d * 0.11 + Vector((0.012 * k * sx, 0, 0)) + side * 0.02
            c.add(between("cone", base, tip, radius1=0.011, radius2=0.002, vertices=8), "bone", "hand_" + s)
    # Spurs of bone along the spine, through the crust.
    for k in range(5):
        z = 1.18 + 0.055 * k
        y = 0.07 + 0.02 * k - 0.015 * k * k
        c.add(between("cone", (0, y - 0.01, z), (0, y + 0.06, z + 0.02), radius1=0.016, radius2=0.003, vertices=8),
              "bone", "spine" if k < 2 else "chest")
    # A rag of burnt cloth at the hips.
    def ragged(a, z, x, y):
        if z < 0.8:
            z += 0.06 * math.sin(5 * a) + 0.04 * math.sin(13 * a + 1) + 0.03 * noise.noise(Vector((a * 3, 0, 0)))
        return x * (1 + 0.04 * math.sin(7 * a)), y + 0.02, z
    rag = lathe("rag", [(0.16, 0.98), (0.18, 0.90), (0.19, 0.82), (0.20, 0.72)], segs=40, shape=ragged)
    thicken(rag, 0.01)
    c.add(rag, "robe", among=["pelvis", "thigh_l", "thigh_r"], power=2.0)

    # Animations, ten frames a second.
    hunch = {"spine": (20, 0, 0), "chest": (14, 0, 0), "neck": (-26, 0, 0), "head": (-8, 0, 0),
             "thigh_l": (-6, 0, 3), "thigh_r": (-6, 0, -3), "shin_l": (10, 0, 0), "shin_r": (10, 0, 0), "move": (0, 0, -0.03),
             "upper_l": (-20, 0, 8), "upper_r": (-28, 0, -6), "fore_l": (-25, 0, 0), "fore_r": (-30, 0, 0)}

    def p(base, **kw):
        out = dict(base)
        for k, v in kw.items():
            out[k] = v
        return out

    stand = [(0.0, p(hunch)), (0.5, p(hunch, spine=(17, 0, 3), head=(-2, 4, 5), upper_l=(-14, 0, 10), move=(0, 0, -0.01))),
             (1.0, p(hunch))]
    step = p(hunch, thigh_l=(-28, 0, 0), shin_l=(18, 0, 0), thigh_r=(16, 0, 0), shin_r=(30, 0, 0), foot_r=(-10, 0, 0),
             pelvis=(0, 0, -6), chest=(10, 4, 8), upper_l=(-10, 0, 8), upper_r=(-44, 0, -6), move=(0, 0, -0.03))
    mid = p(hunch, thigh_l=(-6, 0, 0), shin_l=(6, 0, 0), thigh_r=(-8, 0, 0), shin_r=(45, 0, 0), foot_r=(-8, 0, 0),
            move=(0, 0, 0.0), head=(-4, -6, 0))
    walk = [(0.0, step), (0.25, mid), (0.5, mirror(step)), (0.75, mirror(mid)), (1.0, step)]
    rstep = p(step, spine=(26, 0, 0), thigh_l=(-40, 0, 0), shin_l=(25, 0, 0), thigh_r=(28, 0, 0), shin_r=(55, 0, 0),
              upper_l=(-60, 0, 10), upper_r=(-70, 0, -10), fore_l=(-10, 0, 0), fore_r=(-10, 0, 0), move=(0, 0, -0.05))
    rmid = p(rstep, thigh_l=(-10, 0, 0), shin_l=(10, 0, 0), thigh_r=(-12, 0, 0), shin_r=(70, 0, 0), move=(0, 0, 0.02))
    run = [(0.0, rstep), (0.25, rmid), (0.5, mirror(rstep)), (0.75, mirror(rmid)), (1.0, rstep)]
    wind = p(hunch, spine=(4, 0, -14), chest=(0, 0, -16), upper_r=(-90, 0, -40), fore_r=(-70, 0, 0), hand_r=(-20, 0, 0))
    slash = p(hunch, spine=(26, 0, 18), chest=(14, 0, 18), upper_r=(-70, 0, 40), fore_r=(-5, 0, 0), hand_r=(10, 0, 0),
              thigh_r=(14, 0, 0), thigh_l=(-14, 0, 0), shin_l=(10, 0, 0))
    claw = [(0.0, hunch), (0.35, wind), (0.6, slash), (1.0, hunch)]
    reach = p(hunch, spine=(30, 0, 0), chest=(16, 0, 0), neck=(-30, 0, 0), upper_l=(-100, 0, -10), upper_r=(-100, 0, 10),
              fore_l=(-5, 0, 0), fore_r=(-5, 0, 0), thigh_l=(-30, 0, 0), shin_l=(20, 0, 0), thigh_r=(20, 0, 0), shin_r=(30, 0, 0),
              move=(0, -0.10, -0.06))
    grab = [(0.0, hunch), (0.45, reach), (0.7, p(reach, fore_l=(-50, 0, 0), fore_r=(-50, 0, 0), hand_l=(-30, 0, 0),
                                                 hand_r=(-30, 0, 0))), (1.0, hunch)]
    reel = p(hunch, spine=(-10, 0, 6), chest=(-14, 0, 0), neck=(10, 0, 0), head=(14, 0, -10), upper_l=(-10, 0, 30),
             upper_r=(-20, 0, -30), move=(0, 0.06, 0))
    pain = [(0.0, hunch), (0.3, reel), (1.0, hunch)]
    slump = p(hunch, spine=(30, 0, 0), chest=(20, 0, 0), thigh_l=(-50, 0, 0), shin_l=(90, 0, 0),
              thigh_r=(-50, 0, 0), shin_r=(90, 0, 0), foot_l=(-30, 0, 0), foot_r=(-30, 0, 0), move=(0, 0.1, -0.35))
    death = [(0.0, hunch), (0.3, slump), (1.0, slump)]
    anims = [
        ("stand", 10, stand, True, None),
        ("walk", 12, walk, True, None),
        ("run", 8, run, True, None),
        ("atta", 8, claw, False, None),
        ("attb", 9, grab, False, None),
        ("pain", 6, pain, False, None),
        ("death", 12, death, False, "crumble"),
        ("rise", 12, [(0.0, slump), (0.6, slump), (1.0, hunch)], False, "rise"),
    ]
    build(c, anims, {"crumble": crumble, "rise": rise})


# ------------------------------------------------------------------ the cult

# A standing figure, 1.8 m, facing -Y: the Censer-bearers' frame, and scaled up the Deacons'.
HUMAN = {
    "pelvis": (0, 0, 0.98), "spine": (0, 0, 1.18), "chest": (0, -0.01, 1.40), "neck": (0, -0.02, 1.56),
    "head": (0, -0.03, 1.64), "crown": (0, -0.03, 1.84),
    "hip_l": (0.10, 0, 0.94), "knee_l": (0.11, -0.02, 0.52), "ankle_l": (0.11, 0.02, 0.09), "toe_l": (0.12, -0.12, 0.02),
    "sho_l": (0.21, 0, 1.46), "elb_l": (0.27, 0.02, 1.17), "wri_l": (0.30, -0.04, 0.93), "fin_l": (0.31, -0.08, 0.84),
}
for _k, _v in list(HUMAN.items()):
    if _k.endswith("_l"):
        HUMAN[_k[:-2] + "_r"] = (-_v[0], _v[1], _v[2])


def humanoid(J, extra=()):
    bones = [
        ("pelvis", None, J["pelvis"], J["spine"]),
        ("spine", "pelvis", J["spine"], J["chest"]),
        ("chest", "spine", J["chest"], J["neck"]),
        ("neck", "chest", J["neck"], J["head"]),
        ("head", "neck", J["head"], J["crown"]),
    ]
    for s in "lr":
        bones += [
            ("thigh_" + s, "pelvis", J["hip_" + s], J["knee_" + s]),
            ("shin_" + s, "thigh_" + s, J["knee_" + s], J["ankle_" + s]),
            ("foot_" + s, "shin_" + s, J["ankle_" + s], J["toe_" + s]),
            ("upper_" + s, "chest", J["sho_" + s], J["elb_" + s]),
            ("fore_" + s, "upper_" + s, J["elb_" + s], J["wri_" + s]),
            ("hand_" + s, "fore_" + s, J["wri_" + s], J["fin_" + s]),
        ]
    return bones + list(extra)


def scaled(J, k, wide=1.0):
    return {n: (x * k * wide, y * k, z * k) for n, (x, y, z) in J.items()}


def hang(pose, side="r", sway=(0, 0)):
    """Turns the censer back so its chain hangs straight down from the hand,
    plus a sway (forward, sideways) in degrees."""
    rx = sum(pose.get(b, (0, 0, 0))[0] for b in ("pelvis", "spine", "chest", "upper_" + side, "fore_" + side, "hand_" + side))
    ry = sum(pose.get(b, (0, 0, 0))[1] for b in ("pelvis", "spine", "chest", "upper_" + side, "fore_" + side, "hand_" + side))
    out = dict(pose)
    out["censer"] = (-rx + sway[0], -ry + sway[1], 0)
    return out


def pose_of(base, **kw):
    out = dict(base)
    out.update(kw)
    return out


def robe_fold(amount, hem, seed):
    def shape(a, z, x, y):
        f = 1 + amount * (math.sin(9 * a + seed) * 0.6 + math.sin(17 * a + 2 * seed) * 0.4) * max(0.0, 1 - z / 1.2)
        x, y = x * f, y * f
        if z <= hem + 1e-6:
            z += 0.04 * math.sin(7 * a + seed) + 0.025 * math.sin(15 * a) + 0.02 * noise.noise(Vector((a * 2, seed, 0)))
        return x, y, z
    return shape


def censer(c, top, length, size, bone="censer"):
    """An iron censer full of live coals, hanging on its chain from top."""
    top = Vector(top)
    cen = top - Vector((0, 0, length))
    n = max(3, int(length / 0.07))
    for i in range(n):
        o = prim("torus", major_radius=0.026 * size / 0.15, minor_radius=0.007 * size / 0.15, major_segments=8,
                 minor_segments=4, location=top - Vector((0, 0, (i + 0.5) * (length - size * 0.9) / n)))
        o.scale = (0.7, 1.0, 1.4)
        o.rotation_euler = (0, math.pi / 2, (i % 2) * math.pi / 2)
        c.add(o, "iron", bone)
    bowl = lathe("bowl", [(0.0, -size), (size * 0.6, -size * 0.87), (size * 0.93, -size * 0.4), (size, 0.0)], segs=16, at=cen)
    c.add(bowl, "iron", bone)
    cap = lathe("cap", [(size, size * 0.4), (size * 0.8, size * 0.73), (size * 0.4, size), (0.0, size * 1.13)], segs=16, at=cen)
    c.add(cap, "iron", bone)
    for i in range(6):
        a = math.tau * i / 6
        p0 = cen + Vector((size * math.cos(a), size * math.sin(a), 0.0))
        c.add(between("cylinder", p0, p0 + Vector((0, 0, size * 0.45)), radius=size * 0.06, vertices=5), "iron", bone)
    coals = prim("ico_sphere", radius=size * 0.85, subdivisions=2, location=cen + Vector((0, 0, size * 0.12)))
    c.add(coals, "coal", bone)
    return cen


def robed_body(c, J, k, robe_r, hem_r, seed, sleeve=0.075, glove="leather"):
    """Legs (only the boots show), a robe from shoulders to the floor, wide
    sleeves and gloved hands."""
    legs = {n: J[n] for n in ("pelvis", "hip_l", "knee_l", "ankle_l", "toe_l", "hip_r", "knee_r", "ankle_r", "toe_r")}
    e = []
    for s in "lr":
        e += [("pelvis", "hip_" + s), ("hip_" + s, "knee_" + s), ("knee_" + s, "ankle_" + s), ("ankle_" + s, "toe_" + s)]
    rad = {"pelvis": 0.1 * k}
    for s in "lr":
        rad.update({"hip_" + s: 0.07 * k, "knee_" + s: 0.05 * k, "ankle_" + s: 0.045 * k, "toe_" + s: (0.045 * k, 0.03 * k)})
    c.add(skin_body("legs", legs, e, rad, "pelvis", subdiv=1), "leather",
          among=["pelvis", "thigh_l", "thigh_r", "shin_l", "shin_r", "foot_l", "foot_r"])
    for s in "lr":
        arm = {n: J[n] for n in ("chest", "sho_" + s, "elb_" + s, "wri_" + s)}
        a = skin_body("arm_" + s, arm, [("chest", "sho_" + s), ("sho_" + s, "elb_" + s), ("elb_" + s, "wri_" + s)],
                      {"chest": 0.06 * k, "sho_" + s: 0.075 * k, "elb_" + s: 0.068 * k, "wri_" + s: sleeve * k},
                      "chest", seed=seed, lumps=0.006 * k, subdiv=2)
        c.add(a, "robe", among=["chest", "upper_" + s, "fore_" + s], power=4.0)
        w, f = Vector(J["wri_" + s]), Vector(J["fin_" + s])
        hand = skin_body("hand_" + s, {"w": tuple(w - (f - w) * 0.3), "f": tuple(f)}, [("w", "f")],
                         {"w": 0.03 * k, "f": (0.038 * k, 0.022 * k)}, "w", subdiv=1)
        c.add(hand, glove, "hand_" + s)
    top, waist = J["neck"][2] - 0.02 * k, J["pelvis"][2]
    torso = lathe("torso", [(0.06 * k, top), (robe_r * 0.95, J["sho_l"][2] - 0.02 * k), (robe_r, J["chest"][2]),
                            (robe_r * 0.88, J["spine"][2]), (robe_r * 0.85, waist + 0.04 * k)], segs=32,
                  shape=lambda a, z, x, y: (x, y * 0.78 + J["chest"][1], z))
    c.add(torso, "robe", among=["pelvis", "spine", "chest", "neck"], power=3.0)
    hem = 0.03 * k
    skirt = lathe("skirt", [(robe_r * 0.86, waist + 0.06 * k), (robe_r * 0.95, waist - 0.1 * k), (hem_r * 0.8, waist * 0.55),
                            (hem_r * 0.95, waist * 0.25), (hem_r, hem)], segs=48, shape=robe_fold(0.08, hem, seed))
    thicken(skirt, 0.012 * k)
    c.add(skirt, "robe", among=["pelvis", "thigh_l", "thigh_r", "shin_l", "shin_r"], power=2.5, anchor=("pelvis", 0.45))


def hood(c, J, k, inner_mat="dark"):
    hx, hy, hz = J["head"]

    def shape(a, z, x, y):
        t = (z - hz) / (0.3 * k)
        y = y + hy + 0.03 * k + 0.05 * k * t
        if t > 0.9:
            y += 0.12 * k * (t - 0.9)
        return x + hx, y, z

    def skip(a, z):
        return abs(a - 1.5 * math.pi) < 0.7 and hz - 0.04 * k < z < hz + 0.19 * k

    h = lathe("hood", [(0.10 * k, hz - 0.09 * k), (0.14 * k, hz - 0.03 * k), (0.15 * k, hz + 0.06 * k), (0.145 * k, hz + 0.15 * k),
                       (0.11 * k, hz + 0.23 * k), (0.05 * k, hz + 0.29 * k), (0.01 * k, hz + 0.31 * k)],
              segs=32, shape=shape, skip=skip)
    thicken(h, 0.015 * k)
    c.add(h, "hood", "head")
    inner = prim("uv_sphere", radius=0.115 * k, segments=16, ring_count=8, location=(hx, hy - 0.0 * k, hz + 0.07 * k))
    c.add(inner, inner_mat, "head")
    mantle = lathe("mantle", [(0.07 * k, hz - 0.05 * k), (0.2 * k, hz - 0.12 * k), (0.27 * k, J["sho_l"][2] - 0.02 * k),
                              (0.25 * k, J["sho_l"][2] - 0.12 * k)], segs=32,
                   shape=lambda a, z, x, y: (x * 1.05, y * 0.8 + J["chest"][1], z + 0.02 * k * math.sin(6 * a)))
    thicken(mantle, 0.012 * k)
    c.add(mantle, "robe", among=["chest", "neck"], power=3.0)


def censer_bearer():
    """The cult's foot soldiers: robed and hooded, a leather mask with slits
    that glow, swinging a censer of live coals and throwing them."""
    J = dict(HUMAN)
    J["wri_r"], J["fin_r"] = (-0.33, -0.06, 0.93), (-0.34, -0.10, 0.84)
    top = J["fin_r"]
    bones = humanoid(J, [("censer", "hand_r", top, (top[0], top[1], top[2] - 0.45))])
    c = Creature("censer", bones, hull_bottom=-24.0)
    robed_body(c, J, 1.0, 0.2, 0.34, seed=3.0)
    hood(c, J, 1.0)
    hx, hy, hz = J["head"]
    mask = lathe("mask", [(0.0, -0.02), (0.06, -0.015), (0.09, 0.0)], segs=20,
                 shape=lambda a, z, x, y: (x * 0.95 + hx, -abs(y) * 0.0 + hy - 0.10 + z * 2.0 - 0.0, hz + 0.07 + y))
    mask.rotation_euler = (0, 0, 0)
    c.add(thicken(mask, 0.01), "leather", "head")
    for x in (-0.035, 0.035):
        slit = prim("uv_sphere", radius=0.02, segments=10, ring_count=6, location=(hx + x, hy - 0.128, hz + 0.10))
        slit.scale = (1.4, 0.5, 0.45)
        c.add(slit, "ember", "head")
    belt = prim("torus", major_radius=0.17, minor_radius=0.015, major_segments=32, minor_segments=6, location=(0, 0.0, 1.0))
    belt.scale = (1.0, 0.8, 1.0)
    c.add(belt, "leather", among=["pelvis", "spine"])
    censer(c, top, 0.42, 0.075)

    base = {"spine": (6, 0, 0), "chest": (4, 0, 0), "neck": (-6, 0, 0), "upper_r": (-14, 0, -8), "fore_r": (-50, 0, 0),
            "upper_l": (-6, 0, 6), "fore_l": (-28, 0, 0), "thigh_l": (-3, 0, 0), "thigh_r": (3, 0, 0)}
    stand = [(t, hang(base, sway=(sx, sy))) for t, sx, sy in ((0.0, 8, 0), (0.25, 0, 6), (0.5, -8, 0), (0.75, 0, -6), (1.0, 8, 0))]
    step = pose_of(base, thigh_l=(-24, 0, 0), shin_l=(8, 0, 0), thigh_r=(18, 0, 0), shin_r=(26, 0, 0), foot_r=(-8, 0, 0),
                   pelvis=(0, 0, -5), chest=(4, 0, 6), upper_l=(10, 0, 6), move=(0, 0, -0.02))
    mid = pose_of(base, thigh_l=(-4, 0, 0), shin_l=(4, 0, 0), thigh_r=(-10, 0, 0), shin_r=(40, 0, 0), move=(0, 0, 0.01))
    walk = [(0.0, hang(step, sway=(-10, 0))), (0.25, hang(mid, sway=(0, 0))), (0.5, hang(mirror(step), sway=(10, 0))),
            (0.75, hang(mirror(mid), sway=(0, 0))), (1.0, hang(step, sway=(-10, 0)))]
    rbase = pose_of(base, spine=(16, 0, 0), chest=(6, 0, 0))
    rstep = pose_of(rbase, thigh_l=(-38, 0, 0), shin_l=(20, 0, 0), thigh_r=(28, 0, 0), shin_r=(50, 0, 0), foot_r=(-10, 0, 0),
                    upper_l=(28, 0, 6), fore_l=(-50, 0, 0), move=(0, 0, -0.04))
    rmid = pose_of(rbase, thigh_l=(-8, 0, 0), shin_l=(10, 0, 0), thigh_r=(-14, 0, 0), shin_r=(70, 0, 0), move=(0, 0, 0.03))
    run = [(0.0, hang(rstep, sway=(-25, 0))), (0.25, hang(rmid)), (0.5, hang(mirror(rstep), sway=(25, 0))),
           (0.75, hang(mirror(rmid))), (1.0, hang(rstep, sway=(-25, 0)))]
    up = pose_of(base, spine=(-8, 0, -10), chest=(-6, 0, -12), upper_r=(-165, 0, -15), fore_r=(-20, 0, 0), censer=(150, 0, 0))
    strike = pose_of(base, spine=(22, 0, 14), chest=(12, 0, 10), upper_r=(-70, 0, 15), fore_r=(-10, 0, 0), censer=(-40, 0, 0),
                     thigh_r=(16, 0, 0), thigh_l=(-18, 0, 0), shin_l=(12, 0, 0))
    follow = pose_of(base, spine=(18, 0, 22), chest=(8, 0, 16), upper_r=(-25, 0, 35), fore_r=(-15, 0, 0), censer=(-110, 0, 20))
    swing = [(0.0, hang(base)), (0.3, up), (0.5, strike), (0.7, follow), (1.0, hang(base))]
    back = pose_of(base, spine=(-4, 0, 8), upper_l=(45, 0, 4), fore_l=(-10, 0, 0))
    lob = pose_of(base, spine=(14, 0, -6), upper_l=(-120, 0, 0), fore_l=(-10, 0, 0), hand_l=(-30, 0, 0),
                  thigh_l=(-14, 0, 0), thigh_r=(10, 0, 0))
    throw = [(0.0, hang(base)), (0.4, hang(back, sway=(10, 0))), (0.65, hang(lob, sway=(-15, 0))), (1.0, hang(base))]
    reel = pose_of(base, spine=(-12, 0, 8), chest=(-10, 0, 0), neck=(10, 0, 0), head=(12, 0, -10), upper_l=(-20, 0, 30),
                   move=(0, 0.05, 0))
    pain = [(0.0, hang(base)), (0.3, hang(reel, sway=(20, 10))), (1.0, hang(base))]
    kneel = pose_of(base, spine=(25, 0, 0), thigh_l=(-70, 0, 0), shin_l=(120, 0, 0), thigh_r=(-60, 0, 0), shin_r=(115, 0, 0),
                    foot_l=(-40, 0, 0), foot_r=(-40, 0, 0), move=(0, 0.08, -0.38), upper_r=(-5, 0, -20), fore_r=(-10, 0, 0))
    down = pose_of(base, pelvis=(70, 0, 0), spine=(10, 0, 0), thigh_l=(-80, 0, 0), shin_l=(60, 0, 0), thigh_r=(-75, 0, 8),
                   shin_r=(50, 0, 0), upper_r=(-60, 0, -40), fore_r=(-10, 0, 0), upper_l=(-70, 0, 40), move=(0, -0.2, -0.72))
    death = [(0.0, hang(base)), (0.35, hang(kneel)), (0.8, hang(down, sway=(-60, 0))), (1.0, hang(down, sway=(-80, 0)))]
    anims = [
        ("stand", 8, stand, True, None),
        ("walk", 12, walk, True, None),
        ("run", 8, run, True, None),
        ("swing", 10, swing, False, None),
        ("throw", 9, throw, False, None),
        ("pain", 6, pain, False, None),
        ("death", 10, death, False, None),
    ]
    build(c, anims)


def deacon():
    """A Deacon of the Throat: hunched and hooded, a coal for a face behind an
    iron grille, a censer on a chain and a hooked staff with a hand bell. About
    2.6 m: the large hull."""
    k = 1.42
    J = scaled(HUMAN, k, wide=1.1)
    J["wri_r"], J["fin_r"] = (-0.48, -0.10, 1.30), (-0.49, -0.16, 1.18)
    J["wri_l"], J["fin_l"] = (0.46, -0.10, 1.30), (0.47, -0.16, 1.20)
    top = J["fin_r"]
    bones = humanoid(J, [("censer", "hand_r", top, (top[0], top[1], top[2] - 0.6))])
    c = Creature("deacon", bones, hull_bottom=-24.0)
    robed_body(c, J, k, 0.33, 0.68, seed=1.0, sleeve=0.09, glove="iron")
    hood(c, J, k)
    hx, hy, hz = J["head"]
    coal = prim("uv_sphere", radius=0.10, segments=16, ring_count=8, location=(hx, hy - 0.10, hz + 0.09))
    coal.scale = (1.0, 0.6, 1.15)
    c.add(coal, "coal", "head")
    for i in range(5):
        x = -0.08 + i * 0.04
        c.add(between("cylinder", (hx + x, hy - 0.175, hz - 0.01), (hx + x * 0.85, hy - 0.18, hz + 0.21), radius=0.009, vertices=6),
              "iron", "head")
    for z in (0.02, 0.15):
        c.add(between("cylinder", (hx - 0.11, hy - 0.178, hz + z), (hx + 0.11, hy - 0.178, hz + z), radius=0.01, vertices=6),
              "iron", "head")
    # A chain belt.
    n = 18
    for i in range(n):
        a = math.tau * i / n
        o = prim("torus", major_radius=0.035, minor_radius=0.009, major_segments=8, minor_segments=4)
        o.scale = (1.4, 1.0, 1.0)
        o.rotation_euler = (math.pi / 2 * (i % 2), 0, a + math.pi / 2)
        o.location = (0.31 * math.cos(a), 0.25 * math.sin(a), J["pelvis"][2] + 0.04 * math.sin(a))
        c.add(o, "iron", among=["pelvis", "spine"])
    censer(c, top, 0.55, 0.11)
    # The staff in the left hand: an iron pole, a hook, and the bell on a chain.
    w = Vector(J["fin_l"]) + Vector((0, 0.01, -0.02))
    foot, head_ = w + Vector((0.02, 0.06, -1.15)), w + Vector((-0.04, -0.1, 1.15))
    c.add(between("cylinder", foot, head_, radius=0.022, vertices=8), "iron", "hand_l")
    hook = [head_, head_ + Vector((0.0, -0.06, 0.14)), head_ + Vector((0.0, -0.2, 0.2)), head_ + Vector((0.0, -0.3, 0.1))]
    for a, b in zip(hook, hook[1:]):
        c.add(between("cylinder", a, b, radius=0.02, vertices=8), "iron", "hand_l")
    bell_top = hook[-1] + Vector((0, 0, -0.04))
    c.add(between("cylinder", hook[-1], bell_top + Vector((0, 0, -0.14)), radius=0.006, vertices=5), "iron", "hand_l")
    bell = lathe("bell", [(0.0, 0.19), (0.04, 0.185), (0.065, 0.15), (0.075, 0.08), (0.1, 0.02), (0.105, 0.0)], segs=20,
                 at=tuple(bell_top + Vector((0, 0, -0.36))))
    c.add(thicken(bell, 0.008), "bronze", "hand_l")
    for g in hand_grip(J, "l", k):
        c.add(g, "iron", "hand_l")

    base = {"spine": (14, 0, 0), "chest": (12, 0, 0), "neck": (-16, 0, 0), "head": (-6, 0, 0),
            "upper_r": (-16, 0, -10), "fore_r": (-55, 0, 0), "upper_l": (-10, 0, 8), "fore_l": (-30, 0, 0),
            "thigh_l": (-4, 0, 0), "thigh_r": (4, 0, 0)}
    stand = [(t, hang(pose_of(base, chest=(12 + b, 0, 0)), sway=(sx, sy)))
             for t, b, sx, sy in ((0.0, 0, 6, 0), (0.25, 2, 0, 5), (0.5, 3, -6, 0), (0.75, 2, 0, -5), (1.0, 0, 6, 0))]
    step = pose_of(base, thigh_l=(-20, 0, 0), shin_l=(6, 0, 0), thigh_r=(14, 0, 0), shin_r=(22, 0, 0), pelvis=(0, 0, -4),
                   chest=(12, 0, 5), move=(0, 0, -0.03))
    mid = pose_of(base, thigh_l=(-3, 0, 0), thigh_r=(-8, 0, 0), shin_r=(32, 0, 0), move=(0, 0, 0.0))
    walk = [(0.0, hang(step, sway=(-8, 0))), (0.25, hang(mid)), (0.5, hang(mirror(step), sway=(8, 0))),
            (0.75, hang(mirror(mid))), (1.0, hang(step, sway=(-8, 0)))]
    lift = pose_of(base, spine=(-4, 0, 0), chest=(-2, 0, 0), neck=(-6, 0, 0), upper_l=(-150, 0, 12), fore_l=(-10, 0, 0))
    ring = [(0.0, hang(base))]
    for i, t in enumerate((0.25, 0.35, 0.45, 0.55, 0.65, 0.75)):
        ring.append((t, hang(pose_of(lift, hand_l=(0, 14 if i % 2 else -14, 0), fore_l=(-10 + (6 if i % 2 else -6), 0, 0)),
                             sway=(4, 0))))
    ring.append((1.0, hang(base)))
    wind = pose_of(base, spine=(-6, 0, -12), chest=(-4, 0, -14), upper_r=(-170, 0, -20), fore_r=(-30, 0, 0), censer=(160, 0, 0))
    hurl = pose_of(base, spine=(26, 0, 14), chest=(16, 0, 12), upper_r=(-80, 0, 12), fore_r=(-5, 0, 0), censer=(-70, 0, 0),
                   thigh_r=(14, 0, 0), thigh_l=(-14, 0, 0), shin_l=(10, 0, 0))
    throw = [(0.0, hang(base)), (0.35, wind), (0.55, hurl), (1.0, hang(base))]
    reel = pose_of(base, spine=(-2, 0, 8), chest=(0, 0, 0), neck=(4, 0, 0), head=(10, 0, -10), upper_l=(-30, 0, 30),
                   move=(0, 0.06, 0))
    pain = [(0.0, hang(base)), (0.3, hang(reel, sway=(16, 10))), (1.0, hang(base))]
    kneel = pose_of(base, spine=(30, 0, 0), thigh_l=(-70, 0, 0), shin_l=(120, 0, 0), thigh_r=(-60, 0, 0), shin_r=(115, 0, 0),
                    foot_l=(-40, 0, 0), foot_r=(-40, 0, 0), move=(0, 0.1, -0.52), upper_l=(-20, 0, 30))
    down = pose_of(base, pelvis=(72, 0, 0), spine=(12, 0, 0), thigh_l=(-82, 0, 0), shin_l=(60, 0, 0), thigh_r=(-76, 0, 8),
                   shin_r=(52, 0, 0), upper_r=(-60, 0, -40), fore_r=(-10, 0, 0), upper_l=(-80, 0, 40), move=(0, -0.3, -1.02))
    death = [(0.0, hang(base)), (0.35, hang(kneel)), (0.8, hang(down, sway=(-60, 0))), (1.0, hang(down, sway=(-80, 0)))]
    anims = [
        ("stand", 10, stand, True, None),
        ("walk", 12, walk, True, None),
        ("ring", 12, ring, False, None),
        ("throw", 10, throw, False, None),
        ("pain", 6, pain, False, None),
        ("death", 12, death, False, None),
    ]
    build(c, anims)


def hand_grip(J, s, k):
    """Iron fingers closed round the staff."""
    w, f = Vector(J["wri_" + s]), Vector(J["fin_" + s])
    out = []
    for i in range(3):
        o = prim("torus", major_radius=0.03 * k, minor_radius=0.011 * k, major_segments=10, minor_segments=5,
                 location=f + Vector((0, 0.0, -0.02 * k + 0.022 * k * i)))
        out.append(o)
    return out


CREATURES = {"ashen": ashen, "censer": censer_bearer, "deacon": deacon}

for name, make in CREATURES.items():
    if not ONLY or name in ONLY:
        make()
