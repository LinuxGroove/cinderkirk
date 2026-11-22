#!/usr/bin/env python3
"""The Hot Workings (vein4.map), the Undervein shaft's fourth map.

Down where the vein meets the pit's heat: a hall split by a river of slag
that broke in from below, crossed on the stones left standing in it. The
gold key is on the high working along the far side's north wall; the gold
door down to the Founder is in the east wall.

    python3 maps_src/vein4.py maps_src/vein4.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402
from mine import PROP, lamp, rails, timbers  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
H0, H1, HY = 800, 2048, 640         # the hall
R0, R1 = 1280, 1536                 # the slag river
LEDGE = 256


def build():
    L = Level(wad="cinder.wad", light_wait=0.8, sounds=7, message="The Hot Workings", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=10, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, CANDLE)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The hot drift in.
    L.room(0, -112, 0, H0 - 32, 112, 176, wall="vein_rock1", floor="ore_rock1", ceiling="ore_rock1")
    timbers(L, 0, H0 - 32, -112, 112, 0, 176, every=192)
    rails(L, 0, H0 - 32, -112, 112)
    for x in (200, 560):
        lamp(L, x, 0, 140)
    L.opening(H0 - 32, -64, 0, H0, 64, 128)

    # The hall and the river across it, with stones standing in the slag.
    L.room(H0, -HY, 0, H1, HY, 512, wall="vein_rock1", floor="ore_rock1", ceiling="ore_rock1", floor_depth=64)
    L.opening(R0, -HY, -48, R1, HY, 0)
    L.liquid(R0, -HY, -48, R1, HY, -16, "*lava_slag1")
    for x, y in ((1312, -96), (1424, -16), (1472, 112), (1360, 216), (1440, 340)):
        L.solid(x - 40, y - 40, -48, x + 40, y + 40, 0, "ore_rock1")
    for y in range(-HY + 96, HY, 256):
        L.light(((R0 + R1) / 2, y, 40), 300, EMBER)
    # Burned timbers where a bridge stood.
    L.solid(R0 - 16, -280, -8, R0 + 48, -232, 8, PROP)
    L.solid(R1 - 64, -248, -24, R1 + 16, -216, 0, PROP)

    # The far side: steps up to the high working on the north wall, with
    # the gold key at its west end, over the river.
    L.steps(H1 - 320, HY - 160, H1 - 32, HY, LEDGE, 0, axis="x", tex="ore_rock1")
    L.solid(R0 + 64, HY - 160, LEDGE - 16, H1 - 320, HY, LEDGE, PROP)
    L.solid(R0 + 64, HY - 168, LEDGE, H1 - 320, HY - 160, LEDGE + 36, "iron_rust1")
    for x in range(R0 + 128, H1 - 320, 192):
        L.solid(x, HY - 168, 0 if x > R1 else -48, x + 16, HY - 152, LEDGE - 16, PROP)
    L.add("item_key2", (R0 + 112, HY - 80, LEDGE))
    for x in (1500, 1800):
        lamp(L, x, HY - 80, LEDGE + 160)

    for x, y in ((900, -500), (900, 500), (1100, 0), (1700, -500), (1950, -200), (1700, 0)):
        L.light((x, y, 220), 260, CANDLE)
    L.light((1100, -300, 420), 340, COLD)
    L.light((1800, -300, 420), 340, COLD)

    L.add("monster_bell_ringer", (1050, -300, 24), angle=0)
    L.add("monster_bell_ringer", (1800, -350, 24), angle=180)
    L.add("monster_crucible_brute", (1900, 200, 24), angle=180)
    L.add("monster_censer", (1700, HY - 80, LEDGE + 24), angle=180)
    L.add("monster_gauger", (1300, HY - 80, LEDGE + 24), angle=270)
    L.add("monster_deacon", (1000, 450, 24), angle=0)
    L.add("monster_ashen", (950, 250, 24), angle=0)
    L.add("monster_ashen", (1100, 350, 24), angle=0)
    L.add("monster_ashen", (1150, -500, 24), angle=0)
    L.add("monster_clinker", (1408, 0, 480), angle=180, spawnflags=2)
    L.add("monster_clinker", (1700, 300, 480), angle=180, spawnflags=2)
    L.add("monster_clinker", (500, 0, 150), angle=180, spawnflags=2)

    L.add("item_shells", (300, 80, 0))
    L.add("item_health", (H0 + 64, -HY + 64, 0))
    L.add("item_rockets", (H0 + 64, HY - 64, 0))
    L.add("item_health", (1700, -HY + 64, 0))
    L.add("item_cells", (H1 - 64, -HY + 64, 0))
    L.add("item_armor2", (1600, HY - 80, LEDGE))
    L.add("item_spikes", (1950, 0, 0))

    # The gold door in the east wall, and the way down to the Founder.
    L.opening(H1, -64, 0, H1 + 32, 64, 128)
    L.brush_entity("func_door", [Box(H1, -64, 0, H1 + 32, 64, 128, "door_iron1")],
                   angle=-1, spawnflags=8, speed=60, wait=-1, lip=8, sounds=2)
    L.room(H1 + 32, -96, 0, H1 + 192, 96, 192, wall="vein_rock1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((H1 + 112, 0, 160), 160, EMBER)
    L.brush_entity("trigger_changelevel", [Box(H1 + 64, -64, 0, H1 + 160, 64, 96, "trigger")], map="vein5")
    L.add("info_intermission", (H0 + 60, -HY + 60, 440), mangle=(25, 30, 0))
    L.nook(2048, -528, 0, "e", ('item_armor2', 'item_rockets'), wall="ore_rock1", floor="ore_rock1")   # a secret behind cracked stone
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "vein4.map")
    build().save(out)
    print(out)
