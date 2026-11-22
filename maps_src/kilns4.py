#!/usr/bin/env python3
"""The Sorting House (kilns4.map), the Ossuary Kilns shaft's fourth map.

Where the bones were sorted for the kilns: a broad hall of long tables
under a bell tower, and the first bell-ringer, who tolls the floor. The
sorting stages round the walls stand clear of the floor, so the toll passes
under anyone on them. The gold key is caged under the bell tower; pull the
chain on each stage to haul the cage up.

    python3 maps_src/kilns4.py maps_src/kilns4.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
X1, Y = 1536, 768
STAGE = 64                          # the stages' height: well clear of a toll
STAGES = ((96, -672, 416, -480), (1120, -672, 1440, -480), (96, 480, 416, 672), (1120, 480, 1440, 672))


def build():
    L = Level(start_light=240, wad="cinder.wad", light_wait=0.8, sounds=6, message="The Sorting House", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=14, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, CANDLE)
    L.opening(-32, -64, 0, 0, 64, 128)

    L.room(0, -Y, 0, X1, Y, 512, wall="kiln_brick1", floor="floor_flag1", ceiling="ceil_timber1")
    # The bell tower in the middle: four piers and a cage hung between them.
    L.room(576, -192, 512, 960, 192, 896, wall="ossuary1", floor="ceil_timber1", ceiling="ceil_timber1")
    L.opening(576, -192, 480, 960, 192, 544)
    for x in (576, 928):
        for y in (-192, 160):
            L.solid(x, y, 0, x + 32, y + 32, 896, "crypt_stone1")
    # The sorting stages in the corners, each with a step up and a chain.
    for i, (x0, y0, x1, y1) in enumerate(STAGES):
        L.solid(x0, y0, 0, x1, y1, STAGE, "oak1")
        if y0 < 0:
            L.steps(x0 + 96, y1, x0 + 224, y1 + 64, STAGE, 0, axis="y", tex="oak1")
        else:
            L.steps(x0 + 96, y0 - 64, x0 + 224, y0, 0, STAGE, axis="y", tex="oak1")
        wy = -Y if y0 < 0 else Y - 12
        L.brush_entity("func_button", [Box(x0 + 136, wy, STAGE + 40, x0 + 184, wy + 12, STAGE + 104, "iron_rust1")],
                       angle=270 if y0 < 0 else 90, target="chains", wait=-1, lip=4,
                       message="A chain runs out over the pulley")
        L.light((x0 + 160, wy + (60 if y0 < 0 else -48), STAGE + 140), 160, CANDLE)
    L.add("trigger_counter", None, targetname="chains", count=4, spawnflags=1,
          target="cage", message="The bell tower's cage lifts into the tower")
    # The cage of bars under the tower, with the gold key in it; the chains
    # haul it up into the tower.
    cage = []
    for i in range(5):
        for x0, y0 in ((704 + i * 28, -72), (704 + i * 28, 64), (696, -64 + i * 28), (824, -64 + i * 28)):
            cage.append(Box(x0, y0, 0, x0 + 8, y0 + 8, 128, "iron_rust1"))
    cage.append(Box(696, -72, 128, 832, 72, 144, "iron_rust1"))
    L.brush_entity("func_door", cage, angle=-1, targetname="cage", speed=80, wait=-1, lip=-256, sounds=1)
    L.add("item_key2", (768, 0, 8), target="ash_wakes")
    L.solid(704, -64, 0, 832, 64, 8, "kirk_trim1")

    # Long tables down the floor, between the stages.
    for x in (320, 1216):
        for y in (-256, 0, 256):
            L.solid(x - 112, y - 32, 0, x + 112, y + 32, 40, "oak1")

    for x0, y0, x1, y1 in STAGES:
        L.light(((x0 + x1) / 2, (y0 + y1) / 2, 200), 260, CANDLE)
    for x in (300, 1236):
        L.light((x, 0, 300), 380, CANDLE)
    for x in range(192, X1, 384):
        for y in (-Y + 48, Y - 48):
            L.light((x, y, 260), 300, CANDLE)
    for y in (-400, 0, 400):
        L.light((48, y, 260), 300, CANDLE)
        L.light((X1 - 48, y, 260), 300, CANDLE)
    for y in (-360, 360):
        L.light((768, y, 300), 320, CANDLE)
    L.light((768, 0, 840), 400, COLD)
    L.light((768, 0, 420), 300, EMBER)

    L.add("monster_bell_ringer", (768, -420, 24), angle=180)
    L.add("monster_ash_wraith", (300, -400, 300), angle=0)
    L.add("monster_ash_wraith", (1200, 400, 300), angle=180)
    L.add("monster_censer", (256, -576, STAGE + 24), angle=0)
    L.add("monster_censer", (1280, 576, STAGE + 24), angle=180)
    L.add("monster_gauger", (1280, -576, STAGE + 24), angle=90)
    L.add("monster_ashen", (1000, -400, 24), angle=180)
    L.add("monster_ashen", (1000, 400, 24), angle=180)

    L.add("item_health", (200, -620, STAGE))
    L.add("item_shells", (300, 620, STAGE))
    L.add("item_rockets", (1240, -620, STAGE))
    L.add("item_health", (1340, 620, STAGE))
    L.add("item_spikes", (100, 0, 0))
    L.add("item_armor2", (1480, 0, 0))

    # The gold door at the east end, and the cage on.
    L.opening(X1, -64, 0, X1 + 32, 64, 128)
    L.brush_entity("func_door", [Box(X1, -64, 0, X1 + 32, 64, 128, "door_iron1")],
                   angle=-1, spawnflags=8, speed=60, wait=-1, lip=8, sounds=2)
    L.room(X1 + 32, -96, 0, X1 + 192, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((X1 + 112, 0, 160), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(X1 + 64, -64, 0, X1 + 160, 64, 96, "trigger")], map="kilns5")
    L.add("info_intermission", (100, -700, 400), mangle=(25, 40, 0))
    L.nook(1536, 656, 0, "e", ('item_armor2', 'item_cells'), wall="crypt_stone1", floor="crypt_stone1")   # a secret behind cracked stone
    # Taking the key wakes the dead lying in the ash round it.
    L.add("monster_ashen", (589, -68, 0 + 24), angle=21, spawnflags=64, targetname="ash_wakes")
    L.add("monster_ashen", (689, -175, 0 + 24), angle=66, spawnflags=64, targetname="ash_wakes")
    L.add("monster_ashen", (836, -179, 0 + 24), angle=111, spawnflags=64, targetname="ash_wakes")
    L.add("monster_ashen", (943, -79, 0 + 24), angle=156, spawnflags=64, targetname="ash_wakes")
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "kilns4.map")
    build().save(out)
    print(out)
