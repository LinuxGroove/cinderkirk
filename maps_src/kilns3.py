#!/usr/bin/env python3
"""The Ash Galleries (kilns3.map), the Ossuary Kilns shaft's third map.

The store where the kilns' bone ash was kept until the Deacons wanted it: a
tall hall with three galleries round the walls, heaps of ash on the floor,
and the wraiths that rose out of them filling the space between. The
silver key is at the top, on the west gallery; the silver door out is at
the bottom, in the east wall, so the quick way back down is the drop. A
cracked wall on the middle gallery hides the way to the Reliquary.

    python3 maps_src/kilns3.py maps_src/kilns3.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
X1, Y = 1280, 640
D = 128                               # a gallery's depth
TIERS = (192, 384, 576)
# Where each stair climbs, so the deck above leaves a hole for it.
HOLES = {192: ("s", 256, 640), 384: ("n", 640, 1024), 576: ("s", 640, 1024)}


def deck(L, z, hole):
    side, h0, h1 = hole
    for s, y0, y1 in (("s", -Y, -Y + D), ("n", Y - D, Y)):
        spans = [(0, X1)] if s != side else [(0, h0), (h1, X1)]
        for x0, x1 in spans:
            L.solid(x0, y0, z - 16, x1, y1, z, "iron_plate1")
            L.solid(x0, y0 + (D - 8 if s == "s" else 0), z, x1, y0 + (D if s == "s" else 8), z + 32, "brass_trim1")
    for x0, x1 in ((0, D), (X1 - D, X1)):
        L.solid(x0, -Y + D, z - 16, x1, Y - D, z, "iron_plate1")
        rx = x1 - 8 if x0 == 0 else x0
        L.solid(rx, -Y + D, z, rx + 8, Y - D, z + 32, "brass_trim1")


def build():
    L = Level(wad="cinder.wad", light_wait=0.6, sounds=6, message="The Ash Galleries", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=12, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, CANDLE)
    L.opening(-32, -64, 0, 0, 64, 128)

    L.room(0, -Y, 0, X1, Y, 800, wall="kiln_brick1", floor="ash_floor1", ceiling="ceil_timber1")
    for z in TIERS:
        deck(L, z, HOLES[z])
    # The stairs: south wall to the first gallery, north to the second,
    # south again to the third.
    L.steps(256, -Y, 640, -Y + D, 0, 192, axis="x", tex="crypt_stone1", base=0)
    L.steps(640, Y - D, 1024, Y, 384, 192, axis="x", tex="crypt_stone1", base=176)
    L.steps(640, -Y, 1024, -Y + D, 384, 576, axis="x", tex="crypt_stone1", base=368)
    # Piers holding the galleries up, and the ash heaps on the floor.
    for x in (D, X1 - D):
        for y in (-Y + D, Y - D):
            L.solid(x - 16, y - 16, 0, x + 16, y + 16, 800, "crypt_stone1")
    for x, y, r, h in ((400, -160, 160, 64), (760, 180, 200, 96), (980, -220, 140, 48), (420, 260, 120, 40)):
        for i in range(4):
            k = r * (1 - i / 4)
            L.solid(x - k, y - k * 0.8, 0, x + k, y + k * 0.8, h * (i + 1) / 4, "ash_floor1")
    # Hoppers hung from the roof over the heaps.
    for x, y in ((400, -160), (760, 180), (980, -220)):
        L.solid(x - 64, y - 64, 704, x + 64, y + 64, 768, "iron_rust1")
        L.solid(x - 24, y - 24, 656, x + 24, y + 24, 704, "iron_rust1")
        L.solid(x - 4, y - 4, 768, x + 4, y + 4, 800, "iron_plate1")

    L.add("item_key1", (64, 0, 576), target="ash_wakes")
    for z in TIERS:
        for x, y in ((64, -400), (64, 400), (X1 - 64, -400), (X1 - 64, 400)):
            L.light((x, y, z + 96), 240, CANDLE)
        for x in range(320, X1 - 160, 320):
            for y in (-Y + 64, Y - 64):
                if z == 384 and y < 0 and 640 <= x <= 1024:
                    continue                                    # inside the top stair
                L.light((x, y, z + 110), 240, CANDLE)
    for x in range(320, X1 - 160, 320):
        for y in (-Y + 64, Y - 64):
            L.light((x, y, 110), 240, CANDLE)
    for x, y in ((400, -160), (760, 180), (980, -220)):
        L.light((x, y, 120), 220, EMBER)
    L.light((640, 0, 740), 500, COLD)
    L.light((640, 0, 400), 360, CANDLE)

    # The congregation: ash wraiths all through the hall, keepers on the galleries.
    for x, y, z in ((400, -160, 300), (760, 180, 420), (980, -220, 560), (640, 0, 200), (300, 300, 500)):
        L.add("monster_ash_wraith", (x, y, z), angle=180)
    L.add("monster_ashen", (600, 300, 24), angle=180)
    L.add("monster_ashen", (900, -300, 24), angle=180)
    L.add("monster_censer", (1200, 0, 216), angle=180)
    L.add("monster_gauger", (64, 300, 408), angle=0)
    L.add("monster_censer", (1200, 400, 600), angle=180)
    L.add("monster_deacon", (100, -300, 600), angle=0)
    L.add("monster_clinker", (640, 576, 790), spawnflags=2)

    L.add("item_shells", (64, -300, 192))
    L.add("item_health", (X1 - 64, 300, 192))
    L.add("item_rockets", (X1 - 64, -300, 384))
    L.add("item_health", (64, 300, 384))
    L.add("item_cells", (X1 - 64, 0, 576))
    L.add("item_health", (300, -560, 576))
    L.add("weapon_lightning", (64, 200, 576))

    # The cracked wall on the middle gallery's north side, and the way to
    # the Reliquary behind it.
    L.opening(224, Y, 384, 288, Y + 32, 480)
    L.brush_entity("func_cracked", [Box(224, Y, 384, 288, Y + 32, 480, "kirk_crack1")])
    L.room(192, Y + 32, 384, 320, Y + 256, 544, wall="ossuary1", floor="crypt_stone1", ceiling="crypt_stone1")
    L.brush_entity("trigger_secret", [Box(200, Y + 40, 384, 312, Y + 120, 480, "trigger")])
    L.brush_entity("trigger_changelevel", [Box(192, Y + 224, 384, 320, Y + 256, 512, "trigger")], map="kilns_s")
    L.light((256, Y + 160, 500), 140, EMBER)

    # The silver door at the bottom of the east wall, and the cage on.
    L.opening(X1, -64, 0, X1 + 32, 64, 128)
    L.brush_entity("func_door", [Box(X1, -64, 0, X1 + 32, 64, 128, "door_iron1")],
                   angle=-1, spawnflags=16, speed=60, wait=-1, lip=8, sounds=2)
    L.room(X1 + 32, -96, 0, X1 + 192, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((X1 + 112, 0, 160), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(X1 + 64, -64, 0, X1 + 160, 64, 96, "trigger")], map="kilns4")
    L.add("info_intermission", (1100, -500, 700), mangle=(30, 150, 0))
    L.nook(1280, 528, 0, "e", ('item_armor1', 'item_cells'), wall="crypt_stone1", floor="crypt_stone1")   # a secret behind cracked stone
    # Taking the key wakes the dead lying in the ash round it.
    L.add("monster_ashen", (58, -192, 576 + 24), angle=88, spawnflags=64, targetname="ash_wakes")
    L.add("monster_ashen", (21, 285, 576 + 24), angle=279, spawnflags=64, targetname="ash_wakes")
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "kilns3.map")
    build().save(out)
    print(out)
