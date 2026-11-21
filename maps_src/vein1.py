#!/usr/bin/env python3
"""The Adit (vein1.map), the first map of the Undervein shaft.

Where the Founder's men drove into the hill for the bell's iron: a timbered
drift with the ore rails still in it, opening on the ore hall where the
tubs were tipped. The silver key is on the tipple along the hall's north
wall; the silver door to the decline is in the south wall.

    python3 maps_src/vein1.py maps_src/vein1.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402
from mine import cart, lamp, rails, timbers  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
AX = 1152                           # the adit's east end
H0, H1, HY = 1184, 2048, 576        # the ore hall
TIP = 224                           # the tipple's deck
PROP = "mine_prop1"


def build():
    L = Level(wad="cinder.wad", message="The Adit", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=12, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, CANDLE)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The adit: a long timbered drift with the rails down it.
    L.room(0, -112, 0, AX, 112, 176, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    timbers(L, 0, AX, -112, 112, 0, 176)
    rails(L, 0, AX, -112, 112)
    cart(L, 560, 0)
    for x in range(128, AX, 320):
        lamp(L, x + 72, 0, 140)
    L.opening(AX, -80, 0, H0, 80, 144)

    # The ore hall: a broad working with chutes from the roof, the rails
    # across its floor and the tipple along the north wall.
    L.room(H0, -HY, 0, H1, HY, 448, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    rails(L, H0, H1, -112, 112)
    cart(L, 1400, 0)
    cart(L, 1760, 0, full=False)
    L.solid(H0, HY - 224, TIP - 16, H1, HY, TIP, PROP)
    for x in range(H0 + 96, H1, 192):
        L.solid(x, HY - 224, 0, x + 24, HY - 200, TIP - 16, PROP)               # the tipple's legs
    L.solid(H0 + 224, HY - 232, TIP, H1, HY - 224, TIP + 40, "iron_rust1")      # its rail
    L.steps(H0, HY - 224 - 96, H0 + 224, HY - 224, 0, TIP, axis="x", tex=PROP)
    # Chutes from the tipple down to the floor bins, and heaps of ore.
    for x in (1440, 1824):
        L.solid(x - 48, HY - 224 - 64, 96, x + 48, HY - 224, 112, "iron_rust1")
        L.solid(x - 48, HY - 224 - 64, 112, x - 40, HY - 224, 160, "iron_rust1")
        L.solid(x + 40, HY - 224 - 64, 112, x + 48, HY - 224, 160, "iron_rust1")
        for i in range(3):
            k = 96 - i * 28
            L.solid(x - k, HY - 224 - 96 - k, 0, x + k, HY - 224 - 96 + k * 0.6, 16 * (i + 1), "ore_rock1")
    for x, y, r in ((1360, -380, 120), (1880, -300, 90)):
        for i in range(3):
            k = r * (1 - i / 3)
            L.solid(x - k, y - k * 0.8, 0, x + k, y + k * 0.8, 20 * (i + 1), "ore_rock1")
    for x in range(H0 + 160, H1, 320):
        L.solid(x, -HY, 0, x + 24, -HY + 24, 448, PROP)
        L.solid(x, HY - 24, TIP, x + 24, HY, 448, PROP)
        lamp(L, x + 12, HY - 120, TIP + 150)
        lamp(L, x + 12, -HY + 80, 200)
    L.add("item_key1", (H1 - 96, HY - 112, TIP))

    L.light((1600, 0, 380), 260, COLD)
    L.light((1600, 0, 200), 380, CANDLE)
    L.light((1400, -380, 120), 200, EMBER)

    L.add("monster_ashen", (420, 40, 24), angle=180)
    L.add("monster_ashen", (780, -40, 24), angle=180)
    L.add("monster_clinker", (980, 0, 150), angle=180, spawnflags=2)
    L.add("monster_censer", (1500, HY - 112, TIP + 24), angle=180)
    L.add("monster_gauger", (1900, HY - 112, TIP + 24), angle=180)
    L.add("monster_crucible_brute", (1800, -280, 24), angle=180)
    L.add("monster_ashen", (1500, -200, 24), angle=180)
    L.add("monster_ashen", (1700, 200, 24), angle=180)
    L.add("monster_deacon", (1950, -450, 24), angle=180)
    L.add("monster_clinker", (1600, -300, 420), angle=180, spawnflags=2)

    L.add("item_shells", (300, 80, 0))
    L.add("item_health", (900, -80, 0))
    L.add("item_spikes", (H0 + 96, -HY + 64, 0))
    L.add("item_health", (1300, HY - 112, TIP))
    L.add("item_rockets", (H1 - 64, -HY + 64, 0))
    L.add("item_armor1", (1600, HY - 112, TIP))

    # The silver door in the south wall, and the decline down from it.
    D0, D1 = 1536, 1664
    L.opening(D0, -HY - 32, 0, D1, -HY, 128)
    L.brush_entity("func_door", [Box(D0, -HY - 32, 0, D1, -HY, 128, "door_iron1")],
                   angle=-1, spawnflags=16, speed=60, wait=-1, lip=8, sounds=2)
    L.room(D0 - 32, -1216, -256, D1 + 32, -HY - 32, 176, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    L.solid(D0 - 32, -HY - 96, -256, D1 + 32, -HY - 32, 0, "ore_rock1")
    L.steps(D0 - 32, -1024, D1 + 32, -HY - 96, -256, 0, axis="y", tex="ore_rock1")
    timbers(L, D0 - 32, D1 + 32, -1216, -HY - 32, -256, 176 + 256, every=192, axis="y")
    lamp(L, 1600, -760, 120)
    lamp(L, 1600, -1120, -110)
    L.add("monster_censer", (1600, -1120, -232), angle=90)
    L.add("item_health", (1560, -1160, -256))

    L.opening(D0, -1248, -256, D1, -1216, -128)
    L.room(D0 - 16, -1408, -256, D1 + 16, -1248, -64, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    L.light((1600, -1328, -96), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(D0, -1400, -256, D1, -1300, -160, "trigger")], map="vein2")
    L.add("info_intermission", (1250, -500, 380), mangle=(25, 30, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "vein1.map")
    build().save(out)
    print(out)
