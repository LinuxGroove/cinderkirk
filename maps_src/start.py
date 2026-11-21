#!/usr/bin/env python3
"""The Pithead (start.map), the hub: the hall under the headframe where every
run begins. The lift lever's four notches on the south wall set the skill;
a cage down each shaft opens off the hall (the Foundry to the north, the
Cisterns and the Undervein to the east, the Ossuary Kilns to the south); the
grate over the Throat in the middle of the floor opens once all four shafts
are beaten; and the trophy shelf on the west wall keeps what you've broken.

    python3 maps_src/start.py maps_src/start.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

WARM = (1.0, 0.62, 0.32)
SLAG = (1.0, 0.42, 0.12)
COLD = (0.62, 0.72, 1.0)
CANDLE = (1.0, 0.8, 0.55)

SKILLS = ("Apprentice", "Journeyman", "Master", "Founder's")

# Each shaft's cage: name, the opening in the hall's wall, the cage behind it,
# and the first map (None until the shaft is built).
CAGES = (
    ("The Foundry", (448, 512, 576, 544), (448, 544, 576, 672), "foundry1",
     "The Foundry: casting halls, slag channels and pattern shops"),
    ("The Cisterns", (1024, 192, 1056, 320), (1056, 192, 1184, 320), "cisterns1",
     "The Cisterns: flooded vaults, quench tanks, and what lives in the water"),
    ("The Undervein", (1024, -320, 1056, -192), (1056, -320, 1184, -192), "vein1",
     "The Undervein: the Founder's mine, where the bell's iron was dug"),
    ("The Ossuary Kilns", (640, -544, 768, -512), (640, -672, 768, -544), "kilns1",
     "The Ossuary Kilns: the kirk's crypts, the bone kilns, and the ash that walks"),
)


def build():
    L = Level(wad="cinder.wad", light_wait=0.8, sounds=2, message="The Pithead", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=8, _range=0.6)

    # The hall under the headframe: x 0..1024, y -512..512, floor 0, roof 512.
    L.room(0, -512, 0, 1024, 512, 512, wall="kirk_stone1", floor="iron_plate1",
           ceiling="ceil_timber1")
    # Sooted brick and a carved band, north and south, broken for the cages.
    for y0, y1, gaps in ((-512, -504, (640, 768)), (504, 512, (448, 576))):
        for x0, x1 in ((0, gaps[0]), (gaps[1], 1024)):
            L.solid(x0, y0, 0, x1, y1, 96, "kirk_brick2")
            L.solid(x0, y0, 96, x1, y1, 128, "kirk_trim1")
    for x in (256, 512, 768):                         # the headframe's beams
        L.solid(x - 16, -512, 448, x + 16, 512, 480, "oak_beam1")
    for x, y in ((384, -192), (640, -192), (384, 160), (640, 160)):
        L.solid(x, y, 0, x + 32, y + 32, 448, "kirk_column1")   # its legs, round the Throat

    L.add("info_player_start", (96, 0, 24), angle=0)
    L.add("info_player_coop", (96, 64, 24), angle=0)
    L.add("info_player_coop", (96, -64, 24), angle=0)
    L.add("info_intermission", (128, -400, 300), mangle=(25, 40, 0))

    # The lift lever: four notches on a bronze panel in the south wall.
    L.solid(144, -512, 24, 432, -496, 120, "bronze1")
    L.solid(144, -496, 112, 432, -488, 120, "brass_trim1")
    for i, name in enumerate(SKILLS):
        x = 160 + i * 64
        L.brush_entity("func_button", [Box(x, -496, 48, x + 48, -484, 88, "brass_trim1")],
                       angle=270, target=f"skill{i}", wait=1, lip=4)
        L.add("target_skill", (x + 24, -440, 64), targetname=f"skill{i}", cnt=i)
    L.brush_entity("trigger_once", [Box(144, -480, 0, 432, -352, 128, "trigger")],
                   message="The lift lever: push a notch to set how hard the pit fights.\n"
                           "Apprentice, Journeyman, Master, Founder's")
    L.light((288, -440, 160), 180, CANDLE)

    # The cages.
    for name, (ox0, oy0, ox1, oy1), (cx0, cy0, cx1, cy1), first, sign in CAGES:
        L.room(cx0, cy0, 0, cx1, cy1, 256, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
        if first:
            L.opening(ox0, oy0, 0, ox1, oy1, 160)
            L.brush_entity("trigger_changelevel",
                           [Box(cx0 + 16, cy0 + 16, 0, cx1 - 16, cy1 - 16, 96, "trigger")], map=first,
                           spawnflags=1)   # straight down, no tally
            L.light(((cx0 + cx1) / 2, (cy0 + cy1) / 2, 200), 260, WARM)
        else:
            L.opening(ox0, oy0, 0, ox1, oy1, 160)
            L.solid(ox0, oy0, 0, ox1, oy1, 160, "iron_grid1")       # the gate, shut
            L.light(((cx0 + cx1) / 2, (cy0 + cy1) / 2, 200), 120, COLD)
        # The sign: said as you come near.
        sx0, sy0, sx1, sy1 = ox0 - 32, oy0 - 32, ox1 + 32, oy1 + 32
        if oy0 >= 512:
            sy0, sy1 = 384, 512
        elif oy1 <= -512:
            sy0, sy1 = -512, -384
        else:
            sx0, sx1 = 896, 1024
        L.brush_entity("trigger_multiple", [Box(sx0, sy0, 0, sx1, sy1, 128, "trigger")], message=sign, wait=4)
        # The mark over the cage, shown once every map down it is finished with every secret.
        mx, my = (ox0 + ox1) // 2, (oy0 + oy1) // 2
        if oy0 >= 512:
            box = Box(mx - 32, 500, 176, mx + 32, 512, 240, "kirk_glyph1")
        elif oy1 <= -512:
            box = Box(mx - 32, -512, 176, mx + 32, -500, 240, "kirk_glyph1")
        else:
            box = Box(1012, my - 32, 176, 1024, my + 32, 240, "kirk_glyph1")
        flag = {"foundry1": 1, "cisterns1": 2, "kilns1": 4, "vein1": 8}[first]
        L.brush_entity("func_lift_mark", [box], spawnflags=flag)

    # The Throat: a pit in the middle of the floor, glowing, under a grate
    # that only lifts once all four shafts are beaten.
    L.room(448, -64, -448, 576, 64, -32, wall="kirk_vbrick1", floor="kirk_stone1")
    L.opening(448, -64, -32, 576, 64, 0)
    L.liquid(448, -64, -448, 576, 64, -400)
    L.brush_entity("trigger_changelevel", [Box(448, -64, -320, 576, 64, -160, "trigger")], map="throat1")
    L.brush_entity("func_bossgate", [Box(448, -64, -8, 576, 64, 0, "iron_grid1")])
    L.brush_entity("trigger_multiple", [Box(400, -112, 0, 624, 112, 96, "trigger")],
                   message="The Throat. The grate lifts when all four shafts are beaten", wait=6)
    L.add("light", (512, 0, -380), light=300, _color=SLAG)
    L.add("light", (512, 0, -120), light=200, _color=SLAG)

    # The trophy shelf on the west wall.
    L.solid(0, -224, 96, 48, 224, 104, "oak1")
    L.solid(0, -224, 192, 48, 224, 200, "oak1")
    for flag, y in ((1, -168), (2, -56), (4, 56), (8, 168)):   # a Seal for each shaft beaten
        L.add("misc_seal_trophy", (24, y, 112), spawnflags=flag)
    L.light((96, 0, 160), 200, CANDLE)

    # Light: lamps hung from the headframe, braziers along the walls.
    for x in (256, 768):
        for y in (-256, 256):
            L.solid(x - 8, y - 8, 320, x + 8, y + 8, 352, "lamp_amber1")
            L.solid(x - 2, y - 2, 352, x + 2, y + 2, 448, "iron_plate1")
            L.light((x, y, 300), 360, WARM)
    for y in (-400, 400):
        L.light((96, y, 64), 200, CANDLE)
        L.light((928, y, 64), 200, CANDLE)
    L.light((512, 0, 420), 300, COLD)
    return L


if __name__ == "__main__":
    build().save(sys.argv[1] if len(sys.argv) > 1 else "start.map")
