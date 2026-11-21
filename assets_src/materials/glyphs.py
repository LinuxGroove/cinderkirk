"""Draws the carved foundry marks for the glyph stone: a mask, white where the
stone is cut and glows. Original marks made for Cinderkirk: a bell inside a
gauge ring, hammer strokes, and a border of tally marks."""
import math, sys
from PIL import Image, ImageDraw, ImageFilter

out = sys.argv[1] if len(sys.argv) > 1 else "glyph_mask.png"
S = 1024
im = Image.new("L", (S, S), 0)
d = ImageDraw.Draw(im)
c = S / 2
W = 16  # stroke

# Gauge ring with ticks, like the foundry's pressure dials.
for r in (360, 300):
    d.ellipse([c - r, c - r, c + r, c + r], outline=255, width=W)
for i in range(24):
    a = math.radians(i * 15)
    r0, r1 = (300, 360) if i % 3 == 0 else (318, 342)
    d.line([c + r0 * math.cos(a), c + r0 * math.sin(a), c + r1 * math.cos(a), c + r1 * math.sin(a)], fill=255, width=W)

# The bell: shoulder, waist, flared lip, crown loop and clapper.
pts = []
for t in range(0, 101):
    y = -170 + t * 3.3                     # crown to lip
    k = t / 100
    w = 70 + 40 * k + 95 * k ** 4          # flares at the lip
    pts.append((c + w, c + y))
left = [(2 * c - x, y) for (x, y) in reversed(pts)]
d.line(pts + [(c - 205, c + 160)] + left[1:] + [pts[0]], fill=255, width=W, joint="curve")
d.line([c - 205, c + 160, c + 205, c + 160], fill=255, width=W)
d.ellipse([c - 34, c - 236, c + 34, c - 168], outline=255, width=W)
d.line([c, c - 120, c, c + 190], fill=255, width=W)
d.ellipse([c - 26, c + 176, c + 26, c + 228], fill=255)
# The crack down the bell, the story of the game.
crack = [(c + 40, c - 150), (c + 22, c - 90), (c + 56, c - 40), (c + 30, c + 20), (c + 70, c + 80), (c + 48, c + 158)]
d.line(crack, fill=255, width=W - 4)

# Two hammer strokes across the ring.
for s in (-1, 1):
    d.line([c + s * 250, c + 250, c + s * 420, c + 420], fill=255, width=W + 6)

# Border of tally marks, four and a slash, cut by the founders for each year.
for side in range(4):
    for i in range(10):
        p = 90 + i * 85
        for j in range(4):
            q = p + j * 14
            seg = [(q, 28), (q, 68)]
            if side == 1: seg = [(S - 28, q), (S - 68, q)]
            if side == 2: seg = [(S - q, S - 28), (S - q, S - 68)]
            if side == 3: seg = [(28, S - q), (68, S - q)]
            d.line(seg, fill=255, width=6)
        a, b = (p - 6, 64), (p + 50, 32)
        if side == 0: d.line([a, b], fill=255, width=6)

im = im.filter(ImageFilter.GaussianBlur(2.5))
im.save(out)
print("saved", out)
