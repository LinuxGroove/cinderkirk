#!/usr/bin/env python3
"""The Great Cistern (cisterns5.map), the end of the Cisterns shaft.

The reservoir under the kirk: a pillared hall of black water with causeways
across it to an island in the middle, where the Cistern Seal lies under a
bronze cope. Open both sluices, at the north and south ends of the cross
causeway, and the cope lifts. Taking the Seal opens the gate home.

    python3 maps_src/cisterns5.py maps_src/cisterns5.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

LAMP = (0.95, 0.80, 0.58)
COLD = (0.62, 0.72, 1.0)
DAMP = (0.55, 0.85, 0.75)
CANDLE = (1.0, 0.8, 0.55)
X0, Y0, X1, Y1 = 0, -768, 2048, 768
BED, WATER = -320, -16           # the reservoir's bed and the water's top; the causeways are at 0
IX0, IY0, IX1, IY1 = 768, -256, 1280, 256      # the island


def walkway(L, x0, y0, x1, y1, tex="cist_stone1"):
    L.solid(x0, y0, BED, x1, y1, 0, tex)
    for xa, ya, xb, yb in ((x0, y0, x1, y0 + 8), (x0, y1 - 8, x1, y1)) if x1 - x0 > y1 - y0 else \
            ((x0, y0, x0 + 8, y1), (x1 - 8, y0, x1, y1)):
        L.solid(xa, ya, 0, xb, yb, 8, "verdigris1")                       # the kerbs


def build():
    L = Level(wad="cinder.wad", message="The Great Cistern", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="cist_brick1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, LAMP)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The hall: its floor is the reservoir's bed, under water nearly to the
    # causeways. Pillars every 256 hold up the vault.
    L.room(X0, Y0, BED, X1, Y1, 512, wall="cist_brick1", floor="cist_stone1", ceiling="cist_stone1")
    L.liquid(X0, Y0, BED, X1, Y1, WATER, "*cistern1")
    walkway(L, X0, -64, IX0, 64)                                               # in from the west
    walkway(L, IX1, -64, X1, 64)                                               # out to the east
    walkway(L, 960, IY1, 1088, Y1)                                             # the cross causeway
    walkway(L, 960, Y0, 1088, IY0)
    L.solid(IX0, IY0, BED, IX1, IY1, 0, "cist_stone1")                         # the island
    for x in range(128, X1, 256):
        for y in range(-640, Y1, 256):
            if IX0 - 32 < x < IX1 + 32 and IY0 - 32 < y < IY1 + 32:
                continue
            L.solid(x - 24, y - 24, BED, x + 24, y + 24, 512, "cist_brick1")
            L.solid(x - 32, y - 32, 448, x + 32, y + 32, 480, "cist_stone1")    # the springers
            L.solid(x - 32, y - 32, WATER - 8, x + 32, y + 32, WATER + 24, "verdigris1")
    # Steps out of the water at the island's corners.
    for x, y in ((IX0 - 64, IY0 + 32), (IX0 - 64, IY1 - 96), (IX1, IY0 + 32), (IX1, IY1 - 96)):
        L.solid(x, y, BED, x + 64, y + 64, -40, "cist_stone1")

    # The cope on the island, over the Seal, hung from the vault.
    L.solid(896, -128, 0, 1152, 128, 32, "cist_stone1")
    L.steps(832, -64, 896, 64, 0, 32, tex="cist_stone1")
    L.steps(1152, -64, 1216, 64, 32, 0, tex="cist_stone1")
    cope = [Box(960, -80, 32, 976, 80, 160, "bronze1"),
            Box(1072, -80, 32, 1088, 80, 160, "bronze1"),
            Box(976, -80, 32, 1072, -64, 160, "bronze1"),
            Box(976, 64, 32, 1072, 80, 160, "bronze1"),
            Box(960, -80, 160, 1088, 80, 176, "bronze1"),
            Box(976, -64, 176, 1072, 64, 208, "bronze1")]
    L.brush_entity("func_door", cope, angle=-1, targetname="cope", speed=40, wait=-1, lip=-160, sounds=2)
    L.add("item_sigil", (1024, 0, 56), spawnflags=2)
    for y in (-48, 48):
        L.solid(1022, y - 2, 208, 1026, y + 2, 512, "iron_plate1")             # the chains
    L.light((1024, 0, 260), 220, LAMP)
    for y in (-180, 180):
        L.light((1024, y, 64), 180, DAMP)

    # The sluice wheels, one at each end of the cross causeway.
    for y, side in ((Y1 - 12, "north"), (Y0, "south")):
        L.brush_entity("func_button", [Box(992, y, 40, 1056, y + 12, 104, "verdigris1")],
                       angle=90 if y > 0 else 270, target="sluices", wait=-1, lip=4,
                       message=f"The {side} sluice opens")
        L.light((1024, y + (-48 if y > 0 else 60), 120), 160, CANDLE)
    L.add("trigger_counter", None, targetname="sluices", count=2, spawnflags=1,
          target="cope", message="The water falls away from the cope, and it lifts")

    # Light: lamps hung over the causeways, a glow off the water.
    for x in (256, 640, 1408, 1792):
        L.solid(x - 8, -8, 320, x + 8, 8, 352, "lamp_amber1")
        L.solid(x - 2, -2, 352, x + 2, 2, 512, "iron_plate1")
        L.light((x, 0, 300), 380, LAMP)
    for y in (-512, 512):
        L.solid(1016, y - 8, 320, 1032, y + 8, 352, "lamp_amber1")
        L.solid(1022, y - 2, 352, 1026, y + 2, 512, "iron_plate1")
        L.light((1024, y, 300), 360, LAMP)
    for x in range(256, X1, 512):
        for y in (-512, 512):
            L.light((x, y, 16), 240, DAMP)
    L.light((1024, 0, 460), 500, COLD)

    # Pick-ups.
    L.add("item_health", (96, 32, 0), spawnflags=2)
    L.add("item_shells", (400, 0, 0))
    L.add("item_spikes", (1024, 700, 0))
    L.add("item_rockets", (1024, -700, 0))
    L.add("item_health", (800, 200, 0))
    L.add("item_health", (1240, -200, 0))
    L.add("item_cells", (1600, 0, 0))
    L.add("item_armor2", (1900, 32, 0))
    L.add("item_artifact_envirosuit", (300, 600, BED + 24))

    # The congregation, and the water full of leeches.
    for x, y in ((300, 400), (300, -400), (700, 560), (700, -560), (1400, 420), (1400, -420),
                 (1700, 560), (1700, -560), (900, 420), (1150, -420)):
        L.add("monster_leech", (x, y, -160), angle=180)
    L.add("monster_crucible_brute", (850, -150, 24), angle=180)
    for x, y in ((1200, 180), (1200, -180)):
        L.add("monster_gauger", (x, y, 24), angle=180)
    L.add("monster_deacon", (1120, 0, 64), angle=180, spawnflags=1)
    L.add("monster_censer", (1024, 600, 24), angle=270)
    L.add("monster_censer", (1024, -600, 24), angle=90)
    for x in (500, 1500, 1800):
        L.add("monster_ashen", (x, 0, 24), angle=180)
    L.add("monster_slag_hound", (1024, 400, 24), angle=270, spawnflags=1)
    L.add("monster_slag_hound", (1024, -400, 24), angle=90, spawnflags=1)
    for x in (640, 1408):
        L.add("monster_clinker", (x, 40, 500), spawnflags=2)

    # The gate home at the east end, opened by the cope.
    L.opening(X1, -64, 0, X1 + 32, 64, 128)
    L.brush_entity("func_door", [Box(X1, -64, 0, X1 + 32, 64, 128, "sluice_wood1")],
                   angle=-1, targetname="cope", speed=80, wait=-1, lip=8)
    L.room(X1 + 32, -96, 0, X1 + 192, 96, 192, wall="cist_brick1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((X1 + 112, 0, 160), 160, LAMP)
    L.brush_entity("trigger_changelevel", [Box(X1 + 64, -64, 0, X1 + 160, 64, 96, "trigger")], map="start")
    L.add("info_intermission", (200, -600, 360), mangle=(25, 30, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "cisterns5.map")
    build().save(out)
    print(out)
