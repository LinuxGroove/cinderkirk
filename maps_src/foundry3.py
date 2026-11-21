#!/usr/bin/env python3
"""The Furnace Row (foundry3.map), the Foundry shaft's third map.

Three cupola furnaces stand along the north side of the tapping floor, each
running slag south down a channel cut across it. A lift climbs to the
charging deck behind them, where coal waits in heaps and the silver key sits
by the furnace master's desk; the coal store at the deck's west end has a
cracked wall, and behind it the way down to the Ash Pit (the secret map).
The silver door at the floor's east end opens on the tapping yard and the
cage down to the bell pit.

    python3 maps_src/foundry3.py maps_src/foundry3.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

WARM = (1.0, 0.62, 0.32)
SLAG = (1.0, 0.42, 0.12)
COLD = (0.62, 0.72, 1.0)
CANDLE = (1.0, 0.8, 0.55)
FURNACES = (448, 800, 1152)


def build():
    L = Level(wad="cinder.wad", sounds=4, message="The Furnace Row", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    # The cage's landing, at the west end.
    L.room(0, -96, 0, 128, 96, 192, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (48, 0, 24), angle=0)
    L.add("info_player_coop", (48, 48, 24), angle=0)
    L.add("info_player_coop", (48, -48, 24), angle=0)
    L.light((64, 0, 160), 180, WARM)
    L.opening(128, -64, 0, 160, 64, 128)

    # The tapping floor: x 160..1440, y -384..384, floor 0, roof 448.
    L.room(160, -384, 0, 1440, 384, 448, wall="firebrick1", floor="floor_flag1",
           ceiling="ceil_timber1", floor_depth=96)
    for x in FURNACES:
        L.solid(x, 160, 0, x + 192, 288, 448, "firebrick1")                    # the furnace's stack
        L.solid(x + 64, 144, 0, x + 128, 160, 64, "kirk_vbrick1")               # its tap hole, glowing
        L.opening(x + 72, -320, -64, x + 120, 160, 0)                           # the channel south
        L.liquid(x + 72, -320, -64, x + 120, 160, -24)
        L.solid(x + 56, -64, -8, x + 136, 64, 0, "iron_grid1")                  # a grating over it
        L.add("light", (x + 96, 0, -40), light=180, _color=SLAG)
        L.light((x + 96, 120, 80), 120, SLAG)
    L.solid(160, -384, 0, 1440, -352, 48, "kirk_brick2")
    for x in (288, 640, 992, 1344):
        L.light((x, -200, 300), 300, CANDLE)
        L.light((x, -280, 120), 180, COLD)
    L.add("item_shells", (240, -300, 0))
    L.add("item_spikes", (620, -300, 0))
    L.add("item_health", (980, -320, 0))
    L.add("item_rockets", (1380, -300, 0))
    L.add("monster_ashen", (400, -200, 24), angle=180)
    L.add("monster_ashen", (700, -120, 24), angle=180)
    L.add("monster_gauger", (1000, -220, 24), angle=180)
    L.add("monster_clinker", (700, -200, 24), angle=180, spawnflags=2)
    L.add("monster_clinker", (1100, -120, 24), angle=180, spawnflags=2)
    L.add("monster_censer", (1300, -100, 24), angle=180)
    L.add("monster_slag_hound", (1250, -250, 24), angle=180)
    L.add("monster_slag_hound", (1300, 60, 24), angle=180)

    # The lift up to the charging deck, between the second and third furnace.
    L.brush_entity("func_plat", [Box(1008, 64, 240, 1136, 160, 256, "iron_plate1")], height=256, speed=150)
    L.brush_entity("trigger_once", [Box(992, 32, 0, 1152, 160, 96, "trigger")],
                   message="The lift: stand on it to ride up to the charging deck")
    L.light((1072, 112, 300), 200, WARM)

    # The charging deck behind the furnaces: z 256, y 160..384, back over the stacks.
    L.solid(160, 160, 160, 1440, 384, 256, "kirk_stone1")
    for x in FURNACES:
        L.solid(x + 48, 288, 256, x + 144, 296, 336, "iron_rust1")              # the charging doors
        L.add("light", (x + 96, 320, 300), light=160, _color=SLAG)
    for x in (336, 720, 1280):                                                  # heaps of coal
        L.solid(x, 344, 256, x + 80, 384, 280, "coal1")
        L.solid(x + 16, 360, 280, x + 64, 384, 296, "coal1")
    L.solid(1368, 176, 256, 1432, 240, 296, "oak1")                              # the furnace master's desk
    L.add("item_key1", (1400, 300, 280))
    L.add("item_health", (1200, 330, 256))
    L.add("monster_censer", (600, 336, 280), angle=0)
    L.add("monster_censer", (900, 336, 280), angle=0)
    L.add("monster_deacon", (1390, 330, 280), angle=180)
    for x in (400, 900, 1300):
        L.light((x, 336, 400), 240, WARM)

    # The coal store at the deck's west end, and the cracked wall behind its heap.
    L.opening(160, 192, 256, 192, 320, 384)
    L.room(-96, 160, 256, 128, 384, 400, wall="kirk_stone1", floor="coal1", ceiling="kirk_brick2")
    L.solid(-96, 288, 256, 32, 384, 288, "coal1")
    L.opening(-128, 192, 256, -96, 288, 352)
    L.brush_entity("func_cracked", [Box(-128, 192, 256, -96, 288, 352, "kirk_crack1")])
    L.room(-320, 192, 256, -128, 288, 352, wall="kirk_stone1", floor="ash_floor1")
    L.brush_entity("trigger_secret", [Box(-312, 196, 256, -136, 284, 320, "trigger")])
    L.brush_entity("trigger_changelevel", [Box(-320, 192, 256, -288, 288, 352, "trigger")], map="foundry_s")
    L.add("light", (-224, 240, 300), light=160, _color=SLAG)
    L.add("item_shells", (0, 200, 256))
    L.light((16, 272, 360), 160, CANDLE)

    # The silver door at the east end, and the tapping yard.
    L.opening(1440, -64, 0, 1472, 64, 128)
    L.brush_entity("func_door", [Box(1440, -64, 0, 1472, 64, 128, "door_iron1")],
                   angle=-1, spawnflags=16, speed=80, wait=-1, lip=8)
    L.room(1472, -320, -64, 1984, 320, 320, wall="kirk_brick1", floor="ash_floor1", ceiling="ceil_timber1",
           floor_depth=96)
    L.steps(1472, -64, 1568, 64, 0, -64, base=-64)
    L.solid(1472, -320, -64, 1568, -64, 0, "kirk_stone1")
    L.solid(1472, 64, -64, 1568, 320, 0, "kirk_stone1")
    L.opening(1664, -256, -128, 1888, 256, -64)                                 # a slag pool across the yard
    L.liquid(1664, -256, -128, 1888, 256, -88)
    L.solid(1664, -48, -72, 1888, 48, -64, "iron_grid1")                        # the plank over it
    L.add("light", (1776, 0, -100), light=260, _color=SLAG)
    L.add("monster_deacon", (1920, 200, -40), angle=180)
    L.add("monster_crucible_brute", (1900, -160, -40), angle=180)
    L.add("monster_slag_hound", (1940, 0, -40), angle=180)
    L.add("item_health", (1600, 250, 0))
    L.light((1600, 0, 240), 260, WARM)
    L.light((1900, 0, 240), 260, WARM)
    L.opening(1984, -64, -64, 2016, 64, 64)
    L.room(2016, -96, -64, 2144, 96, 128, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((2080, 0, 96), 160, WARM)
    L.brush_entity("trigger_changelevel", [Box(2048, -64, -64, 2128, 64, 32, "trigger")], map="foundry4")
    L.add("info_intermission", (300, -300, 300), mangle=(25, 30, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "foundry3.map")
    build().save(out)
    print(out)
