#!/usr/bin/env python3
"""The Stopes (vein2.map), the Undervein shaft's second map.

Where the ore was cut upward from the drifts until whole chambers stood
hollow in the hill: a tall stope staged with timber, the gold key on its
top stage, then a haulage way to the deeper stope, where the rock runs hot
and slag has pooled in the floor. The gold door is at the deep stope's
far end.

    python3 maps_src/vein2.py maps_src/vein2.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402
from mine import PROP, cart, lamp, rails, timbers  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
A0, A1, AY = 672, 1376, 384         # the first stope
S1, S2 = 192, 400                   # its two stages
B0, B1, BY = 2016, 2656, 448        # the deep stope
BF = -256                           # its floor


def build():
    L = Level(wad="cinder.wad", sounds=7, message="The Stopes", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=12, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, CANDLE)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The crosscut in.
    L.room(0, -96, 0, 640, 96, 160, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    timbers(L, 0, 640, -96, 96, 0, 160)
    rails(L, 0, 640, -96, 96)
    for x in (160, 480):
        lamp(L, x, 0, 126)
    L.opening(640, -64, 0, A0, 64, 128)

    # The first stope: tall, with a stage on the south side, a walkway
    # across the west end and a top stage on the north side.
    L.room(A0, -AY, 0, A1, AY, 640, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    L.solid(A0, -AY, S1 - 16, 1152, -192, S1, PROP)
    L.steps(1152, -AY, A1, -192, S1, 0, axis="x", tex=PROP)
    L.solid(A0, -192, S1 - 16, 768, 192, S1, PROP)
    L.steps(A0, 192, 896, AY, S1, S2, axis="x", tex=PROP, base=S1 - 16)
    L.solid(896, 192, S2 - 16, A1, AY, S2, PROP)
    L.solid(768, -192, S1, 776, 192, S1 + 36, "iron_rust1")                 # the walkway's rail
    L.solid(896, 184, S2, A1, 192, S2 + 36, "iron_rust1")                    # the top stage's
    for x in range(A0 + 96, 1152, 192):
        L.solid(x, -200, 0, x + 16, -184, S1 - 16, PROP)
    for x in range(960, A1, 160):
        L.solid(x, 184, 0, x + 16, 200, S2 - 16, PROP)
    for y in (-160, 0, 160):
        L.solid(752, y, 0, 768, y + 16, S1 - 16, PROP)
    # Stulls wedged across the stope's upper reaches.
    for x, z in ((900, 520), (1180, 460), (1040, 580)):
        L.solid(x, -AY, z, x + 24, AY, z + 24, PROP)
    L.add("item_key2", (A1 - 64, 288, S2))
    for x in (800, 1100):
        lamp(L, x, -288, S1 + 120)
        lamp(L, x + 200, 288, S2 + 120)
    L.light((1024, 0, 560), 300, COLD)
    L.light((1024, 0, 140), 320, CANDLE)
    L.light((720, 0, S1 + 110), 200, CANDLE)

    # The haulage way to the deep stope.
    L.opening(A1, -64, 0, A1 + 32, 64, 128)
    L.room(A1 + 32, -96, 0, B0 - 32, 96, 160, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    timbers(L, A1 + 32, B0 - 32, -96, 96, 0, 160)
    rails(L, A1 + 32, B0 - 32, -96, 96)
    cart(L, 1700, 0)
    for x in (1520, 1840):
        lamp(L, x, 0, 126)
    L.opening(B0 - 32, -64, 0, B0, 64, 128)

    # The deep stope: a ledge at the haulage's level, a stair down the
    # south side, and slag pooled in the floor where the rock runs hot.
    L.room(B0, -BY, BF, B1, BY, 384, wall="vein_rock1", floor="vein_rock1", ceiling="ore_rock1", floor_depth=64)
    L.solid(B0, -BY, BF, B0 + 192, BY, 0, "ore_rock1")
    L.solid(B0 + 184, -BY + 160, 0, B0 + 192, BY, 36, "iron_rust1")
    L.steps(B0 + 192, -BY, B0 + 448, -BY + 160, 0, BF, axis="x", tex=PROP)
    L.opening(2304, -192, BF - 48, 2560, 192, BF)
    L.liquid(2304, -192, BF - 48, 2560, 192, BF - 16, "*lava_slag1")
    for x in (2304, 2560):
        L.light((x, 0, BF + 40), 260, EMBER)
    L.light((2432, -300, BF + 40), 220, EMBER)
    L.light((2432, 300, BF + 40), 220, EMBER)
    L.light((2336, 0, 300), 360, COLD)
    for y in (-300, 300):
        lamp(L, B0 + 96, y, 140)
    lamp(L, B1 - 64, -200, BF + 160)
    lamp(L, B1 - 64, 200, BF + 160)

    L.add("monster_ashen", (300, 40, 24), angle=180)
    L.add("monster_ashen", (900, 100, 24), angle=180)
    L.add("monster_ashen", (1200, -60, 24), angle=180)
    L.add("monster_censer", (900, -288, S1 + 24), angle=90)
    L.add("monster_gauger", (1250, 288, S2 + 24), angle=180)
    L.add("monster_deacon", (1300, 100, 24), angle=180)
    L.add("monster_clinker", (1000, 0, 620), angle=180, spawnflags=2)
    L.add("monster_clinker", (1800, 0, 140), angle=180, spawnflags=2)
    L.add("monster_crucible_brute", (2400, -330, BF + 24), angle=180)
    L.add("monster_bell_ringer", (2560, 320, BF + 24), angle=180)
    L.add("monster_censer", (B0 + 96, 200, 24), angle=0)
    L.add("monster_clinker", (2432, 0, 360), angle=180, spawnflags=2)

    L.add("item_shells", (400, -60, 0))
    L.add("item_health", (A0 + 64, -300, 0))
    L.add("item_spikes", (A0 + 48, 0, S1))
    L.add("item_health", (1000, 288, S2))
    L.add("item_rockets", (1900, 60, 0))
    L.add("item_health", (B0 + 96, -300, 0))
    L.add("item_armor2", (B1 - 64, -380, BF))
    L.add("item_cells", (B1 - 64, 380, BF))

    # The gold door at the far end of the deep stope's floor.
    L.opening(B1, -64, BF, B1 + 32, 64, BF + 128)
    L.brush_entity("func_door", [Box(B1, -64, BF, B1 + 32, 64, BF + 128, "door_iron1")],
                   angle=-1, spawnflags=8, speed=60, wait=-1, lip=8, sounds=2)
    L.room(B1 + 32, -96, BF, B1 + 192, 96, BF + 192, wall="ore_rock1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((B1 + 112, 0, BF + 160), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(B1 + 64, -64, BF, B1 + 160, 64, BF + 96, "trigger")], map="vein3")
    L.add("info_intermission", (A0 + 60, -330, 560), mangle=(25, 30, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "vein2.map")
    build().save(out)
    print(out)
