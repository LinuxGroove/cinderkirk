#!/usr/bin/env python3
"""Write Cinderkirk's HUD as SVG: the pieces of the status bar, its icons,
labels and numerals, and the weapon wheel's pieces. The engine rasterises
them with nanosvg at the screen's own resolution (engine/Quake/hud_svg.c), so
the HUD stays sharp from 720p to 8K.

    tools/hud_svg.py OUT_DIR

Every piece is drawn in the units of the mockup's 1280x720 status bar
(the bar is 72 tall), so the engine scales them all by one number. Text is
turned into paths here (nanosvg draws no text), from the game's own fonts:
Barlow Condensed for numbers and Cinzel for labels.

Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
"""

import math
import os
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets_src", "fonts")
NUM_FONT = TTFont(os.path.join(FONTS, "barlow-condensed-latin-700-normal.woff"))
LAB_FONT = TTFont(os.path.join(FONTS, "cinzel-latin-700-normal.woff"))
TEXT_FONT = TTFont(os.path.join(FONTS, "barlow-condensed-latin-500-normal.woff"))

# The numeral atlas: these glyphs in cells of CELL_W x CELL_H, the baseline
# BASELINE down each cell, at NUM_SIZE. hud_svg.c and sbar_foundry.c read the
# same numbers (HUD_DIGITS, HUD_DIGIT_*).
DIGITS = "0123456789/-:"
NUM_SIZE = 54.0
CELL_W = 27.0
CELL_H = 46.0
BASELINE = 41.0

BRASS = """<linearGradient id="brass" x1="0%" y1="0%" x2="0%" y2="100%">
  <stop offset="0" stop-color="#f3cf86"/><stop offset="0.45" stop-color="#b9843a"/><stop offset="1" stop-color="#6e4518"/>
</linearGradient>"""
BRASS_TEXT = """<linearGradient id="fill" x1="0%" y1="0%" x2="0%" y2="100%">
  <stop offset="0" stop-color="#fff3d6"/><stop offset="0.5" stop-color="#ecd3a0"/><stop offset="0.55" stop-color="#c9a064"/><stop offset="1" stop-color="#e7c88f"/>
</linearGradient>"""
HOT_TEXT = """<linearGradient id="fill" x1="0%" y1="0%" x2="0%" y2="100%">
  <stop offset="0" stop-color="#fff0c0"/><stop offset="0.5" stop-color="#ffb050"/><stop offset="1" stop-color="#e2641a"/>
</linearGradient>"""
DIM_TEXT = """<linearGradient id="fill" x1="0%" y1="0%" x2="0%" y2="100%">
  <stop offset="0" stop-color="#9a8466"/><stop offset="1" stop-color="#6a5844"/>
</linearGradient>"""
# The bar's body; the same gradient in the strip and the dial's housing.
BAR = """<linearGradient id="bar" gradientUnits="userSpaceOnUse" x1="0" y1="648" x2="0" y2="720">
  <stop offset="0" stop-color="#2a221c"/><stop offset="0.12" stop-color="#1b1612"/><stop offset="1" stop-color="#0a0807"/>
</linearGradient>"""

LIT = "#e7d3ab"
HOT = "#ff9a3a"
DIM = "#5b4d3e"


def svg(w, h, body, defs="", box=None):
    x0, y0 = (box or (0, 0))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}" height="{h:g}" '
            f'viewBox="{x0:g} {y0:g} {w:g} {h:g}">\n<defs>{defs}</defs>\n{body}\n</svg>\n')


def text_path(font, text, size, x, y, anchor="start", spacing=0.0):
    """Text as one path's d, its baseline at y; and its width."""
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    width = sum(gs[cmap[ord(c)]].width * scale for c in text) + spacing * (len(text) - 1)
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width
    pen = SVGPathPen(gs)
    for c in text:
        g = gs[cmap[ord(c)]]
        g.draw(TransformPen(pen, (scale, 0, 0, -scale, x, y)))
        x += g.width * scale + spacing
    return pen.getCommands(), width


def numeral(font, text, size, x, y, anchor="start", stroke=1.4):
    """Text drawn as the mockup drew numbers: a dark outline under a gradient."""
    d, w = text_path(font, text, size, x, y, anchor)
    return (f'<path d="{d}" fill="none" stroke="#120a06" stroke-width="{stroke * 2:g}" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="url(#fill)"/>'), w


def write(out, name, data):
    with open(os.path.join(out, name + ".svg"), "w") as fh:
        fh.write(data)


# --- Numerals ----------------------------------------------------------------

def digits(out):
    for name, grad in (("digits", BRASS_TEXT), ("digits_hot", HOT_TEXT), ("digits_dim", DIM_TEXT)):
        body = []
        for i, c in enumerate(DIGITS):
            p, _ = numeral(NUM_FONT, c, NUM_SIZE, i * CELL_W + CELL_W / 2, BASELINE, "middle")
            body.append(p)
        write(out, name, svg(CELL_W * len(DIGITS), CELL_H, "\n".join(body), grad))


# --- Labels ------------------------------------------------------------------

LAB_SIZE = 12.0
LAB_H = 11.0  # caps are 0.7 em; the label's top is the caps' top
LABELS = {
    "armour": "ARMOUR", "health": "HEALTH", "keys": "KEYS", "secrets": "SECRETS",
    "frags": "FRAGS", "pressure": "PRESSURE",
    "kills": "KILLS", "time": "TIME",
    "shells": "SHELLS", "slag": "SLAG", "iron": "IRON", "clappers": "CLAPPERS",
}


def labels(out):
    for key, text in LABELS.items():
        colour = "#3a2614" if key == "pressure" else "#c4a674"
        size = 9.5 if key == "pressure" else LAB_SIZE
        d, w = text_path(LAB_FONT, text, size, 0.5, size * 0.7 + 0.5, spacing=size * 0.23)
        write(out, "lab_" + key, svg(w + 1, size * 0.7 + 1.5, f'<path d="{d}" fill="{colour}"/>'))


# --- The bar -----------------------------------------------------------------

# The brass edge along the top of the bar, solid so the pieces meet unseen.
EDGE = "#c08a3e"
EDGE_LIGHT = "#f3cf86"


def rivet():
    return ('<circle cx="3" cy="3" r="2.1" fill="#d9aa5c"/>'
            '<circle cx="2.4" cy="2.4" r="0.8" fill="#fff1c8"/>')


def bar(out):
    # A slice of the bar, stretched to the screen's width: from y 640 to 720.
    body = (f'<rect x="0" y="648" width="16" height="72" fill="url(#bar)" opacity="0.93"/>'
            f'<rect x="0" y="646.5" width="16" height="3" fill="{EDGE}"/>'
            f'<rect x="0" y="646.5" width="16" height="1" fill="{EDGE_LIGHT}"/>')
    write(out, "bar", svg(16, 80, body, BAR, (0, 640)))
    write(out, "rivet", svg(6, 6, rivet()))
    write(out, "divider", svg(2, 52, '<rect width="2" height="52" fill="url(#brass)" opacity="0.8"/>', BRASS))


def housing(out):
    """The raised middle of the bar, with the Pressure dial's face in it:
    from x 440 to 840 and y 620 to 720 of the mockup."""
    top = 642
    edge = f"M440 {top + 6} L470 {top + 6} L502 {top - 14} L778 {top - 14} L810 {top + 6} L840 {top + 6}"
    # Only the raised part: the strip under it is the bar itself.
    body = [f'<path d="M470 {top + 6} L502 {top - 14} L778 {top - 14} L810 {top + 6} Z" fill="url(#bar)" opacity="0.93"/>',
            f'<path d="{edge}" fill="none" stroke="{EDGE}" stroke-width="3" stroke-linejoin="round"/>',
            f'<path d="{edge}" fill="none" stroke="{EDGE_LIGHT}" stroke-width="1" stroke-linejoin="round" transform="translate(0 -1)"/>']
    for x in range(512, 771, 32):
        body.append(f'<g transform="translate({x - 3} {top - 9})">{rivet()}</g>')
    cx, cy, r = 640, top + 48, 52
    body.append(f'<circle cx="{cx}" cy="{cy + 1.5}" r="{r + 7}" fill="#000" opacity="0.5"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="url(#brass)"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#dial)"/>')
    a0, a1 = math.pi * 1.08, math.pi * 1.92

    def p(a, rr):
        return cx + rr * math.cos(a), cy + rr * math.sin(a)
    rr = r - 9
    (x0, y0), (x1, y1) = p(a0 + (a1 - a0) * 0.75, rr), p(a1, rr)
    body.append(f'<path d="M{x0:.2f} {y0:.2f} A{rr} {rr} 0 0 1 {x1:.2f} {y1:.2f}" stroke="#a2240e" stroke-width="7" fill="none"/>')
    for i in range(21):
        a = a0 + (a1 - a0) * i / 20
        big = i % 5 == 0
        (xa, ya), (xb, yb) = p(a, r - (17 if big else 12)), p(a, r - 5)
        body.append(f'<line x1="{xa:.2f}" y1="{ya:.2f}" x2="{xb:.2f}" y2="{yb:.2f}" stroke="#2a1a0e" stroke-width="{2.4 if big else 1.2}"/>')
    for i, n in ((0, "0"), (10, "50"), (20, "100")):
        a = a0 + (a1 - a0) * i / 20
        x, y = p(a, r - 27)
        d, _ = text_path(NUM_FONT, n, 11, x, y + 4, "middle")
        body.append(f'<path d="{d}" fill="#3a2614"/>')
    d, _ = text_path(LAB_FONT, "PRESSURE", 8.5, cx, cy + 24, "middle", 8.5 * 0.2)
    body.append(f'<path d="{d}" fill="#3a2614"/>')
    dial = """<radialGradient id="dial" cx="0.5" cy="0.6" r="0.6">
  <stop offset="0" stop-color="#e9dcbc"/><stop offset="0.8" stop-color="#c9b48a"/><stop offset="1" stop-color="#8a7350"/>
</radialGradient>"""
    write(out, "housing", svg(400, 100, "\n".join(body), BAR + BRASS + dial, (440, 620)))
    # The needle points along +x from its pivot, at (6, 6) in its own box.
    write(out, "needle", svg(50, 12,
          '<path d="M0 6 L6 1.5 L48 6 L6 10.5 Z" fill="#1a0c06"/>'
          '<path d="M6 6 L48 6 L6 10.5 Z" fill="#000" opacity="0.25"/>'))
    write(out, "dial_cap", svg(14, 14, '<circle cx="7" cy="7" r="6" fill="url(#brass)" stroke="#2a1a0c" stroke-width="1"/>', BRASS))
    # The needle's glow when Pressure is in the red.
    write(out, "dial_hot", svg(120, 120, '<circle cx="60" cy="60" r="58" fill="url(#g)"/>',
          '<radialGradient id="g" cx="0.5" cy="0.5" r="0.5"><stop offset="0.7" stop-color="#ff5a1a" stop-opacity="0"/>'
          '<stop offset="0.86" stop-color="#ff5a1a" stop-opacity="0.55"/><stop offset="1" stop-color="#ff5a1a" stop-opacity="0"/></radialGradient>'))


# --- Icons -------------------------------------------------------------------

def shadow(body, dy=1.5):
    """A soft dark copy under a shape, in place of the mockup's drop shadow."""
    return f'<g transform="translate(0 {dy})" opacity="0.55" fill="#000" stroke="#000">{body}</g>'


def stat_icons(out):
    armour = ('<path d="M4 4 L38 0 L50 6 L48 34 Q44 48 26 54 Q8 48 4 34 Z" fill="url(#brass)" stroke="#2a1a0c" stroke-width="1.5"/>'
              '<path d="M12 10 L38 7 L44 12 L42 32 Q38 42 26 46 Q14 42 12 32 Z" fill="#3a2a1c"/>'
              + "".join(f'<circle cx="{x}" cy="{y}" r="1.8" fill="#ffe2a0"/>' for x, y in ((10, 10), (44, 12), (26, 50), (8, 32), (46, 32))))
    armour_shape = '<path d="M4 4 L38 0 L50 6 L48 34 Q44 48 26 54 Q8 48 4 34 Z"/>'
    write(out, "armour", svg(54, 58, shadow(armour_shape) + armour, BRASS, (-1, -1)))
    flask = ('<path d="M20 0 L32 0 L32 14 Q50 22 48 40 Q46 56 26 56 Q6 56 4 40 Q2 22 20 14 Z" fill="#e8d7b4" fill-opacity="0.22" stroke="url(#brass)" stroke-width="3"/>'
             '<path d="M7 34 Q14 30 26 34 Q38 38 45 33 Q46 52 26 53 Q7 53 7 34 Z" fill="#d2381a"/>'
             '<path d="M11 38 Q18 36 24 38" fill="none" stroke="#ff9a6a" stroke-width="1.5" opacity="0.7"/>'
             '<rect x="17" y="-3" width="18" height="6" rx="2" fill="url(#brass)"/>')
    write(out, "health", svg(56, 64, flask, BRASS, (-2, -5)))
    # Ammo, by the kind the weapon in hand uses.
    slag = ('<path d="M24 0 Q44 26 44 37 Q44 56 24 56 Q4 56 4 37 Q4 26 24 0 Z" fill="#ff8a2a" opacity="0.35"/>'
            '<path d="M24 2 Q42 26 42 36 Q42 54 24 54 Q6 54 6 36 Q6 26 24 2 Z" fill="#ff8a2a"/>'
            '<path d="M24 14 Q34 30 34 37 Q34 47 24 47 Q14 47 14 37 Q14 30 24 14 Z" fill="#ffe6a0"/>')
    write(out, "ammo_slag", svg(48, 58, slag, "", (0, -1)))
    shells = "".join(
        f'<g transform="translate({x} {y})">'
        '<rect x="0" y="10" width="13" height="34" rx="2" fill="#a8321c" stroke="#2a1a0c" stroke-width="1.2"/>'
        '<rect x="0" y="36" width="13" height="9" fill="url(#brass)" stroke="#2a1a0c" stroke-width="1.2"/>'
        '<rect x="2" y="12" width="3" height="22" fill="#e86a40" opacity="0.6"/></g>'
        for x, y in ((6, 6), (19, 2), (32, 6)))
    write(out, "ammo_shells", svg(52, 56, shells, BRASS))
    iron = ('<circle cx="26" cy="30" r="20" fill="#3a3330" stroke="#1a1410" stroke-width="2"/>'
            '<circle cx="26" cy="30" r="14" fill="#ff8a2a" opacity="0.85"/>'
            '<circle cx="21" cy="25" r="5" fill="#ffe6a0"/>')
    write(out, "ammo_iron", svg(52, 56, iron))
    clapper = ('<rect x="23" y="2" width="6" height="30" rx="2" fill="url(#brass)"/>'
               '<circle cx="26" cy="40" r="12" fill="url(#brass)" stroke="#2a1a0c" stroke-width="1.5"/>')
    write(out, "ammo_clappers", svg(52, 56, clapper, BRASS))


def keys(out):
    # Two keys that differ in shape as well as colour: the iron key's bow is a
    # ring, the bronze key's a trefoil.
    for name, colour, bow in (
        ("key1", "#c9ccd0", '<circle cx="12" cy="18" r="10" fill="none" stroke="{f}" stroke-width="5"/>'),
        ("key2", "url(#brass)", "".join(f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="{{f}}" stroke-width="4"/>'
                                        for x, y in ((12, 9), (5, 22), (19, 22)))),
    ):
        for lit in (True, False):
            f = colour if lit else "#5a5048"
            body = (bow.format(f=f) + f'<rect x="21" y="15" width="34" height="6" fill="{f}"/>'
                    f'<rect x="44" y="21" width="6" height="11" fill="{f}"/><rect x="34" y="21" width="5" height="8" fill="{f}"/>')
            if lit:
                body = shadow(bow.format(f="#000") + '<rect x="21" y="15" width="34" height="6"/>') + body
            write(out, name + ("" if lit else "_dim"),
                  svg(58, 36, f'<g opacity="{1 if lit else 0.45}">{body}</g>', BRASS, (0, 0)))


# Weapon silhouettes, in a 100 x 60 box facing right: (shape, hot parts).
WEAPONS = {
    "pick": ('<path d="M18 52 L62 14" stroke-width="7" stroke-linecap="round" fill="none"/>'
             '<path d="M40 8 Q66 2 92 18 Q70 14 58 20 Q48 14 40 8Z"/><path d="M58 20 L48 12" stroke-width="5" fill="none"/>', ""),
    "scattergun": ('<rect x="34" y="22" width="62" height="7" rx="2"/><rect x="34" y="31" width="52" height="6" rx="2"/>'
                   '<path d="M8 40 L36 26 L44 26 L44 40 L30 44 L14 52 Z"/><path d="M44 40 Q46 52 36 52 Q30 50 34 42" fill="none" stroke-width="4"/>', ""),
    "spitter": ('<rect x="40" y="30" width="54" height="9" rx="3"/><rect x="18" y="26" width="28" height="18" rx="3"/>'
                '<path d="M22 44 L30 44 L26 58 L16 58 Z"/><circle cx="96" cy="34" r="6"/>',
                '<rect x="50" y="10" width="16" height="20" rx="3"/>'),
    "bolt": ('<rect x="10" y="30" width="70" height="7" rx="2"/><path d="M62 10 Q74 34 62 58" fill="none" stroke-width="5"/>'
             '<path d="M40 33 L96 33" stroke-width="3" fill="none"/><path d="M90 28 L98 33 L90 38Z"/><path d="M18 37 L28 37 L24 52 L14 52Z"/>', ""),
    "crucible": ('<rect x="16" y="32" width="58" height="10" rx="3"/><rect x="58" y="10" width="40" height="5" rx="2"/>'
                 '<path d="M22 42 L32 42 L28 56 L18 56 Z"/>', '<path d="M60 14 Q60 34 78 34 Q96 34 96 14 Z"/>'),
    "steam": ('<rect x="14" y="26" width="50" height="16" rx="5"/><path d="M62 26 L92 14 L92 54 L62 42 Z"/>'
              '<circle cx="34" cy="18" r="7" fill="none" stroke-width="4"/><path d="M20 42 L30 42 L26 56 L16 56Z"/>', ""),
    "mortar": ('<rect x="24" y="18" width="52" height="28" rx="6"/><circle cx="86" cy="32" r="10"/>'
               '<path d="M28 46 L40 46 L36 58 L24 58Z"/><rect x="40" y="12" width="8" height="40" rx="2"/>', ""),
    "toll": ('<rect x="14" y="28" width="40" height="12" rx="4"/>'
             '<path d="M52 24 Q60 24 66 16 Q80 12 96 6 L96 62 Q80 56 66 52 Q60 44 52 44 Z"/><path d="M20 40 L30 40 L26 54 L16 54Z"/>', ""),
}
# What each weapon's Overpressure does, for the wheel's middle.
WEAPON_OVER = [
    "A steam-driven charge that splits cracked stone and staggers anything.",
    "Overpressure: a heated slug that goes through a line of creatures.",
    "Overpressure: a gout of slag that leaves the floor burning.",
    "Overpressure: five rivets at once, in a fan.",
    "Overpressure: three loads of molten iron at once.",
    "Overpressure: a blast at your feet that throws you up and over.",
    "Overpressure: a cluster shell that splits into six.",
    "Overpressure: a toll that stops Deacons raising the dead.",
]
WEAPON_NAMES = ["Pick", "Scattergun", "Spitter", "Bolt Caster", "Crucible", "Steam Cannon", "Shot Mortar", "Tolling Iron"]


def weapons(out):
    for i, (key, (shape, hot)) in enumerate(WEAPONS.items()):
        for state, main, glow in (("", LIT, HOT), ("_dim", DIM, DIM)):
            body = (f'<g fill="{main}" stroke="{main}">{shape}</g>'
                    + (f'<g fill="{glow}" stroke="{glow}">{hot}</g>' if hot else ""))
            write(out, f"w{i + 1}{state}", svg(100, 64, body, "", (0, -2)))


def slots(out):
    for name, fill, stroke, width in (("slot", "#120d0a", "#3a3026", 1), ("slot_cur", "#3a2412", "url(#brass)", 2)):
        write(out, name, svg(52, 28, f'<rect x="1" y="1" width="50" height="26" rx="3" fill="{fill}" fill-opacity="0.8" '
                                     f'stroke="{stroke}" stroke-width="{width}"/>', BRASS))


# --- The weapon wheel ------------------------------------------------------

WHEEL_R0, WHEEL_R1, WHEEL_GAP = 104, 262, 0.018


def wheel(out):
    """One wedge of eight, pointing up (slot 1's place); the engine turns it.
    Its box is centred on the wheel's middle."""
    n = 8
    a0 = -math.pi / 2 - math.pi / n + WHEEL_GAP
    a1 = -math.pi / 2 + math.pi / n - WHEEL_GAP
    R = WHEEL_R1 + 16

    def wedge(r1):
        def p(a, r):
            return f"{r * math.cos(a):.2f} {r * math.sin(a):.2f}"
        return (f"M{p(a0, WHEEL_R0)} L{p(a0, r1)} A{r1} {r1} 0 0 1 {p(a1, r1)} "
                f"L{p(a1, WHEEL_R0)} A{WHEEL_R0} {WHEEL_R0} 0 0 0 {p(a0, WHEEL_R0)} Z")
    hot = ('<radialGradient id="hot" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="280">'
           '<stop offset="0.35" stop-color="#7a4416"/><stop offset="1" stop-color="#d48a38"/></radialGradient>')
    for name, r1, fill, op, stroke, sw in (
        ("wedge", WHEEL_R1, "#1c1511", 0.86, "#4a3a2a", 1.2),
        ("wedge_empty", WHEEL_R1, "#0d0a08", 0.86, "#4a3a2a", 1.2),
        ("wedge_sel", WHEEL_R1 + 14, "url(#hot)", 0.95, "#ffd08a", 2.5),
    ):
        body = f'<path d="{wedge(r1)}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"/>'
        if name == "wedge_sel":
            body = f'<path d="{wedge(r1 + 4)}" fill="none" stroke="#ffb050" stroke-width="6" opacity="0.25"/>' + body
        write(out, name, svg(2 * R, 2 * R, body, hot, (-R, -R)))
    hub = WHEEL_R0 - 8
    write(out, "wheel_hub", svg(2 * hub + 4, 2 * hub + 4,
          f'<circle cx="0" cy="0" r="{hub}" fill="#0e0b09" fill-opacity="0.92" stroke="url(#brass)" stroke-width="3"/>',
          BRASS, (-hub - 2, -hub - 2)))
    write(out, "wheel_pointer", svg(24, 20, '<path d="M2 18 L12 0 L22 18 Z" fill="#ffd08a"/>'))
    vig = ('<radialGradient id="v" cx="0.5" cy="0.5" r="0.75"><stop offset="0.55" stop-color="#000" stop-opacity="0"/>'
           '<stop offset="1" stop-color="#000" stop-opacity="0.55"/></radialGradient>')
    write(out, "vignette", svg(160, 90, '<rect width="160" height="90" fill="url(#v)"/>', vig))
    # The weapons' names, in the wedges (lit and not found) and big in the hub.
    for i, name in enumerate(WEAPON_NAMES):
        up = name.upper()
        for state, colour in (("", "#e8d2a8"), ("_dim", "#4f4234")):
            d, w = text_path(LAB_FONT, up if not state else "—", 11, 0.5, 8.2, spacing=1.5)
            write(out, f"wname{i + 1}{state}", svg(w + 1, 9.5, f'<path d="{d}" fill="{colour}"/>'))
        d, w = text_path(LAB_FONT, up, 22, 1, 16.5, spacing=2)
        write(out, f"wtitle{i + 1}", svg(w + 2, 19, f'<path d="{d}" fill="#f6e6c4"/>'))
    for i, over in enumerate(WEAPON_OVER):
        lines, line = [], ""
        for word in over.split():
            if line and len(line) + 1 + len(word) > 26:
                lines.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        lines.append(line)
        body = []
        for k, text in enumerate(lines):
            d, _ = text_path(TEXT_FONT, text, 14.5, 90, 12 + k * 16, "middle", 0.2)
            body.append(f'<path d="{d}" fill="#d9c6a2"/>')
        write(out, f"wdesc{i + 1}", svg(180, 16 * len(lines) + 2, "".join(body)))
    d, w = text_path(LAB_FONT, "TIME SLOWS WHILE THE WHEEL IS OPEN", 12, 0.5, 9, spacing=12 * 0.23)
    write(out, "wheel_slow", svg(w + 1, 10.5, f'<path d="{d}" fill="#d9b880"/>'))
    for key, text in (("wheel_hint_pad", "Right stick to choose, let go to equip"),
                      ("wheel_hint_kbm", "Move the mouse to choose, let go to equip")):
        d, w = text_path(TEXT_FONT, text, 17, 1, 14, spacing=0.6)
        write(out, key, svg(w + 2, 18, f'<path d="{d}" fill="none" stroke="#000" stroke-width="3" stroke-opacity="0.6" '
                                       f'stroke-linejoin="round"/><path d="{d}" fill="#efe1c4"/>'))


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    digits(out)
    labels(out)
    bar(out)
    housing(out)
    stat_icons(out)
    keys(out)
    weapons(out)
    slots(out)
    wheel(out)


if __name__ == "__main__":
    main()
