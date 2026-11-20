"""Cinderkirk world textures: procedural materials in Blender, baked to the four
maps the pipeline in ideas/25-cinderkirk.md describes.

    blender -b -P materials.py -- <out dir> [resolution] [only=name,name]
    python materials.py -- <out dir> [resolution]      (with the bpy wheel)

Each material is built from nodes on a 2 m plane and baked with Cycles to
<name>.png (albedo, no lighting), <name>_norm.png (tangent-space normal),
<name>_gloss.png (shininess: 1 - roughness) and, when it glows, <name>_luma.png.
Every texture tiles: noise is sampled on a torus in 4D, and brick counts divide
the tile evenly. Liquids start with '*' in the map, and are saved with '#', as
QuakeSpasm-family ports look for them.
"""
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "textures")
RES = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 1024
ONLY = next((a[5:].split(",") for a in argv if a.startswith("only=")), None)
HERE = os.path.dirname(os.path.abspath(__file__))
TAU = math.tau


class Graph:
    """A small helper for writing node graphs as expressions."""

    def __init__(self, mat):
        self.t = mat.node_tree
        self.t.nodes.clear()
        self.uv = self.node("ShaderNodeTexCoord").outputs["UV"]

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

    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        nd = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b, c)):
            self.feed(nd.inputs[i], v)
        return nd.outputs[0]

    def add(self, a, b): return self.math("ADD", a, b)
    def mul(self, a, b): return self.math("MULTIPLY", a, b)
    def sub(self, a, b): return self.math("SUBTRACT", a, b)
    def clamp(self, a): return self.math("ADD", a, 0.0, clamp=True)

    def remap(self, v, lo, hi, to_lo=0.0, to_hi=1.0, smooth=True):
        nd = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP" if smooth else "LINEAR")
        self.feed(nd.inputs["Value"], v)
        nd.inputs["From Min"].default_value = lo
        nd.inputs["From Max"].default_value = hi
        nd.inputs["To Min"].default_value = to_lo
        nd.inputs["To Max"].default_value = to_hi
        return nd.outputs["Result"]

    def mixc(self, fac, a, b, blend="MIX"):
        nd = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=True)
        self.feed(nd.inputs[0], fac)
        self.feed(nd.inputs[6], a)
        self.feed(nd.inputs[7], b)
        return nd.outputs[2]

    def mixf(self, fac, a, b):
        nd = self.node("ShaderNodeMix", data_type="FLOAT", clamp_factor=True)
        self.feed(nd.inputs[0], fac)
        self.feed(nd.inputs[2], a)
        self.feed(nd.inputs[3], b)
        return nd.outputs[0]

    def torus(self, r, ox=0.0):
        """UV on a torus in 4D, so noise sampled there tiles in both directions."""
        sep = self.node("ShaderNodeSeparateXYZ")
        self.feed(sep.inputs[0], self.uv)
        a = self.mul(sep.outputs["X"], TAU)
        b = self.mul(sep.outputs["Y"], TAU)
        comb = self.node("ShaderNodeCombineXYZ")
        self.feed(comb.inputs["X"], self.add(self.mul(self.math("COSINE", a), r), ox))
        self.feed(comb.inputs["Y"], self.mul(self.math("SINE", a), r))
        self.feed(comb.inputs["Z"], self.mul(self.math("COSINE", b), r))
        return comb.outputs[0], self.mul(self.math("SINE", b), r)

    def noise(self, r, detail=6.0, rough=0.55, distort=0.0, seed=0.0):
        vec, w = self.torus(r, ox=seed * 17.0)
        nd = self.node("ShaderNodeTexNoise", noise_dimensions="4D")
        self.feed(nd.inputs["Vector"], vec)
        self.feed(nd.inputs["W"], w)
        nd.inputs["Scale"].default_value = 1.0
        nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough
        nd.inputs["Distortion"].default_value = distort
        return nd.outputs["Fac"]

    def voronoi(self, r, feature="F1", out="Distance", seed=0.0, rand=1.0):
        vec, w = self.torus(r, ox=seed * 23.0)
        nd = self.node("ShaderNodeTexVoronoi", voronoi_dimensions="4D", feature=feature)
        self.feed(nd.inputs["Vector"], vec)
        self.feed(nd.inputs["W"], w)
        nd.inputs["Scale"].default_value = 1.0
        nd.inputs["Randomness"].default_value = rand
        return nd.outputs[out]

    def bricks(self, across, rows, mortar, c1, c2, cm, offset=0.5, bias=0.0, smooth=0.2):
        nd = self.node("ShaderNodeTexBrick", offset=offset, offset_frequency=2, squash=1.0, squash_frequency=2)
        self.feed(nd.inputs["Vector"], self.uv)
        self.feed(nd.inputs["Color1"], c1)
        self.feed(nd.inputs["Color2"], c2)
        self.feed(nd.inputs["Mortar"], cm)
        nd.inputs["Scale"].default_value = 1.0
        nd.inputs["Mortar Size"].default_value = mortar
        nd.inputs["Mortar Smooth"].default_value = smooth
        nd.inputs["Bias"].default_value = bias
        nd.inputs["Brick Width"].default_value = 1.0 / across
        nd.inputs["Row Height"].default_value = 1.0 / rows
        return nd.outputs["Color"], nd.outputs["Fac"]

    def image(self, path, non_color=True):
        img = bpy.data.images.load(path)
        if non_color:
            img.colorspace_settings.name = "Non-Color"
        nd = self.node("ShaderNodeTexImage", image=img)
        self.feed(nd.inputs["Vector"], self.uv)
        return nd.outputs["Color"]

    def finish(self, color, rough, height, bump=0.6, dist=0.02, emit=None, emit_strength=0.0, metal=0.0):
        bsdf = self.node("ShaderNodeBsdfPrincipled")
        self.feed(bsdf.inputs["Base Color"], color)
        self.feed(bsdf.inputs["Roughness"], rough)
        self.feed(bsdf.inputs["Metallic"], metal)
        b = self.node("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = dist * 3.0
        self.feed(b.inputs["Height"], height)
        self.t.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
        if emit is not None:
            self.feed(bsdf.inputs["Emission Color"], emit)
            bsdf.inputs["Emission Strength"].default_value = emit_strength
        out = self.node("ShaderNodeOutputMaterial")
        self.t.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        self.maps = {"albedo": color, "rough": rough, "emit": emit}
        self.bsdf, self.out = bsdf, out


def soot(g, r=1.1, seed=0.0, lo=0.62, hi=1.0):
    """A slow multiply layer: soot and smoke staining."""
    n = g.noise(r, 5.0, 0.6, seed=seed)
    return g.remap(n, 0.35, 0.72, hi, lo)


def brick_base(g, seed=0.0):
    col, fac = g.bricks(8, 16, 0.006, (0.115, 0.050, 0.034), (0.062, 0.036, 0.028), (0.034, 0.031, 0.028), bias=-0.1)
    chip = g.noise(9.0, 4.0, 0.6, seed=seed + 1)
    mortar = g.remap(g.add(fac, g.mul(g.sub(chip, 0.5), 0.9)), 0.46, 0.56)
    speck = g.remap(g.noise(60.0, 2.0, 0.5, seed=seed + 2), 0.62, 0.75)
    col = g.mixc(g.mul(speck, 0.35), col, (0.20, 0.12, 0.09))
    col = g.mixc(mortar, col, (0.030, 0.028, 0.026))
    s = soot(g, seed=seed + 3)
    col = g.mixc(1.0, col, g.mixc(s, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), blend="MULTIPLY")
    pits = g.remap(g.voronoi(40.0, seed=seed + 4), 0.0, 0.18, 0.0, 1.0)
    height = g.add(g.mul(g.sub(1.0, mortar), 1.0), g.add(g.mul(chip, 0.15), g.mul(pits, 0.1)))
    rough = g.add(0.80, g.mul(mortar, 0.14))
    return col, rough, height, mortar


def m_brick(g):
    col, rough, height, _ = brick_base(g)
    g.finish(col, rough, height, bump=1.0)


def m_vein_brick(g):
    col, rough, height, mortar = brick_base(g, seed=5.0)
    wob = g.mul(g.sub(g.noise(4.0, 3.0, 0.5, seed=6), 0.5), 0.07)
    d = g.add(g.voronoi(1.3, "DISTANCE_TO_EDGE", seed=7), wob)
    crack = g.remap(d, 0.0, 0.03, 1.0, 0.0)
    region = g.remap(g.noise(0.9, 3.0, 0.5, seed=8), 0.45, 0.6)
    glow_mortar = g.mul(g.mul(mortar, region), g.remap(d, 0.0, 0.14, 1.0, 0.0))
    vein = g.clamp(g.add(g.mul(crack, region), g.mul(glow_mortar, 0.8)))
    scorch = g.mul(region, g.remap(d, 0.0, 0.2, 1.0, 0.0))
    col = g.mixc(g.mul(scorch, 0.85), col, (0.025, 0.014, 0.010))
    col = g.mixc(vein, col, (0.45, 0.12, 0.02))
    hot = g.mixc(crack, (0.85, 0.16, 0.02), (1.0, 0.62, 0.18))
    emit = g.mixc(vein, (0.0, 0.0, 0.0), hot)
    height = g.sub(height, g.mul(vein, 0.5))
    g.finish(col, rough, height, bump=1.0, emit=emit, emit_strength=4.0)


def m_stone(g, seed=10.0):
    col, fac = g.bricks(3, 6, 0.004, (0.300, 0.272, 0.240), (0.235, 0.218, 0.198), (0.10, 0.092, 0.084), bias=0.0)
    chip = g.noise(7.0, 4.0, 0.6, seed=seed)
    mortar = g.remap(g.add(fac, g.mul(g.sub(chip, 0.5), 1.1)), 0.40, 0.62)
    grain = g.noise(5.0, 10.0, 0.62, seed=seed + 1)
    col = g.mixc(1.0, col, g.mixc(grain, (0.80, 0.80, 0.80), (1.12, 1.10, 1.06)), blend="MULTIPLY")
    col = g.mixc(mortar, col, (0.07, 0.065, 0.06))
    s = soot(g, 0.9, seed=seed + 2, lo=0.42)
    col = g.mixc(1.0, col, g.mixc(s, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), blend="MULTIPLY")
    height = g.add(g.mul(g.sub(1.0, mortar), 0.75), g.mul(grain, 0.25))
    rough = g.add(0.74, g.mul(mortar, 0.18))
    return col, rough, height, mortar


def m_stone_final(g):
    col, rough, height, _ = m_stone(g)
    g.finish(col, rough, height, bump=1.0)


def m_glyph(g):
    col, rough, height, _ = m_stone(g, seed=30.0)
    mask = g.image(os.path.join(HERE, "glyph_mask.png"))
    sep = g.node("ShaderNodeSeparateColor")
    g.feed(sep.inputs[0], mask)
    m = sep.outputs[0]
    cut = g.remap(m, 0.15, 0.6)
    burn = g.remap(m, 0.02, 0.2)
    col = g.mixc(g.mul(burn, 0.7), col, (0.02, 0.012, 0.01))
    col = g.mixc(cut, col, (0.55, 0.20, 0.04))
    flicker = g.remap(g.noise(3.0, 3.0, 0.5, seed=31), 0.3, 0.7, 0.7, 1.0)
    emit = g.mixc(cut, (0.0, 0.0, 0.0), g.mixc(flicker, (0.9, 0.30, 0.04), (1.0, 0.66, 0.24)))
    height = g.sub(height, g.mul(cut, 0.6))
    g.finish(col, rough, height, bump=0.9, emit=emit, emit_strength=4.0)


def m_iron(g):
    col, fac = g.bricks(4, 2, 0.003, (0.090, 0.088, 0.092), (0.066, 0.065, 0.070), (0.02, 0.02, 0.02), offset=0.0, bias=0.0, smooth=0.0)
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    u32, v32 = g.mul(sep.outputs["X"], 32.0), g.mul(sep.outputs["Y"], 32.0)
    fu = g.sub(g.math("FRACT", u32), 0.5)
    fv = g.sub(g.math("FRACT", v32), 0.5)
    dist = g.math("SQRT", g.add(g.mul(fu, fu), g.mul(fv, fv)))
    dome = g.remap(dist, 0.24, 0.08)
    rowi = g.math("MODULO", g.math("FLOOR", v32), 16.0)
    coli = g.math("MODULO", g.math("FLOOR", u32), 8.0)
    band = g.clamp(g.add(g.add(g.math("LESS_THAN", rowi, 0.5), g.math("GREATER_THAN", rowi, 14.5)),
                         g.add(g.math("LESS_THAN", coli, 0.5), g.math("GREATER_THAN", coli, 6.5))))
    rivet = g.mul(dome, band)
    rustn = g.noise(2.2, 7.0, 0.62, seed=40)
    rust = g.clamp(g.remap(g.add(g.add(rustn, g.mul(fac, 0.35)), g.mul(rivet, 0.15)), 0.50, 0.66))
    streak = g.remap(g.noise(1.0, 2.0, 0.4, seed=41), 0.5, 0.65)
    rust = g.clamp(g.add(rust, g.mul(streak, g.mul(band, 0.4))))
    rcol = g.mixc(g.noise(14.0, 4.0, 0.6, seed=42), (0.20, 0.07, 0.025), (0.36, 0.15, 0.05))
    col = g.mixc(g.mul(rivet, 0.5), col, (0.16, 0.15, 0.15))
    col = g.mixc(rust, col, rcol)
    col = g.mixc(fac, col, (0.012, 0.012, 0.012))
    s = soot(g, 1.0, seed=43, lo=0.5)
    col = g.mixc(1.0, col, g.mixc(s, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), blend="MULTIPLY")
    pit = g.noise(30.0, 3.0, 0.6, seed=44)
    height = g.add(g.add(g.mul(g.sub(1.0, fac), 0.4), g.mul(rivet, 0.7)), g.mul(g.mul(rust, pit), 0.12))
    rough = g.mixf(rust, 0.42, 0.9)
    g.finish(col, rough, height, bump=0.7, dist=0.015, metal=g.sub(1.0, rust))


def m_floor(g):
    col, fac = g.bricks(4, 4, 0.010, (0.150, 0.140, 0.130), (0.105, 0.100, 0.094), (0.03, 0.026, 0.022), bias=0.0)
    chip = g.noise(8.0, 4.0, 0.6, seed=50)
    joint = g.remap(g.add(fac, g.mul(g.sub(chip, 0.5), 0.8)), 0.42, 0.6)
    d = g.voronoi(2.0, "DISTANCE_TO_EDGE", seed=51)
    cracks = g.mul(g.remap(d, 0.0, 0.012, 1.0, 0.0), g.remap(g.noise(1.4, 2.0, 0.5, seed=52), 0.55, 0.62))
    wear = g.noise(3.0, 8.0, 0.6, seed=53)
    col = g.mixc(1.0, col, g.mixc(wear, (0.78, 0.78, 0.78), (1.15, 1.13, 1.1)), blend="MULTIPLY")
    col = g.mixc(g.clamp(g.add(joint, cracks)), col, (0.025, 0.022, 0.02))
    s = soot(g, 0.8, seed=54, lo=0.55)
    col = g.mixc(1.0, col, g.mixc(s, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), blend="MULTIPLY")
    height = g.add(g.mul(g.sub(1.0, g.clamp(g.add(joint, cracks))), 0.6), g.mul(wear, 0.2))
    rough = g.mixf(g.remap(wear, 0.5, 0.7), 0.82, 0.55)
    g.finish(col, rough, height, bump=1.0)


def m_slag(g):
    wob = g.mul(g.sub(g.noise(3.0, 4.0, 0.55, seed=60), 0.5), 0.09)
    d = g.add(g.voronoi(1.6, "DISTANCE_TO_EDGE", seed=61), wob)
    molten = g.remap(d, 0.0, 0.07, 1.0, 0.0)
    crust_n = g.noise(10.0, 6.0, 0.6, seed=62)
    heat = g.remap(g.noise(0.8, 3.0, 0.5, seed=63), 0.3, 0.7)
    crust = g.mixc(crust_n, (0.035, 0.026, 0.022), (0.075, 0.05, 0.04))
    col = g.mixc(molten, crust, (0.95, 0.42, 0.08))
    hot = g.mixc(molten, (1.0, 0.32, 0.03), (1.0, 0.78, 0.30))
    dull = g.mixc(heat, (0.10, 0.012, 0.0), (0.34, 0.05, 0.0))
    emit = g.mixc(molten, dull, hot)
    height = g.add(g.mul(g.sub(1.0, molten), 0.8), g.mul(crust_n, 0.25))
    rough = g.mixf(molten, 0.86, 0.3)
    g.finish(col, rough, height, bump=0.8, emit=emit, emit_strength=6.0)


def m_bronze(g):
    tarn = g.noise(3.0, 8.0, 0.6, seed=70)
    base = g.mixc(tarn, (0.30, 0.17, 0.07), (0.56, 0.36, 0.16))
    verd = g.remap(g.add(g.noise(1.6, 6.0, 0.62, seed=71), g.mul(g.noise(12.0, 3.0, 0.5, seed=72), 0.25)), 0.66, 0.78)
    vcol = g.mixc(g.noise(20.0, 3.0, 0.5, seed=73), (0.12, 0.32, 0.27), (0.26, 0.50, 0.42))
    col = g.mixc(verd, base, vcol)
    height = g.add(g.mul(verd, 0.3), g.mul(tarn, 0.08))
    rough = g.mixf(verd, 0.32, 0.8)
    g.finish(col, rough, height, bump=0.4, metal=g.sub(1.0, verd))


def m_cloth(g):
    """Charred cloth for the Deacon's robe: a coarse weave, burnt through in
    places, with embers still alive at the burnt edges."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    wu = g.math("SINE", g.mul(sep.outputs["X"], TAU * 90.0))
    wv = g.math("SINE", g.mul(sep.outputs["Y"], TAU * 90.0))
    weave = g.remap(g.mul(wu, wv), -1.0, 1.0)
    fold = g.noise(1.5, 4.0, 0.5, distort=0.6, seed=80)
    col = g.mixc(fold, (0.030, 0.027, 0.025), (0.075, 0.066, 0.058))
    col = g.mixc(g.mul(weave, 0.3), col, (0.12, 0.11, 0.10))
    burn_n = g.noise(2.5, 6.0, 0.6, seed=81)
    burnt = g.remap(burn_n, 0.64, 0.66)
    edge = g.clamp(g.sub(g.remap(burn_n, 0.605, 0.64), burnt))
    col = g.mixc(burnt, col, (0.008, 0.007, 0.006))
    emit = g.mixc(edge, (0.0, 0.0, 0.0), (1.0, 0.36, 0.05))
    height = g.add(g.mul(fold, 0.6), g.sub(g.mul(weave, 0.15), g.mul(burnt, 0.4)))
    g.finish(col, g.mixf(burnt, 0.92, 0.7), height, bump=0.7, dist=0.01, emit=emit, emit_strength=3.0)


def m_leather(g):
    wr = g.noise(6.0, 8.0, 0.65, distort=1.2, seed=90)
    grain = g.noise(50.0, 3.0, 0.5, seed=91)
    col = g.mixc(wr, (0.07, 0.035, 0.018), (0.17, 0.09, 0.045))
    scuff = g.remap(g.noise(3.0, 5.0, 0.6, seed=92), 0.6, 0.7)
    col = g.mixc(scuff, col, (0.26, 0.17, 0.10))
    height = g.add(g.mul(wr, 0.6), g.mul(grain, 0.2))
    g.finish(col, g.mixf(scuff, 0.55, 0.8), height, bump=0.6, dist=0.008)


def m_oak(g):
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    n = g.noise(3.0, 6.0, 0.6, seed=100)
    ring = g.math("SINE", g.add(g.mul(sep.outputs["Y"], TAU * 24.0), g.mul(n, 9.0)))
    ring = g.remap(ring, -1.0, 1.0)
    col = g.mixc(ring, (0.10, 0.05, 0.022), (0.20, 0.11, 0.05))
    pores = g.remap(g.noise(80.0, 2.0, 0.5, seed=101), 0.6, 0.72)
    col = g.mixc(g.mul(pores, 0.5), col, (0.04, 0.02, 0.01))
    g.finish(col, g.mixf(ring, 0.55, 0.7), g.add(g.mul(ring, 0.3), g.mul(pores, -0.2)), bump=0.5, dist=0.006)


MATERIALS = {
    "kirk_brick1": m_brick,
    "kirk_vbrick1": m_vein_brick,
    "kirk_stone1": m_stone_final,
    "kirk_glyph1": m_glyph,
    "iron_plate1": m_iron,
    "floor_flag1": m_floor,
    "*slag1": m_slag,
    "bronze1": m_bronze,
    "cloth_char1": m_cloth,
    "leather1": m_leather,
    "oak1": m_oak,
}


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    # CYCLES_DEVICE=OPTIX (or CUDA, HIP, ONEAPI) bakes on the GPU; samples
    # smooth the procedural detail (BAKE_SAMPLES, 4 on the CPU, 32 on a GPU).
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
        else:
            print(f"no {device} device, baking on the CPU", flush=True)
    sc.cycles.samples = int(os.environ.get("BAKE_SAMPLES", 32 if sc.cycles.device == "GPU" else 4))
    sc.render.bake.margin = 0
    bpy.ops.mesh.primitive_plane_add(size=2.0)
    return bpy.context.active_object


def bake_to(plane, g, name, kind, source=None, non_color=False):
    """Bakes one map. Colour maps are baked as emission from the socket that
    feeds them, so lighting never gets into them; the normal map is a NORMAL bake."""
    img = bpy.data.images.new(name, RES, RES, alpha=False)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    nd = g.node("ShaderNodeTexImage", image=img)
    for n in g.t.nodes:
        n.select = False
    nd.select = True
    g.t.nodes.active = nd
    if kind == "NORMAL":
        g.t.links.new(g.bsdf.outputs["BSDF"], g.out.inputs["Surface"])
        bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
    else:
        em = g.node("ShaderNodeEmission")
        g.feed(em.inputs["Color"], source)
        em.inputs["Strength"].default_value = 1.0
        g.t.links.new(em.outputs["Emission"], g.out.inputs["Surface"])
        bpy.ops.object.bake(type="EMIT")
        g.t.links.new(g.bsdf.outputs["BSDF"], g.out.inputs["Surface"])
    path = os.path.join(OUT, name.replace("*", "#") + ".png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    print("baked", path, flush=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, build in MATERIALS.items():
        if ONLY and name not in ONLY:
            continue
        plane = setup()
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        plane.data.materials.append(mat)
        g = Graph(mat)
        build(g)
        bake_to(plane, g, name, "EMIT", g.maps["albedo"])
        bake_to(plane, g, name + "_norm", "NORMAL", non_color=True)
        gloss = g.math("SUBTRACT", 1.0, g.maps["rough"])
        bake_to(plane, g, name + "_gloss", "EMIT", gloss, non_color=True)
        if g.maps["emit"] is not None:
            bake_to(plane, g, name + "_luma", "EMIT", g.maps["emit"])


main()
