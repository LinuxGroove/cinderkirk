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


def m_water(g):
    """Quench water: black and oily, with a dull sheen and the heat's glow
    coming through where the slag was dropped in."""
    ripple = g.noise(2.5, 6.0, 0.55, distort=0.4, seed=80)
    film = g.noise(1.2, 4.0, 0.5, seed=81)
    # Liquids are drawn unlit, so this is what the eye sees: keep it near black.
    col = g.mixc(ripple, (0.002, 0.004, 0.005), (0.009, 0.013, 0.014))
    col = g.mixc(g.remap(film, 0.55, 0.7), col, (0.018, 0.015, 0.011))
    warm = g.remap(g.noise(0.9, 3.0, 0.5, seed=82), 0.62, 0.8)
    emit = g.mixc(warm, (0.0, 0.0, 0.0), (0.30, 0.07, 0.01))
    g.finish(col, 0.08, g.mul(ripple, 0.5), bump=0.35, emit=emit, emit_strength=1.5)


def m_grate(g):
    """A steam vent's grate: iron bars over a dark shaft that glows faintly."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    u8 = g.math("FRACT", g.mul(sep.outputs["X"], 8.0))
    v2 = g.math("FRACT", g.mul(sep.outputs["Y"], 2.0))
    bar = g.clamp(g.add(g.remap(g.math("ABSOLUTE", g.sub(u8, 0.5)), 0.30, 0.36),
                        g.remap(g.math("ABSOLUTE", g.sub(v2, 0.5)), 0.44, 0.47)))
    rustn = g.noise(3.0, 7.0, 0.62, seed=90)
    rust = g.remap(rustn, 0.48, 0.66)
    iron = g.mixc(rust, (0.08, 0.078, 0.082), (0.28, 0.12, 0.045))
    deep = g.mixc(g.noise(1.5, 3.0, 0.5, seed=91), (0.006, 0.004, 0.004), (0.03, 0.012, 0.006))
    col = g.mixc(bar, deep, iron)
    emit = g.mixc(bar, (0.25, 0.06, 0.01), (0.0, 0.0, 0.0))
    height = g.add(g.mul(bar, 0.9), g.mul(rustn, 0.1))
    g.finish(col, g.mixf(rust, 0.45, 0.9), height, bump=1.0, emit=emit, emit_strength=1.2,
             metal=g.mul(bar, g.sub(1.0, rust)))


def m_cracked(g):
    """Stone with a split running through it, wide enough to see from across
    a room: the Pick's Overpressure breaks it."""
    col, rough, height, _ = m_stone(g, seed=100.0)
    d = g.voronoi(0.45, "DISTANCE_TO_EDGE", seed=101)
    keep = g.remap(g.noise(0.6, 2.0, 0.5, seed=102), 0.46, 0.54)   # only some of the cell edges split
    split = g.mul(g.remap(d, 0.0, 0.025, 1.0, 0.0), keep)
    edge = g.mul(g.remap(d, 0.0, 0.08, 1.0, 0.0), keep)
    col = g.mixc(g.mul(edge, 0.5), col, (0.16, 0.14, 0.12))
    col = g.mixc(split, col, (0.012, 0.010, 0.009))
    height = g.sub(height, g.mul(split, 0.9))
    g.finish(col, rough, height, bump=1.1)


def m_brick_soot(g):
    """The same brick low down by the furnaces: blacker, with a crust of soot
    that's flaked off in patches."""
    col, rough, height, mortar = brick_base(g, seed=110.0)
    crust = g.remap(g.noise(2.0, 6.0, 0.62, seed=111), 0.52, 0.6)
    col = g.mixc(g.mul(crust, 0.7), col, (0.012, 0.011, 0.010))
    height = g.add(height, g.mul(crust, 0.12))
    g.finish(col, g.mixf(crust, rough, 0.95), height, bump=1.0)


def m_trim(g):
    """A carved stone band to run along the walls: a roll, a cove and a row
    of bell-shaped dentils, the same all along so it tiles one way."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    u, v = sep.outputs["X"], sep.outputs["Y"]
    roll = g.math("SINE", g.mul(g.math("FRACT", g.mul(v, 4.0)), math.pi))   # four rolls up the tile
    fu = g.sub(g.math("FRACT", g.mul(u, 8.0)), 0.5)
    fv = g.sub(g.math("FRACT", g.mul(v, 4.0)), 0.5)
    bell = g.remap(g.add(g.math("ABSOLUTE", fu), g.mul(g.math("ABSOLUTE", fv), 0.7)), 0.34, 0.26)
    grain = g.noise(5.0, 8.0, 0.6, seed=121)
    col = g.mixc(grain, (0.22, 0.20, 0.18), (0.31, 0.28, 0.25))
    deep = g.remap(roll, 0.0, 0.25, 1.0, 0.0)
    col = g.mixc(g.mul(deep, 0.8), col, (0.05, 0.045, 0.04))
    s = soot(g, 0.9, seed=122, lo=0.5)
    col = g.mixc(1.0, col, g.mixc(s, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), blend="MULTIPLY")
    height = g.add(g.mul(roll, 0.6), g.add(g.mul(bell, 0.4), g.mul(grain, 0.1)))
    g.finish(col, g.add(0.72, g.mul(deep, 0.2)), height, bump=1.0)


def m_column(g):
    """Fluted stone for pillars: sixteen flutes round the tile, worn smooth
    at hand height and sooted above."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    flute = g.remap(g.math("COSINE", g.mul(sep.outputs["X"], TAU * 16.0)), -1.0, 1.0)
    drum = g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(sep.outputs["Y"], 2.0)), 0.5)), 0.49, 0.5)
    grain = g.noise(5.0, 9.0, 0.6, seed=131)
    col = g.mixc(grain, (0.24, 0.22, 0.20), (0.33, 0.31, 0.28))
    col = g.mixc(g.mul(g.sub(1.0, flute), 0.5), col, (0.10, 0.09, 0.08))
    col = g.mixc(drum, col, (0.05, 0.045, 0.04))
    s = soot(g, 0.8, seed=132, lo=0.45)
    col = g.mixc(1.0, col, g.mixc(s, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), blend="MULTIPLY")
    height = g.sub(g.add(g.mul(flute, 0.7), g.mul(grain, 0.15)), g.mul(drum, 0.5))
    g.finish(col, g.mixf(grain, 0.78, 0.6), height, bump=1.0)


def m_ceiling(g):
    """Timber ceiling: boards between heavy joists, black with a century of smoke."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    u = sep.outputs["X"]
    ju = g.math("FRACT", g.mul(u, 2.0))
    joist = g.remap(g.math("ABSOLUTE", g.sub(ju, 0.5)), 0.40, 0.42, 0.0, 1.0)
    board = g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(u, 12.0)), 0.5)), 0.47, 0.5)
    n = g.noise(3.0, 6.0, 0.6, seed=140)
    ring = g.remap(g.math("SINE", g.add(g.mul(sep.outputs["Y"], TAU * 6.0), g.mul(n, 12.0))), -1.0, 1.0)
    col = g.mixc(ring, (0.05, 0.03, 0.018), (0.10, 0.06, 0.03))
    col = g.mixc(joist, col, g.mixc(ring, (0.07, 0.04, 0.02), (0.13, 0.075, 0.04)))
    col = g.mixc(board, col, (0.01, 0.008, 0.006))
    s = soot(g, 0.7, seed=141, lo=0.35)
    col = g.mixc(1.0, col, g.mixc(s, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), blend="MULTIPLY")
    height = g.sub(g.add(g.mul(joist, 0.8), g.mul(ring, 0.15)), g.mul(board, 0.3))
    g.finish(col, g.mixf(ring, 0.84, 0.7), height, bump=1.0)


def m_beam(g):
    """A hewn oak beam with adze marks and an iron strap every half tile."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    n = g.noise(2.0, 6.0, 0.6, seed=150)
    ring = g.remap(g.math("SINE", g.add(g.mul(sep.outputs["Y"], TAU * 16.0), g.mul(n, 10.0))), -1.0, 1.0)
    adze = g.remap(g.noise(5.0, 3.0, 0.5, distort=0.3, seed=151), 0.3, 0.7)  # broad, shallow adze marks
    col = g.mixc(ring, (0.09, 0.05, 0.025), (0.19, 0.11, 0.055))
    col = g.mixc(g.mul(adze, 0.3), col, (0.05, 0.03, 0.015))
    su = g.math("FRACT", g.mul(sep.outputs["X"], 2.0))
    strap = g.remap(g.math("ABSOLUTE", g.sub(su, 0.5)), 0.06, 0.05)
    rivet = g.mul(strap, g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(sep.outputs["Y"], 6.0)), 0.5)), 0.12, 0.06))
    rust = g.remap(g.noise(8.0, 5.0, 0.6, seed=152), 0.5, 0.65)
    iron = g.mixc(rust, (0.07, 0.07, 0.075), (0.25, 0.11, 0.04))
    col = g.mixc(strap, col, iron)
    height = g.add(g.add(g.mul(adze, 0.12), g.mul(ring, 0.12)), g.add(g.mul(strap, 0.5), g.mul(rivet, 0.4)))
    g.finish(col, g.mixf(strap, g.mixf(ring, 0.7, 0.82), 0.5), height, bump=0.6, metal=g.mul(strap, g.sub(1.0, rust)))


def m_grid(g):
    """Iron floor grating over the dark, for walkways above the slag: bars
    both ways, the glow coming up between them."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    bu = g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(sep.outputs["X"], 16.0)), 0.5)), 0.36, 0.40)
    bv = g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(sep.outputs["Y"], 16.0)), 0.5)), 0.36, 0.40)
    bar = g.clamp(g.add(bu, bv))
    rust = g.remap(g.noise(3.0, 6.0, 0.6, seed=160), 0.52, 0.68)
    wear = g.remap(g.noise(1.2, 3.0, 0.5, seed=161), 0.5, 0.7)
    iron = g.mixc(rust, g.mixc(wear, (0.07, 0.07, 0.075), (0.20, 0.19, 0.19)), (0.26, 0.11, 0.04))
    hole = g.mixc(g.noise(1.0, 3.0, 0.5, seed=162), (0.01, 0.004, 0.002), (0.05, 0.015, 0.004))
    col = g.mixc(bar, hole, iron)
    emit = g.mixc(bar, (0.18, 0.04, 0.006), (0.0, 0.0, 0.0))
    g.finish(col, g.mixf(rust, g.mixf(wear, 0.5, 0.3), 0.9), g.mul(bar, 1.0), bump=1.0, emit=emit,
             emit_strength=1.0, metal=g.mul(bar, g.sub(1.0, rust)))


def m_rust(g):
    """Iron sheet that's given up: rust in blisters and runs, flaking to the metal."""
    n = g.noise(2.5, 8.0, 0.65, seed=170)
    blister = g.remap(g.voronoi(14.0, "F1", seed=171), 0.0, 0.4, 1.0, 0.0)
    flake = g.remap(g.noise(5.0, 6.0, 0.6, seed=172), 0.62, 0.66)
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    run = g.remap(g.noise(1.0, 2.0, 0.4, seed=173), 0.5, 0.7)
    col = g.mixc(n, (0.18, 0.06, 0.02), (0.40, 0.17, 0.06))
    col = g.mixc(g.mul(run, 0.6), col, (0.10, 0.035, 0.012))
    col = g.mixc(flake, col, (0.10, 0.10, 0.105))
    height = g.add(g.mul(blister, 0.35), g.sub(g.mul(n, 0.3), g.mul(flake, 0.4)))
    g.finish(col, g.mixf(flake, 0.92, 0.45), height, bump=0.8, dist=0.012, metal=g.mul(flake, 0.9))


def m_copper(g):
    """Copper sheet for vats and pipes: warm metal under brown oxide, with
    blue-green running from the seams."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    seam = g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(sep.outputs["X"], 2.0)), 0.5)), 0.485, 0.495)
    ox = g.noise(2.5, 7.0, 0.6, seed=180)
    base = g.mixc(ox, (0.40, 0.17, 0.08), (0.62, 0.32, 0.16))
    brown = g.remap(g.noise(1.4, 5.0, 0.6, seed=181), 0.45, 0.65)
    base = g.mixc(g.mul(brown, 0.7), base, (0.17, 0.08, 0.04))
    drip = g.mul(g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(sep.outputs["X"], 2.0)), 0.5)), 0.5, 0.38),
                 g.remap(g.noise(6.0, 4.0, 0.6, seed=182), 0.45, 0.7))
    col = g.mixc(drip, base, (0.18, 0.42, 0.34))
    col = g.mixc(seam, col, (0.06, 0.03, 0.02))
    height = g.sub(g.add(g.mul(drip, 0.2), g.mul(ox, 0.08)), g.mul(seam, 0.5))
    g.finish(col, g.mixf(g.clamp(g.add(drip, brown)), 0.3, 0.8), height, bump=0.5,
             metal=g.sub(1.0, g.clamp(g.add(drip, g.mul(brown, 0.6)))))


def m_kiln_tile(g):
    """Glazed kiln tiles on the floor: oxblood glaze, crazed and chipped."""
    col, fac = g.bricks(8, 8, 0.008, (0.30, 0.06, 0.04), (0.22, 0.05, 0.035), (0.05, 0.04, 0.035), offset=0.0, bias=0.0, smooth=0.1)
    craze = g.remap(g.voronoi(30.0, "DISTANCE_TO_EDGE", seed=190), 0.0, 0.015, 1.0, 0.0)
    chip = g.remap(g.noise(6.0, 5.0, 0.6, seed=191), 0.66, 0.70)
    col = g.mixc(g.mul(craze, 0.4), col, (0.08, 0.02, 0.015))
    col = g.mixc(chip, col, (0.42, 0.30, 0.22))
    s = soot(g, 0.8, seed=192, lo=0.5)
    col = g.mixc(1.0, col, g.mixc(s, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), blend="MULTIPLY")
    height = g.sub(g.sub(1.0, g.mul(fac, 0.8)), g.add(g.mul(chip, 0.3), g.mul(craze, 0.05)))
    g.finish(col, g.mixf(g.clamp(g.add(fac, chip)), 0.2, 0.85), height, bump=0.8)


def m_ash(g):
    """Packed ash and cinders underfoot, with clinker pressed into it."""
    n = g.noise(4.0, 9.0, 0.65, seed=200)
    clink = g.remap(g.voronoi(18.0, "F1", seed=201), 0.0, 0.35, 1.0, 0.0)
    clink = g.mul(clink, g.remap(g.noise(3.0, 3.0, 0.5, seed=202), 0.5, 0.6))
    patch = g.noise(0.9, 4.0, 0.6, seed=204)
    col = g.mixc(n, (0.05, 0.048, 0.045), (0.20, 0.19, 0.18))
    col = g.mixc(g.remap(patch, 0.4, 0.7), col, (0.11, 0.08, 0.06))   # rusty, burnt patches
    col = g.mixc(g.mul(g.remap(g.noise(30.0, 2.0, 0.5, seed=205), 0.6, 0.7), 0.6), col, (0.30, 0.29, 0.27))   # pale grit
    col = g.mixc(clink, col, (0.03, 0.022, 0.02))
    ember = g.mul(clink, g.remap(g.noise(9.0, 3.0, 0.5, seed=203), 0.72, 0.78))
    emit = g.mixc(ember, (0.0, 0.0, 0.0), (0.9, 0.25, 0.03))
    g.finish(col, g.mixf(clink, g.mixf(n, 0.97, 0.85), 0.6), g.add(g.mul(n, 0.5), g.mul(clink, 0.8)), bump=1.0, emit=emit, emit_strength=2.0)


def m_coal(g):
    """A heap of coal: black lumps with sharp glinting faces."""
    d = g.voronoi(10.0, "F1", seed=210)
    e = g.voronoi(10.0, "DISTANCE_TO_EDGE", seed=210)
    lump = g.remap(d, 0.0, 0.6, 1.0, 0.0)
    face = g.remap(g.voronoi(40.0, "F1", seed=211), 0.0, 0.5)
    col = g.mixc(face, (0.012, 0.012, 0.013), (0.045, 0.045, 0.05))
    col = g.mixc(g.remap(e, 0.0, 0.03, 1.0, 0.0), col, (0.004, 0.004, 0.004))
    g.finish(col, g.mixf(face, 0.25, 0.6), g.add(g.mul(lump, 0.8), g.mul(face, 0.2)), bump=1.0)


def m_sand(g):
    """Moulding sand: damp, dark and fine, with the prints of patterns pulled from it."""
    n = g.noise(60.0, 3.0, 0.5, seed=220)
    damp = g.noise(1.5, 5.0, 0.6, seed=221)
    col = g.mixc(damp, (0.12, 0.07, 0.04), (0.22, 0.14, 0.08))
    col = g.mixc(g.mul(n, 0.3), col, (0.30, 0.20, 0.12))
    ring = g.voronoi(1.2, "F1", seed=222)
    print_ = g.mul(g.remap(g.math("ABSOLUTE", g.sub(ring, 0.25)), 0.03, 0.0), g.remap(g.noise(0.8, 2.0, 0.5, seed=223), 0.5, 0.56))
    col = g.mixc(g.mul(print_, 0.5), col, (0.08, 0.045, 0.025))
    g.finish(col, g.mixf(damp, 0.98, 0.8), g.sub(g.mul(n, 0.2), g.mul(print_, 0.6)), bump=0.8, dist=0.01)


def m_firebrick(g):
    """Yellow firebrick lining the furnaces, scorched brown to black where the
    heat licks it."""
    col, fac = g.bricks(8, 16, 0.006, (0.32, 0.25, 0.15), (0.26, 0.20, 0.12), (0.13, 0.11, 0.09), bias=-0.1)
    chip = g.noise(9.0, 4.0, 0.6, seed=230)
    mortar = g.remap(g.add(fac, g.mul(g.sub(chip, 0.5), 0.8)), 0.46, 0.56)
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    lick = g.remap(g.add(g.mul(g.noise(1.2, 5.0, 0.6, seed=231), 0.8), g.mul(g.math("SINE", g.mul(sep.outputs["Y"], TAU)), 0.08)), 0.45, 0.75)
    col = g.mixc(g.mul(lick, 0.9), col, g.mixc(lick, (0.25, 0.14, 0.06), (0.03, 0.02, 0.015)))
    col = g.mixc(mortar, col, (0.12, 0.10, 0.08))
    height = g.add(g.mul(g.sub(1.0, mortar), 1.2), g.mul(chip, 0.2))
    g.finish(col, g.add(g.mixf(chip, 0.74, 0.86), g.mul(mortar, 0.1)), height, bump=1.3)


def m_door(g):
    """Iron door planking: vertical boards behind heavy bands and studs."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    u, v = sep.outputs["X"], sep.outputs["Y"]
    board = g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(u, 6.0)), 0.5)), 0.47, 0.5)
    bv = g.math("FRACT", g.mul(v, 3.0))
    band = g.remap(g.math("ABSOLUTE", g.sub(bv, 0.5)), 0.12, 0.10)
    fu = g.sub(g.math("FRACT", g.mul(u, 12.0)), 0.5)
    stud = g.mul(band, g.remap(g.math("SQRT", g.add(g.mul(fu, fu), g.mul(g.sub(bv, 0.5), g.mul(g.sub(bv, 0.5), 9.0)))), 0.22, 0.12))
    rust = g.remap(g.noise(3.0, 6.0, 0.6, seed=240), 0.5, 0.66)
    plate = g.mixc(rust, (0.075, 0.072, 0.075), (0.25, 0.10, 0.035))
    iron = g.mixc(band, plate, g.mixc(rust, (0.11, 0.105, 0.11), (0.30, 0.13, 0.05)))
    col = g.mixc(board, iron, (0.015, 0.013, 0.012))
    col = g.mixc(g.mul(stud, 0.6), col, (0.20, 0.19, 0.18))
    height = g.add(g.sub(g.mul(band, 0.5), g.mul(board, 0.3)), g.mul(stud, 0.5))
    g.finish(col, g.mixf(rust, 0.45, 0.85), height, bump=1.0, metal=g.sub(1.0, rust))


def m_plaster(g):
    """Limewash over plaster, yellowed and cracked, fallen away to the brick in places."""
    col_b, rough_b, height_b, _ = brick_base(g, seed=250.0)
    n = g.noise(2.0, 8.0, 0.6, seed=251)
    gone = g.remap(g.noise(1.1, 5.0, 0.6, seed=252), 0.58, 0.61)
    crack = g.mul(g.remap(g.voronoi(2.5, "DISTANCE_TO_EDGE", seed=253), 0.0, 0.01, 1.0, 0.0),
                  g.remap(g.noise(1.5, 2.0, 0.5, seed=254), 0.5, 0.6))
    col = g.mixc(n, (0.28, 0.26, 0.21), (0.40, 0.37, 0.31))
    col = g.mixc(crack, col, (0.08, 0.07, 0.06))
    s = soot(g, 0.8, seed=255, lo=0.4)
    col = g.mixc(1.0, col, g.mixc(s, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), blend="MULTIPLY")
    col = g.mixc(gone, col, col_b)
    height = g.mixf(gone, g.sub(g.add(1.2, g.mul(n, 0.1)), g.mul(crack, 0.4)), g.mul(height_b, 0.6))
    g.finish(col, g.mixf(gone, 0.9, rough_b), height, bump=1.0)


def m_lamp(g):
    """Amber glass in iron cames, lit from behind: the foundry's lamps."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    cu = g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(sep.outputs["X"], 4.0)), 0.5)), 0.44, 0.47)
    cv = g.remap(g.math("ABSOLUTE", g.sub(g.math("FRACT", g.mul(sep.outputs["Y"], 2.0)), 0.5)), 0.46, 0.48)
    came = g.clamp(g.add(cu, cv))
    seed_ = g.noise(8.0, 4.0, 0.5, seed=260)
    glass = g.mixc(seed_, (0.55, 0.25, 0.05), (0.85, 0.50, 0.15))
    col = g.mixc(came, glass, (0.04, 0.04, 0.045))
    glow = g.mixc(g.remap(g.noise(1.0, 2.0, 0.5, seed=261), 0.3, 0.7), (0.8, 0.35, 0.06), (1.0, 0.65, 0.25))
    emit = g.mixc(came, glow, (0.0, 0.0, 0.0))
    g.finish(col, g.mixf(came, 0.15, 0.6), g.sub(g.mul(came, 0.8), g.mul(seed_, 0.1)), bump=0.8,
             emit=emit, emit_strength=5.0, metal=came)


def m_brass(g):
    """A brass trim band: polished where hands go, dark with tarnish in the grooves."""
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.uv)
    v = g.math("FRACT", g.mul(sep.outputs["Y"], 4.0))
    groove = g.remap(g.math("ABSOLUTE", g.sub(v, 0.5)), 0.30, 0.34)
    bead = g.math("SINE", g.mul(v, math.pi))
    tarn = g.noise(3.0, 7.0, 0.6, seed=270)
    col = g.mixc(tarn, (0.42, 0.28, 0.09), (0.70, 0.52, 0.22))
    dark = g.clamp(g.add(g.mul(groove, 0.8), g.remap(g.noise(1.5, 4.0, 0.6, seed=271), 0.55, 0.7)))
    col = g.mixc(dark, col, (0.12, 0.08, 0.03))
    g.finish(col, g.mixf(dark, 0.22, 0.6), g.add(g.mul(bead, 0.6), g.mul(groove, 0.3)), bump=0.7, metal=1.0)


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
    "*water1": m_water,
    "vent_grate1": m_grate,
    "kirk_crack1": m_cracked,
    "kirk_brick2": m_brick_soot,
    "kirk_trim1": m_trim,
    "kirk_column1": m_column,
    "ceil_timber1": m_ceiling,
    "oak_beam1": m_beam,
    "iron_grid1": m_grid,
    "iron_rust1": m_rust,
    "copper1": m_copper,
    "kiln_tile1": m_kiln_tile,
    "ash_floor1": m_ash,
    "coal1": m_coal,
    "sand_mould1": m_sand,
    "firebrick1": m_firebrick,
    "door_iron1": m_door,
    "plaster1": m_plaster,
    "lamp_amber1": m_lamp,
    "brass_trim1": m_brass,
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
