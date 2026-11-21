#!/usr/bin/env python3
"""The Settling Tanks (cisterns3.map), the Cisterns shaft's third map.

A hall of open iron tanks where the quench water stood to settle: six
tanks in two rows with aisles between, catwalks over them, and the lift up
to the catwalks at the west end. The silver key lies at the bottom of the
middle north tank; the silver door is at the top of the east catwalk.

    python3 maps_src/cisterns3.py maps_src/cisterns3.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

LAMP = (0.95, 0.80, 0.58)
COLD = (0.62, 0.72, 1.0)
DAMP = (0.55, 0.85, 0.75)
TANKS = [(x, y) for x in (256, 704, 1152) for y in (-416, 96)]   # south-west corners, 320 square
CAT = 224                                                        # the catwalks' height


def build():
    L = Level(wad="cinder.wad", sounds=5, message="The Settling Tanks", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="cist_brick1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, LAMP)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The hall: x 0..1664, y -512..512, floor 0, roof 448. The tanks stand
    # 160 high, sunk 128 into the floor, and full nearly to the rim.
    L.room(0, -512, 0, 1664, 512, 448, wall="cist_brick1", floor="cist_stone1", ceiling="ceil_timber1",
           floor_depth=192)
    for x, y in TANKS:
        L.opening(x + 16, y + 16, -128, x + 304, y + 304, 0)
        for b in ((x, y, x + 320, y + 16), (x, y + 304, x + 320, y + 320), (x, y + 16, x + 16, y + 304),
                  (x + 304, y + 16, x + 320, y + 304)):
            L.solid(b[0], b[1], -128, b[2], b[3], 160, "tank_iron1")
        L.liquid(x + 16, y + 16, -128, x + 304, y + 304, 144, "*cistern1")
        L.solid(x, y, 160, x + 320, y + 16, 168, "brass_trim1")
    # Catwalks: one down the middle over the aisle, one across each end, and
    # the lift from the floor at the west end.
    L.solid(160, -48, CAT - 16, 1536, 48, CAT, "iron_grid1")
    for x0 in (160, 1536):
        L.solid(x0, -480, CAT - 16, x0 + 96, 480, CAT, "iron_plate1")
    L.brush_entity("func_plat", [Box(64, -48, CAT - 16, 160, 48, CAT, "iron_plate1")], height=CAT, speed=150)
    for x in range(256, 1536, 192):
        L.solid(x - 2, -2, CAT, x + 2, 2, 448, "iron_plate1")               # hangers

    L.add("item_key1", (864, 256, -104))
    L.add("item_health", (380, 256, -104))
    for (x, y), n in zip(TANKS, (1, 2, 3, 1, 2, 1)):
        for i in range(n):
            L.add("monster_leech", (x + 100 + i * 60, y + 160, 40), angle=90)
    L.add("monster_gauger", (900, 0, CAT + 24), angle=180)
    L.add("monster_gauger", (1580, 300, CAT + 24), angle=180)
    L.add("monster_crucible_brute", (1000, -48, 24), angle=180)
    for x, y in ((600, -480), (1100, 480), (1450, -480)):
        L.add("monster_ashen", (x, y, 24), angle=180)
    L.add("monster_censer", (200, 400, CAT + 24), angle=270)
    L.add("item_rockets", (1580, -300, CAT))
    L.add("item_spikes", (40, 400, 0))
    L.add("item_shells", (40, -400, 0))
    L.add("weapon_grenadelauncher", (1600, 0, 0))

    for x in (352, 800, 1248):
        for y in (-256, 256):
            L.solid(x - 8, y - 8, 352, x + 8, y + 8, 384, "lamp_amber1")
            L.solid(x - 2, y - 2, 384, x + 2, y + 2, 448, "iron_plate1")
            L.light((x, y, 330), 360, LAMP)
            L.light((x + 16, y, 40), 180, DAMP)
    L.light((864, 0, 400), 300, COLD)

    # The silver door at the east end of the catwalk, and the cage on.
    L.opening(1664, -64, CAT, 1696, 64, CAT + 128)
    L.brush_entity("func_door", [Box(1664, -64, CAT, 1696, 64, CAT + 128, "sluice_wood1")],
                   angle=-1, spawnflags=16, speed=60, wait=-1, lip=8, sounds=2)
    L.solid(1536, -64, CAT - 16, 1664, 64, CAT, "iron_plate1")
    L.room(1696, -96, CAT, 1856, 96, CAT + 192, wall="cist_brick1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((1776, 0, CAT + 160), 160, LAMP)
    L.brush_entity("trigger_changelevel", [Box(1728, -64, CAT, 1824, 64, CAT + 96, "trigger")], map="cisterns4")
    L.add("info_intermission", (100, -440, 380), mangle=(25, 25, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "cisterns3.map")
    build().save(out)
    print(out)
