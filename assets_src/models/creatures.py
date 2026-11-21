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
import contextlib
import fcntl
import os
import tempfile
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
        self.flags = 0  # the MD3's model flags: 8 (EF_ROTATE) spins a pickup

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
    "firebrick": ("firebrick1", 0.5, (1.0, 1.0, 1.0)),
    "mould": ("sand_mould1", 0.9, (0.85, 0.85, 0.85)),
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
    if name == "cope":
        # The mould's clay, burst along crooked seams with the iron showing.
        col, _ = g.tile("sand_mould1", 0.9, (0.8, 0.8, 0.8))
        crack = g.voronoi(2.2, seed=70.0)
        wob = g.noise(6.0, 3.0, 0.5, seed=71.0)
        c = g.ramp(g.mixc(0.05, crack, wob, blend="ADD"), [(0.03, (1, 1, 1)), (0.06, (0, 0, 0))])
        burst = g.ramp(g.noise(1.2, 2.0, 0.5, seed=72.0), [(0.45, (0, 0, 0)), (0.6, (1, 1, 1))])
        seam = g.mixc(burst, (0, 0, 0), c)
        col = g.mixc(seam, col, (0.6, 0.18, 0.03))
        glow = g.mixc(seam, (0, 0, 0), (1.0, 0.5, 0.12))
        return g, col, glow
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
        glow = g.mixc(g.mixc(heat, (0, 0, 0), c), (0, 0, 0), (1.0, 0.33, 0.06))
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
    if name == "crust":
        # Slag gone hard: black glassy rock in plates, the cracks between them
        # still molten and glowing.
        n = g.noise(9.0, 6.0, 0.62, seed=60.0)
        col = g.ramp(n, [(0.3, (0.02, 0.016, 0.014)), (0.6, (0.07, 0.055, 0.045)), (0.8, (0.16, 0.12, 0.09))])
        crack = g.voronoi(5.0, seed=61.0)
        c = g.ramp(crack, [(0.0, (1, 1, 1)), (0.025, (0, 0, 0))])
        col = g.mixc(c, col, (0.30, 0.07, 0.015))
        heat = g.ramp(g.noise(2.5, 2.0, 0.5, seed=62.0), [(0.45, (0.0, 0.0, 0.0)), (0.65, (1, 1, 1))])
        glow = g.mixc(g.mixc(heat, (0, 0, 0), c), (0, 0, 0), (1.0, 0.36, 0.05))
        return g, col, glow
    if name == "slag":
        n = g.noise(30.0, 5.0, 0.6, seed=13.0)
        col = g.ramp(n, [(0.35, (0.5, 0.12, 0.02)), (0.65, (0.9, 0.45, 0.1))])
        glow = g.ramp(n, [(0.3, (0.7, 0.18, 0.02)), (0.7, (1.0, 0.7, 0.3))])
        return g, col, glow
    if name == "leech":
        # Wet leech skin: grey-green, darker bands across, a pale belly stripe.
        n = g.noise(12.0, 5.0, 0.6, seed=90.0)
        col = g.ramp(n, [(0.3, (0.03, 0.04, 0.03)), (0.7, (0.10, 0.12, 0.08))])
        band = g.ramp(g.noise(30.0, 1.0, 0.3, seed=91.0), [(0.45, (1, 1, 1)), (0.55, (0, 0, 0))])
        col = g.mixc(band, col, (0.015, 0.02, 0.015))
        return g, col, None
    if name == "flesh":
        n = g.noise(20.0, 4.0, 0.6, seed=92.0)
        return g, g.ramp(n, [(0.3, (0.25, 0.03, 0.03)), (0.7, (0.5, 0.08, 0.06))]), None
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
    # Bakes from runs side by side (make -j weapons) take turns on a GPU: eight
    # at once ran a 12 GB card out of memory and Cycles left black or patchy skins.
    with gpu_turn():
        bpy.ops.object.bake(type="EMIT" if kind != "AO" else "AO")
    a = pixels(img).reshape(RES, RES, 4)[::-1, :, :3]
    if kind != "glow" and a.max() <= 0.0:
        raise SystemExit(f"{obj.name}: the {kind} bake came out black (out of GPU memory?)")
    return a


@contextlib.contextmanager
def gpu_turn():
    """Holds a lock file while baking on the GPU, so parallel runs take turns."""
    if bpy.context.scene.cycles.device != "GPU":
        yield
        return
    with open(os.path.join(tempfile.gettempdir(), "cinderkirk-gpu-bake.lock"), "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def pixels(img):
    """An image's pixels as a flat float32 array (foreach_get, far quicker than pixels[:])."""
    a = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(a)
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
    size = md3.write(os.path.join(OUT, c.name + ".md3"), [surf], names, c.flags)
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
        a = pixels(im).reshape(size, size, 4)[::-1, :, :3]
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


def hood(c, J, k, inner_mat="dark", mat="hood", rag=0.0):
    """A cowl over the head and a mantle on the shoulders; `rag` crumples
    them (the wraith's is ash, not cloth)."""
    hx, hy, hz = J["head"]

    def shape(a, z, x, y):
        if rag:
            r = 1.0 + rag * noise.noise(Vector((math.cos(a) * 2.0, math.sin(a) * 2.0, z * 9.0 / k)))
            x, y = x * r, y * r
        t = (z - hz) / (0.3 * k)
        y = y + hy + 0.03 * k + 0.05 * k * t
        if t > 0.9:
            y += 0.12 * k * (t - 0.9)
        if rag:
            y -= rag * 0.5 * k * max(0.0, t - 0.5)        # the cowl's peak slumps forward
            if t < -0.2:                                   # and its hem hangs in tatters
                z -= rag * 0.35 * k * abs(math.sin(a * 7.0) + 0.6 * math.sin(a * 13.0 + 1.0))
        return x + hx, y, z

    def skip(a, z):
        if rag:                                             # an arched opening, not a visor
            f = abs(a - 1.5 * math.pi) / 0.75
            return f < 1.0 and hz - 0.06 * k < z < hz + 0.21 * k - 0.12 * k * f * f
        return abs(a - 1.5 * math.pi) < 0.7 and hz - 0.04 * k < z < hz + 0.19 * k

    h = lathe("hood", [(0.10 * k, hz - 0.09 * k), (0.14 * k, hz - 0.03 * k), (0.15 * k, hz + 0.06 * k), (0.145 * k, hz + 0.15 * k),
                       (0.11 * k, hz + 0.23 * k), (0.05 * k, hz + 0.29 * k), (0.01 * k, hz + 0.31 * k)],
              segs=32, shape=shape, skip=skip)
    thicken(h, 0.015 * k)
    c.add(h, mat, "head")
    inner = prim("uv_sphere", radius=0.115 * k, segments=16, ring_count=8, location=(hx, hy - 0.0 * k, hz + 0.07 * k))
    c.add(inner, inner_mat, "head")
    mantle = lathe("mantle", [(0.07 * k, hz - 0.05 * k), (0.2 * k, hz - 0.12 * k), (0.27 * k, J["sho_l"][2] - 0.02 * k),
                              (0.25 * k, J["sho_l"][2] - 0.12 * k)], segs=32,
                   shape=lambda a, z, x, y: (x * 1.05, y * 0.8 + J["chest"][1],
                                             z + 0.02 * k * math.sin(6 * a) - rag * 0.3 * k * max(0.0, math.sin(5 * a + 1.0))))
    thicken(mantle, 0.012 * k)
    c.add(mantle, "robe" if mat == "hood" else mat, among=["chest", "neck"], power=3.0)


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


# ------------------------------------------------------------------ slag hounds

def slag_hound():
    """A slag hound: a lean dog of cooled slag, its ribs open and molten, that
    hunts in packs. About 0.8 m at the shoulder, facing -Y."""
    k = 1.2
    J = scaled({
        "hips": (0, 0.36, 0.62), "spine": (0, 0.02, 0.66), "chest": (0, -0.30, 0.66), "neck": (0, -0.48, 0.80),
        "head": (0, -0.58, 0.84), "snout": (0, -0.84, 0.76),
        "sho_l": (0.12, -0.32, 0.54), "elb_l": (0.13, -0.26, 0.34), "wri_l": (0.13, -0.32, 0.10), "toe_l": (0.13, -0.42, 0.025),
        "hip_l": (0.12, 0.38, 0.56), "knee_l": (0.13, 0.24, 0.36), "hock_l": (0.13, 0.44, 0.16), "paw_l": (0.13, 0.36, 0.025),
        "tail1": (0, 0.52, 0.64), "tail2": (0, 0.74, 0.56), "tail3": (0, 0.92, 0.40),
    }, k)
    for n in list(J):
        if n.endswith("_l"):
            x, y, z = J[n]
            J[n[:-2] + "_r"] = (-x, y, z)
    jaw_at = (0, -0.60 * k, 0.78 * k)
    bones = [
        ("hips", None, J["hips"], J["spine"]),
        ("chest", "hips", J["spine"], J["chest"]),
        ("neck", "chest", J["chest"], J["neck"]),
        ("head", "neck", J["neck"], J["snout"]),
        ("jaw", "head", jaw_at, (0, -0.83 * k, 0.70 * k)),
        ("tail1", "hips", J["tail1"], J["tail2"]),
        ("tail2", "tail1", J["tail2"], J["tail3"]),
    ]
    for s in "lr":
        bones += [
            ("upper_" + s, "chest", J["sho_" + s], J["elb_" + s]),
            ("fore_" + s, "upper_" + s, J["elb_" + s], J["wri_" + s]),
            ("fpaw_" + s, "fore_" + s, J["wri_" + s], J["toe_" + s]),
            ("thigh_" + s, "hips", J["hip_" + s], J["knee_" + s]),
            ("shin_" + s, "thigh_" + s, J["knee_" + s], J["hock_" + s]),
            ("hpaw_" + s, "shin_" + s, J["hock_" + s], J["paw_" + s]),
        ]
    c = Creature("hound", bones, hull_bottom=-24.0)
    edges = [("hips", "spine"), ("spine", "chest"), ("chest", "neck"), ("neck", "head"), ("head", "snout"),
             ("hips", "tail1"), ("tail1", "tail2"), ("tail2", "tail3")]
    for s in "lr":
        edges += [("chest", "sho_" + s), ("sho_" + s, "elb_" + s), ("elb_" + s, "wri_" + s), ("wri_" + s, "toe_" + s),
                  ("hips", "hip_" + s), ("hip_" + s, "knee_" + s), ("knee_" + s, "hock_" + s), ("hock_" + s, "paw_" + s)]
    r = lambda v: tuple(a * k for a in v) if isinstance(v, tuple) else v * k
    radius = {"hips": r((0.10, 0.11)), "spine": r((0.085, 0.10)), "chest": r((0.12, 0.17)), "neck": r(0.075),
              "head": r((0.075, 0.08)), "snout": r((0.04, 0.035)), "tail1": r(0.04), "tail2": r(0.028), "tail3": r(0.012)}
    for s in "lr":
        radius.update({"sho_" + s: r(0.075), "elb_" + s: r(0.045), "wri_" + s: r(0.03), "toe_" + s: r((0.035, 0.02)),
                       "hip_" + s: r(0.085), "knee_" + s: r(0.055), "hock_" + s: r(0.03), "paw_" + s: r((0.035, 0.02))})
    rib_y0, rib_y1 = -0.40 * k, 0.0

    def gaunt(p, n):
        # A tucked belly behind the chest, and grooves where the ribs show.
        if p.z < 0.62 * k and -0.15 * k < p.y < 0.30 * k:
            p = p + Vector((0, 0, 0.06 * k * math.sin((p.y + 0.15 * k) / (0.45 * k) * math.pi)))
        if rib_y0 < p.y < rib_y1 and abs(p.x) > 0.04 * k:
            g = max(0.0, math.sin((p.y - rib_y0) * math.tau / (0.075 * k)))
            p = p - n * 0.014 * k * g
        return p

    body = skin_body("body", J, edges, radius, "hips", seed=3, lumps=0.012 * k, shape=gaunt)
    c.add(body, "crust", among=[b[0] for b in bones if b[0] != "jaw"], power=5.0)
    # The ribs: molten bars curving down each flank, sunk into the crust and glowing through it.
    for i in range(6):
        y = rib_y0 + (i + 0.5) * 0.075 * k
        f = 1.0 - 0.07 * i
        rx, rz, cz = 0.118 * k * f, 0.15 * k * f, 0.665 * k
        for sx in (1, -1):
            pts = [Vector((sx * rx * math.sin(a), y + 0.012 * k * a, cz + rz * math.cos(a)))
                   for a in np.linspace(0.35, 2.3, 8)]
            for a, b in zip(pts, pts[1:]):
                c.add(between("cylinder", a, b, radius=0.010 * k, vertices=6), "slag", "chest" if y < -0.12 * k else "hips")
    # Plates of crust along the back, like a ridge of cooled spatter.
    for i in range(9):
        y = -0.40 * k + i * 0.09 * k
        z = 0.80 * k - 0.04 * k * abs(i - 3) / 3 if i < 6 else 0.74 * k
        h = 0.07 * k * (1.0 - abs(i - 3) / 7)
        c.add(between("cone", (0, y + 0.02 * k, z - 0.04 * k), (0, y - 0.03 * k, z + h), radius1=0.03 * k, radius2=0.004,
                      vertices=6), "crust", "chest" if y < -0.05 * k else "hips")
    # The head: a long skull, a heavy brow and a jaw full of slag teeth.
    hx, hy, hz = J["head"]
    skull = prim("uv_sphere", radius=0.09 * k, segments=18, ring_count=10, location=(0, hy - 0.04 * k, hz + 0.01 * k))
    skull.scale = (0.85, 1.35, 0.8)
    c.add(skull, "crust", "head")
    for sx in (1, -1):
        brow = prim("uv_sphere", radius=0.035 * k, segments=10, ring_count=6, location=(sx * 0.045 * k, hy - 0.10 * k, hz + 0.05 * k))
        brow.scale = (1.0, 1.4, 0.6)
        c.add(brow, "crust", "head")
        eye = prim("uv_sphere", radius=0.016 * k, segments=10, ring_count=6, location=(sx * 0.05 * k, hy - 0.125 * k, hz + 0.025 * k))
        c.add(eye, "ember", "head")
        ear = between("cone", (sx * 0.05 * k, hy + 0.02 * k, hz + 0.06 * k), (sx * 0.08 * k, hy + 0.10 * k, hz + 0.13 * k),
                      radius1=0.03 * k, radius2=0.003, vertices=6)
        c.add(ear, "crust", "head")
    jx, jy, jz = jaw_at
    jaw = prim("uv_sphere", radius=0.06 * k, segments=14, ring_count=8, location=(0, jy - 0.11 * k, jz - 0.01 * k))
    jaw.scale = (0.7, 1.9, 0.45)
    c.add(jaw, "crust", "jaw")
    mouth = prim("uv_sphere", radius=0.05 * k, segments=12, ring_count=6, location=(0, jy - 0.12 * k, jz + 0.015 * k))
    mouth.scale = (0.6, 1.9, 0.3)
    c.add(mouth, "slag", "jaw")
    for i in range(5):
        y = jy - 0.04 * k - i * 0.035 * k
        for sx in (1, -1):
            x = sx * 0.03 * k * (1 - i * 0.12)
            c.add(between("cone", (x, y, jz + 0.01 * k), (x, y, jz + 0.045 * k), radius1=0.008 * k, radius2=0.001, vertices=5),
                  "bone", "jaw")
            c.add(between("cone", (x, y - 0.01 * k, hz - 0.035 * k), (x, y - 0.01 * k, hz - 0.07 * k), radius1=0.008 * k,
                          radius2=0.001, vertices=5), "bone", "head")
    # Claws.
    for s, toe in (("l", "toe_l"), ("r", "toe_r"), ("l", "paw_l"), ("r", "paw_r")):
        bone = ("fpaw_" if toe.startswith("toe") else "hpaw_") + s
        tx, ty, tz = J[toe]
        for dx in (-0.02, 0.0, 0.02):
            c.add(between("cone", (tx + dx * k, ty - 0.01 * k, tz + 0.01 * k), (tx + dx * 1.3 * k, ty - 0.06 * k, 0.0),
                          radius1=0.007 * k, radius2=0.001, vertices=5), "bone", bone)

    # Animations, ten frames a second.
    base = {"neck": (8, 0, 0), "head": (-6, 0, 0), "tail1": (-10, 0, 0), "tail2": (-15, 0, 0)}
    stand = [(0.0, base),
             (0.5, pose_of(base, chest=(-2, 0, 0), neck=(6, 0, 6), head=(-4, 0, 8), tail1=(-12, 0, 10), tail2=(-15, 0, 14),
                           move=(0, 0, 0.008))),
             (1.0, base)]
    # The gallop: gathered with the legs under it, then stretched out flying.
    gather = pose_of(base, hips=(-8, 0, 0), chest=(14, 0, 0), neck=(-6, 0, 0), head=(4, 0, 0),
                     upper_l=(30, 0, 0), fore_l=(-20, 0, 0), upper_r=(22, 0, 0), fore_r=(-30, 0, 0),
                     thigh_l=(-45, 0, 0), shin_l=(30, 0, 0), thigh_r=(-38, 0, 0), shin_r=(35, 0, 0),
                     tail1=(10, 0, 0), tail2=(5, 0, 0), move=(0, 0, -0.04 * k))
    stretch = pose_of(base, hips=(4, 0, 0), chest=(-8, 0, 0), neck=(6, 0, 0), head=(-4, 0, 0),
                      upper_l=(-40, 0, 0), fore_l=(8, 0, 0), fpaw_l=(10, 0, 0), upper_r=(-32, 0, 0), fore_r=(12, 0, 0),
                      thigh_l=(40, 0, 0), shin_l=(-10, 0, 0), hpaw_l=(-30, 0, 0), thigh_r=(35, 0, 0), shin_r=(0, 0, 0),
                      tail1=(-30, 0, 0), tail2=(-20, 0, 0), move=(0, 0, 0.05 * k))
    reach_ = pose_of(base, hips=(-2, 0, 0), chest=(4, 0, 0), upper_l=(-20, 0, 0), fore_l=(30, 0, 0), upper_r=(-10, 0, 0),
                     fore_r=(40, 0, 0), thigh_l=(10, 0, 0), shin_l=(20, 0, 0), thigh_r=(0, 0, 0), shin_r=(20, 0, 0),
                     move=(0, 0, 0.0))
    land = pose_of(base, hips=(-4, 0, 0), chest=(6, 0, 0), upper_l=(10, 0, 0), fore_l=(-5, 0, 0), upper_r=(20, 0, 0),
                   fore_r=(-10, 0, 0), thigh_l=(-10, 0, 0), shin_l=(5, 0, 0), thigh_r=(-20, 0, 0), shin_r=(15, 0, 0),
                   move=(0, 0, -0.02 * k))
    run = [(0.0, gather), (0.33, stretch), (0.6, reach_), (0.8, land), (1.0, gather)]
    trot_a = pose_of(base, upper_l=(-20, 0, 0), fore_l=(15, 0, 0), upper_r=(16, 0, 0), thigh_l=(16, 0, 0), thigh_r=(-20, 0, 0),
                     shin_r=(20, 0, 0), move=(0, 0, 0.01 * k))
    trot_b = pose_of(base, move=(0, 0, -0.01 * k), shin_l=(15, 0, 0), fore_r=(20, 0, 0))
    walk = [(0.0, trot_a), (0.25, trot_b), (0.5, mirror(trot_a)), (0.75, mirror(trot_b)), (1.0, trot_a)]
    # The bite: drop the head, jaws wide, snap.
    low = pose_of(base, chest=(6, 0, 0), neck=(20, 0, 0), head=(4, 0, 0), jaw=(10, 0, 0), upper_l=(-10, 0, 0),
                  upper_r=(-14, 0, 0), thigh_l=(-12, 0, 0), thigh_r=(-12, 0, 0), shin_l=(12, 0, 0), shin_r=(12, 0, 0),
                  move=(0, 0, -0.04 * k))
    gape = pose_of(low, neck=(-4, 0, 0), head=(-14, 0, 0), jaw=(38, 0, 0), move=(0, -0.10 * k, -0.02 * k))
    snap = pose_of(low, neck=(10, 0, 4), head=(6, 0, 10), jaw=(0, 0, 0), move=(0, -0.14 * k, -0.03 * k))
    bite = [(0.0, base), (0.25, low), (0.45, gape), (0.6, snap), (0.75, pose_of(snap, head=(2, 0, -14), neck=(10, 0, -6))),
            (1.0, base)]
    # The lunge: a crouch, a long flat leap with the jaws open, and the landing.
    crouch = pose_of(base, hips=(-6, 0, 0), chest=(8, 0, 0), neck=(-4, 0, 0), head=(-6, 0, 0),
                     upper_l=(30, 0, 0), fore_l=(-40, 0, 0), upper_r=(30, 0, 0), fore_r=(-40, 0, 0),
                     thigh_l=(-50, 0, 0), shin_l=(50, 0, 0), thigh_r=(-50, 0, 0), shin_r=(50, 0, 0),
                     tail1=(20, 0, 0), move=(0, 0.05 * k, -0.14 * k))
    fly = pose_of(base, hips=(4, 0, 0), chest=(-6, 0, 0), neck=(-2, 0, 0), head=(-10, 0, 0), jaw=(40, 0, 0),
                  upper_l=(-50, 0, 0), fore_l=(10, 0, 0), upper_r=(-46, 0, 0), fore_r=(14, 0, 0),
                  thigh_l=(50, 0, 0), shin_l=(-15, 0, 0), hpaw_l=(-30, 0, 0), thigh_r=(50, 0, 0), shin_r=(-15, 0, 0),
                  hpaw_r=(-30, 0, 0), tail1=(-30, 0, 0), tail2=(-10, 0, 0), move=(0, 0, 0.04 * k))
    leap = [(0.0, base), (0.2, crouch), (0.35, fly), (0.8, pose_of(fly, jaw=(10, 0, 0))), (1.0, land)]
    flinch = pose_of(base, hips=(0, 6, 0), chest=(0, 6, 10), neck=(-6, 0, -16), head=(-10, 0, -18), jaw=(25, 0, 0),
                     move=(0, 0.06 * k, 0))
    pain = [(0.0, base), (0.3, flinch), (1.0, base)]
    # Death: the legs go, it rolls onto its side and the heat goes out of it.
    buckle = pose_of(base, chest=(10, 0, 0), neck=(20, 0, 0), upper_l=(20, 0, 0), fore_l=(-60, 0, 0), upper_r=(30, 0, 0),
                     fore_r=(-70, 0, 0), thigh_l=(-30, 0, 0), shin_l=(40, 0, 0), thigh_r=(-20, 0, 0), shin_r=(30, 0, 0),
                     move=(0, 0, -0.16 * k))
    side = pose_of(base, hips=(0, 82, 0), chest=(0, 4, 6), neck=(-10, 0, 10), head=(-20, 0, 0), jaw=(20, 0, 0),
                   upper_l=(-30, 0, 0), fore_l=(-10, 0, 0), upper_r=(-10, 0, 0), fore_r=(-30, 0, 0),
                   thigh_l=(-20, 0, 0), shin_l=(10, 0, 0), thigh_r=(10, 0, 0), shin_r=(25, 0, 0),
                   tail1=(10, 0, 30), tail2=(0, 0, 20), move=(-0.30 * k, 0, -0.42 * k))
    death = [(0.0, base), (0.3, buckle), (0.7, side), (1.0, pose_of(side, jaw=(30, 0, 0), neck=(-14, 0, 14)))]
    anims = [
        ("stand", 10, stand, True, None),
        ("walk", 8, walk, True, None),
        ("run", 6, run, True, None),
        ("bite", 8, bite, False, None),
        ("leap", 9, leap, False, None),
        ("pain", 5, pain, False, None),
        ("death", 10, death, False, None),
    ]
    build(c, anims)


# ------------------------------------------------------------------ gaugers

def gauger():
    """A Gauger: a foundry worker who stayed. Work clothes under a leather
    apron, a riveted iron mask with a pressure gauge for a face, a boiler on
    the back and a steam lance held low in both hands. About 1.8 m."""
    J = dict(HUMAN)
    # The arms already hold the lance at the hip, pointing ahead.
    J.update({"elb_r": (-0.25, 0.04, 1.18), "wri_r": (-0.17, -0.20, 1.05), "fin_r": (-0.15, -0.29, 1.04),
              "elb_l": (0.24, -0.06, 1.17), "wri_l": (0.04, -0.46, 1.10), "fin_l": (0.0, -0.55, 1.11)})
    butt, tip = Vector((-0.13, 0.22, 1.08)), Vector((-0.06, -1.10, 1.13))
    bones = humanoid(J, [("lance", "hand_r", J["wri_r"], tuple(tip))])
    c = Creature("gauger", bones, hull_bottom=-24.0)
    # Body: a stick figure in work clothes, boots and gloves.
    body = {n: J[n] for n in ("pelvis", "spine", "chest", "neck", "hip_l", "knee_l", "ankle_l", "hip_r", "knee_r", "ankle_r",
                              "sho_l", "elb_l", "wri_l", "sho_r", "elb_r", "wri_r")}
    e = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck")]
    rad = {"pelvis": (0.15, 0.11), "spine": (0.14, 0.11), "chest": (0.17, 0.12), "neck": 0.055}
    for s in "lr":
        e += [("pelvis", "hip_" + s), ("hip_" + s, "knee_" + s), ("knee_" + s, "ankle_" + s),
              ("chest", "sho_" + s), ("sho_" + s, "elb_" + s), ("elb_" + s, "wri_" + s)]
        rad.update({"hip_" + s: 0.075, "knee_" + s: 0.055, "ankle_" + s: 0.048,
                    "sho_" + s: 0.065, "elb_" + s: 0.05, "wri_" + s: 0.04})
    c.add(skin_body("body", body, e, rad, "pelvis", seed=4.0, lumps=0.004), "robe", power=4.0,
          among=[b[0] for b in bones if b[0] not in ("lance", "head", "hand_l", "hand_r", "foot_l", "foot_r")])
    for s in "lr":
        ax, ay, az = J["ankle_" + s]
        boot = prim("uv_sphere", radius=0.06, segments=14, ring_count=8, location=(ax, ay - 0.06, 0.05))
        boot.scale = (0.85, 1.8, 0.8)
        c.add(boot, "leather", "foot_" + s)
        w, f = Vector(J["wri_" + s]), Vector(J["fin_" + s])
        glove = skin_body("glove_" + s, {"w": tuple(w - (f - w) * 0.4), "f": tuple(f)}, [("w", "f")],
                          {"w": 0.042, "f": (0.045, 0.03)}, "w", subdiv=1)
        c.add(glove, "leather", "hand_" + s)
    # The apron, from the chest to the knees, round the front.
    apron = lathe("apron", [(0.13, 1.42), (0.17, 1.25), (0.185, 1.0), (0.2, 0.75), (0.21, 0.52)], segs=32,
                  shape=lambda a, z, x, y: (x * 1.05, y * 0.8 - 0.01, z),
                  skip=lambda a, z: math.sin(a) > -0.2)
    c.add(thicken(apron, 0.01), "leather", among=["pelvis", "spine", "chest", "thigh_l", "thigh_r"], power=3.0,
          anchor=("pelvis", 0.4))
    belt = prim("torus", major_radius=0.165, minor_radius=0.016, major_segments=32, minor_segments=6, location=(0, 0.0, 1.0))
    belt.scale = (1.05, 0.8, 1.0)
    c.add(belt, "leather", among=["pelvis", "spine"])
    # The boiler on the back, with gauges of its own and a hose up to the mask.
    tank = lathe("tank", [(0.0, 1.0), (0.1, 1.01), (0.115, 1.06), (0.115, 1.45), (0.1, 1.5), (0.0, 1.52)], segs=20,
                 at=(0.0, 0.2, 0.0))
    c.add(tank, "iron", "chest")
    for z in (1.08, 1.43):
        band = prim("torus", major_radius=0.117, minor_radius=0.01, major_segments=24, minor_segments=5, location=(0, 0.2, z))
        c.add(band, "bronze", "chest")
    for sx in (-1, 1):
        c.add(between("cylinder", (sx * 0.12, 0.08, 1.46), (sx * 0.1, 0.0, 1.2), radius=0.012, vertices=6), "leather", "chest")
    hose = [Vector((0.0, 0.25, 1.52)), Vector((0.06, 0.18, 1.66)), Vector((0.1, 0.02, 1.70)), Vector((0.09, -0.08, 1.64))]
    for a, b in zip(hose, hose[1:]):
        c.add(between("cylinder", a, b, radius=0.016, vertices=8), "leather", among=["chest", "head"], power=6.0)
    # The head: an iron mask, riveted, with a pressure gauge for a face.
    hx, hy, hz = J["head"]
    helm = prim("uv_sphere", radius=0.115, segments=20, ring_count=12, location=(hx, hy + 0.005, hz + 0.07))
    helm.scale = (0.95, 1.05, 1.08)
    c.add(helm, "iron", "head")
    for i in range(10):
        a = math.tau * i / 10
        r = prim("uv_sphere", radius=0.009, segments=6, ring_count=4,
                 location=(hx + 0.112 * math.cos(a) * 0.95, hy + 0.112 * math.sin(a), hz + 0.02))
        c.add(r, "bronze", "head")
    rim = between("cylinder", (hx, hy - 0.10, hz + 0.08), (hx, hy - 0.135, hz + 0.08), radius=0.07, vertices=24)
    c.add(rim, "bronze", "head")
    dial = between("cylinder", (hx, hy - 0.134, hz + 0.08), (hx, hy - 0.138, hz + 0.08), radius=0.058, vertices=24)
    c.add(dial, "ember", "head")
    c.add(between("cylinder", (hx, hy - 0.14, hz + 0.08), (hx + 0.035, hy - 0.142, hz + 0.115), radius=0.005, vertices=4),
          "dark", "head")
    for sx in (-1, 1):
        c.add(between("cylinder", (hx + sx * 0.06, hy - 0.08, hz - 0.03), (hx + sx * 0.03, hy - 0.11, hz - 0.06),
                      radius=0.022, vertices=8), "iron", "head")
    # The lance: an iron pipe through both hands, a brass valve and nozzle.
    c.add(between("cylinder", butt, tip, radius=0.024, vertices=10), "iron", "lance")
    c.add(between("cylinder", butt + Vector((0, 0.04, 0)), butt, radius=0.034, vertices=10), "bronze", "lance")
    v = butt + (tip - butt) * 0.35
    c.add(between("cylinder", v + Vector((0, 0, 0.0)), v + Vector((0, 0, 0.08)), radius=0.01, vertices=6), "bronze", "lance")
    wheel = prim("torus", major_radius=0.035, minor_radius=0.007, major_segments=12, minor_segments=4,
                 location=tuple(v + Vector((0, 0, 0.08))))
    c.add(wheel, "bronze", "lance")
    noz = tip + (tip - butt).normalized() * 0.12
    c.add(between("cone", tip, noz, radius1=0.03, radius2=0.045, vertices=12), "bronze", "lance")
    c.add(between("cylinder", noz - (tip - butt).normalized() * 0.01, noz, radius=0.036, vertices=12), "coal", "lance")
    hb = [Vector((0.0, 0.25, 1.05)), Vector((-0.08, 0.28, 1.0)), butt + Vector((0, 0.05, 0))]
    for a, b in zip(hb, hb[1:]):
        c.add(between("cylinder", a, b, radius=0.015, vertices=8), "leather", among=["chest", "hand_r"], power=6.0)

    base = {"spine": (4, 0, 0), "neck": (-4, 0, 0), "thigh_l": (-4, 0, 0), "thigh_r": (4, 0, 0)}
    stand = [(0.0, base), (0.5, pose_of(base, chest=(3, 0, 0), head=(-3, 0, 4), move=(0, 0, -0.005))), (1.0, base)]
    step = pose_of(base, thigh_l=(-24, 0, 0), shin_l=(8, 0, 0), thigh_r=(18, 0, 0), shin_r=(26, 0, 0), foot_r=(-8, 0, 0),
                   pelvis=(0, 0, -5), chest=(0, 0, 4), move=(0, 0, -0.02))
    mid = pose_of(base, thigh_l=(-4, 0, 0), shin_l=(4, 0, 0), thigh_r=(-10, 0, 0), shin_r=(40, 0, 0), move=(0, 0, 0.01))
    walk = [(0.0, step), (0.25, mid), (0.5, mirror(step)), (0.75, mirror(mid)), (1.0, step)]
    rbase = pose_of(base, spine=(14, 0, 0), chest=(4, 0, 0))
    rstep = pose_of(rbase, thigh_l=(-38, 0, 0), shin_l=(20, 0, 0), thigh_r=(28, 0, 0), shin_r=(50, 0, 0), foot_r=(-10, 0, 0),
                    move=(0, 0, -0.04))
    rmid = pose_of(rbase, thigh_l=(-8, 0, 0), shin_l=(10, 0, 0), thigh_r=(-14, 0, 0), shin_r=(70, 0, 0), move=(0, 0, 0.03))
    run = [(0.0, rstep), (0.25, rmid), (0.5, mirror(rstep)), (0.75, mirror(rmid)), (1.0, rstep)]
    # Aim: brace, lift the lance to the shoulder; the valve hisses while it builds.
    brace = pose_of(base, thigh_l=(-20, 0, 0), shin_l=(14, 0, 0), thigh_r=(14, 0, 0), shin_r=(10, 0, 0), spine=(8, 0, 0),
                    upper_r=(-14, 0, 0), fore_r=(8, 0, 0), upper_l=(-12, 0, 0), fore_l=(6, 0, 0), move=(0, 0, -0.03))
    aim = [(0.0, base), (0.4, brace), (0.7, pose_of(brace, chest=(-2, 0, 0))), (1.0, pose_of(brace, chest=(-3, 0, 0)))]
    kick = pose_of(brace, spine=(0, 0, 0), chest=(-6, 0, 0), upper_r=(-4, 0, 0), upper_l=(-2, 0, 0), move=(0, 0.06, -0.03))
    fire = [(0.0, brace), (0.25, kick), (1.0, base)]
    back = pose_of(base, upper_r=(20, 0, 0), fore_r=(0, 0, 0), upper_l=(24, 0, 0), spine=(-4, 0, 0), move=(0, 0.05, 0))
    thrust = pose_of(base, spine=(16, 0, 0), chest=(6, 0, 0), upper_r=(-40, 0, 0), fore_r=(10, 0, 0), upper_l=(-50, 0, 0),
                     thigh_l=(-28, 0, 0), shin_l=(16, 0, 0), thigh_r=(18, 0, 0), move=(0, -0.12, -0.03))
    jab = [(0.0, base), (0.35, back), (0.55, thrust), (0.7, thrust), (1.0, base)]
    reel = pose_of(base, spine=(-12, 0, 8), chest=(-10, 0, 0), neck=(10, 0, 0), head=(12, 0, -10), upper_l=(10, 0, 20),
                   move=(0, 0.05, 0))
    pain = [(0.0, base), (0.3, reel), (1.0, base)]
    kneel = pose_of(base, spine=(25, 0, 0), thigh_l=(-70, 0, 0), shin_l=(120, 0, 0), thigh_r=(-60, 0, 0), shin_r=(115, 0, 0),
                    foot_l=(-40, 0, 0), foot_r=(-40, 0, 0), upper_r=(30, 0, 0), move=(0, 0.08, -0.38))
    down = pose_of(base, pelvis=(70, 0, 0), spine=(10, 0, 0), thigh_l=(-80, 0, 0), shin_l=(60, 0, 0), thigh_r=(-75, 0, 8),
                   shin_r=(50, 0, 0), upper_r=(-20, 0, -30), upper_l=(-60, 0, 40), move=(0, -0.2, -0.74))
    death = [(0.0, base), (0.35, kneel), (0.8, down), (1.0, down)]
    anims = [
        ("stand", 8, stand, True, None),
        ("walk", 12, walk, True, None),
        ("run", 8, run, True, None),
        ("aim", 8, aim, False, None),
        ("fire", 5, fire, False, None),
        ("jab", 8, jab, False, None),
        ("pain", 6, pain, False, None),
        ("death", 10, death, False, None),
    ]
    build(c, anims)


# ------------------------------------------------------------------ crucible brutes

def crucible_brute():
    """A Crucible Brute: a huge bent furnace hand in iron and leather, its
    head sunk between its shoulders, carrying a crucible of molten slag in a
    pair of tongs. About 2.9 m standing: the large hull."""
    k = 1.55
    J = scaled(HUMAN, k, wide=1.35)
    # Arms out front and low, the tongs' crossbar between the hands.
    J.update({"elb_r": (-0.48, -0.10, 1.70), "wri_r": (-0.34, -0.50, 1.36), "fin_r": (-0.28, -0.60, 1.30),
              "elb_l": (0.48, -0.10, 1.70), "wri_l": (0.34, -0.50, 1.36), "fin_l": (0.28, -0.60, 1.30)})
    J["neck"], J["head"], J["crown"] = (0, -0.10, 2.30), (0, -0.16, 2.36), (0, -0.18, 2.62)
    cx, cy, cz = 0.0, -0.66, 0.95          # the crucible, hanging in the tongs
    bones = humanoid(J, [("crucible", "hand_r", J["fin_r"], (cx, cy, cz))])
    c = Creature("brute", bones, hull_bottom=-24.0)
    body = {n: J[n] for n in ("pelvis", "spine", "chest", "neck", "hip_l", "knee_l", "ankle_l", "hip_r", "knee_r", "ankle_r",
                              "sho_l", "elb_l", "wri_l", "sho_r", "elb_r", "wri_r")}
    e = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck")]
    rad = {"pelvis": (0.30, 0.24), "spine": (0.34, 0.26), "chest": (0.44, 0.30), "neck": (0.17, 0.15)}
    for s in "lr":
        e += [("pelvis", "hip_" + s), ("hip_" + s, "knee_" + s), ("knee_" + s, "ankle_" + s),
              ("chest", "sho_" + s), ("sho_" + s, "elb_" + s), ("elb_" + s, "wri_" + s)]
        rad.update({"hip_" + s: 0.17, "knee_" + s: 0.13, "ankle_" + s: 0.10,
                    "sho_" + s: 0.19, "elb_" + s: 0.14, "wri_" + s: 0.10})
    c.add(skin_body("body", body, e, rad, "pelvis", seed=9.0, lumps=0.02), "crust", power=4.0,
          among=[b[0] for b in bones if b[0] not in ("crucible", "head", "hand_l", "hand_r", "foot_l", "foot_r")])
    # A leather apron and iron plates over the shoulders and forearms, a hump of a head.
    apron = lathe("apron", [(0.30, 1.75), (0.34, 1.45), (0.36, 1.2), (0.38, 0.95), (0.40, 0.7)], segs=32,
                  shape=lambda a, z, x, y: (x * 1.08, y * 0.82 - 0.02, z), skip=lambda a, z: math.sin(a) > -0.15)
    c.add(thicken(apron, 0.02), "leather", among=["pelvis", "spine", "chest", "thigh_l", "thigh_r"], power=3.0,
          anchor=("pelvis", 0.4))
    for s, sx in (("l", 1), ("r", -1)):
        sh = prim("uv_sphere", radius=0.2, segments=16, ring_count=8, location=(sx * 0.58, 0.02, 2.24))
        sh.scale = (1.0, 1.1, 0.55)
        c.add(sh, "iron", among=["chest", "upper_" + s], power=6.0)
        a, b = Vector(J["elb_" + s]), Vector(J["wri_" + s])
        c.add(between("cylinder", a + (b - a) * 0.15, a + (b - a) * 0.9, radius=0.13, vertices=12), "iron", "fore_" + s)
        ax, ay, az = J["ankle_" + s]
        boot = prim("uv_sphere", radius=0.13, segments=14, ring_count=8, location=(ax, ay - 0.1, 0.1))
        boot.scale = (0.9, 1.6, 0.8)
        c.add(boot, "leather", "foot_" + s)
        fist = prim("uv_sphere", radius=0.1, segments=12, ring_count=8, location=J["fin_" + s])
        c.add(fist, "leather", "hand_" + s)
    hx, hy, hz = J["head"]
    head = prim("uv_sphere", radius=0.21, segments=16, ring_count=10, location=(hx, hy - 0.04, hz + 0.14))
    head.scale = (1.0, 1.1, 0.85)
    c.add(head, "crust", "head")
    for sx in (-1, 1):
        eye = prim("uv_sphere", radius=0.03, segments=8, ring_count=6, location=(hx + sx * 0.08, hy - 0.25, hz + 0.16))
        c.add(eye, "ember", "head")
    visor = between("cylinder", (hx - 0.17, hy - 0.22, hz + 0.24), (hx + 0.17, hy - 0.22, hz + 0.24), radius=0.035, vertices=8)
    c.add(visor, "iron", "head")
    # The tongs: two iron arms from the fists that cross and grip the crucible's rim.
    rim_z = cz + 0.30
    for sx in (-1, 1):
        f = Vector(J["fin_r" if sx < 0 else "fin_l"])
        jaw = Vector((cx + sx * 0.30, cy, rim_z))
        bend = Vector((cx + sx * 0.18, cy + 0.05, rim_z + 0.25))
        c.add(between("cylinder", f, bend, radius=0.025, vertices=8), "iron", "crucible")
        c.add(between("cylinder", bend, jaw, radius=0.025, vertices=8), "iron", "crucible")
    c.add(between("cylinder", Vector(J["fin_r"]), Vector(J["fin_l"]), radius=0.02, vertices=8), "iron", "crucible")
    pot = lathe("pot", [(0.0, cz - 0.30), (0.20, cz - 0.29), (0.27, cz - 0.15), (0.30, cz + 0.12), (0.31, rim_z),
                        (0.27, rim_z), (0.26, cz + 0.10)], segs=28)
    c.add(pot, "firebrick", "crucible")
    melt = between("cylinder", (cx, cy, rim_z - 0.06), (cx, cy, rim_z - 0.03), radius=0.265, vertices=28)
    melt.location = (cx, cy, rim_z - 0.045)
    c.add(melt, "slag", "crucible")
    lip = between("cone", (cx, cy - 0.27, rim_z - 0.02), (cx, cy - 0.40, rim_z + 0.02), radius1=0.06, radius2=0.02, vertices=8)
    c.add(lip, "firebrick", "crucible")

    base = {"spine": (18, 0, 0), "chest": (10, 0, 0), "neck": (-20, 0, 0), "head": (-8, 0, 0),
            "thigh_l": (-8, 0, -4), "thigh_r": (-8, 0, 4), "shin_l": (14, 0, 0), "shin_r": (14, 0, 0), "move": (0, 0, -0.06)}
    stand = [(0.0, base), (0.5, pose_of(base, chest=(12, 0, 0), crucible=(0, 0, 0), move=(0, 0, -0.08))), (1.0, base)]
    step = pose_of(base, thigh_l=(-26, 0, -4), shin_l=(18, 0, 0), thigh_r=(10, 0, 4), shin_r=(26, 0, 0), pelvis=(0, 6, -6),
                   chest=(10, -4, 6), move=(0, 0, -0.10))
    mid = pose_of(base, thigh_l=(-10, 0, -4), shin_l=(14, 0, 0), thigh_r=(-16, 0, 4), shin_r=(50, 0, 0), pelvis=(0, 0, 0),
                  move=(0, 0, -0.03))
    walk = [(0.0, step), (0.25, mid), (0.5, mirror(step)), (0.75, mirror(mid)), (1.0, step)]
    # The pour: tip the crucible forward and sweep it across.
    tip = pose_of(base, spine=(26, 0, 0), chest=(16, 0, 0), upper_r=(-20, 0, 0), upper_l=(-20, 0, 0), crucible=(70, 0, 0),
                  move=(0, -0.05, -0.12))
    pour = [(0.0, base), (0.3, tip), (0.5, pose_of(tip, chest=(16, 0, -12), crucible=(80, 0, 0))),
            (0.75, pose_of(tip, chest=(16, 0, 12), crucible=(80, 0, 0))), (1.0, base)]
    # The swing: heave the crucible up and bring it down in front.
    heave = pose_of(base, spine=(-6, 0, 0), chest=(-10, 0, 0), upper_r=(-110, 0, 0), upper_l=(-110, 0, 0),
                    fore_r=(-30, 0, 0), fore_l=(-30, 0, 0), crucible=(-40, 0, 0), move=(0, 0.05, 0.0))
    smash = pose_of(base, spine=(34, 0, 0), chest=(16, 0, 0), upper_r=(10, 0, 0), upper_l=(10, 0, 0), crucible=(30, 0, 0),
                    thigh_l=(-30, 0, -4), shin_l=(30, 0, 0), move=(0, -0.15, -0.2))
    swing = [(0.0, base), (0.4, heave), (0.6, smash), (0.75, smash), (1.0, base)]
    reel = pose_of(base, spine=(4, 0, 10), chest=(0, 0, 8), head=(10, 0, -12), move=(0, 0.06, -0.06))
    pain = [(0.0, base), (0.3, reel), (1.0, base)]
    sag = pose_of(base, spine=(36, 0, 0), chest=(20, 0, 0), thigh_l=(-60, 0, -6), shin_l=(100, 0, 0), thigh_r=(-55, 0, 6),
                  shin_r=(100, 0, 0), foot_l=(-30, 0, 0), foot_r=(-30, 0, 0), crucible=(40, 0, 0), move=(0, 0.1, -0.6))
    fall = pose_of(sag, pelvis=(60, 0, 0), spine=(20, 0, 0), thigh_l=(-80, 0, -6), thigh_r=(-80, 0, 6), shin_l=(40, 0, 0),
                   shin_r=(40, 0, 0), upper_r=(-60, 0, -20), upper_l=(-60, 0, 20), crucible=(90, 0, 0), move=(0, -0.4, -1.3))
    death = [(0.0, base), (0.35, sag), (0.8, fall), (1.0, fall)]
    anims = [
        ("stand", 10, stand, True, None),
        ("walk", 12, walk, True, None),
        ("pour", 12, pour, False, None),
        ("swing", 10, swing, False, None),
        ("pain", 6, pain, False, None),
        ("death", 12, death, False, None),
    ]
    build(c, anims)


# ------------------------------------------------------------------ clinkers

def clinker():
    """A clinker: a crust of slag the size of a dog's head on six thin legs,
    its middle still molten, that scuttles and bursts. Built at 0.5 m long."""
    bones = [("body", None, (0, 0.0, 0.18), (0, -0.25, 0.20)), ("core", "body", (0, 0.0, 0.20), (0, 0.0, 0.32))]
    feet = {}
    for i, (y, spread) in enumerate(((-0.15, 0.28), (0.0, 0.32), (0.15, 0.28))):
        for s, sx in (("l", 1), ("r", -1)):
            hip = (sx * 0.12, y, 0.18)
            knee = (sx * spread, y - 0.04 * (1 - i), 0.30)
            foot = (sx * (spread + 0.08), y - 0.06 * (1 - i), 0.0)
            n = "%s%d" % (s, i)
            bones += [("thigh_" + n, "body", hip, knee), ("shin_" + n, "thigh_" + n, knee, foot)]
            feet[n] = (hip, knee, foot)
    c = Creature("clinker", bones, hull_bottom=-24.0)
    shell = prim("uv_sphere", radius=0.2, segments=20, ring_count=12, location=(0, 0, 0.22))
    shell.scale = (1.0, 1.25, 0.6)
    apply_all(shell)
    for v in shell.data.vertices:
        q = v.co * 6.0
        v.co += v.normal * 0.035 * (noise.noise(q) + 0.5 * noise.noise(q * 2.3))
    c.add(shell, "crust", "body")
    for i in range(7):
        a = math.tau * i / 7
        p = Vector((0.14 * math.cos(a), 0.18 * math.sin(a), 0.30))
        c.add(between("cone", p, p + Vector((0.04 * math.cos(a), 0.05 * math.sin(a), 0.08)), radius1=0.04, radius2=0.004,
                      vertices=5), "crust", "body")
    core = prim("ico_sphere", radius=0.1, subdivisions=2, location=(0, 0, 0.32))
    core.scale = (1.0, 1.2, 0.5)
    c.add(core, "slag", "core")
    for sx in (-1, 1):
        eye = prim("uv_sphere", radius=0.018, segments=8, ring_count=6, location=(sx * 0.05, -0.23, 0.24))
        c.add(eye, "ember", "body")
        mand = between("cone", (sx * 0.06, -0.22, 0.17), (sx * 0.02, -0.34, 0.12), radius1=0.025, radius2=0.004, vertices=5)
        c.add(mand, "bone", "body")
    for n, (hip, knee, foot) in feet.items():
        c.add(between("cylinder", hip, knee, radius=0.016, vertices=5), "crust", "thigh_" + n)
        c.add(between("cone", knee, foot, radius1=0.014, radius2=0.003, vertices=5), "crust", "shin_" + n)

    def legs(phase, lift):
        """A tripod gait: legs l0, r1, l2 against r0, l1, r2."""
        p = {}
        for n in feet:
            side, i = n[0], int(n[1])
            group = (side == "l") == (i % 2 == 0)
            up = lift if group == phase else 0.0
            swing = (16 if group == phase else -16) * (1 if side == "l" else -1)
            p["thigh_" + n] = (0, -up, swing)
            p["shin_" + n] = (0, up * 0.5, 0)
        return p
    base = {}
    stand = [(0.0, base), (0.5, pose_of(base, core=(0, 0, 0), move=(0, 0, 0.01))), (1.0, base)]
    run = [(0.0, legs(True, 30)), (0.5, legs(False, 30)), (1.0, legs(True, 30))]
    swell = pose_of(base, body=(-10, 0, 0), move=(0, 0, 0.06), **{"thigh_" + n: (0, 25 if n[0] == "l" else -25, 0) for n in feet})
    burst = [(0.0, base), (0.5, swell), (0.75, pose_of(swell, body=(-6, 0, 4))), (1.0, pose_of(swell, body=(-12, 0, -4)))]
    pain = [(0.0, base), (0.4, pose_of(base, body=(10, 0, 10), move=(0, 0.04, 0))), (1.0, base)]
    curl = {"thigh_" + n: (0, -70 if n[0] == "l" else 70, 0) for n in feet}
    curl.update({"shin_" + n: (0, -60 if n[0] == "l" else 60, 0) for n in feet})
    curl["move"] = (0, 0, -0.1)
    death = [(0.0, base), (0.5, pose_of(curl, body=(0, 40, 0))), (1.0, pose_of(curl, body=(0, 170, 0), move=(0, 0, 0.08)))]
    anims = [
        ("stand", 6, stand, True, None),
        ("run", 4, run, True, None),
        ("burst", 8, burst, False, None),
        ("pain", 4, pain, False, None),
        ("death", 8, death, False, None),
    ]
    build(c, anims)


# ------------------------------------------------------------------ cistern leeches

def leech():
    """A cistern leech: a ribbed grey-green worm as long as a man, flat as a
    belt, with a round sucker ringed in teeth at the front. Built facing -Y,
    level, at the hull's middle so it swims at a stoker's chest."""
    n = 7
    L = 1.5
    pts = [(0.0, -L / 2 + L * i / (n - 1), 0.75) for i in range(n)]
    bones = [("seg%d" % i, "seg%d" % (i - 1) if i else None, pts[i], pts[i + 1] if i + 1 < n else (0, pts[i][1] + 0.2, 0.75))
             for i in range(n)]
    c = Creature("leech", bones, hull_bottom=-24.0)
    joints = {"j%d" % i: p for i, p in enumerate(pts)}
    joints["tail"] = (0, pts[-1][1] + 0.18, 0.75)
    edges = [("j%d" % i, "j%d" % (i + 1)) for i in range(n - 1)] + [("j%d" % (n - 1), "tail")]
    rad = {}
    for i in range(n):
        t = i / (n - 1)
        w = 0.09 + 0.07 * math.sin(math.pi * (0.25 + 0.75 * t))
        rad["j%d" % i] = (w, w * 0.45)
    rad["tail"] = (0.04, 0.02)

    def ribs(p, nn):
        g = 0.5 + 0.5 * math.sin(p.y * math.tau / 0.06)
        return p - nn * 0.006 * g
    body = skin_body("body", joints, edges, rad, "j0", seed=5, lumps=0.003, shape=ribs)
    c.add(body, "leech", among=[b[0] for b in bones], power=4.0)
    # The sucker: a ring of lip round a red throat, teeth pointing in.
    x0, y0, z0 = pts[0]
    lip = prim("torus", major_radius=0.085, minor_radius=0.03, major_segments=20, minor_segments=8, location=(x0, y0 - 0.03, z0))
    lip.rotation_euler = (math.pi / 2, 0, 0)
    c.add(lip, "leech", "seg0")
    throat = prim("uv_sphere", radius=0.07, segments=14, ring_count=8, location=(x0, y0 - 0.01, z0))
    throat.scale = (1.0, 0.5, 1.0)
    c.add(throat, "flesh", "seg0")
    for i in range(12):
        a = math.tau * i / 12
        p = Vector((x0 + 0.075 * math.cos(a), y0 - 0.05, z0 + 0.075 * math.sin(a)))
        c.add(between("cone", p, p + Vector((-0.04 * math.cos(a), 0.0, -0.04 * math.sin(a))), radius1=0.009, radius2=0.001,
                      vertices=4), "bone", "seg0")
    # Two rows of pale eyespots along the back.
    for i in range(1, n - 1):
        for sx in (-1, 1):
            e = prim("uv_sphere", radius=0.012, segments=6, ring_count=4, location=(sx * 0.04, pts[i][1], 0.75 + 0.055))
            c.add(e, "ember", "seg%d" % i)

    def wave(phase, amp, lift=0.0):
        p = {}
        for i in range(1, n):
            p["seg%d" % i] = (lift * math.sin(phase + i * 0.9), 0, amp * math.sin(phase + i * 0.9) * (1 if i else 0))
        return p
    swim = [(k / 8, wave(math.tau * k / 8, 22, 6)) for k in range(9)]
    hold = wave(0, 10, 0)
    latch = [(0.0, hold), (0.5, pose_of(hold, seg1=(20, 0, 0), seg2=(10, 0, 0), move=(0, -0.05, 0))), (1.0, hold)]
    pain = [(0.0, wave(0, 8)), (0.4, wave(1.5, 40, 20)), (1.0, wave(3, 8))]
    curl = {"seg%d" % i: (0, 0, 35) for i in range(1, n)}
    curl["move"] = (0, 0, -0.3)
    death = [(0.0, wave(0, 10)), (0.5, pose_of(curl, seg0=(0, 60, 0))), (1.0, pose_of(curl, seg0=(0, 150, 0), move=(0, 0, -0.6)))]
    anims = [
        ("swim", 8, swim, True, None),
        ("latch", 6, latch, True, None),
        ("pain", 4, pain, False, None),
        ("death", 8, death, False, None),
    ]
    build(c, anims)


# ------------------------------------------------------------------ ash wraiths

def ash_wraith():
    """An ash wraith: a hooded thing of ash from the waist up, long clawed
    hands, and below the waist only a trail of ash that streams out behind.
    Built facing -Y at 1.9 m from the trail's tip to the crown, floating."""
    J = scaled(HUMAN, 1.05)
    w = J["pelvis"]
    tips = [(0, 0.12, 0.62), (0, 0.32, 0.34), (0, 0.6, 0.12)]
    extra = [("trail1", "pelvis", w, tips[0]), ("trail2", "trail1", tips[0], tips[1]), ("trail3", "trail2", tips[1], tips[2])]
    for s, sx in (("l", 1), ("r", -1)):
        f = Vector(J["fin_" + s])
        for i, dx in enumerate((-0.03, 0.0, 0.03)):
            a = f + Vector((sx * dx, -0.01, 0.0))
            extra.append(("claw%d_%s" % (i, s), "hand_" + s, tuple(a), tuple(a + Vector((sx * dx * 0.6, -0.04, -0.13)))))
    c = Creature("wraith", humanoid(J, extra), hull_bottom=-24.0)
    k = 1.05
    for s in "lr":
        arm = {n: J[n] for n in ("chest", "sho_" + s, "elb_" + s, "wri_" + s)}
        a = skin_body("arm_" + s, arm, [("chest", "sho_" + s), ("sho_" + s, "elb_" + s), ("elb_" + s, "wri_" + s)],
                      {"chest": 0.06 * k, "sho_" + s: 0.07 * k, "elb_" + s: 0.06 * k, "wri_" + s: 0.085 * k},
                      "chest", seed=11, lumps=0.012, subdiv=2)
        c.add(a, "ash", among=["chest", "upper_" + s, "fore_" + s], power=4.0)
        wr, fi = Vector(J["wri_" + s]), Vector(J["fin_" + s])
        hand = skin_body("hand_" + s, {"w": tuple(wr - (fi - wr) * 0.3), "f": tuple(fi)}, [("w", "f")],
                         {"w": 0.026, "f": (0.032, 0.018)}, "w", subdiv=1)
        c.add(hand, "bone", "hand_" + s)
        for i in range(3):
            b = c.bones[c.index["claw%d_%s" % (i, s)]]
            c.add(between("cone", b[2], b[3], radius1=0.011, radius2=0.001, vertices=5), "bone", "claw%d_%s" % (i, s))
    top = J["neck"][2] - 0.02
    torso = lathe("torso", [(0.06, top), (0.2, J["sho_l"][2] - 0.03), (0.21, J["chest"][2]), (0.17, J["spine"][2]),
                            (0.15, w[2] + 0.02)], segs=32,
                  shape=lambda a, z, x, y: (x, y * 0.75 + J["chest"][1], z))
    c.add(torso, "ash", among=["pelvis", "spine", "chest", "neck"], power=3.0)

    def stream(a, z, x, y):
        t = max(0.0, min(1.0, 1.0 - z / w[2]))
        rag = 1.0 + 0.35 * t * (math.sin(7 * a) * 0.6 + noise.noise(Vector((a * 3.0, z * 6.0, 1.0))))
        return x * rag, y * rag + 0.62 * t * t, z
    trail = lathe("trail", [(0.16, w[2] + 0.04), (0.18, w[2] - 0.12), (0.15, w[2] * 0.6), (0.09, w[2] * 0.33),
                            (0.03, 0.1), (0.0, 0.04)], segs=40, shape=stream)
    thicken(trail, 0.01)
    c.add(trail, "ash", among=["pelvis", "trail1", "trail2", "trail3"], power=2.0)
    hood(c, J, k, mat="ash", rag=0.3)
    hx, hy, hz = J["head"]
    for x in (-0.04, 0.04):
        eye = prim("uv_sphere", radius=0.022, segments=10, ring_count=6, location=(hx + x, hy - 0.135, hz + 0.08))
        eye.scale = (1.2, 0.5, 0.6)
        c.add(eye, "ember", "head")

    def claws(curl):
        return {"claw%d_%s" % (i, s): (curl, 0, 0) for i in range(3) for s in "lr"}
    base = pose_of(claws(10), spine=(8, 0, 0), chest=(6, 0, 0), neck=(-4, 0, 0), upper_l=(-18, 0, 12), fore_l=(-40, 0, 0),
                   upper_r=(-18, 0, -12), fore_r=(-40, 0, 0), trail1=(14, 0, 0), trail2=(10, 0, 0), trail3=(8, 0, 0))

    def drifting(t):
        a = math.tau * t
        return pose_of(base, move=(0, 0, 0.05 * math.sin(a)), trail1=(14 + 6 * math.sin(a), 0, 10 * math.sin(a)),
                       trail2=(10, 0, 14 * math.sin(a - 1.0)), trail3=(8, 0, 18 * math.sin(a - 2.0)),
                       upper_l=(-18 + 6 * math.sin(a), 0, 12), upper_r=(-18 - 6 * math.sin(a), 0, -12))
    drift = [(k8 / 8, drifting(k8 / 8)) for k8 in range(9)]
    dive = pose_of(claws(-25), pelvis=(38, 0, 0), spine=(10, 0, 0), chest=(6, 0, 0), neck=(-30, 0, 0), head=(-14, 0, 0),
                   upper_l=(-95, 0, 18), fore_l=(-10, 0, 0), upper_r=(-95, 0, -18), fore_r=(-10, 0, 0),
                   trail1=(-28, 0, 0), trail2=(-12, 0, 0), trail3=(-8, 0, 0))
    swoop = [(0.0, base), (0.4, dive), (0.7, pose_of(dive, trail2=(-4, 0, 10), trail3=(0, 0, 16))),
             (1.0, pose_of(dive, trail2=(-4, 0, -10), trail3=(0, 0, -16)))]
    rake_up = pose_of(dive, upper_r=(-150, 0, -30), fore_r=(-30, 0, 0), upper_l=(-60, 0, 10), spine=(-4, 0, -10))
    rake = pose_of(dive, upper_r=(-40, 0, 25), fore_r=(-10, 0, 0), upper_l=(-140, 0, 20), fore_l=(-30, 0, 0),
                   spine=(18, 0, 14), **claws(40))
    claw = [(0.0, dive), (0.3, rake_up), (0.55, rake), (1.0, base)]
    reel = pose_of(base, spine=(-16, 0, 8), chest=(-10, 0, 0), head=(14, 0, -10), upper_l=(-60, 0, 40), upper_r=(-50, 0, -40),
                   trail1=(40, 0, 0), move=(0, 0.08, 0.06))
    pain = [(0.0, base), (0.35, reel), (1.0, base)]
    sag = pose_of(base, spine=(30, 0, 0), chest=(20, 0, 0), neck=(20, 0, 0), upper_l=(10, 0, 20), upper_r=(10, 0, -20),
                  fore_l=(-10, 0, 0), fore_r=(-10, 0, 0), move=(0, 0, -0.3))
    death = [(0.0, base), (0.3, sag), (1.0, sag)]
    anims = [
        ("drift", 8, drift, True, None),
        ("swoop", 8, swoop, False, None),
        ("claw", 6, claw, False, None),
        ("pain", 4, pain, False, None),
        ("death", 10, death, False, "crumble"),
    ]
    build(c, anims, {"crumble": crumble})


# ------------------------------------------------------------------ bell-ringers

def bell_ringer():
    """A bell-ringer: a gaunt giant of ash with a bronze bell where its ribs
    should be, the clapper hanging inside, and a ringer's mallet in its right
    hand. It tolls itself, and the toll runs out along the floor. About 3.2 m:
    the large hull."""
    k = 1.7
    J = scaled(HUMAN, k, wide=1.3)
    J["neck"], J["head"], J["crown"] = (0, -0.06, 2.68), (0, -0.1, 2.76), (0, -0.12, 3.06)
    ch = Vector(J["chest"])
    mal0 = Vector(J["fin_r"])
    mal1 = mal0 + Vector((0.0, -0.25, -0.85))
    bones = humanoid(J, [("clapper", "chest", tuple(ch + Vector((0, 0, 0.15))), tuple(ch + Vector((0, 0, -0.55)))),
                         ("mallet", "hand_r", tuple(mal0), tuple(mal1))])
    c = Creature("ringer", bones, hull_bottom=-24.0)
    body = {n: J[n] for n in ("pelvis", "spine", "chest", "neck", "hip_l", "knee_l", "ankle_l", "toe_l", "hip_r", "knee_r",
                              "ankle_r", "toe_r", "sho_l", "elb_l", "wri_l", "sho_r", "elb_r", "wri_r")}
    e = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck")]
    rad = {"pelvis": (0.22, 0.17), "spine": (0.13, 0.11), "chest": (0.14, 0.12), "neck": (0.09, 0.08)}
    for sd in "lr":
        e += [("pelvis", "hip_" + sd), ("hip_" + sd, "knee_" + sd), ("knee_" + sd, "ankle_" + sd), ("ankle_" + sd, "toe_" + sd),
              ("chest", "sho_" + sd), ("sho_" + sd, "elb_" + sd), ("elb_" + sd, "wri_" + sd)]
        rad.update({"hip_" + sd: 0.16, "knee_" + sd: 0.11, "ankle_" + sd: 0.085, "toe_" + sd: (0.09, 0.05),
                    "sho_" + sd: 0.13, "elb_" + sd: 0.095, "wri_" + sd: 0.075})
    c.add(skin_body("body", body, e, rad, "pelvis", seed=21.0, lumps=0.015), "ash", power=4.0,
          among=[b[0] for b in bones if b[0] not in ("clapper", "mallet", "head", "hand_l", "hand_r")])
    # The bell, round the chest from the neck to the hips, open at the mouth.
    bell = lathe("bell", [(0.10, 2.70), (0.30, 2.62), (0.38, 2.42), (0.40, 2.15), (0.46, 1.92), (0.58, 1.74),
                          (0.64, 1.64), (0.60, 1.60)], segs=54,
                 shape=lambda a, z, x, y: (x, y * 0.9 + ch.y, z),
                 skip=lambda a, z: 1.84 < z < 2.44 and (a % (math.tau / 9)) > math.tau / 9 * 0.4)   # cut into ribs
    thicken(bell, 0.03)
    c.add(bell, "bronze", among=["chest", "spine"], power=6.0)
    for z in (2.5, 1.7):
        band = prim("torus", major_radius=0.40 if z > 2 else 0.63, minor_radius=0.018, major_segments=40, minor_segments=6,
                    location=(0, ch.y, z))
        band.scale = (1.0, 0.9, 1.0)
        c.add(band, "bronze", among=["chest", "spine"], power=6.0)
    clap = prim("uv_sphere", radius=0.13, segments=14, ring_count=8, location=tuple(ch + Vector((0, 0, -0.32))))
    c.add(clap, "ember", "clapper")          # hot from tolling, so it shows through the slots
    c.add(between("cylinder", ch + Vector((0, 0, 0.15)), ch + Vector((0, 0, -0.25)), radius=0.025, vertices=8), "iron", "clapper")
    for sd in "lr":
        w, f = Vector(J["wri_" + sd]), Vector(J["fin_" + sd])
        c.add(between("cylinder", w, f, radius=0.065, vertices=10), "ash", "hand_" + sd)      # the hand from the wrist on
        fist = prim("uv_sphere", radius=0.085, segments=12, ring_count=8, location=tuple(w.lerp(f, 0.7)))
        fist.scale = (0.8, 1.0, 1.2)
        c.add(fist, "ash", "hand_" + sd)
    # The head: small, hooded in sacking, two coals for eyes.
    hx, hy, hz = J["head"]
    skull = prim("uv_sphere", radius=0.15, segments=16, ring_count=10, location=(hx, hy, hz + 0.12))
    skull.scale = (0.9, 1.05, 1.1)
    c.add(skull, "bone", "head")
    hd = prim("uv_sphere", radius=0.19, segments=16, ring_count=10, location=(hx, hy + 0.05, hz + 0.16))
    hd.scale = (1.0, 1.0, 1.15)
    for v in hd.data.vertices:
        if v.co.y < -0.08:
            v.co.y = -0.08
    c.add(hd, "hood", "head")
    for sx in (-1, 1):
        eye = prim("uv_sphere", radius=0.03, segments=8, ring_count=6, location=(hx + sx * 0.06, hy - 0.14, hz + 0.14))
        c.add(eye, "ember", "head")
    # The mallet.
    c.add(between("cylinder", mal0 + (mal0 - mal1) * 0.1, mal1, radius=0.03, vertices=8), "oak", "mallet")
    c.add(between("cylinder", mal1 + Vector((-0.2, 0, 0)), mal1 + Vector((0.2, 0, 0)), radius=0.11, vertices=14), "iron", "mallet")

    base = {"spine": (22, 0, 0), "chest": (10, 0, 0), "neck": (-34, 0, 0), "upper_r": (-24, 0, -6), "fore_r": (-36, 0, 0),
            "upper_l": (-4, 0, 8), "fore_l": (-20, 0, 0), "thigh_l": (-6, 0, -2), "thigh_r": (-6, 0, 2),
            "shin_l": (12, 0, 0), "shin_r": (12, 0, 0), "move": (0, 0, -0.05)}
    stand = [(t, pose_of(base, clapper=(sw, 0, 0), chest=(6 + sw * 0.1, 0, 0))) for t, sw in ((0, 6), (0.5, -6), (1.0, 6))]
    step = pose_of(base, thigh_l=(-28, 0, -2), shin_l=(18, 0, 0), thigh_r=(12, 0, 2), shin_r=(30, 0, 0), pelvis=(0, 6, -6),
                   chest=(6, -4, 6), clapper=(-10, 0, 8), move=(0, 0, -0.1))
    mid = pose_of(base, thigh_l=(-10, 0, -2), shin_l=(12, 0, 0), thigh_r=(-18, 0, 2), shin_r=(55, 0, 0),
                  clapper=(10, 0, 0), move=(0, 0, -0.02))
    walk = [(0.0, step), (0.25, mid), (0.5, mirror(step)), (0.75, mirror(mid)), (1.0, step)]
    # The toll: mallet up and back, then into the bell's flank, and the clapper swings.
    up = pose_of(base, spine=(-6, 0, 10), chest=(-6, 0, 12), upper_r=(-160, 0, -30), fore_r=(-40, 0, 0),
                 mallet=(-30, 0, 0), move=(0, 0.04, 0))
    hit = pose_of(base, spine=(16, 0, -14), chest=(10, 0, -16), upper_r=(-60, 0, 30), fore_r=(-70, 0, 0),
                  mallet=(-60, 0, 0), clapper=(-25, 0, 20), thigh_r=(-20, 0, 2), move=(0, -0.05, -0.12))
    ring = pose_of(hit, clapper=(20, 0, -20), chest=(4, 0, -6))
    toll = [(0.0, base), (0.45, up), (0.6, hit), (0.75, ring), (0.88, pose_of(base, clapper=(-12, 0, 8))), (1.0, base)]
    back = pose_of(base, spine=(0, 0, -20), chest=(0, 0, -24), upper_l=(-60, 0, -40), fore_l=(-30, 0, 0))
    lash = pose_of(base, spine=(18, 0, 26), chest=(10, 0, 30), upper_l=(-80, 0, 60), fore_l=(-10, 0, 0),
                   thigh_l=(-22, 0, -2), shin_l=(24, 0, 0), move=(0, -0.08, -0.08))
    swing = [(0.0, base), (0.4, back), (0.62, lash), (1.0, base)]
    reel = pose_of(base, spine=(-8, 0, 10), chest=(-8, 0, 6), neck=(6, 0, 0), clapper=(30, 0, 0), move=(0, 0.06, 0))
    pain = [(0.0, base), (0.35, reel), (1.0, base)]
    kneel = pose_of(base, spine=(24, 0, 0), thigh_l=(-80, 0, -2), shin_l=(125, 0, 0), thigh_r=(-70, 0, 2), shin_r=(120, 0, 0),
                    foot_l=(-40, 0, 0), foot_r=(-40, 0, 0), clapper=(-30, 0, 0), move=(0, 0.1, -0.72))
    down = pose_of(kneel, pelvis=(70, 0, 0), spine=(14, 0, 0), thigh_l=(-90, 0, -2), shin_l=(60, 0, 0), thigh_r=(-85, 0, 6),
                   shin_r=(50, 0, 0), upper_r=(-70, 0, -40), upper_l=(-70, 0, 40), clapper=(60, 0, 0), move=(0, -0.4, -1.5))
    death = [(0.0, base), (0.35, kneel), (0.8, down), (1.0, down)]
    anims = [
        ("stand", 8, stand, True, None),
        ("walk", 12, walk, True, None),
        ("toll", 14, toll, False, None),
        ("swing", 10, swing, False, None),
        ("pain", 5, pain, False, None),
        ("death", 12, death, False, None),
    ]
    build(c, anims)


# ------------------------------------------------------------------ the Founder

def founder():
    """The Founder: the man who cast the bell, grown into his own last mould.
    From the waist down he is the clay cope of a bell mould, cracked, with
    the iron still molten inside it; above it a furnace master of slag crust
    in an iron cap, his forearms and hands running with iron that drips from
    his fingers. About 3.8 m: the large hull, drawn big."""
    k = 1.9
    J = scaled(HUMAN, k, wide=1.3)
    J["neck"], J["head"], J["crown"] = (0, -0.06, 3.00), (0, -0.10, 3.10), (0, -0.12, 3.44)
    c = Creature("founder", humanoid(J), hull_bottom=-24.0)
    px, py, pz = J["pelvis"]
    # The mould: a bell's cope from the floor to the waist, hooped in iron,
    # split where the iron inside shows through.
    prof = [(1.06, 0.0), (1.08, 0.08), (1.0, 0.16)]
    for i in range(1, 15):                              # a bell's cope: flared at the lip, a waist, a shoulder
        z = 0.16 + (pz - 0.16) * i / 15
        u = z / pz
        prof.append((0.98 - 0.62 * u + 0.18 * u * u * (1 - u) * 4, z))
    prof += [(0.44, pz + 0.06), (0.32, pz + 0.12)]
    cope = lathe("cope", prof, segs=64, shape=lambda a, z, x, y: (x, y * 0.92 + py, z))
    thicken(cope, 0.05)
    c.add(cope, "cope", "pelvis")
    for z, r in ((0.12, 1.06),):
        hoop = prim("torus", major_radius=r, minor_radius=0.04, major_segments=48, minor_segments=8, location=(0, py, z))
        hoop.scale = (1.0, 0.92, 1.0)
        c.add(hoop, "iron", "pelvis")
    # The man: slag crust from the waist up.
    body = {n: J[n] for n in ("pelvis", "spine", "chest", "neck", "sho_l", "elb_l", "sho_r", "elb_r")}
    e = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck")]
    rad = {"pelvis": (0.42, 0.32), "spine": (0.44, 0.32), "chest": (0.52, 0.36), "neck": (0.19, 0.17)}
    for sd in "lr":
        e += [("chest", "sho_" + sd), ("sho_" + sd, "elb_" + sd)]
        rad.update({"sho_" + sd: 0.21, "elb_" + sd: 0.16})
    up = ["pelvis", "spine", "chest", "neck", "upper_l", "upper_r"]
    c.add(skin_body("body", body, e, rad, "pelvis", seed=31.0, lumps=0.025), "crust", among=up, power=4.0)
    collar = prim("torus", major_radius=0.24, minor_radius=0.05, major_segments=28, minor_segments=8,
                  location=(0, J["neck"][1], J["neck"][2] - 0.06))
    collar.scale = (1.15, 1.0, 1.0)
    c.add(collar, "iron", "chest")
    for sd in "lr":
        el, wr, fi = Vector(J["elb_" + sd]), Vector(J["wri_" + sd]), Vector(J["fin_" + sd])
        c.add(between("cone", el, wr, radius1=0.16, radius2=0.12, vertices=14), "crust", "fore_" + sd)   # forearms crusting over
        c.add(between("cylinder", wr, fi, radius=0.11, vertices=12), "slag", "hand_" + sd)
        fist = prim("uv_sphere", radius=0.17, segments=14, ring_count=10, location=tuple(wr.lerp(fi, 0.75)))
        fist.scale = (0.85, 1.0, 1.25)
        c.add(fist, "slag", "hand_" + sd)
        band = prim("torus", major_radius=0.13, minor_radius=0.03, major_segments=20, minor_segments=6, location=tuple(el.lerp(wr, 0.1)))
        c.add(band, "iron", "fore_" + sd)
        hand = (fi - wr).normalized()
        side = Vector((1, 0, 0)) if sd == "l" else Vector((-1, 0, 0))
        for j, off in enumerate((-0.07, -0.02, 0.03, 0.08)):                  # thick fingers, curled
            root = wr.lerp(fi, 0.95) + side * off * 0.9 + Vector((0, -0.03, 0))
            tip = root + hand * 0.17 + Vector((0, -0.07, -0.02))
            c.add(between("cone", root, tip, radius1=0.042, radius2=0.022, vertices=8), "slag", "hand_" + sd)
        thumb = wr.lerp(fi, 0.6) - side * 0.11
        c.add(between("cone", thumb, thumb + Vector((0, -0.14, -0.06)) - side * 0.03, radius1=0.045, radius2=0.025,
                      vertices=8), "slag", "hand_" + sd)
        for i, (dx, dy) in enumerate(((0.05, -0.03), (-0.04, 0.02), (0.0, -0.06))):
            top = fi + Vector((dx, dy, -0.02))
            c.add(between("cone", top, top + Vector((0, 0, -0.22 - 0.08 * i)), radius1=0.035, radius2=0.004, vertices=6),
                  "slag", "hand_" + sd)                         # iron dripping from his fingers
    # The head: crust, two coals, a founder's cap of iron and a beard run in slag.
    hx, hy, hz = J["head"]
    head = prim("uv_sphere", radius=0.29, segments=18, ring_count=12, location=(hx, hy - 0.02, hz + 0.16))
    head.scale = (0.95, 1.05, 1.1)
    c.add(head, "crust", "head")
    cap = lathe("cap", [(0.29, hz + 0.24), (0.28, hz + 0.36), (0.22, hz + 0.45), (0.0, hz + 0.48)], segs=24,
                shape=lambda a, z, x, y: (x + hx, y + hy - 0.02, z))
    c.add(thicken(cap, 0.02), "iron", "head")
    for sx in (-1, 1):
        eye = prim("uv_sphere", radius=0.06, segments=10, ring_count=6, location=(hx + sx * 0.1, hy - 0.26, hz + 0.17))
        eye.scale = (1.3, 0.6, 0.8)
        c.add(eye, "ember", "head")
    # A beard of crust over the chest, run through with iron.
    beard = prim("uv_sphere", radius=0.24, segments=14, ring_count=10, location=(hx, hy - 0.2, hz - 0.2))
    beard.scale = (1.0, 0.38, 1.3)
    for v in beard.data.vertices:
        if v.co.z < 0:
            v.co.y *= 1.0 + v.co.z * 1.5
    c.add(beard, "crust", "head")
    for dx in (-0.07, 0.04):
        top = Vector((hx + dx, hy - 0.29, hz + 0.02))
        c.add(between("cone", top, top + Vector((0, -0.02, -0.36)), radius1=0.03, radius2=0.004, vertices=6), "slag", "head")

    base = {"spine": (10, 0, 0), "chest": (8, 0, 0), "neck": (-16, 0, 0), "head": (-6, 0, 0),
            "upper_l": (-10, 0, 14), "upper_r": (-10, 0, -14), "fore_l": (-30, 0, 0), "fore_r": (-30, 0, 0)}
    stand = [(0.0, base), (0.5, pose_of(base, chest=(12, 0, 0), neck=(-20, 0, 0), move=(0, 0, 0.02))), (1.0, base)]
    lurch = pose_of(base, pelvis=(0, 0, 8), chest=(10, 0, -10), upper_l=(-20, 0, 14), upper_r=(0, 0, -14), move=(0, 0, 0.04))
    walk = [(0.0, base), (0.25, lurch), (0.5, base), (0.75, mirror(lurch)), (1.0, base)]
    # The pour: both hands out and tipped, sweeping across.
    out = pose_of(base, spine=(18, 0, 0), chest=(12, 0, 0), upper_l=(-75, 0, 10), upper_r=(-75, 0, -10),
                  fore_l=(-15, 0, 0), fore_r=(-15, 0, 0), hand_l=(45, 0, 0), hand_r=(45, 0, 0), move=(0, -0.04, -0.06))
    pour = [(0.0, base), (0.25, out), (0.5, pose_of(out, chest=(12, 0, -18))), (0.8, pose_of(out, chest=(12, 0, 18))),
            (1.0, base)]
    # The hurl: the right hand back and over, flinging a gout of iron.
    back = pose_of(base, spine=(0, 0, -16), chest=(-8, 0, -20), upper_r=(-150, 0, -40), fore_r=(-50, 0, 0))
    throw = pose_of(base, spine=(20, 0, 14), chest=(14, 0, 18), upper_r=(-70, 0, 20), fore_r=(-10, 0, 0), move=(0, -0.06, -0.05))
    hurl = [(0.0, base), (0.45, back), (0.65, throw), (1.0, base)]
    # The slam: both fists up, then down into the floor before him.
    raise_ = pose_of(base, spine=(-6, 0, 0), chest=(-10, 0, 0), upper_l=(-165, 0, 10), upper_r=(-165, 0, -10),
                     fore_l=(-20, 0, 0), fore_r=(-20, 0, 0), move=(0, 0.04, 0.04))
    down = pose_of(base, spine=(36, 0, 0), chest=(20, 0, 0), upper_l=(-50, 0, 6), upper_r=(-50, 0, -6),
                   fore_l=(-10, 0, 0), fore_r=(-10, 0, 0), move=(0, -0.08, -0.2))
    slam = [(0.0, base), (0.45, raise_), (0.6, down), (0.8, down), (1.0, base)]
    reel = pose_of(base, spine=(-10, 0, 8), chest=(-10, 0, 6), neck=(0, 0, -10), upper_l=(-40, 0, 30), move=(0, 0.04, 0))
    pain = [(0.0, base), (0.35, reel), (1.0, base)]
    # His death: he reaches up once, then slumps over the mould and it sinks.
    reach = pose_of(base, spine=(-14, 0, 0), chest=(-14, 0, 0), neck=(-30, 0, 0), upper_l=(-170, 0, 20), upper_r=(-170, 0, -20),
                    fore_l=(-10, 0, 0), fore_r=(-10, 0, 0))
    slump = pose_of(base, spine=(50, 0, 0), chest=(30, 0, 0), neck=(10, 0, 0), upper_l=(-30, 0, 30), upper_r=(-20, 0, -30),
                    fore_l=(-60, 0, 0), fore_r=(-60, 0, 0), move=(0, -0.1, -0.5))
    sunk = pose_of(slump, pelvis=(12, 0, 0), move=(0, -0.2, -1.4))
    death = [(0.0, base), (0.25, reach), (0.55, slump), (0.9, sunk), (1.0, sunk)]
    anims = [
        ("stand", 10, stand, True, None),
        ("walk", 12, walk, True, None),
        ("pour", 16, pour, False, None),
        ("hurl", 12, hurl, False, None),
        ("slam", 12, slam, False, None),
        ("pain", 6, pain, False, None),
        ("death", 20, death, False, None),
    ]
    build(c, anims)


CREATURES = {"ashen": ashen, "censer": censer_bearer, "deacon": deacon, "hound": slag_hound,
             "gauger": gauger, "brute": crucible_brute, "clinker": clinker, "leech": leech,
             "wraith": ash_wraith, "ringer": bell_ringer, "founder": founder}

if __name__ == "__main__":  # weapons.py imports the rest
    for name, make in CREATURES.items():
        if not ONLY or name in ONLY:
            make()
