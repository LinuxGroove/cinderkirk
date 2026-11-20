#!/usr/bin/env python3
"""The Foundry Gate (start.map): the first level, and the test bed for the
tool chain.

The gatehouse where you come in, steps down to the Casting Floor with a slag
channel across it and an iron bridge, the silver key on a plinth at the far
end, and the key door to the belfry, where the way down to the Foundry opens.

    python3 maps_src/start.py maps_src/start.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Level  # noqa: E402

WARM = (1.0, 0.62, 0.32)
SLAG = (1.0, 0.42, 0.12)
COLD = (0.62, 0.72, 1.0)
CANDLE = (1.0, 0.8, 0.55)


def build():
    L = Level(wad="cinder.wad", message="The Foundry Gate", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    # The gatehouse: x 0..512, floor 0, ceiling 256.
    L.room(0, -256, 0, 512, 256, 256)
    # Pillars 64 wide on the 64 grid, so each glyph stone shows one whole mark.
    for y in (-256, 224):
        for x in (128, 320):
            L.solid(x, y, 0, x + 64, y + 32, 256, "kirk_stone1")
            gy0, gy1 = (y + 32, y + 34) if y < 0 else (y - 2, y)
            L.solid(x, gy0, 64, x + 64, gy1, 128, "kirk_glyph1")
    for x in (64, 192, 320, 448):
        L.solid(x, -256, 208, x + 24, 256, 232, "oak1")
    L.add("info_player_start", (48, 0, 24), angle=0)
    L.add("info_player_deathmatch", (48, 128, 24), angle=0)
    L.add("info_player_deathmatch", (48, -128, 24), angle=0)
    L.add("item_shells", (256, 160, 0))
    L.add("item_health", (256, -192, 0))
    L.add("weapon_supershotgun", (400, 0, 16))
    for x in (160, 416):
        L.light((x, 0, 176), 240, WARM)
    L.light((256, 200, 120), 160, CANDLE)
    L.light((256, -200, 120), 160, CANDLE)

    # The arch down to the Casting Floor.
    L.opening(512, -96, 0, 544, 96, 192)

    # The Casting Floor: x 544..1568, floor -64, ceiling 384.
    L.room(544, -384, -64, 1568, 384, 384, floor_depth=128)
    L.steps(544, -96, 640, 96, 0, -64, base=-64)
    L.solid(544, -384, -64, 640, -96, 0, "kirk_stone1")   # the landing either side
    L.solid(544, 96, -64, 640, 384, 0, "kirk_stone1")
    # The slag channel across the hall, 96 deep, and the bridge over it.
    L.opening(928, -384, -160, 1120, 384, -64)
    L.solid(928, -416, -192, 1120, 416, -160, "kirk_stone1")
    L.liquid(928, -384, -160, 1120, 384, -112)
    L.solid(928, -64, -80, 1120, 64, -64, "iron_plate1")
    for y0 in (-64, 56):
        L.solid(928, y0, -64, 1120, y0 + 8, -24, "iron_plate1")
        for x in (928, 1016, 1104):
            L.solid(x, y0, -64, x + 16, y0 + 8, 0, "bronze1")
    # Pillars with glyph stones, and the tie beams.
    for x in (704, 832, 1216, 1344, 1472):
        for y in (-384, 352):
            L.solid(x, y, -64, x + 64, y + 32, 384, "kirk_stone1")
            gy0, gy1 = (y + 32, y + 34) if y < 0 else (y - 2, y)
            L.solid(x, gy0, 0, x + 64, gy1, 64, "kirk_glyph1")
        L.solid(x + 16, -384, 300, x + 48, 384, 332, "oak1")
    # The plinth at the far end, with the key on it.
    L.solid(1440, -48, -64, 1536, 48, -32, "bronze1")
    L.add("item_key1", (1488, 0, 0))
    L.add("weapon_nailgun", (1360, -256, -48))
    L.add("item_spikes", (1360, 256, -64))
    L.add("item_armor1", (720, 300, -64))
    L.add("item_health", (1200, -300, -64))
    # Who's waiting.
    L.add("monster_army", (800, 120, -40), angle=180)
    L.add("monster_army", (800, -160, -40), angle=180)
    L.add("monster_dog", (1250, 0, -40), angle=180)
    L.add("monster_dog", (1300, 200, -40), angle=180)
    L.add("monster_army", (1450, -250, -40), angle=180)
    L.add("monster_ogre", (1450, 250, -40), angle=180)
    # Light: the slag, braziers along the walls, cold light from high up.
    L.add("light", (1024, 0, -100), light=200, _color=SLAG, _surface="*slag1",
          _surface_offset=12)
    for x in (760, 1260, 1440):
        L.light((x, -300, 64), 260, WARM)
        L.light((x, 300, 64), 260, WARM)
    for x in (700, 1024, 1350):
        L.light((x, 0, 340), 220, COLD, wait=2)
    L.light((1488, 0, 48), 120, (0.85, 0.85, 1.0))
    for x in (960, 1088):
        L.light((x, 0, 40), 180, WARM)

    # The key door to the belfry.
    L.opening(1568, -64, -64, 1600, 64, 64)
    L.brush_entity("func_door", [_box(1568, -64, -64, 1600, 64, 64, "iron_plate1")],
                   angle=-1, spawnflags=16, speed=80, wait=-1, lip=8)

    # The belfry: x 1600..1984, floor -64, tall.
    L.room(1600, -192, -64, 1984, 192, 512)
    for x in (1664, 1856):
        L.solid(x, -192, 400, x + 32, 192, 432, "oak1")
    L.add("monster_knight", (1760, 96, -40), angle=180)
    L.add("monster_knight", (1760, -96, -40), angle=180)
    L.add("item_health", (1900, 120, -64))
    L.light((1792, 0, 320), 320, WARM)
    L.light((1920, 0, 32), 200, SLAG)
    L.brush_entity("trigger_changelevel", [_box(1920, -64, -64, 1984, 64, 64, "trigger")],
                   map="start")
    L.add("info_intermission", (1024, -300, 160), mangle=(20, 30, 0))
    return L


def _box(*a):
    from mapkit import Box
    return Box(*a)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "start.map")
    build().save(out)
    print(out)
