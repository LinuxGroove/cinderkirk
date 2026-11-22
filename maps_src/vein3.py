#!/usr/bin/env python3
"""The Winding Engine (vein3.map), the Undervein shaft's third map.

The engine house at the head of the mine's main shaft: the winding drum,
the headgear over the shaft, and the cage, which drops when you step in.
At the bottom are the onsetting station and the old workings beyond it,
where the silver key is and the rock runs hot; the silver door on is in
the station's east wall. A cracked wall in the old workings hides the way
to the Lode.

    python3 maps_src/vein3.py maps_src/vein3.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402
from mine import PROP, cart, lamp, rails, timbers  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
HX = 896                            # the engine house's east wall
S0, S1, SY = 928, 1120, 96          # the shaft
BOT = -832                          # the shaft's bottom
CAGE_H = 136


def build():
    L = Level(start_light=190, wad="cinder.wad", light_wait=0.7, sounds=7, message="The Winding Engine", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=12, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, CANDLE)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The engine house: brick, the drum on its plinths, the engine's beam
    # and cylinder, and a rope out to the sheave over the shaft.
    L.room(0, -320, 0, HX, 320, 416, wall="firebrick1", floor="floor_flag1", ceiling="ceil_timber1")
    dx, dz = 400, 176
    for y in (-200, 168):
        L.solid(dx - 80, y, 0, dx + 80, y + 32, dz, "crypt_stone1")
    L.solid(dx - 96, -168, dz - 64, dx + 96, 168, dz + 64, "iron_rust1")
    L.solid(dx - 64, -168, dz - 96, dx + 64, 168, dz + 96, "iron_rust1")
    L.solid(dx - 8, -200, dz - 8, dx + 8, 200, dz + 8, "iron_plate1")
    for y in (-176, 160):
        L.solid(dx - 100, y, dz - 100, dx + 100, y + 16, dz + 100, "iron_plate1")
    L.solid(dx - 4, -60, dz + 96, S1 - 96 + 4, -52, dz + 104, "iron_plate1")        # the rope to the sheave
    L.solid(dx - 4, 52, dz + 96, S1 - 96 + 4, 60, dz + 104, "iron_plate1")
    L.solid(160, -280, 0, 256, -120, 224, "iron_rust1")                            # the engine's cylinder
    L.solid(192, -248, 224, 224, -152, 320, "iron_plate1")
    L.solid(96, -216, 320, 400, -184, 344, PROP)                                    # and its beam
    L.solid(560, -300, 0, 600, -120, 64, "crypt_stone1")
    L.light((dx, 0, 380), 320, CANDLE)
    for x, y in ((120, 240), (120, -40), (640, 240), (640, -240), (820, 0)):
        L.light((x, y, 200), 240, CANDLE)
    L.light((210, -90, 260), 200, EMBER)

    # The shaft, open from the engine house, the headgear's sheave over it.
    L.opening(HX, -64, 0, S0, 64, 144)
    L.room(S0, -SY, BOT, S1, SY, 416, wall="ore_rock1", floor="ore_rock1", ceiling="iron_rust1")
    L.solid(S0, -72, 336, S1, -56, 368, "iron_rust1")
    L.solid(S0, 56, 336, S1, 72, 368, "iron_rust1")
    L.solid(S0 + 80, -72, 344, S0 + 112, 72, 360, "iron_plate1")
    for z in range(-64, BOT, -192):
        L.solid(S0, -SY, z, S0 + 16, SY, z + 16, PROP)
        L.solid(S1 - 16, -SY, z, S1, SY, z + 16, PROP)
        L.light(((S0 + S1) / 2, 0, z + 80), 220, CANDLE)
    L.light(((S0 + S1) / 2, 0, 260), 240, CANDLE)
    # The cage: a floor, corner posts and a roof frame, dropped by stepping in.
    c0, c1, cy = S0 + 16, S1 - 16, SY - 16          # clear of the shaft's timbers
    cage = [Box(c0, -cy, -16, c1, cy, 0, "iron_plate1")]
    for x in (c0, c1 - 8):
        for y in (-cy, cy - 8):
            cage.append(Box(x, y, 0, x + 8, y + 8, CAGE_H - 8, "iron_rust1"))
    for y in (-cy, cy - 8):
        cage.append(Box(c0, y, CAGE_H - 8, c1, y + 8, CAGE_H, "iron_rust1"))
    L.brush_entity("func_door", cage, angle=-2, targetname="cage", speed=110, wait=-1,
                   lip=CAGE_H + 16 - (0 - BOT), sounds=1)
    L.brush_entity("trigger_once", [Box(c0 + 16, -cy + 16, 0, c1 - 16, cy - 16, 64, "trigger")],
                   target="cage", delay=1, message="The cage drops")

    # The onsetting station at the bottom.
    L.opening(S1, -64, BOT, S1 + 32, 64, BOT + 128)
    st0, st1 = S1 + 32, 1632
    L.room(st0, -256, BOT, st1, 256, BOT + 256, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    timbers(L, st0, st1, -256, 256, BOT, 256, every=192)
    rails(L, st0, st1, -96, 96, BOT)
    cart(L, 1300, 0, BOT + 8)
    cart(L, 1480, 0, BOT + 8, full=False)
    for x in (1240, 1560):
        lamp(L, x, -160, BOT + 200)
        lamp(L, x, 160, BOT + 200)

    # North to the old workings.
    L.opening(1216, 256, BOT, 1344, 288, BOT + 128)
    L.room(1200, 288, BOT, 1360, 1088, BOT + 160, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    timbers(L, 1200, 1360, 288, 1088, BOT, 160, axis="y")
    for y in (480, 800):
        lamp(L, 1280, y + 40, BOT + 124)
    L.opening(1216, 1088, BOT, 1344, 1120, BOT + 128)
    W0, W1, WY0, WY1 = 1088, 2048, 1120, 1600
    L.room(W0, WY0, BOT, W1, WY1, BOT + 320, wall="vein_rock1", floor="vein_rock1", ceiling="ore_rock1", floor_depth=64)
    L.opening(1504, WY0 + 64, BOT - 48, 1600, WY1 - 64, BOT)                         # a slag crack across the floor
    L.liquid(1504, WY0 + 64, BOT - 48, 1600, WY1 - 64, BOT - 16, "*lava_slag1")
    L.solid(1488, 1296, BOT - 8, 1616, 1424, BOT + 8, "iron_plate1")
    for y in (1200, 1520):
        L.light((1552, y, BOT + 40), 240, EMBER)
    L.light((1552, 1360, BOT + 260), 320, COLD)
    for x, y in ((1200, 1200), (1200, 1520), (1900, 1200), (1900, 1520)):
        L.light((x, y, BOT + 200), 220, CANDLE)
    for x in (1300, 1820):
        L.solid(x, WY0, BOT, x + 24, WY0 + 24, BOT + 320, PROP)
        L.solid(x, WY1 - 24, BOT, x + 24, WY1, BOT + 320, PROP)
    L.add("item_key1", (W1 - 80, 1360, BOT))

    # The cracked wall at the old workings' north-east, and the way to the Lode.
    L.opening(1888, WY1, BOT, 1952, WY1 + 32, BOT + 96)
    L.brush_entity("func_cracked", [Box(1888, WY1, BOT, 1952, WY1 + 32, BOT + 96, "kirk_crack1")])
    L.room(1856, WY1 + 32, BOT, 1984, WY1 + 288, BOT + 128, wall="vein_rock1", floor="ore_rock1", ceiling="ore_rock1")
    L.brush_entity("trigger_secret", [Box(1864, WY1 + 40, BOT, 1976, WY1 + 120, BOT + 96, "trigger")])
    L.brush_entity("trigger_changelevel", [Box(1856, WY1 + 256, BOT, 1984, WY1 + 288, BOT + 112, "trigger")], map="vein_s")
    L.light((1920, WY1 + 180, BOT + 100), 140, EMBER)

    L.add("monster_ashen", (300, 200, 24), angle=180)
    L.add("monster_ashen", (600, -60, 24), angle=180)
    L.add("monster_censer", (700, 220, 24), angle=180)
    L.add("monster_deacon", (800, -220, 24), angle=180)
    L.add("monster_clinker", (400, 0, 400), angle=180, spawnflags=2)
    L.add("monster_crucible_brute", (1450, -160, BOT + 24), angle=180)
    L.add("monster_censer", (1560, 160, BOT + 24), angle=180)
    L.add("monster_clinker", (1280, 700, BOT + 150), angle=270, spawnflags=2)
    L.add("monster_bell_ringer", (1800, 1360, BOT + 24), angle=180)
    L.add("monster_gauger", (1200, 1520, BOT + 24), angle=0)
    L.add("monster_ashen", (1300, 1260, BOT + 24), angle=0)
    L.add("monster_clinker", (1700, 1360, BOT + 300), angle=180, spawnflags=2)

    L.add("item_shells", (100, 240, 0))
    L.add("item_health", (820, 240, 0))
    L.add("item_rockets", (820, -240, 0))
    L.add("item_health", (1220, -200, BOT))
    L.add("item_spikes", (1280, 1000, BOT))
    L.add("item_health", (1150, 1180, BOT))
    L.add("item_cells", (1980, 1540, BOT))
    L.add("item_armor1", (1980, 1180, BOT))

    # The silver door in the station's east wall, and on.
    L.opening(st1, -64, BOT, st1 + 32, 64, BOT + 128)
    L.brush_entity("func_door", [Box(st1, -64, BOT, st1 + 32, 64, BOT + 128, "door_iron1")],
                   angle=-1, spawnflags=16, speed=60, wait=-1, lip=8, sounds=2)
    L.room(st1 + 32, -96, BOT, st1 + 192, 96, BOT + 192, wall="ore_rock1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((st1 + 112, 0, BOT + 160), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(st1 + 64, -64, BOT, st1 + 160, 64, BOT + 96, "trigger")], map="vein4")
    L.add("info_intermission", (60, 280, 360), mangle=(25, -30, 0))
    L.nook(2048, 1488, -832, "e", ('item_health', 'item_rockets'), wall="ore_rock1", floor="ore_rock1")   # a secret behind cracked stone
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "vein3.map")
    build().save(out)
    print(out)
