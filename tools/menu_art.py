#!/usr/bin/env python3
"""Draw Cinderkirk's menu titles, menu items, side plaque and console
background, in place of LibreQuake's and vkQuake's.

    tools/menu_art.py PALETTE OUT_DIR TEXTURE_DIR GLYPH_MASK

Each picture is written twice: gfx/<name>.lmp at the size the menus lay out
(Quake's 320-wide menu), and gfx/<name>.png at SCALE times that, which the
engine draws in its place, so the menus stay sharp on a 4K screen.
"""

import os
import struct
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

SCALE = 4
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets_src", "fonts")
HEAVY = os.path.join(FONTS, "cinzel-latin-900-normal.woff")
BOLD = os.path.join(FONTS, "cinzel-latin-700-normal.woff")
# Running text: Barlow Condensed, which stays readable small and on a TV.
TEXT = os.path.join(FONTS, "barlow-condensed-latin-500-normal.woff")
TEXT_BOLD = os.path.join(FONTS, "barlow-condensed-latin-700-normal.woff")

# Menu titles: name -> text. Width follows the text; height is 24.
TITLES = {
    "ttl_main": "CINDERKIRK",
    "ttl_sgl": "STORY",
    "ttl_cstm": "CONTROLS",
    "p_multi": "PIT FIGHTS",
    "p_option": "OPTIONS",
    "p_load": "LOAD",
    "p_save": "SAVE",
    "p_skill": "DIFFICULTY",
    "p_mods": "MODS",
    "complete": "COMPLETE",
    "finale": "THE END",
    "vidmodes": "VIDEO",
    "loading": "LOADING",
    "pause": "PAUSED",
    "ranking": "SCORES",
}

# The Pit Fights connection rows (the menu greys out a dim_* one it can't use).
NET_ROWS = {"netmen3": "LAN (IPX)", "netmen4": "LAN AND INTERNET"}
NET_DIM = {"dim_ipx": "LAN (IPX)", "dim_tcp": "LAN AND INTERNET"}

# How to Play, one page each; the engine's NUM_HELP_PAGES must match.
# Each page is a heading and lines of (label, text); a label of None is a paragraph.
HELP = [
    ("HOW TO PLAY", [
        (None, "You're the last stoker at the bell foundry of Cinderkirk, built over a pit "
               "that never stopped burning. Something has come up out of it. Fight your way down."),
        (None, "Keys open the doors that match them. Find the key, then come back."),
        (None, "Slag kills. Keep off the glowing floor of the channels."),
        (None, "Fighting builds Pressure, the dial in the middle of the status bar. Spend it on a dash "
               "or a weapon's Overpressure shot. Jump on a steam vent to be thrown high."),
        (None, "Some walls hide a way through: shoot or strike the ones that look wrong."),
    ]),
    ("CONTROLLER", [
        ("Move", "Left stick"),
        ("Look", "Right stick, or tilt the pad"),
        ("Fire", "Right trigger"),
        ("Jump", "A"),
        ("Dash", "B"),
        ("Overpressure", "Left trigger"),
        ("Walk", "Click the left stick"),
        ("Weapon wheel", "Hold LB; tap it for the last weapon"),
        ("Change weapon", "RB, or the d-pad"),
        ("Scores", "Y"),
        ("Menu", "Start"),
    ]),
    ("KEYBOARD AND MOUSE", [
        ("Move", "W A S D, or the arrow keys"),
        ("Look", "Mouse"),
        ("Fire", "Left button"),
        ("Jump", "Space"),
        ("Dash", "Shift"),
        ("Overpressure", "Right button"),
        ("Weapon wheel", "Hold Q, point with the mouse"),
        ("Change weapon", "Mouse wheel"),
        ("Pick a weapon", "1 to 8"),
        ("Quick save and load", "F6 and F9"),
        ("Menu", "Esc"),
    ]),
]

# Menu item lists: name -> (size, rows). Rows are 20 apart, as the menus expect.
ITEMS = {
    "mainmenu": ((240, 112), ["STORY", "PIT FIGHTS", "OPTIONS", "HOW TO PLAY", "QUIT"]),
    "mainmenu2": ((240, 123), ["STORY", "PIT FIGHTS", "OPTIONS", "HOW TO PLAY", "MODS", "QUIT"]),
    "sp_menu": ((232, 64), ["NEW GAME", "LOAD", "SAVE"]),
    "sp_maps": ((116, 20), ["LEVELS"]),
    "mp_menu": ((232, 64), ["JOIN A FIGHT", "HOST A FIGHT", "SETUP"]),
    "skillmenu": ((180, 82), ["APPRENTICE", "JOURNEYMAN", "MASTER", "BELLFOUNDER"]),
}


def load_palette(path):
    return np.frombuffer(open(path, "rb").read(), dtype=np.uint8).reshape(256, 3).astype(np.int32)


def write_lmp(path, img, palette):
    """An lmp: width, height, then palette indices, 255 where transparent."""
    rgba = np.asarray(img.convert("RGBA")).astype(np.int32)
    rgb, a = rgba[:, :, :3], rgba[:, :, 3]
    usable = palette[:224]
    d = ((rgb.reshape(-1, 1, 3) - usable[None]) ** 2).sum(axis=2)
    idx = d.argmin(axis=1).astype(np.uint8).reshape(a.shape)
    idx[a < 128] = 255
    h, w = idx.shape
    with open(path, "wb") as f:
        f.write(struct.pack("<ii", w, h) + idx.tobytes())


def save(out, name, big, palette):
    """Save the big picture as PNG and a small copy as the lmp."""
    w, h = big.size[0] // SCALE, big.size[1] // SCALE
    big.save(os.path.join(out, name + ".png"))
    write_lmp(os.path.join(out, name + ".lmp"), big.resize((w, h), Image.LANCZOS), palette)


def ember_text(size, text, font_path, height, align="left"):
    """Cast-bronze letters: a hot gradient, a dark rim and a soft glow."""
    W, H = size[0] * SCALE, size[1] * SCALE
    font = ImageFont.truetype(font_path, int(height * SCALE))
    mask = Image.new("L", (W, H))
    d = ImageDraw.Draw(mask)
    box = d.textbbox((0, 0), text, font=font)
    tw = box[2] - box[0]
    # Centre on the capitals' height, so a Q's tail doesn't lift its row.
    cap = d.textbbox((0, 0), "H", font=font)
    x = {"left": 2 * SCALE, "center": (W - tw) // 2}[align] - box[0]
    y = (H - (cap[3] - cap[1])) // 2 - cap[1]
    d.text((x, y), text, font=font, fill=255)
    return mask


def colour_letters(mask):
    W, H = mask.size
    ys = np.linspace(0, 1, H)[:, None]
    top = np.array([255, 226, 150])
    mid = np.array([240, 140, 48])
    bot = np.array([150, 52, 18])
    t = np.where(ys < 0.5, ys * 2, (ys - 0.5) * 2)[..., None]
    grad = np.where((ys < 0.5)[..., None], top * (1 - t) + mid * t, mid * (1 - t) + bot * t)
    grad = np.broadcast_to(grad, (H, W, 3)).astype(np.uint8)
    fill = Image.fromarray(grad, "RGB")
    rim = mask.filter(ImageFilter.MaxFilter(2 * (SCALE // 2) + 1))
    glow = mask.filter(ImageFilter.GaussianBlur(SCALE * 2))
    out = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    out.paste((255, 96, 20, 255), (0, 0), glow.point(lambda v: int(v * 0.55)))
    out.paste((28, 14, 8, 255), (0, 0), rim)
    out.paste(fill, (0, 0), mask)
    return out


def title(text):
    font = ImageFont.truetype(HEAVY, 20 * SCALE)
    w = font.getbbox(text)[2] // SCALE + 8
    w += w % 2
    return colour_letters(ember_text((w, 24), text, HEAVY, 19, "center"))


def items(size, rows):
    W, H = size[0] * SCALE, size[1] * SCALE
    sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, text in enumerate(rows):
        row = colour_letters(ember_text((size[0], 20), text, BOLD, 15))
        sheet.alpha_composite(row, (0, i * 20 * SCALE))
    return sheet


def plaque(tex_dir, glyph_mask):
    """The tall plate down the left of the menus: bronze, with the foundry mark."""
    W, H = 32 * SCALE, 144 * SCALE
    bronze = Image.open(os.path.join(tex_dir, "bronze1.png")).convert("RGB").resize((W, W))
    plate = Image.new("RGB", (W, H))
    for y in range(0, H, W):
        plate.paste(bronze, (0, y))
    plate = Image.eval(plate, lambda v: int(v * 0.8))
    out = plate.convert("RGBA")
    d = ImageDraw.Draw(out)
    d.rectangle((0, 0, W - 1, H - 1), outline=(40, 22, 10, 255), width=SCALE)
    d.rectangle((SCALE * 2, SCALE * 2, W - 1 - SCALE * 2, H - 1 - SCALE * 2),
                outline=(214, 150, 70, 255), width=max(1, SCALE // 2))
    mark = Image.open(glyph_mask).convert("L").resize((W - 8 * SCALE, W - 8 * SCALE), Image.LANCZOS)
    hot = colour_letters(Image.eval(mark, lambda v: 255 - v) if np.asarray(mark).mean() > 127 else mark)
    out.alpha_composite(hot, (4 * SCALE, 6 * SCALE))
    word = ember_text((112, 24), "CINDERKIRK", HEAVY, 13, "center").rotate(90, expand=True)
    word = colour_letters(word)
    out.alpha_composite(word, ((W - word.size[0]) // 2, 34 * SCALE))
    return out


def net_row(text, dim):
    row = colour_letters(ember_text((264, 20), text, BOLD, 15))
    if dim:
        grey = row.convert("LA").convert("RGBA")
        grey.putalpha(row.getchannel("A").point(lambda v: v // 2))
        row = grey
    return row


def inter():
    """The intermission's labels, lined up with the numbers the engine draws
    at 8, 48 and 88 below the picture's top."""
    W, H = 128 * SCALE, 112 * SCALE
    sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, text in enumerate(["TIME", "SECRETS", "KILLS"]):
        row = colour_letters(ember_text((128, 24), text, HEAVY, 17))
        sheet.alpha_composite(row, (0, (8 + 40 * i) * SCALE))
    return sheet


def wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def help_page(tex_dir, n, heading, rows):
    """A How to Play page: a dark brick panel in a bronze frame."""
    W, H = 320 * SCALE, 200 * SCALE
    brick = Image.open(os.path.join(tex_dir, "kirk_brick1.png")).convert("RGB").resize((W // 3, W // 3))
    wall = Image.new("RGB", (W, H))
    for y in range(0, H, W // 3):
        for x in range(0, W, W // 3):
            wall.paste(brick, (x, y))
    a = np.asarray(wall).astype(np.float32) / 255
    ys = np.linspace(0, 1, H)[:, None, None]
    a = np.clip(a * (0.16 + 0.22 * ys ** 2) * np.array([1.0, 0.62, 0.4]) * 1.6, 0, 1)
    page = Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(page)
    d.rectangle((0, 0, W - 1, H - 1), outline=(40, 22, 10, 255), width=3 * SCALE)
    d.rectangle((4 * SCALE, 4 * SCALE, W - 1 - 4 * SCALE, H - 1 - 4 * SCALE),
                outline=(214, 150, 70, 255), width=SCALE // 2)
    head = colour_letters(ember_text((320, 26), heading, HEAVY, 18, "center"))
    page.alpha_composite(head, (0, 8 * SCALE))
    d.line((80 * SCALE, 36 * SCALE, 240 * SCALE, 36 * SCALE), fill=(214, 150, 70, 255), width=SCALE // 2)

    body = ImageFont.truetype(TEXT, int((10.5 if rows and rows[0][0] is None else 11) * SCALE))
    label = ImageFont.truetype(TEXT_BOLD, int(11 * SCALE))
    ink, gold = (236, 222, 200, 255), (246, 176, 82, 255)
    y = 43 * SCALE
    if rows and rows[0][0] is None:
        # Paragraphs fill the panel from x 22 to 298 and must stop above the pager.
        for _, text in rows:
            for line in wrap(d, text, body, 276 * SCALE):
                d.text((22 * SCALE, y), line, font=body, fill=ink)
                y += 12 * SCALE
            y += 4 * SCALE
        assert y <= (200 - 22) * SCALE, f"How to Play page {n + 1} runs into the pager"
    else:
        for name, text in rows:
            d.text((150 * SCALE, y), name, font=label, fill=gold, anchor="ra")
            d.text((162 * SCALE, y), text, font=body, fill=ink)
            y += 13 * SCALE
    foot = ImageFont.truetype(TEXT_BOLD, 10 * SCALE)
    d.text((W // 2, H - 18 * SCALE), f"<   {n + 1} of {len(HELP)}   >", font=foot,
           fill=(214, 150, 70, 255), anchor="ma")
    return page.convert("RGB")


def menuplyr(path, palette):
    """The setup screen's stoker, 48x56, in palette indices: the coat in the
    shirt colour's range (16-31) and the trousers in the pants' (96-111), so
    the engine recolours it as the player picks colours. Drawn at 4x as
    regions with a light value, then taken down to one index a pixel."""
    S, W, H = 4, 48, 56
    reg = Image.new("L", (W * S, H * S), 0)      # 0 empty, 1 iron, 2 coat, 3 trousers, 4 leather, 5 glow
    d = ImageDraw.Draw(reg)
    cx = W * S // 2
    def box(x0, y0, x1, y1, r, rad=0):
        d.rounded_rectangle((cx + x0 * S, y0 * S, cx + x1 * S, y1 * S), radius=rad * S, fill=r)
    box(-14, 52, -3, 55, 4, 1)                    # boots
    box(3, 52, 14, 55, 4, 1)
    box(-11, 32, -2, 53, 3, 1)                    # trousers
    box(2, 32, 11, 53, 3, 1)
    box(-12, 15, 12, 36, 2, 3)                    # the coat, open at the front
    box(-13, 33, -4, 40, 2, 1)                    # its skirts
    box(4, 33, 13, 40, 2, 1)
    box(-2, 17, 2, 36, 4)                         # leather apron down the middle
    box(-12, 29, 12, 31, 4)                       # belt
    box(-19, 16, -12, 34, 2, 2)                   # sleeves
    box(12, 16, 19, 34, 2, 2)
    box(-20, 33, -13, 38, 4, 2)                   # gloves
    box(13, 33, 20, 38, 4, 2)
    box(-8, 2, 8, 16, 1, 3)                       # the iron hood
    box(-6, 7, 6, 10, 5)                          # its eye slit, lit
    box(-11, 14, 11, 17, 1, 1)                    # collar
    r = np.asarray(reg).reshape(H, S, W, S)
    xs = np.linspace(-1, 1, W * S)[None, :]
    ys = np.linspace(0, 1, H * S)[:, None]
    light = np.clip(0.75 - 0.45 * np.abs(xs + 0.25) - 0.25 * ys, 0.05, 1).reshape(H, S, W, S)
    out = np.full((H, W), 255, np.uint8)
    pal = palette
    fixed = [i for i in range(224) if not (16 <= i < 32 or 96 <= i < 112)]   # never recoloured

    def nearest(rgb):
        return fixed[int(((pal[fixed] - np.array(rgb)) ** 2).sum(axis=1).argmin())]
    iron = [nearest((v, v, v + 4)) for v in range(16, 120, 7)]
    leather = [nearest((v, int(v * 0.62), int(v * 0.4))) for v in range(20, 140, 8)]
    glow = nearest((255, 170, 60))
    for y in range(H):
        for x in range(W):
            cell = r[y, :, x, :]
            vals, counts = np.unique(cell, return_counts=True)
            k = int(vals[counts.argmax()])
            if k == 0:
                continue
            l = float(light[y, :, x, :].mean())
            # Edges of each region darker, so shapes read at this size.
            if (cell != k).any():
                l *= 0.6
            if k == 1:
                out[y, x] = iron[min(len(iron) - 1, int(l * len(iron)))]
            elif k == 2:
                out[y, x] = 16 + min(15, int(l * 16))
            elif k == 3:
                out[y, x] = 96 + min(15, int(l * 16))
            elif k == 4:
                out[y, x] = leather[min(len(leather) - 1, int(l * len(leather)))]
            else:
                out[y, x] = glow
    with open(path, "wb") as f:
        f.write(struct.pack("<ii", W, H) + out.tobytes())


def menudot(frame):
    """The menu cursor: a coal that breathes, six frames."""
    W, H = 16 * SCALE, 20 * SCALE
    glow = 0.55 + 0.45 * np.sin(frame / 6 * np.pi * 2) ** 2
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    halo = Image.new("L", (W, H))
    ImageDraw.Draw(halo).ellipse((2 * SCALE, 4 * SCALE, 14 * SCALE, 16 * SCALE), fill=int(200 * glow))
    out.paste((255, 110, 30, 255), (0, 0), halo.filter(ImageFilter.GaussianBlur(2 * SCALE)))
    coal = Image.new("L", (W, H))
    c, r = (8 * SCALE, 10 * SCALE), 4 * SCALE
    ImageDraw.Draw(coal).polygon([(c[0], c[1] - r), (c[0] + r, c[1]), (c[0], c[1] + r), (c[0] - r, c[1])], fill=255)
    hot = colour_letters(coal)
    out.alpha_composite(hot)
    return out


def conback(tex_dir, glyph_mask):
    """The console background: dark brick lit from below by the pit."""
    W, H = 320 * SCALE, 200 * SCALE
    brick = Image.open(os.path.join(tex_dir, "kirk_brick1.png")).convert("RGB").resize((W // 2, W // 2))
    wall = Image.new("RGB", (W, H))
    for y in range(0, H, W // 2):
        for x in range(0, W, W // 2):
            wall.paste(brick, (x, y))
    a = np.asarray(wall).astype(np.float32) / 255
    ys = np.linspace(0, 1, H)[:, None, None]
    light = 0.18 + 0.55 * ys ** 2.2
    tint = np.array([1.0, 0.55, 0.28]) * ys + np.array([0.55, 0.5, 0.55]) * (1 - ys)
    a = np.clip(a * light * tint * 1.6, 0, 1)
    out = Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")
    mark = Image.open(glyph_mask).convert("L").resize((48 * SCALE, 48 * SCALE), Image.LANCZOS)
    mark = Image.eval(mark, lambda v: 255 - v) if np.asarray(mark).mean() > 127 else mark
    hot = colour_letters(mark)
    hot.putalpha(ImageChops.multiply(hot.getchannel("A"), Image.new("L", hot.size, 150)))
    out.alpha_composite(hot, (W - 56 * SCALE, H - 70 * SCALE))
    word = colour_letters(ember_text((90, 16), "CINDERKIRK", HEAVY, 10, "center"))
    out.alpha_composite(word, (W - 94 * SCALE, H - 20 * SCALE))
    return out.convert("RGB")


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    palette = load_palette(sys.argv[1])
    out = os.path.join(sys.argv[2], "gfx")
    tex_dir, glyph_mask = sys.argv[3], sys.argv[4]
    os.makedirs(out, exist_ok=True)
    for name, text in TITLES.items():
        save(out, name, title(text), palette)
    for name, (size, rows) in ITEMS.items():
        save(out, name, items(size, rows), palette)
    for f in range(6):
        save(out, f"menudot{f + 1}", menudot(f), palette)
    save(out, "qplaque", plaque(tex_dir, glyph_mask), palette)
    save(out, "conback", conback(tex_dir, glyph_mask), palette)
    for name, text in NET_ROWS.items():
        save(out, name, net_row(text, False), palette)
    for name, text in NET_DIM.items():
        save(out, name, net_row(text, True), palette)
    save(out, "inter", inter(), palette)
    menuplyr(os.path.join(out, "menuplyr.lmp"), palette)
    for n, (heading, rows) in enumerate(HELP):
        save(out, f"help{n}", help_page(tex_dir, n, heading, rows), palette)
    print(f"menu art in {out}")


if __name__ == "__main__":
    main()
