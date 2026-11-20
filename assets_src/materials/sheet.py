"""Contact sheet of the baked texture sets: albedo, _norm, _gloss, _luma per material.
python3 sheet.py <textures dir> <out.png>"""
import sys, os
from PIL import Image, ImageDraw, ImageFont
src, out = sys.argv[1], sys.argv[2]
names = ["kirk_brick1", "kirk_vbrick1", "kirk_stone1", "kirk_glyph1", "iron_plate1", "floor_flag1",
         "#slag1", "bronze1", "cloth_char1", "leather1", "oak1"]
T, PAD, LAB = 200, 10, 26
cols = ["", "_norm", "_gloss", "_luma"]
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
half = (len(names) + 1) // 2
gw = len(cols) * (T + PAD) + PAD
W = gw * 2 + 30
H = 40 + half * (T + LAB + PAD) + PAD
img = Image.new("RGB", (W, H), (18, 14, 12))
d = ImageDraw.Draw(img)
for g in range(2):
    for c, suf in enumerate(cols):
        d.text((g * (gw + 30) + PAD + c * (T + PAD), 12), suf or "albedo", fill=(230, 190, 140), font=bold)
for i, n in enumerate(names):
    g, r = divmod(i, half)
    x0 = g * (gw + 30) + PAD
    y0 = 40 + r * (T + LAB + PAD)
    d.text((x0, y0), n + "  (1024 px, tiles)", fill=(220, 210, 200), font=font)
    for c, suf in enumerate(cols):
        p = os.path.join(src, n + suf + ".png")
        x = x0 + c * (T + PAD)
        if os.path.exists(p):
            im = Image.open(p).convert("RGB").resize((T, T), Image.LANCZOS)
            img.paste(im, (x, y0 + LAB))
        else:
            d.rectangle([x, y0 + LAB, x + T - 1, y0 + LAB + T - 1], outline=(60, 50, 45))
            d.text((x + 60, y0 + LAB + 90), "no glow", fill=(90, 80, 70), font=font)
img.save(out)
print(img.size)
