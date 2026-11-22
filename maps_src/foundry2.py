#!/usr/bin/env python3
"""The Moulding Floor (foundry2.map), the Foundry shaft's second map.

The cage from the Foundry Gate's belfry lands you at the west end of the
moulding floor: a long hall of sand with moulds rammed into it, walkways
along both sides and an overhead crane. Off the north walkway is the core
shop, with the gold key up on its mezzanine; the gold door at the east end
of the floor opens on the drying ovens, where a vent throws you up to a
hidden ledge, and past them the cage down to the furnaces.

    python3 maps_src/foundry2.py maps_src/foundry2.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

WARM = (1.0, 0.62, 0.32)
SLAG = (1.0, 0.42, 0.12)
COLD = (0.62, 0.72, 1.0)
CANDLE = (1.0, 0.8, 0.55)


def build():
    L = Level(start_light=190, wad="cinder.wad", light_wait=0.8, sounds=4, message="The Moulding Floor", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    # The cage's landing, and a passage east.
    L.room(0, -128, 0, 256, 128, 192, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (64, 0, 24), angle=0)
    L.add("info_player_coop", (64, 64, 24), angle=0)
    L.add("info_player_coop", (64, -64, 24), angle=0)
    L.light((128, 0, 160), 200, WARM)
    L.opening(256, -64, 0, 288, 64, 128)
    L.room(288, -64, 0, 384, 64, 128, wall="kirk_brick1", ceiling="ceil_timber1")
    L.opening(384, -64, 0, 416, 64, 128)
    L.add("item_shells", (300, 20, 0))
    L.light((336, 0, 100), 140, CANDLE)

    # The moulding floor: x 416..1664, y -448..448, sand at -128, roof 384.
    L.room(416, -448, -128, 1664, 448, 384, wall="kirk_brick1", floor="sand_mould1",
           ceiling="ceil_timber1", floor_depth=64)
    for y0, y1 in ((-448, -320), (320, 448)):                     # the walkways, iron on top
        L.solid(416, y0, -128, 1664, y1, -8, "kirk_stone1")
        L.solid(416, y0, -8, 1664, y1, 0, "iron_plate1")
        ry = y1 if y0 < 0 else y0 - 8                             # and their rails
        for x in range(416, 1664, 96):
            L.solid(x, ry, 0, x + 8, ry + 8, 40, "iron_rust1")
        L.solid(416, ry, 40, 1664, ry + 8, 48, "iron_rust1")
    L.solid(416, -128, -128, 544, 128, -8, "kirk_stone1")           # the landing from the passage
    L.solid(416, -128, -8, 544, 128, 0, "iron_plate1")
    L.steps(544, -64, 672, 64, 0, -128, base=-128)
    for x0 in (1536,):                                              # steps back up at the far end
        L.steps(x0, -320, x0 + 128, -256, -128, 0, axis="x", base=-128)
    L.solid(1536, 256, -128, 1664, 320, 0, "kirk_stone1")
    # Moulds rammed into the floor, a hand deep, and moulding boxes.
    for x in (736, 928, 1120, 1312):
        for y0 in (-224, 96):
            L.opening(x, y0, -160, x + 96, y0 + 128, -128)
    for x, y in ((832, -40), (1024, 30), (1216, -60), (1408, 20)):
        L.solid(x, y, -128, x + 64, y + 48, -112, "oak1")
        L.solid(x + 4, y + 4, -112, x + 60, y + 44, -110, "sand_mould1")
    # The crane: rails along the walls, its bridge and a ladle on a chain.
    for y in (-312, 304):
        L.solid(416, y, 304, 1664, y + 8, 320, "iron_rust1")
    L.solid(992, -312, 288, 1040, 312, 320, "iron_rust1")
    L.solid(1012, -4, 176, 1020, 4, 288, "iron_plate1")
    L.solid(984, -28, 128, 1048, 28, 176, "bronze1")
    for x in (640, 1024, 1408):                                    # the roof's tie beams
        L.solid(x - 16, -448, 336, x + 16, 448, 368, "oak_beam1")

    L.add("item_spikes", (700, -400, 0))
    L.add("item_health", (1200, 380, 0))
    L.add("item_shells", (1250, -100, -128))
    L.add("item_armor1", (1580, 380, 0))
    L.add("monster_ashen", (800, 200, -104), angle=180)
    L.add("monster_ashen", (900, -200, -104), angle=180)
    L.add("monster_ashen", (1100, 150, -104), angle=180)
    L.add("monster_gauger", (1300, -150, -104), angle=180)
    L.add("monster_clinker", (1000, 0, -104), angle=180, spawnflags=2)
    L.add("monster_clinker", (1200, 120, -104), angle=180, spawnflags=2)
    L.add("monster_censer", (1100, 400, 24), angle=180)
    L.add("monster_gauger", (1350, -400, 24), angle=180)
    L.add("monster_slag_hound", (1500, 0, -104), angle=180)
    L.add("monster_slag_hound", (1550, 100, -104), angle=180)
    L.add("monster_slag_hound", (1550, -100, -104), angle=180)
    L.add("monster_deacon", (1600, 0, -104), angle=180, spawnflags=1)   # waits for you
    for x in (640, 1024, 1408):
        for y in (-200, 200):
            L.solid(x - 8, y - 8, 200, x + 8, y + 8, 232, "lamp_amber1")
            L.solid(x - 2, y - 2, 232, x + 2, y + 2, 336, "iron_plate1")
            L.light((x, y, 176), 320, WARM)
    for x in (512, 1088, 1600):
        for y in (-384, 384):
            L.light((x, y, 96), 220, CANDLE)
    L.light((830, 0, 350), 300, COLD)

    # The core shop, off the north walkway: x 896..1344, floor 0.
    L.opening(960, 448, 0, 1088, 480, 128)
    L.room(896, 480, 0, 1344, 832, 224, wall="plaster1", floor="oak1", ceiling="ceil_timber1")
    for y in (576, 672):                                           # benches of cores drying
        L.solid(928, y, 0, 1120, y + 32, 40, "oak1")
        for x in range(944, 1104, 48):
            L.solid(x, y + 4, 40, x + 24, y + 28, 64, "sand_mould1")
    L.solid(1152, 704, 0, 1344, 832, 112, "oak1")                   # the mezzanine
    L.steps(1152, 576, 1216, 704, 0, 112, axis="y", tex="oak1")
    L.add("item_key2", (1280, 768, 136))                             # keys stand on their middle
    L.add("weapon_supershotgun", (1250, 540, 0))
    L.add("item_spikes", (940, 780, 0))
    L.add("monster_ashen", (1000, 620, 24), angle=270)
    L.add("monster_ashen", (1060, 720, 24), angle=270)
    L.add("monster_gauger", (1280, 560, 24), angle=180)
    L.add("monster_censer", (1300, 780, 136), angle=270)
    for x in (1000, 1200):
        L.solid(x - 8, 632, 176, x + 8, 648, 208, "lamp_amber1")
        L.light((x, 640, 150), 280, WARM)
    L.light((1250, 700, 190), 200, CANDLE)
    L.light((1280, 768, 160), 140, (0.85, 0.85, 1.0))

    # The gold door at the east end of the floor, and the drying ovens.
    L.opening(1664, -64, -128, 1696, 64, 0)
    L.brush_entity("func_door", [Box(1664, -64, -128, 1696, 64, 0, "door_iron1")],
                   angle=-1, spawnflags=8, speed=80, wait=-1, lip=8)
    L.room(1696, -256, -128, 2304, 256, 256, wall="firebrick1", floor="ash_floor1", ceiling="kirk_brick2")
    for x in (1792, 1984, 2176):                                   # the ovens: glowing mouths in the walls
        for y0, y1 in ((-288, -256), (256, 288)):
            L.opening(x, y0, -128, x + 96, y1, -32)
            back = (y0 - 32, y0) if y0 < 0 else (y1, y1 + 32)
            L.solid(x, back[0], -128, x + 96, back[1], -32, "kirk_vbrick1")
            L.light((x + 48, (y0 + y1) / 2, -80), 160, SLAG)
    L.add("monster_deacon", (2200, 0, -104), angle=180)
    L.add("monster_censer", (2250, -180, -104), angle=180)
    L.add("monster_censer", (2250, 180, -104), angle=180)
    L.add("monster_slag_hound", (2000, -120, -104), angle=180)
    L.add("monster_slag_hound", (2000, 120, -104), angle=180)
    L.add("item_rockets", (1750, 200, -128))
    L.add("item_health", (1750, -220, -128))
    L.light((1850, 0, 160), 300, WARM)
    L.light((2150, 0, 160), 300, WARM)
    # The vent, and the ledge it throws you up to (secret).
    L.solid(2208, 96, -128, 2272, 160, -124, "vent_grate1")
    L.brush_entity("trigger_vent", [Box(2212, 100, -124, 2268, 156, -92, "trigger")], speed=640)
    L.solid(2112, 176, 176, 2304, 256, 192, "iron_plate1")
    L.brush_entity("trigger_secret", [Box(2112, 176, 192, 2304, 256, 248, "trigger")])
    L.add("item_health", (2200, 216, 192), spawnflags=2)
    L.add("item_rockets", (2150, 216, 192))
    L.light((2200, 216, 240), 120, COLD)

    # The cage down to the furnaces.
    L.opening(2304, -64, -128, 2336, 64, 0)
    L.room(2336, -96, -128, 2464, 96, 64, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((2400, 0, 32), 160, WARM)
    L.brush_entity("trigger_changelevel", [Box(2368, -64, -128, 2448, 64, -32, "trigger")], map="foundry3")
    L.add("info_intermission", (700, -380, 160), mangle=(20, 20, 0))
    L.nook(1552, 448, 0, "n", ('item_armor1', 'item_shells'), wall="kirk_stone1", floor="coal1")   # a secret behind cracked stone
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "foundry2.map")
    build().save(out)
    print(out)
